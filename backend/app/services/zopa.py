"""Game-theoretic negotiation math engine.

Three responsibilities:

1. ZOPA (Zone of Possible Agreement)
   Does a deal exist at all?  The overlap between what the seller will accept
   (floor) and what the buyer can afford (max unit price after freight) is the
   ZOPA.  If it is empty, no LLM rounds are needed.

2. Concession curves
   Two strategies, both deterministic given round_number / max_rounds:

   Conceder  - linear walk from start toward limit over the round budget.
               Maximises the chance of agreement; accepts lower margin.

   Boulware  - holds close to the opening position for most rounds, then drops
               sharply at the deadline.  Maximises margin if the deal closes;
               risks no-deal.  Named after Lemuel Boulware (GE, 1948).

   The curve returns the recommended price for the current round.  Agents
   receive this as a pre-computed hint so they can apply the strategy without
   having to reason about arithmetic from scratch.  The coordinator still
   validates every offer against hard limits regardless of what the agent says.

3. BATNA (Best Alternative to a Negotiated Agreement)
   If multiple sellers are in the candidate list, the buyer agent knows the
   best competing quote.  This is passed as a fact in the brief so the buyer
   can reference it as leverage without the agent having to invent a number.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# ZOPA
# ---------------------------------------------------------------------------


@dataclass
class ZOPAResult:
    """Whether a deal is theoretically possible given the two private limits."""

    exists: bool
    # Overlap between seller floor and buyer ceiling, in paise/tonne.
    # Positive = room to negotiate.  Zero or negative = no deal is possible.
    overlap_paise_per_tonne: int
    seller_floor_paise_per_tonne: int
    buyer_ceiling_paise_per_tonne: int


def compute_zopa(
    seller_floor_paise_per_tonne: int,
    buyer_ceiling_paise_per_tonne: int,
) -> ZOPAResult:
    """Check whether the ZOPA is non-empty.

    The buyer ceiling is the maximum unit price the buyer can pay after
    subtracting the fixed freight charge from the budget.  It is pre-computed
    by costing.max_unit_price_within_budget before this is called.
    """
    overlap = buyer_ceiling_paise_per_tonne - seller_floor_paise_per_tonne
    return ZOPAResult(
        exists=overlap >= 0,
        overlap_paise_per_tonne=overlap,
        seller_floor_paise_per_tonne=seller_floor_paise_per_tonne,
        buyer_ceiling_paise_per_tonne=buyer_ceiling_paise_per_tonne,
    )


# ---------------------------------------------------------------------------
# Concession curves
# ---------------------------------------------------------------------------


def concession_target(
    strategy: str,
    round_number: int,
    max_rounds: int,
    start: int,
    limit: int,
    max_share: float = 0.80,
) -> int:
    """Return the recommended price for this round.

    Args:
        strategy:     "conceder" or "boulware"
        round_number: 0-indexed current round
        max_rounds:   total rounds available
        start:        starting price (asking price for seller, opening bid for buyer)
        limit:        hard limit (floor for seller, ceiling for buyer)
        max_share:    maximum fraction of the gap conceded by the final round (default 0.80)

    Returns:
        Recommended price in paise/tonne for this round.
    """
    if max_rounds <= 1:
        gap = limit - start
        return int(round(start + gap * max_share))

    # progress in [0.0, 1.0] where 1.0 = final round
    t = min(1.0, max(0.0, round_number / (max_rounds - 1)))

    if strategy == "boulware":
        # Boulware: concede (t^4) of the concession budget -- barely moves early,
        # drops sharply in the last round.
        concession_fraction = (t ** 4) * max_share
    else:
        # Conceder (default): linear walk across the concession budget.
        concession_fraction = t * max_share

    gap = limit - start  # negative for seller (floor < asking), positive for buyer
    recommended = start + gap * concession_fraction
    return int(round(recommended))



# ---------------------------------------------------------------------------
# BATNA
# ---------------------------------------------------------------------------


@dataclass
class BATNAResult:
    """The buyer's best outside option among competing sellers."""

    exists: bool
    # Best (lowest) unit price offered by any other candidate seller.
    best_competitor_asking_paise_per_tonne: int | None
    best_competitor_district: str | None
    best_competitor_listing_id: str | None


def extract_batna(
    current_listing_id: str,
    candidates: list[tuple[str, int, str]],
) -> BATNAResult:
    """Find the best alternative among other candidate sellers.

    The BATNA is the asking price of the cheapest non-current seller.
    Passed to the buyer agent so it can say:
    'Seller B in Davangere quoted X/t -- can you beat it?'

    Args:
        current_listing_id: The listing currently being negotiated.
        candidates: list of (listing_id, asking_price_paise_per_tonne, district)

    Returns:
        BATNAResult with the cheapest alternative listing's details, or
        BATNAResult(exists=False) if there is no other candidate.
    """
    others = [
        (lid, price, district)
        for lid, price, district in candidates
        if lid != current_listing_id
    ]
    if not others:
        return BATNAResult(
            exists=False,
            best_competitor_asking_paise_per_tonne=None,
            best_competitor_district=None,
            best_competitor_listing_id=None,
        )

    best = min(others, key=lambda x: x[1])
    return BATNAResult(
        exists=True,
        best_competitor_asking_paise_per_tonne=best[1],
        best_competitor_district=best[2],
        best_competitor_listing_id=best[0],
    )
