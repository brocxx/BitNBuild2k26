"""Compatibility analysis and candidate selection.

A listing becomes a candidate only when every check passes. Anything unknown
produces a reason code, never an assumed pass - in particular, contamination
notes that are not covered by a reviewed compatibility flag yield
QUALITY_REVIEW_REQUIRED even when moisture is within limits.

Asking price is deliberately not a filter. A listing above the buyer's budget
still qualifies, because the seller may concede during negotiation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import schemas
from app.config import get_settings
from app.db import models
from app.services.costing import compute_costs
from app.services.serializers import to_listing, to_transport_option

MATERIAL_MISMATCH = "MATERIAL_MISMATCH"
PROCESS_UNCONFIRMED = "PROCESS_UNCONFIRMED"
QUALITY_MISMATCH = "QUALITY_MISMATCH"
QUALITY_REVIEW_REQUIRED = "QUALITY_REVIEW_REQUIRED"
INSUFFICIENT_QUANTITY = "INSUFFICIENT_QUANTITY"
TIME_WINDOW_MISMATCH = "TIME_WINDOW_MISMATCH"
NO_TRANSPORT_OPTION = "NO_TRANSPORT_OPTION"


def _aware(value: datetime) -> datetime:
    """SQLite hands back naive datetimes; treat stored times as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@dataclass
class CandidateEvaluation:
    listing: models.Listing
    reason_codes: list[str] = field(default_factory=list)
    usable_transport: list[models.TransportOption] = field(default_factory=list)
    pathway_use: str = ""

    @property
    def is_eligible(self) -> bool:
        return not self.reason_codes


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def assess_contamination(
    db: Session, notes: str, material_id: str, process_id: str
) -> tuple[str, str]:
    """Return (verdict, note) from the reviewed compatibility table.

    Verdicts: accept | review | reject. An uncovered keyword is 'review'.
    """
    flags = list(
        db.scalars(
            select(models.MaterialCompatibilityFlag).where(
                models.MaterialCompatibilityFlag.material_id == material_id,
                models.MaterialCompatibilityFlag.receiving_process_id == process_id,
            )
        )
    )
    cleaned = (notes or "").strip().lower()

    if not cleaned:
        baseline = next((f for f in flags if not f.contamination_keyword), None)
        if baseline:
            return baseline.verdict, baseline.note
        return "review", "No reviewed compatibility baseline for this material and process."

    matched = [f for f in flags if f.contamination_keyword and f.contamination_keyword in cleaned]
    if not matched:
        return (
            "review",
            "Contamination notes are not covered by a reviewed compatibility flag.",
        )
    # Strictest verdict wins.
    for verdict in ("reject", "review", "accept"):
        hit = next((f for f in matched if f.verdict == verdict), None)
        if hit:
            return hit.verdict, hit.note
    return "review", ""


def windows_feasible(listing: models.Listing, requirement: models.Requirement) -> bool:
    """Material must be collectable in time to meet the delivery deadline."""
    return _aware(listing.pickup_start) <= _aware(requirement.delivery_end)


def usable_transport_options(
    options: list[models.TransportOption],
    listing: models.Listing,
    requirement: models.Requirement,
    now: datetime,
) -> list[models.TransportOption]:
    """Options that can actually carry this shipment on this schedule."""
    usable = []
    for option in options:
        if _aware(option.expires_at) <= now:
            continue
        if option.capacity_kg < requirement.quantity_kg:
            continue
        pickup_at = _aware(option.pickup_at)
        delivery_at = _aware(option.delivery_at)
        if not (_aware(listing.pickup_start) <= pickup_at <= _aware(listing.pickup_end)):
            continue
        if not (
            _aware(requirement.delivery_start)
            <= delivery_at
            <= _aware(requirement.delivery_end)
        ):
            continue
        if pickup_at >= delivery_at:
            continue
        usable.append(option)

    # Cheapest first, then earliest delivery, then ID for a deterministic tie.
    usable.sort(key=lambda o: (o.freight_paise, _aware(o.delivery_at), o.id))
    return usable


def pathway_use(db: Session, material_id: str, process_id: str) -> str:
    pathway = db.scalar(
        select(models.SymbiosisPathway).where(
            models.SymbiosisPathway.material_id == material_id,
            models.SymbiosisPathway.receiving_process_id == process_id,
        )
    )
    return pathway.use_case if pathway else ""


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_listing(
    db: Session,
    listing: models.Listing,
    requirement: models.Requirement,
    options: list[models.TransportOption],
    now: datetime,
) -> CandidateEvaluation:
    evaluation = CandidateEvaluation(listing=listing)

    if listing.material_id != requirement.material_id:
        evaluation.reason_codes.append(MATERIAL_MISMATCH)

    buyer_processes = {
        link.process_id for link in requirement.buyer.receiving_processes if link.confirmed
    }
    use_case = pathway_use(db, listing.material_id, requirement.receiving_process_id)
    if requirement.receiving_process_id not in buyer_processes or not use_case:
        evaluation.reason_codes.append(PROCESS_UNCONFIRMED)
    evaluation.pathway_use = use_case

    if listing.moisture_pct > requirement.max_moisture_pct:
        evaluation.reason_codes.append(QUALITY_MISMATCH)

    verdict, _note = assess_contamination(
        db, listing.contamination_notes, listing.material_id, requirement.receiving_process_id
    )
    if verdict == "reject":
        evaluation.reason_codes.append(QUALITY_MISMATCH)
    elif verdict == "review":
        evaluation.reason_codes.append(QUALITY_REVIEW_REQUIRED)

    if listing.available_quantity_kg < requirement.quantity_kg:
        evaluation.reason_codes.append(INSUFFICIENT_QUANTITY)

    if not windows_feasible(listing, requirement):
        evaluation.reason_codes.append(TIME_WINDOW_MISMATCH)

    evaluation.usable_transport = usable_transport_options(options, listing, requirement, now)
    if not evaluation.usable_transport:
        evaluation.reason_codes.append(NO_TRANSPORT_OPTION)

    return evaluation


def evaluate_requirement(
    db: Session, requirement: models.Requirement, now: datetime | None = None
) -> list[CandidateEvaluation]:
    """Evaluate every open listing of the requested material."""
    now = now or datetime.now(timezone.utc)

    listings = list(
        db.scalars(
            select(models.Listing).where(
                models.Listing.material_id == requirement.material_id,
                models.Listing.status == "open",
                models.Listing.seller_business_id != requirement.buyer_business_id,
            )
        )
    )

    options_by_listing: dict[str, list[models.TransportOption]] = {}
    if listings:
        rows = db.scalars(
            select(models.TransportOption).where(
                models.TransportOption.requirement_id == requirement.id,
                models.TransportOption.listing_id.in_([listing.id for listing in listings]),
            )
        )
        for option in rows:
            options_by_listing.setdefault(option.listing_id, []).append(option)

    return [
        evaluate_listing(
            db, listing, requirement, options_by_listing.get(listing.id, []), now
        )
        for listing in listings
    ]


def build_matches_response(
    db: Session, requirement: models.Requirement, now: datetime | None = None
) -> schemas.MatchesResponse:
    settings = get_settings()
    evaluations = evaluate_requirement(db, requirement, now)

    candidates: list[schemas.MatchCandidate] = []
    excluded: list[schemas.ExcludedListing] = []
    missing_transport: list[str] = []

    for evaluation in evaluations:
        if NO_TRANSPORT_OPTION in evaluation.reason_codes:
            missing_transport.append(evaluation.listing.id)

        if not evaluation.is_eligible:
            excluded.append(
                schemas.ExcludedListing(
                    listing_id=evaluation.listing.id,
                    reason_codes=evaluation.reason_codes,
                )
            )
            continue

        shown = evaluation.usable_transport[: settings.max_transport_options_per_listing]
        best = shown[0]
        candidates.append(
            schemas.MatchCandidate(
                listing=to_listing(evaluation.listing),
                pathway_use=evaluation.pathway_use,
                transport_options=[to_transport_option(option) for option in shown],
                initial_best_cost=compute_costs(
                    evaluation.listing.asking_price_paise_per_tonne,
                    requirement.quantity_kg,
                    best.freight_paise,
                ),
            )
        )

    # Same ordering the broker uses: delivered cost, then earlier delivery, then ID.
    candidates.sort(
        key=lambda c: (
            c.initial_best_cost.buyer_total_paise,
            c.transport_options[0].delivery_at,
            c.listing.id,
        )
    )

    return schemas.MatchesResponse(
        requirement_id=requirement.id,
        candidates=candidates,
        excluded=excluded,
        missing_transport_listing_ids=missing_transport,
    )
