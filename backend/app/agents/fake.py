"""Deterministic local negotiator.

This is not a stand-in for Gemini in the demo - every event it produces is
labelled as a simulated negotiation. It exists so the coordinator, the
reservation path and the whole test suite can be exercised without a network
call or an API quota, and so Build 2 only has to swap the provider.

Concession model, both sides linear over the round budget:

    seller  starts at the asking price and walks down towards its floor
    buyer   starts low and walks up towards the highest unit price its budget
            can still cover at this freight charge

They accept when the opponent's standing price is already on their side of
their own limit. If the seller's floor sits above what the buyer's budget can
reach, they never cross, and the coordinator reports BUDGET_NOT_MET honestly.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.agents.base import AgentContext, AgentDecision
from app.services.costing import compute_costs, max_unit_price_within_budget
from app.services.zopa import concession_target

# Fraction of the gap to its own limit that a side concedes by the final round.
SELLER_TOTAL_CONCESSION = Decimal("0.80")
BUYER_TOTAL_CONCESSION = Decimal("0.85")
# Buyer's opening bid, as a fraction of the price its budget could bear.
BUYER_OPENING_FRACTION = Decimal("0.72")


def _interpolate(start: int, end: int, step: int, total_steps: int, share: Decimal) -> int:
    """Move from `start` towards `end` by `share` of the gap over the rounds."""
    if total_steps <= 1:
        progress = share
    else:
        progress = share * Decimal(min(step, total_steps - 1)) / Decimal(total_steps - 1)
    delta = (Decimal(end) - Decimal(start)) * progress
    return int((Decimal(start) + delta).quantize(Decimal(1), rounding=ROUND_HALF_UP))


class FakeAgentProvider:
    """Deterministic, offline negotiator. Labelled as simulated everywhere."""

    name = "fake"

    def decide(self, context: AgentContext) -> AgentDecision:
        if context.role == "seller":
            return self._seller(context)
        if context.role == "buyer":
            return self._buyer(context)
        return self._broker(context)

    # -- seller ------------------------------------------------------------

    def _seller(self, context: AgentContext) -> AgentDecision:
        floor = context.seller_floor_paise_per_tonne
        assert floor is not None, "seller agent requires its own floor"

        standing = self._last_from(context, "buyer")

        if standing is not None and standing.unit_price_paise_per_tonne >= floor:
            return AgentDecision(
                action="accept",
                listing_id=context.listing_id,
                transport_option_id=context.transport.transport_option_id,
                unit_price_paise_per_tonne=standing.unit_price_paise_per_tonne,
                responds_to_offer_id=standing.offer_id,
                explanation=(
                    "The offered unit price covers our minimum acceptable return on this "
                    f"batch, and the {context.transport.label} slot fits our pickup window."
                ),
            )

        # Use game-theory concession curve (Boulware or Conceder)
        price = concession_target(
            strategy=context.strategy,
            round_number=context.round_number,
            max_rounds=context.max_rounds,
            start=context.asking_price_paise_per_tonne,
            limit=floor,
            max_share=float(SELLER_TOTAL_CONCESSION),
        )
        price = max(price, floor)

        if standing is None:
            return AgentDecision(
                action="propose",
                listing_id=context.listing_id,
                transport_option_id=context.transport.transport_option_id,
                unit_price_paise_per_tonne=price,
                explanation=(
                    f"Opening at our listed price for {context.quantity_kg} kg, collected in "
                    f"the {context.transport.label} slot."
                ),
            )

        return AgentDecision(
            action="counter",
            listing_id=context.listing_id,
            transport_option_id=context.transport.transport_option_id,
            unit_price_paise_per_tonne=price,
            responds_to_offer_id=standing.offer_id,
            explanation=(
                "We can improve on our previous figure given the confirmed quantity, but "
                "not to the level bid."
            ),
        )

    # -- buyer -------------------------------------------------------------

    def _buyer(self, context: AgentContext) -> AgentDecision:
        budget = context.buyer_max_total_paise
        assert budget is not None, "buyer agent requires its own budget"

        ceiling = max_unit_price_within_budget(
            budget, context.transport.freight_paise, context.quantity_kg
        )
        standing = self._last_from(context, "seller")

        if standing is not None:
            total = compute_costs(
                standing.unit_price_paise_per_tonne,
                context.quantity_kg,
                context.transport.freight_paise,
            ).buyer_total_paise
            if total <= budget:
                return AgentDecision(
                    action="accept",
                    listing_id=context.listing_id,
                    transport_option_id=context.transport.transport_option_id,
                    unit_price_paise_per_tonne=standing.unit_price_paise_per_tonne,
                    responds_to_offer_id=standing.offer_id,
                    explanation=(
                        "Delivered cost including freight is within what this input is "
                        f"worth to us for {context.intended_use or 'this process'}."
                    ),
                )

        if ceiling <= 0:
            return AgentDecision(
                action="reject",
                listing_id=context.listing_id,
                transport_option_id=context.transport.transport_option_id,
                unit_price_paise_per_tonne=0,
                responds_to_offer_id=standing.offer_id if standing else None,
                explanation=(
                    "The freight charge alone exceeds what we can pay delivered for this "
                    "quantity, so no unit price makes this route workable."
                ),
            )

        opening = int(
            (Decimal(ceiling) * BUYER_OPENING_FRACTION).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
        )
        # Use game-theory concession curve (Boulware or Conceder)
        price = concession_target(
            strategy=context.strategy,
            round_number=context.round_number,
            max_rounds=context.max_rounds,
            start=opening,
            limit=ceiling,
            max_share=float(BUYER_TOTAL_CONCESSION),
        )
        price = min(price, ceiling)

        if standing is None:
            return AgentDecision(
                action="propose",
                listing_id=context.listing_id,
                transport_option_id=context.transport.transport_option_id,
                unit_price_paise_per_tonne=price,
                explanation=(
                    f"Bidding for {context.quantity_kg} kg delivered into "
                    f"{context.buyer_district}, freight included in our assessment."
                ),
            )

        return AgentDecision(
            action="counter",
            listing_id=context.listing_id,
            transport_option_id=context.transport.transport_option_id,
            unit_price_paise_per_tonne=price,
            responds_to_offer_id=standing.offer_id,
            explanation=(
                "Raising our bid, taking the quoted freight charge on this route into "
                "account."
            ),
        )

    # -- broker ------------------------------------------------------------

    def _broker(self, context: AgentContext) -> AgentDecision:
        """Selects the transport slot; it never invents a carrier discount."""
        return AgentDecision(
            action="propose",
            listing_id=context.listing_id,
            transport_option_id=context.transport.transport_option_id,
            unit_price_paise_per_tonne=context.asking_price_paise_per_tonne,
            explanation=(
                f"Routing {context.seller_district} to {context.buyer_district} on "
                f"{context.transport.label} at the quoted freight charge of "
                f"{context.transport.freight_paise} paise per shipment "
                f"({context.transport.source})."
            ),
        )

    @staticmethod
    def _last_from(context: AgentContext, author: str):
        for offer in reversed(context.history):
            if offer.author == author and offer.action in ("propose", "counter"):
                return offer
        return None
