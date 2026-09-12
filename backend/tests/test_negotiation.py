"""Coordinator behaviour: agreement, no-deal, provider failure, idempotency."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.agents.base import (
    AgentContext,
    AgentDecision,
    InvalidModelOutput,
    ProviderUnavailable,
)
from app.db import models
from app.services.coordinator import Coordinator
from tests.conftest import auth, make_listing, make_requirement, make_transport


def start(client, scenario, listing_ids, *, key="key-1", email=None):
    return client.post(
        "/api/v1/negotiations",
        json={"requirement_id": scenario.requirement.id, "listing_ids": listing_ids},
        headers={**auth(email or scenario.buyer_email), "Idempotency-Key": key},
    )


def test_agreement_creates_one_deal_and_reserves_stock_once(client, db, scenario):
    listing_ids = [listing.id for listing in scenario.listings]
    before = {listing.id: listing.available_quantity_kg for listing in scenario.listings}

    response = start(client, scenario, listing_ids)
    assert response.status_code == 202
    negotiation_id = response.json()["id"]

    detail = client.get(
        f"/api/v1/negotiations/{negotiation_id}", headers=auth(scenario.buyer_email)
    ).json()
    assert detail["status"] == "agreed", detail
    assert detail["deal_id"]

    deal = client.get(
        f"/api/v1/deals/{detail['deal_id']}", headers=auth(scenario.buyer_email)
    ).json()
    assert deal["quantity_kg"] == scenario.requirement.quantity_kg
    assert deal["status"] == "agreed"
    assert deal["costs"]["buyer_total_paise"] <= scenario.requirement.buyer_max_total_paise
    assert deal["intended_use"].startswith("Fuel for brick kiln")

    db.expire_all()
    # Exactly one listing lost stock, and exactly the requested quantity.
    reduced = [
        listing
        for listing in db.query(models.Listing).all()
        if listing.available_quantity_kg != before[listing.id]
    ]
    assert len(reduced) == 1
    assert reduced[0].id == deal["listing_id"]
    assert before[reduced[0].id] - reduced[0].available_quantity_kg == deal["quantity_kg"]

    requirement = db.get(models.Requirement, scenario.requirement.id)
    assert requirement.status == "fulfilled"
    assert db.query(models.Deal).count() == 1


def test_at_least_one_counteroffer_changes_the_terms(client, db, scenario):
    start(client, scenario, [scenario.listings[2].id])
    offers = (
        db.query(models.Offer).order_by(models.Offer.created_at, models.Offer.id).all()
    )
    assert len(offers) >= 3
    assert any(offer.action == "counter" for offer in offers)
    prices = [offer.unit_price_paise_per_tonne for offer in offers]
    assert len(set(prices)) > 1, "terms never moved during the negotiation"


def test_low_budget_produces_no_deal_without_breaching_a_seller_floor(client, db, scenario):
    # Freight alone is 1,500,000; this budget cannot reach any seller's floor.
    scenario.requirement.buyer_max_total_paise = 5_000_000
    db.commit()

    response = start(client, scenario, [listing.id for listing in scenario.listings])
    negotiation_id = response.json()["id"]

    detail = client.get(
        f"/api/v1/negotiations/{negotiation_id}", headers=auth(scenario.buyer_email)
    ).json()
    assert detail["status"] == "no_deal"
    assert detail["failure_code"] == "BUDGET_NOT_MET"
    assert detail["deal_id"] is None
    assert db.query(models.Deal).count() == 0

    db.expire_all()
    for listing in db.query(models.Listing).all():
        assert listing.available_quantity_kg == 60_000  # nothing reserved

    # No offer the seller made ever went below its floor.
    for offer in db.query(models.Offer).filter(models.Offer.author == "seller"):
        listing = db.get(models.Listing, offer.listing_id)
        assert offer.unit_price_paise_per_tonne >= listing.seller_floor_paise_per_tonne


def test_cheapest_delivered_acceptance_wins_not_the_nearest_seller(client, db, scenario):
    response = start(client, scenario, [listing.id for listing in scenario.listings])
    detail = client.get(
        f"/api/v1/negotiations/{response.json()['id']}", headers=auth(scenario.buyer_email)
    ).json()
    deal = client.get(
        f"/api/v1/deals/{detail['deal_id']}", headers=auth(scenario.buyer_email)
    ).json()

    accepted = [
        offer
        for offer in db.query(models.Offer).filter(models.Offer.action == "accept").all()
    ]
    assert accepted, "expected at least one acceptance"
    best = min(offer.buyer_total_paise for offer in accepted)
    assert deal["costs"]["buyer_total_paise"] == best


def test_events_are_ascending_without_duplicates_and_support_polling(client, scenario):
    response = start(client, scenario, [scenario.listings[0].id])
    negotiation_id = response.json()["id"]

    first = client.get(
        f"/api/v1/negotiations/{negotiation_id}/events",
        headers=auth(scenario.buyer_email),
    ).json()
    seqs = [event["seq"] for event in first["items"]]
    assert seqs == sorted(seqs)
    assert len(seqs) == len(set(seqs))
    assert first["last_seq"] == seqs[-1]
    assert first["items"][0]["type"] == "started"
    assert first["items"][-1]["type"] in ("agreed", "no_deal", "failed")

    # A poll from the last sequence returns nothing new.
    second = client.get(
        f"/api/v1/negotiations/{negotiation_id}/events?after_seq={first['last_seq']}",
        headers=auth(scenario.buyer_email),
    ).json()
    assert second["items"] == []
    assert second["last_seq"] == first["last_seq"]


def test_repeated_idempotency_key_returns_the_original_run(client, db, scenario):
    first = start(client, scenario, [scenario.listings[0].id], key="same-key")
    assert first.status_code == 202

    second = start(client, scenario, [scenario.listings[0].id], key="same-key")
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert db.query(models.Negotiation).count() == 1


def test_same_key_with_a_different_body_is_a_conflict(client, scenario):
    start(client, scenario, [scenario.listings[0].id], key="reused")
    response = start(client, scenario, [scenario.listings[1].id], key="reused")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_missing_idempotency_key_is_rejected(client, scenario):
    response = client.post(
        "/api/v1/negotiations",
        json={
            "requirement_id": scenario.requirement.id,
            "listing_ids": [scenario.listings[0].id],
        },
        headers=auth(scenario.buyer_email),
    )
    assert response.status_code == 422


def test_only_the_buyer_can_start_a_negotiation(client, scenario):
    response = start(
        client, scenario, [scenario.listings[0].id], email=scenario.seller_emails[0]
    )
    assert response.status_code == 403


def test_more_than_three_listings_is_rejected(client, db, scenario):
    extra = make_listing(db, scenario.sellers[0], scenario.now, asking=250_000, floor=200_000)
    make_transport(db, extra, scenario.requirement, scenario.now, freight_paise=1_000_000)
    db.commit()

    response = start(
        client, scenario, [listing.id for listing in scenario.listings] + [extra.id]
    )
    assert response.status_code == 422


def test_a_second_negotiation_for_the_same_requirement_is_blocked_while_one_is_live(
    client, db, scenario
):
    """A terminal run may be retried; a live one may not be duplicated."""
    start(client, scenario, [scenario.listings[0].id], key="first")

    # Re-read: the run committed through the request's own session.
    db.expire_all()
    negotiation = db.query(models.Negotiation).one()
    negotiation.status = "running"
    db.get(models.Requirement, scenario.requirement.id).status = "open"
    db.commit()

    response = start(client, scenario, [scenario.listings[1].id], key="second")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NEGOTIATION_IN_PROGRESS"


def test_expired_transport_quote_ends_the_candidate_as_quote_expired(client, db, scenario):
    listing = scenario.listings[0]
    scenario.transport[listing.id].expires_at = scenario.now - timedelta(hours=1)
    db.commit()

    response = start(client, scenario, [listing.id])
    detail = client.get(
        f"/api/v1/negotiations/{response.json()['id']}", headers=auth(scenario.buyer_email)
    ).json()
    assert detail["status"] == "no_deal"
    assert detail["failure_code"] == "QUOTE_EXPIRED"


def test_stock_that_disappears_before_the_run_ends_the_candidate(client, db, scenario):
    listing = scenario.listings[0]
    listing.available_quantity_kg = 10
    db.commit()

    response = start(client, scenario, [listing.id])
    detail = client.get(
        f"/api/v1/negotiations/{response.json()['id']}", headers=auth(scenario.buyer_email)
    ).json()
    assert detail["status"] == "no_deal"
    assert detail["failure_code"] == "STALE_STOCK"


# ---------------------------------------------------------------------------
# Provider failures must never fabricate an agreement
# ---------------------------------------------------------------------------


class BrokenProvider:
    name = "broken"

    def decide(self, context: AgentContext) -> AgentDecision:
        raise ProviderUnavailable("Simulated Gemini outage.")


class GarbageProvider:
    name = "garbage"

    def __init__(self) -> None:
        self.calls = 0

    def decide(self, context: AgentContext) -> AgentDecision:
        self.calls += 1
        if self.calls == 1:
            return AgentDecision(
                action="propose",
                listing_id=context.listing_id,
                transport_option_id=context.transport.transport_option_id,
                unit_price_paise_per_tonne=context.asking_price_paise_per_tonne,
                explanation="ok",
            )
        raise InvalidModelOutput("Model returned prose instead of a decision.")


class WrongListingProvider:
    name = "wrong-listing"

    def decide(self, context: AgentContext) -> AgentDecision:
        return AgentDecision(
            action="propose",
            listing_id="a-listing-that-does-not-exist",
            transport_option_id=context.transport.transport_option_id,
            unit_price_paise_per_tonne=100,
            explanation="",
        )


class AbsurdPriceProvider:
    name = "absurd-price"

    def decide(self, context: AgentContext) -> AgentDecision:
        return AgentDecision(
            action="propose",
            listing_id=context.listing_id,
            transport_option_id=context.transport.transport_option_id,
            unit_price_paise_per_tonne=context.asking_price_paise_per_tonne * 500,
            explanation="",
        )


def _run_with(db, scenario, provider) -> models.Negotiation:
    negotiation = models.Negotiation(
        requirement_id=scenario.requirement.id,
        buyer_business_id=scenario.buyer.id,
        status="queued",
        max_rounds=4,
    )
    db.add(negotiation)
    db.flush()
    db.add(
        models.NegotiationCandidate(
            negotiation_id=negotiation.id,
            listing_id=scenario.listings[0].id,
            seller_business_id=scenario.sellers[0].id,
            order_index=0,
        )
    )
    db.commit()
    Coordinator(db, provider=provider).run(negotiation.id)
    db.commit()
    db.refresh(negotiation)
    return negotiation


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        (BrokenProvider(), "PROVIDER_UNAVAILABLE"),
        (GarbageProvider(), "INVALID_MODEL_OUTPUT"),
        (WrongListingProvider(), "INVALID_MODEL_OUTPUT"),
        (AbsurdPriceProvider(), "INVALID_MODEL_OUTPUT"),
    ],
)
def test_provider_problems_fail_the_run_and_never_create_a_deal(
    db, scenario, provider, expected
):
    negotiation = _run_with(db, scenario, provider)
    assert negotiation.status == "failed"
    assert negotiation.failure_code == expected
    assert db.query(models.Deal).count() == 0

    db.expire_all()
    assert db.get(models.Listing, scenario.listings[0].id).available_quantity_kg == 60_000
    assert db.get(models.Requirement, scenario.requirement.id).status == "open"

    events = (
        db.query(models.NegotiationEvent)
        .filter(models.NegotiationEvent.negotiation_id == negotiation.id)
        .all()
    )
    assert any(event.type == "failed" for event in events)


def test_interrupted_runs_are_closed_on_restart(db, scenario):
    from app.services.coordinator import recover_interrupted_runs

    negotiation = models.Negotiation(
        requirement_id=scenario.requirement.id,
        buyer_business_id=scenario.buyer.id,
        status="running",
        max_rounds=4,
    )
    db.add(negotiation)
    db.commit()

    assert recover_interrupted_runs() == 1

    db.expire_all()
    db.refresh(negotiation)
    assert negotiation.status == "failed"
    assert negotiation.failure_code == "INTERRUPTED"


def test_round_limit_is_respected(client, db, scenario):
    response = start(client, scenario, [scenario.listings[0].id])
    negotiation = db.query(models.Negotiation).one()
    assert negotiation.round <= negotiation.max_rounds
    assert response.status_code == 202
