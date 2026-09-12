"""Delivered-cost arithmetic.

One place, used by matching, the coordinator, and deal creation, so a number
shown on the Matches screen is computed by exactly the same code that later
commits the deal. Agents never compute authoritative totals.

    material_paise        = round_half_up(unit_price_paise_per_tonne * quantity_kg / 1000)
    buyer_total_paise     = material_paise + freight_paise
    seller_receives_paise = material_paise

Python's round() is banker's rounding, and float division would drift on large
paise values, so this uses Decimal with ROUND_HALF_UP throughout.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.api.schemas import Costs

KG_PER_TONNE = Decimal(1000)


def round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def material_paise(unit_price_paise_per_tonne: int, quantity_kg: int) -> int:
    if unit_price_paise_per_tonne < 0 or quantity_kg < 0:
        raise ValueError("price and quantity must be non-negative")
    return round_half_up(
        Decimal(unit_price_paise_per_tonne) * Decimal(quantity_kg) / KG_PER_TONNE
    )


def compute_costs(
    unit_price_paise_per_tonne: int, quantity_kg: int, freight_paise: int
) -> Costs:
    if freight_paise < 0:
        raise ValueError("freight must be non-negative")
    material = material_paise(unit_price_paise_per_tonne, quantity_kg)
    return Costs(
        material_paise=material,
        freight_paise=freight_paise,
        buyer_total_paise=material + freight_paise,
        seller_receives_paise=material,
    )


def max_unit_price_within_budget(
    budget_paise: int, freight_paise: int, quantity_kg: int
) -> int:
    """Highest unit price whose delivered total still fits the budget.

    Rounds down, so the resulting total is guaranteed to be <= budget.
    """
    if quantity_kg <= 0:
        return 0
    remaining = budget_paise - freight_paise
    if remaining <= 0:
        return 0
    return int(Decimal(remaining) * KG_PER_TONNE / Decimal(quantity_kg))
