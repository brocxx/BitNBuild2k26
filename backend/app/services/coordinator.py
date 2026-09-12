"""The negotiation coordinator.

Ordinary Python, not a fourth agent. It owns the workflow; the agents only
propose terms and explain them.

    1. re-check each candidate listing against the requirement
    2. broker fixes the transport slot for the candidate
    3. seller and buyer alternate for at most max_rounds rounds
    4. every agent decision is validated before it becomes an offer
    5. provisional acceptances are collected, never reserved
    6. the cheapest delivered acceptance is committed in one transaction
    7. anything else produces an explicit failure code

Provider failure and unusable model output end the run as `failed`. They never
produce an agreement, and they are never replaced with a simulated one.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import (
    AgentContext,
    AgentDecision,
    AgentProvider,
    InvalidModelOutput,
    OfferView,
    ProviderUnavailable,
    TransportView,
)
from app.agents.privacy import scrub_explanation
from app.agents.registry import build_provider
from app.config import Settings, get_settings
from app.db import models
from app.db.session import session_scope
from app.services import matching
from app.services.costing import compute_costs, max_unit_price_within_budget
from app.services.reservations import ReservationFailed, commit_deal
from app.services.zopa import BATNAResult, ZOPAResult, compute_zopa, concession_target, extract_batna

logger = logging.getLogger(__name__)

OFFER_VALIDITY = timedelta(hours=6)
# An agent quoting more than this multiple of the asking price is treated as
# unusable output rather than a negotiating position.
MAX_PRICE_MULTIPLE = 5

BUDGET_NOT_MET = "BUDGET_NOT_MET"
SELLER_DECLINED = "SELLER_DECLINED"
QUOTE_EXPIRED = "QUOTE_EXPIRED"
STALE_STOCK = "STALE_STOCK"
ROUND_LIMIT = "ROUND_LIMIT"
PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
INVALID_MODEL_OUTPUT = "INVALID_MODEL_OUTPUT"
INTERRUPTED = "INTERRUPTED"
# No mathematical overlap between seller floor and buyer ceiling.
ZOPA_IMPOSSIBLE = "ZOPA_IMPOSSIBLE"

# How an exclusion found at negotiation time maps onto a negotiation outcome.
_REASON_TO_FAILURE = {
    matching.INSUFFICIENT_QUANTITY: STALE_STOCK,
    matching.NO_TRANSPORT_OPTION: QUOTE_EXPIRED,
}


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class NegotiationAborted(Exception):
    """Terminal execution error: the run ends as `failed`."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class CandidateOutcome:
    listing_id: str
    accepted_offer: models.Offer | None
    failure_code: str | None
    intended_use: str


class Coordinator:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        provider: AgentProvider | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self._provider = provider

    @property
    def provider(self) -> AgentProvider:
        if self._provider is None:
            try:
                self._provider = build_provider(self.settings)
            except ProviderUnavailable as exc:
                raise NegotiationAborted(PROVIDER_UNAVAILABLE, str(exc)) from exc
        return self._provider

    # -- event log ---------------------------------------------------------

    def emit(
        self,
        negotiation: models.Negotiation,
        type_: str,
        actor: str,
        message: str,
        offer_id: str | None = None,
        listing_id: str | None = None,
    ) -> None:
        negotiation.last_seq += 1
        self.db.add(
            models.NegotiationEvent(
                negotiation_id=negotiation.id,
                seq=negotiation.last_seq,
                type=type_,
                actor=actor,
                message=message,
                offer_id=offer_id,
                listing_id=listing_id,
            )
        )
        # Commit, not flush. The negotiation timeline is what the UI polls
        # every two seconds, and a flush is invisible to other connections
        # until the transaction ends. With the instant local negotiator nobody
        # would notice; with Gemini a run takes tens of seconds, and the whole
        # timeline would appear in one jump at the end instead of filling in
        # live. The event log is append-only, so committing progressively is
        # safe: the reservation is a separate atomic step at the end, and a
        # crash mid-run leaves status=running for startup recovery to close.
        self.db.commit()

    # -- main entry point --------------------------------------------------

    def run(self, negotiation_id: str) -> None:
        negotiation = self.db.get(models.Negotiation, negotiation_id)
        if negotiation is None or negotiation.status not in ("queued", "running"):
            return

        requirement = self.db.get(models.Requirement, negotiation.requirement_id)
        if requirement is None:
            self._fail(negotiation, STALE_STOCK, "The requirement no longer exists.")
            return

        negotiation.status = "running"
        negotiation.agent_mode = self.settings.agent_mode
        mode_note = (
            "Simulated negotiator (AGENT_MODE=fake)."
            if self.settings.agent_mode == "fake"
            else "Gemini agents."
        )
        self.emit(
            negotiation,
            "started",
            "system",
            f"Negotiation started for {requirement.quantity_kg} kg of "
            f"{requirement.material_id}. {mode_note}",
        )
        self.db.flush()

        candidates = list(
            self.db.scalars(
                select(models.NegotiationCandidate)
                .where(models.NegotiationCandidate.negotiation_id == negotiation.id)
                .order_by(models.NegotiationCandidate.order_index)
            )
        )

        outcomes: list[CandidateOutcome] = []
        try:
            for candidate in candidates:
                outcomes.append(self._run_candidate(negotiation, requirement, candidate))
                self.db.flush()
        except NegotiationAborted as exc:
            self._fail(negotiation, exc.code, exc.message)
            return

        self._settle(negotiation, requirement, outcomes)

    # -- one candidate -----------------------------------------------------

    def _run_candidate(
        self,
        negotiation: models.Negotiation,
        requirement: models.Requirement,
        candidate: models.NegotiationCandidate,
    ) -> CandidateOutcome:
        now = datetime.now(timezone.utc)
        listing = self.db.get(models.Listing, candidate.listing_id)
        if listing is None:
            return self._reject_candidate(
                negotiation, candidate, STALE_STOCK, "Listing no longer exists.", ""
            )

        options = list(
            self.db.scalars(
                select(models.TransportOption).where(
                    models.TransportOption.listing_id == listing.id,
                    models.TransportOption.requirement_id == requirement.id,
                )
            )
        )
        evaluation = matching.evaluate_listing(self.db, listing, requirement, options, now)

        if not evaluation.is_eligible:
            reason = evaluation.reason_codes[0]
            failure = _REASON_TO_FAILURE.get(reason, STALE_STOCK)
            return self._reject_candidate(
                negotiation,
                candidate,
                failure,
                f"Listing is no longer eligible: {', '.join(evaluation.reason_codes)}.",
                evaluation.pathway_use,
            )

        negotiation.current_listing_id = listing.id

        # ------------------------------------------------------------------
        # Pre-compute game-theory context before any LLM calls.
        # ------------------------------------------------------------------

        # Determine strategy: the seller's setting drives their agent;
        # the buyer's setting drives their agent.
        seller_strategy = listing.negotiation_strategy
        buyer_strategy = requirement.negotiation_strategy

        # BATNA: build the candidate list for extract_batna.
        all_candidates = list(
            self.db.scalars(
                select(models.NegotiationCandidate)
                .where(models.NegotiationCandidate.negotiation_id == negotiation.id)
                .order_by(models.NegotiationCandidate.order_index)
            )
        )
        # Load asking prices and districts for all candidates so extract_batna
        # can find the cheapest alternative.
        candidate_tuples: list[tuple[str, int, str]] = []
        for c in all_candidates:
            c_listing = self.db.get(models.Listing, c.listing_id)
            if c_listing is not None:
                candidate_tuples.append(
                    (c_listing.id, c_listing.asking_price_paise_per_tonne, c_listing.district)
                )
        batna = extract_batna(listing.id, candidate_tuples)

        # ZOPA: use the first usable transport's freight to compute buyer ceiling.
        # (transport var is bound later; use evaluation directly here.)
        _zopa_transport = evaluation.usable_transport[0]
        buyer_ceiling = max_unit_price_within_budget(
            requirement.buyer_max_total_paise,
            _zopa_transport.freight_paise,
            requirement.quantity_kg,
        )
        zopa = compute_zopa(
            seller_floor_paise_per_tonne=listing.seller_floor_paise_per_tonne,
            buyer_ceiling_paise_per_tonne=buyer_ceiling,
        )

        # Emit ZOPA result as a system event so the UI can show it without leaking private limits.
        if zopa.exists:
            self.emit(
                negotiation,
                "started",
                "system",
                "ZOPA verified: feasible negotiation zone exists. "
                f"Strategies: seller {seller_strategy}, buyer {buyer_strategy}.",
                listing_id=listing.id,
            )
        else:
            # No overlap — skip all LLM calls and fail immediately.
            self.emit(
                negotiation,
                "candidate_rejected",
                "system",
                "ZOPA impossible: seller floor exceeds buyer budget ceiling. "
                "No price exists that satisfies both parties. Skipping rounds.",
                listing_id=listing.id,
            )
            return self._reject_candidate(
                negotiation,
                candidate,
                BUDGET_NOT_MET,
                "No price satisfies both the seller floor and buyer budget on this route.",
                evaluation.pathway_use,
            )

        # ------------------------------------------------------------------

        transport = evaluation.usable_transport[0]
        transport_view = TransportView(
            transport_option_id=transport.id,
            label=transport.label,
            freight_paise=transport.freight_paise,
            pickup_at=_aware(transport.pickup_at).isoformat(),
            delivery_at=_aware(transport.delivery_at).isoformat(),
            source=transport.source,
        )
        allowed_option_ids = {option.id for option in evaluation.usable_transport}

        # The broker fixes the route before any price is discussed. It selects
        # from quoted options only and cannot alter the freight charge.
        broker_context = self._context(
            "broker", negotiation, requirement, listing, transport_view, evaluation, 0, []
        )
        broker_decision = self._ask("broker", broker_context, allowed_option_ids, listing)
        self.emit(
            negotiation,
            "offer",
            "broker",
            scrub_explanation(broker_decision.explanation, []),
            listing_id=listing.id,
        )

        history: list[OfferView] = []
        offers: list[models.Offer] = []
        # Cheapest delivered total the seller was ever willing to quote. If the
        # rounds run out, this is what decides whether the honest reason is
        # "the buyer could not afford it" or simply "they ran out of rounds".
        best_seller_total: int | None = None

        for round_number in range(negotiation.max_rounds):
            candidate.rounds_used = round_number + 1
            negotiation.round = round_number + 1

            for role in ("seller", "buyer"):
                context = self._context(
                    role,
                    negotiation,
                    requirement,
                    listing,
                    transport_view,
                    evaluation,
                    round_number,
                    history,
                    seller_strategy=seller_strategy,
                    buyer_strategy=buyer_strategy,
                    zopa=zopa,
                    batna=batna,
                )
                decision = self._ask(role, context, allowed_option_ids, listing)

                standing = self._standing_offer(offers, opponent_of=role)

                if decision.action == "accept":
                    if standing is None or (
                        decision.responds_to_offer_id
                        and decision.responds_to_offer_id != standing.id
                    ):
                        raise NegotiationAborted(
                            INVALID_MODEL_OUTPUT,
                            f"{role} agent accepted an offer that is not the standing one.",
                        )
                    accept_offer = self._persist_offer(
                        negotiation,
                        listing,
                        transport,
                        requirement,
                        role,
                        "accept",
                        standing.unit_price_paise_per_tonne,
                        standing.id,
                        decision.explanation,
                        context.private_values,
                        round_number,
                    )
                    verdict = self._check_mutual_terms(
                        listing, requirement, accept_offer
                    )
                    if verdict is None:
                        candidate.status = "accepted_provisional"
                        candidate.best_offer_id = accept_offer.id
                        self.emit(
                            negotiation,
                            "offer",
                            role,
                            f"{role.capitalize()} accepted at "
                            f"{accept_offer.unit_price_paise_per_tonne} paise/tonne; "
                            f"delivered {accept_offer.buyer_total_paise} paise.",
                            offer_id=accept_offer.id,
                            listing_id=listing.id,
                        )
                        return CandidateOutcome(
                            listing_id=listing.id,
                            accepted_offer=accept_offer,
                            failure_code=None,
                            intended_use=evaluation.pathway_use,
                        )
                    # An acceptance that violates a limit is not an agreement.
                    return self._reject_candidate(
                        negotiation,
                        candidate,
                        verdict,
                        "Accepted terms failed server validation against the "
                        "participants' own limits.",
                        evaluation.pathway_use,
                    )

                if decision.action == "reject":
                    failure = BUDGET_NOT_MET if role == "buyer" else SELLER_DECLINED
                    return self._reject_candidate(
                        negotiation,
                        candidate,
                        failure,
                        scrub_explanation(decision.explanation, context.private_values)
                        or f"{role} ended the exchange.",
                        evaluation.pathway_use,
                    )

                offer = self._persist_offer(
                    negotiation,
                    listing,
                    transport,
                    requirement,
                    role,
                    decision.action,
                    decision.unit_price_paise_per_tonne,
                    decision.responds_to_offer_id,
                    decision.explanation,
                    context.private_values,
                    round_number,
                )
                offers.append(offer)
                history.append(
                    OfferView(
                        offer_id=offer.id,
                        author=role,
                        action=offer.action,
                        unit_price_paise_per_tonne=offer.unit_price_paise_per_tonne,
                        buyer_total_paise=offer.buyer_total_paise,
                        seller_receives_paise=offer.seller_receives_paise,
                        explanation=offer.explanation,
                    )
                )
                if role == "seller" and (
                    best_seller_total is None or offer.buyer_total_paise < best_seller_total
                ):
                    best_seller_total = offer.buyer_total_paise

                self.emit(
                    negotiation,
                    "offer",
                    role,
                    f"{role.capitalize()} {offer.action} at "
                    f"{offer.unit_price_paise_per_tonne} paise/tonne "
                    f"(delivered {offer.buyer_total_paise} paise).",
                    offer_id=offer.id,
                    listing_id=listing.id,
                )

        priced_out = (
            best_seller_total is not None
            and best_seller_total > requirement.buyer_max_total_paise
        )
        failure = BUDGET_NOT_MET if priced_out else ROUND_LIMIT
        message = (
            "The seller's best delivered price stayed above what the buyer can pay."
            if priced_out
            else f"No agreement after {negotiation.max_rounds} rounds."
        )
        return self._reject_candidate(
            negotiation, candidate, failure, message, evaluation.pathway_use
        )

    # -- agent plumbing ----------------------------------------------------

    def _context(
        self,
        role: str,
        negotiation: models.Negotiation,
        requirement: models.Requirement,
        listing: models.Listing,
        transport: TransportView,
        evaluation: matching.CandidateEvaluation,
        round_number: int,
        history: list[OfferView],
        seller_strategy: str = "conceder",
        buyer_strategy: str = "conceder",
        zopa: ZOPAResult | None = None,
        batna: BATNAResult | None = None,
    ) -> AgentContext:
        strategy = seller_strategy if role == "seller" else buyer_strategy

        # Pre-compute the concession curve target for this role + round.
        if role == "seller" and listing.seller_floor_paise_per_tonne is not None:
            target = concession_target(
                strategy=strategy,
                round_number=round_number,
                max_rounds=negotiation.max_rounds,
                start=listing.asking_price_paise_per_tonne,
                limit=listing.seller_floor_paise_per_tonne,
                max_share=0.80,
            )
        elif role == "buyer" and requirement.buyer_max_total_paise is not None:
            ceiling = max_unit_price_within_budget(
                requirement.buyer_max_total_paise,
                transport.freight_paise,
                requirement.quantity_kg,
            )
            opening = int(ceiling * 0.72)
            target = concession_target(
                strategy=strategy,
                round_number=round_number,
                max_rounds=negotiation.max_rounds,
                start=opening,
                limit=ceiling,
                max_share=0.85,
            )
        else:
            target = None

        return AgentContext(
            role=role,  # type: ignore[arg-type]
            round_number=round_number,
            max_rounds=negotiation.max_rounds,
            listing_id=listing.id,
            material_id=listing.material_id,
            quantity_kg=requirement.quantity_kg,
            asking_price_paise_per_tonne=listing.asking_price_paise_per_tonne,
            transport=transport,
            seller_district=listing.district,
            buyer_district=requirement.district,
            intended_use=evaluation.pathway_use,
            history=list(history),
            seller_floor_paise_per_tonne=(
                listing.seller_floor_paise_per_tonne if role == "seller" else None
            ),
            buyer_max_total_paise=(
                requirement.buyer_max_total_paise if role == "buyer" else None
            ),
            # Game theory fields
            strategy=strategy,
            concession_target_paise_per_tonne=target,
            zopa_exists=zopa.exists if zopa else None,
            batna_price_paise_per_tonne=(
                batna.best_competitor_asking_paise_per_tonne
                if role == "buyer" and batna and batna.exists
                else None
            ),
            batna_district=(
                batna.best_competitor_district
                if role == "buyer" and batna and batna.exists
                else None
            ),
            batna_listing_id=(
                batna.best_competitor_listing_id
                if role == "buyer" and batna and batna.exists
                else None
            ),
        )

    def _ask(
        self,
        role: str,
        context: AgentContext,
        allowed_option_ids: set[str],
        listing: models.Listing,
    ) -> AgentDecision:
        try:
            decision = self.provider.decide(context)
        except ProviderUnavailable as exc:
            raise NegotiationAborted(PROVIDER_UNAVAILABLE, str(exc)) from exc
        except InvalidModelOutput as exc:
            raise NegotiationAborted(INVALID_MODEL_OUTPUT, str(exc)) from exc
        except Exception as exc:  # an SDK that raises something unexpected
            logger.exception("%s agent raised an unexpected error", role)
            raise NegotiationAborted(PROVIDER_UNAVAILABLE, str(exc)) from exc

        if decision.listing_id != listing.id:
            raise NegotiationAborted(
                INVALID_MODEL_OUTPUT, f"{role} agent referenced an unknown listing."
            )
        if decision.transport_option_id not in allowed_option_ids:
            raise NegotiationAborted(
                INVALID_MODEL_OUTPUT, f"{role} agent referenced an unavailable transport option."
            )
        ceiling = listing.asking_price_paise_per_tonne * MAX_PRICE_MULTIPLE
        if decision.unit_price_paise_per_tonne > max(ceiling, 1):
            raise NegotiationAborted(
                INVALID_MODEL_OUTPUT, f"{role} agent returned an out-of-range unit price."
            )
        return decision

    def _persist_offer(
        self,
        negotiation: models.Negotiation,
        listing: models.Listing,
        transport: models.TransportOption,
        requirement: models.Requirement,
        author: str,
        action: str,
        unit_price: int,
        responds_to: str | None,
        explanation: str,
        private_values: list[int],
        round_number: int,
    ) -> models.Offer:
        costs = compute_costs(unit_price, requirement.quantity_kg, transport.freight_paise)
        now = datetime.now(timezone.utc)

        # SHA-256 audit chain: each offer hashes its data + the previous hash.
        # This makes the negotiation history tamper-evident: modifying any
        # past offer breaks every subsequent hash.
        prev_offers = self.db.scalars(
            select(models.Offer)
            .where(models.Offer.negotiation_id == negotiation.id)
            .order_by(models.Offer.created_at.desc())
            .limit(1)
        ).first()
        prev_hash = prev_offers.chain_hash if prev_offers else "GENESIS"

        offer = models.Offer(
            negotiation_id=negotiation.id,
            listing_id=listing.id,
            transport_option_id=transport.id,
            quantity_kg=requirement.quantity_kg,
            unit_price_paise_per_tonne=unit_price,
            material_paise=costs.material_paise,
            freight_paise=costs.freight_paise,
            buyer_total_paise=costs.buyer_total_paise,
            seller_receives_paise=costs.seller_receives_paise,
            pickup_at=transport.pickup_at,
            delivery_at=transport.delivery_at,
            author=author,
            action=action,
            responds_to_offer_id=responds_to,
            explanation=scrub_explanation(explanation, private_values),
            expires_at=now + OFFER_VALIDITY,
            round=round_number,
        )

        # Compute chain hash over deterministic payload.
        chain_payload = json.dumps(
            {
                "negotiation_id": negotiation.id,
                "round": round_number,
                "author": author,
                "action": action,
                "unit_price_paise_per_tonne": unit_price,
                "buyer_total_paise": costs.buyer_total_paise,
                "timestamp_utc": now.isoformat(),
                "prev_hash": prev_hash,
            },
            sort_keys=True,
        )
        offer.chain_hash = hashlib.sha256(chain_payload.encode()).hexdigest()
        self.db.add(offer)
        self.db.flush()
        return offer

    @staticmethod
    def _standing_offer(offers: list[models.Offer], opponent_of: str) -> models.Offer | None:
        opponent = "buyer" if opponent_of == "seller" else "seller"
        for offer in reversed(offers):
            if offer.author == opponent and offer.action in ("propose", "counter"):
                return offer
        return None

    @staticmethod
    def _check_mutual_terms(
        listing: models.Listing, requirement: models.Requirement, offer: models.Offer
    ) -> str | None:
        """Server-side authority check. Returns a failure code, or None if valid."""
        if offer.unit_price_paise_per_tonne < listing.seller_floor_paise_per_tonne:
            return SELLER_DECLINED
        if offer.buyer_total_paise > requirement.buyer_max_total_paise:
            return BUDGET_NOT_MET
        return None

    def _reject_candidate(
        self,
        negotiation: models.Negotiation,
        candidate: models.NegotiationCandidate,
        failure_code: str,
        message: str,
        intended_use: str,
    ) -> CandidateOutcome:
        candidate.status = "rejected"
        candidate.reason_code = failure_code
        self.emit(
            negotiation,
            "candidate_rejected",
            "system",
            message,
            listing_id=candidate.listing_id,
        )
        return CandidateOutcome(
            listing_id=candidate.listing_id,
            accepted_offer=None,
            failure_code=failure_code,
            intended_use=intended_use,
        )

    # -- settlement --------------------------------------------------------

    def _settle(
        self,
        negotiation: models.Negotiation,
        requirement: models.Requirement,
        outcomes: list[CandidateOutcome],
    ) -> None:
        accepted = [o for o in outcomes if o.accepted_offer is not None]

        # Broker ranking: delivered cost, then earlier delivery, then listing ID.
        accepted.sort(
            key=lambda o: (
                o.accepted_offer.buyer_total_paise,  # type: ignore[union-attr]
                _aware(o.accepted_offer.delivery_at),  # type: ignore[union-attr]
                o.listing_id,
            )
        )

        for outcome in accepted:
            offer = outcome.accepted_offer
            assert offer is not None
            try:
                deal = commit_deal(
                    self.db,
                    negotiation=negotiation,
                    offer=offer,
                    intended_use=outcome.intended_use,
                )
            except ReservationFailed as exc:
                self.emit(
                    negotiation,
                    "candidate_rejected",
                    "system",
                    f"Could not commit this candidate: {exc.message}",
                    listing_id=outcome.listing_id,
                )
                continue

            for candidate in self.db.scalars(
                select(models.NegotiationCandidate).where(
                    models.NegotiationCandidate.negotiation_id == negotiation.id
                )
            ):
                if candidate.listing_id == outcome.listing_id:
                    candidate.status = "won"
                elif candidate.status == "accepted_provisional":
                    candidate.status = "superseded"

            negotiation.status = "agreed"
            negotiation.deal_id = deal.id
            negotiation.current_listing_id = outcome.listing_id
            negotiation.failure_code = None
            self.emit(
                negotiation,
                "agreed",
                "system",
                f"Agreement reached. Delivered total {offer.buyer_total_paise} paise for "
                f"{offer.quantity_kg} kg; {offer.quantity_kg} kg reserved against the listing.",
                offer_id=offer.id,
                listing_id=outcome.listing_id,
            )
            self.db.flush()
            return

        failure = self._summarise_failure(outcomes)
        negotiation.status = "no_deal"
        negotiation.failure_code = failure
        self.emit(
            negotiation,
            "no_deal",
            "system",
            f"No feasible agreement across {len(outcomes)} candidate(s): {failure}.",
        )
        self.db.flush()

    @staticmethod
    def _summarise_failure(outcomes: list[CandidateOutcome]) -> str:
        codes = [o.failure_code for o in outcomes if o.failure_code]
        # Most informative first: a budget shortfall explains more than a
        # generic round limit.
        for code in (BUDGET_NOT_MET, SELLER_DECLINED, QUOTE_EXPIRED, STALE_STOCK, ROUND_LIMIT):
            if code in codes:
                return code
        return ROUND_LIMIT

    # -- failure -----------------------------------------------------------

    def _fail(self, negotiation: models.Negotiation, code: str, message: str) -> None:
        negotiation.status = "failed"
        negotiation.failure_code = code
        self.emit(negotiation, "failed", "system", message)
        self.db.flush()


def run_negotiation(negotiation_id: str) -> None:
    """Background-task entry point. Owns its own session."""
    try:
        with session_scope() as db:
            Coordinator(db).run(negotiation_id)
    except Exception:
        logger.exception("Negotiation %s crashed", negotiation_id)
        try:
            with session_scope() as db:
                negotiation = db.get(models.Negotiation, negotiation_id)
                if negotiation and negotiation.status in ("queued", "running"):
                    Coordinator(db)._fail(
                        negotiation, INTERRUPTED, "The negotiation run was interrupted."
                    )
        except Exception:  # pragma: no cover - last resort
            logger.exception("Could not mark negotiation %s failed", negotiation_id)


def recover_interrupted_runs() -> int:
    """Called at startup: no run survives a restart in a pending state."""
    with session_scope() as db:
        stale = list(
            db.scalars(
                select(models.Negotiation).where(
                    models.Negotiation.status.in_(["queued", "running"])
                )
            )
        )
        coordinator = Coordinator(db)
        for negotiation in stale:
            coordinator._fail(
                negotiation,
                INTERRUPTED,
                "The backend restarted while this negotiation was in progress.",
            )
        return len(stale)
