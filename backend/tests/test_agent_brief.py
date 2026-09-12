"""What an agent is told, and what it must never be told.

These run offline. They exist because two things went wrong on the first live
Gemini runs and both were fixed by moving a calculation out of the model:

  - the buyer agent accepted a delivered total above its own budget, having
    mis-derived price x quantity + freight
  - agents justified prices with "current market conditions", which this
    system cannot possibly know

The brief now carries a precomputed ceiling and an explicit "may I accept"
flag, and the prompt forbids market language.
"""

from __future__ import annotations

import json

import pytest

from app.agents.base import AgentContext, OfferView, TransportView
from app.agents.prompts import build_brief, system_instruction

FREIGHT = 1_500_000
QUANTITY_KG = 20_000
BUDGET = 7_000_000
FLOOR = 240_000


def transport() -> TransportView:
    return TransportView(
        transport_option_id="T1",
        label="Standard flatbed",
        freight_paise=FREIGHT,
        pickup_at="2026-09-20T05:00:00+00:00",
        delivery_at="2026-09-22T05:00:00+00:00",
        source="configured_estimate",
    )


def context(role: str, history: list[OfferView] | None = None) -> AgentContext:
    return AgentContext(
        role=role,  # type: ignore[arg-type]
        round_number=0,
        max_rounds=4,
        listing_id="L1",
        material_id="rice_husk",
        quantity_kg=QUANTITY_KG,
        asking_price_paise_per_tonne=275_000,
        transport=transport(),
        seller_district="DAVANGERE",
        buyer_district="BALLARI",
        intended_use="Fuel for brick kiln firing",
        history=history or [],
        seller_floor_paise_per_tonne=FLOOR if role == "seller" else None,
        buyer_max_total_paise=BUDGET if role == "buyer" else None,
    )


def seller_offer(unit_price: int) -> OfferView:
    return OfferView(
        offer_id="O1",
        author="seller",
        action="counter",
        unit_price_paise_per_tonne=unit_price,
        buyer_total_paise=unit_price * QUANTITY_KG // 1000 + FREIGHT,
        seller_receives_paise=unit_price * QUANTITY_KG // 1000,
        explanation="",
    )


def buyer_offer(unit_price: int) -> OfferView:
    return OfferView(
        offer_id="O2",
        author="buyer",
        action="counter",
        unit_price_paise_per_tonne=unit_price,
        buyer_total_paise=unit_price * QUANTITY_KG // 1000 + FREIGHT,
        seller_receives_paise=unit_price * QUANTITY_KG // 1000,
        explanation="",
    )


# ---------------------------------------------------------------------------
# Each side sees only its own limit
# ---------------------------------------------------------------------------


def test_buyer_brief_never_contains_the_seller_floor():
    brief = build_brief(context("buyer", [seller_offer(270_000)]))
    assert str(FLOOR) not in brief
    assert "minimum" not in brief.lower()


def test_seller_brief_never_contains_the_buyer_budget():
    brief = build_brief(context("seller", [buyer_offer(250_000)]))
    assert str(BUDGET) not in brief
    assert "budget" not in brief.lower()


def test_broker_brief_contains_neither_limit():
    brief = build_brief(context("broker"))
    assert str(FLOOR) not in brief
    assert str(BUDGET) not in brief


# ---------------------------------------------------------------------------
# The arithmetic is done for the model, not by it
# ---------------------------------------------------------------------------


def test_buyer_is_given_a_precomputed_price_ceiling():
    brief = json.loads(build_brief(context("buyer")))
    ceiling = brief["highest_unit_price_you_can_pay_paise_per_tonne"]
    # (7,000,000 - 1,500,000) / 20 tonnes
    assert ceiling == 275_000
    # And paying exactly the ceiling must land within budget.
    assert ceiling * QUANTITY_KG // 1000 + FREIGHT <= BUDGET


@pytest.mark.parametrize(
    ("seller_price", "acceptable"),
    [(270_000, True), (275_000, True), (275_050, False), (300_000, False)],
)
def test_buyer_is_told_whether_it_may_accept(seller_price, acceptable):
    brief = json.loads(build_brief(context("buyer", [seller_offer(seller_price)])))
    assert brief["you_may_accept_the_standing_price"] is acceptable
    assert brief["standing_price_from_seller_paise_per_tonne"] == seller_price


@pytest.mark.parametrize(
    ("buyer_price", "acceptable"),
    [(239_999, False), (240_000, True), (260_000, True)],
)
def test_seller_is_told_whether_it_may_accept(buyer_price, acceptable):
    brief = json.loads(build_brief(context("seller", [buyer_offer(buyer_price)])))
    assert brief["you_may_accept_the_standing_bid"] is acceptable


def test_no_acceptance_flag_on_the_opening_move():
    buyer = json.loads(build_brief(context("buyer")))
    seller = json.loads(build_brief(context("seller")))
    assert "you_may_accept_the_standing_price" not in buyer
    assert "you_may_accept_the_standing_bid" not in seller


def test_an_agents_own_prior_offer_is_not_treated_as_standing():
    """The flag must reflect the opponent's offer, not the agent's own."""
    brief = json.loads(build_brief(context("buyer", [buyer_offer(200_000)])))
    assert "you_may_accept_the_standing_price" not in brief


# ---------------------------------------------------------------------------
# Instructions
# ---------------------------------------------------------------------------


def test_every_role_is_forbidden_from_claiming_market_knowledge():
    for role in ("buyer", "seller", "broker"):
        instruction = system_instruction(role).lower()
        assert "no market information" in instruction
        assert "market rate" in instruction


def test_broker_is_told_to_stay_out_of_pricing():
    instruction = system_instruction("broker")
    assert "DO NOT negotiate or comment on the material's unit price" in instruction


def test_roles_are_told_how_to_open():
    assert "opening move" in system_instruction("seller")
    assert "opening move" in system_instruction("buyer")
