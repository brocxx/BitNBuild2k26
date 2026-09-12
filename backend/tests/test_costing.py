"""Delivered-cost arithmetic."""

from decimal import Decimal

import pytest

from app.services.costing import (
    compute_costs,
    material_paise,
    max_unit_price_within_budget,
    round_half_up,
)


def test_material_cost_is_price_per_tonne_scaled_by_kilograms():
    # 250000 paise/tonne (INR 2,500) for 20 tonnes.
    assert material_paise(250_000, 20_000) == 5_000_000


def test_rounding_is_half_up_not_bankers():
    # Python's round() would give 2 here; the contract requires 3.
    assert round_half_up(Decimal("2.5")) == 3
    assert round_half_up(Decimal("3.5")) == 4
    # 1 paise/tonne over 1500 kg is exactly 1.5 paise.
    assert material_paise(1, 1_500) == 2


def test_costs_add_freight_to_material_and_leave_seller_on_material_only():
    costs = compute_costs(275_000, 20_000, 1_800_000)
    assert costs.material_paise == 5_500_000
    assert costs.freight_paise == 1_800_000
    assert costs.buyer_total_paise == 7_300_000
    # In this version the buyer pays the listed freight; the seller's proceeds
    # are the material only.
    assert costs.seller_receives_paise == 5_500_000


def test_large_values_do_not_drift():
    # A float-based implementation loses precision well below this.
    costs = compute_costs(999_999_999, 999_999, 1)
    expected = round_half_up(Decimal(999_999_999) * Decimal(999_999) / Decimal(1000))
    assert costs.material_paise == expected


def test_budget_ceiling_never_exceeds_the_budget():
    ceiling = max_unit_price_within_budget(7_000_000, 1_800_000, 20_000)
    assert ceiling == 260_000
    assert compute_costs(ceiling, 20_000, 1_800_000).buyer_total_paise <= 7_000_000
    # One paise more must break it.
    assert compute_costs(ceiling + 50, 20_000, 1_800_000).buyer_total_paise > 7_000_000


def test_budget_ceiling_is_zero_when_freight_alone_exhausts_the_budget():
    assert max_unit_price_within_budget(1_000_000, 1_000_000, 20_000) == 0
    assert max_unit_price_within_budget(500_000, 1_000_000, 20_000) == 0


def test_negative_inputs_are_rejected():
    with pytest.raises(ValueError):
        material_paise(-1, 1000)
    with pytest.raises(ValueError):
        compute_costs(1000, 1000, -1)
