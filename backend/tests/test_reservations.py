"""Stock reservation, competing requests, and the deal lifecycle."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.db import models
from app.services.reservations import (
    ReservationFailed,
    TransitionRejected,
    apply_status,
    commit_deal,
)
from tests.conftest import auth, make_business, make_requirement, make_transport
from tests.test_negotiation import start


def _offer_for(db, negotiation, listing, requirement, transport, unit_price) -> models.Offer:
    from app.services.costing import compute_costs

    costs = compute_costs(unit_price, requirement.quantity_kg, transport.freight_paise)
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
        author="buyer",
        action="accept",
        explanation="",
        expires_at=transport.expires_at,
    )
    db.add(offer)
    db.flush()
    return offer


def _negotiation_for(db, requirement, buyer) -> models.Negotiation:
    negotiation = models.Negotiation(
        requirement_id=requirement.id, buyer_business_id=buyer.id, status="running"
    )
    db.add(negotiation)
    db.flush()
    return negotiation


def test_two_requirements_cannot_both_take_the_last_batch(client, db, scenario):
    """The classic double-allocation case: one batch, two buyers wanting it all."""
    listing = scenario.listings[0]
    listing.available_quantity_kg = scenario.requirement.quantity_kg  # exactly one order
    db.commit()

    other_buyer = make_business(
        db,
        "Second Brick Kiln",
        "buyer2@test.local",
        is_buyer=True,
        processes=("brick_kiln_fuel",),
    )
    second = make_requirement(db, other_buyer, scenario.now, budget_paise=7_000_000)
    make_transport(db, listing, second, scenario.now, freight_paise=1_500_000)
    db.commit()

    first = start(client, scenario, [listing.id], key="a")
    first_status = client.get(
        f"/api/v1/negotiations/{first.json()['id']}", headers=auth(scenario.buyer_email)
    ).json()

    second_response = client.post(
        "/api/v1/negotiations",
        json={"requirement_id": second.id, "listing_ids": [listing.id]},
        headers={**auth("buyer2@test.local"), "Idempotency-Key": "b"},
    )
    second_status = client.get(
        f"/api/v1/negotiations/{second_response.json()['id']}",
        headers=auth("buyer2@test.local"),
    ).json()

    assert first_status["status"] == "agreed"
    assert second_status["status"] == "no_deal"
    assert second_status["failure_code"] == "STALE_STOCK"

    db.expire_all()
    assert db.query(models.Deal).count() == 1
    assert db.get(models.Listing, listing.id).available_quantity_kg == 0


def test_two_concurrent_commits_cannot_both_take_the_last_batch(db, scenario):
    """The genuinely concurrent case, not two sequential API calls.

    Regression test. The first implementation did a read-modify-write on the
    ORM object, so two transactions could both read the same stock level and
    both succeed - the unique constraint on deals.requirement_id does not help
    here, because these are two different requirements competing for one batch.
    The fix was a conditional UPDATE whose predicate the database re-evaluates
    at write time.
    """
    import threading

    from app.db.session import SessionLocal

    listing = scenario.listings[0]
    listing.available_quantity_kg = scenario.requirement.quantity_kg  # one order only
    db.commit()

    second_buyer = make_business(
        db,
        "Rival Kiln",
        "rival@test.local",
        is_buyer=True,
        processes=("brick_kiln_fuel",),
    )
    rival = make_requirement(db, second_buyer, scenario.now, budget_paise=9_000_000)
    make_transport(db, listing, rival, scenario.now, freight_paise=1_500_000)
    db.commit()

    requirement_ids = [scenario.requirement.id, rival.id]
    barrier = threading.Barrier(len(requirement_ids))
    outcomes: list[str] = []
    guard = threading.Lock()

    def attempt(requirement_id: str) -> None:
        session = SessionLocal()
        try:
            requirement = session.get(models.Requirement, requirement_id)
            negotiation = _negotiation_for(session, requirement, requirement.buyer)
            transport = session.scalar(
                select(models.TransportOption).where(
                    models.TransportOption.requirement_id == requirement_id,
                    models.TransportOption.listing_id == listing.id,
                )
            )
            offer = _offer_for(
                session,
                negotiation,
                session.get(models.Listing, listing.id),
                requirement,
                transport,
                # Above this listing's floor (263,500) and inside both budgets,
                # so the only thing that can refuse a commit is the stock race.
                270_000,
            )
            session.commit()

            barrier.wait(timeout=30)
            try:
                commit_deal(
                    session, negotiation=negotiation, offer=offer, intended_use="fuel"
                )
                session.commit()
                result = "won"
            except ReservationFailed as exc:
                session.rollback()
                result = f"lost:{exc.code}"
        except Exception as exc:  # noqa: BLE001 - surface anything unexpected
            session.rollback()
            result = f"error:{type(exc).__name__}"
        finally:
            session.close()
        with guard:
            outcomes.append(result)

    threads = [
        threading.Thread(target=attempt, args=(requirement_id,))
        for requirement_id in requirement_ids
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert outcomes.count("won") == 1, outcomes
    assert not [o for o in outcomes if o.startswith("error:")], outcomes

    db.expire_all()
    assert db.query(models.Deal).count() == 1
    assert db.get(models.Listing, listing.id).available_quantity_kg == 0


def test_commit_is_rejected_when_stock_fell_away(db, scenario):
    listing, requirement = scenario.listings[0], scenario.requirement
    transport = scenario.transport[listing.id]
    negotiation = _negotiation_for(db, requirement, scenario.buyer)
    offer = _offer_for(db, negotiation, listing, requirement, transport, 264_000)

    listing.available_quantity_kg = requirement.quantity_kg - 1
    db.flush()

    with pytest.raises(ReservationFailed) as exc:
        commit_deal(db, negotiation=negotiation, offer=offer, intended_use="")
    assert exc.value.code == "INSUFFICIENT_STOCK"


def test_commit_is_rejected_on_an_expired_quote(db, scenario):
    listing, requirement = scenario.listings[0], scenario.requirement
    transport = scenario.transport[listing.id]
    negotiation = _negotiation_for(db, requirement, scenario.buyer)
    offer = _offer_for(db, negotiation, listing, requirement, transport, 264_000)

    transport.expires_at = scenario.now - timedelta(minutes=1)
    db.flush()

    with pytest.raises(ReservationFailed) as exc:
        commit_deal(db, negotiation=negotiation, offer=offer, intended_use="")
    assert exc.value.code == "QUOTE_EXPIRED"


def test_commit_is_rejected_below_the_floor_or_above_the_budget(db, scenario):
    listing, requirement = scenario.listings[0], scenario.requirement
    transport = scenario.transport[listing.id]
    negotiation = _negotiation_for(db, requirement, scenario.buyer)

    below_floor = _offer_for(
        db, negotiation, listing, requirement, transport, listing.seller_floor_paise_per_tonne - 1
    )
    with pytest.raises(ReservationFailed):
        commit_deal(db, negotiation=negotiation, offer=below_floor, intended_use="")

    db.rollback()
    negotiation = _negotiation_for(db, requirement, scenario.buyer)
    over_budget = _offer_for(db, negotiation, listing, requirement, transport, 400_000)
    with pytest.raises(ReservationFailed):
        commit_deal(db, negotiation=negotiation, offer=over_budget, intended_use="")


def test_a_requirement_can_only_ever_have_one_deal(db, scenario):
    listing, requirement = scenario.listings[0], scenario.requirement
    transport = scenario.transport[listing.id]
    negotiation = _negotiation_for(db, requirement, scenario.buyer)
    offer = _offer_for(db, negotiation, listing, requirement, transport, 264_000)

    commit_deal(db, negotiation=negotiation, offer=offer, intended_use="")
    db.commit()

    second = _negotiation_for(db, requirement, scenario.buyer)
    repeat = _offer_for(db, second, listing, requirement, transport, 264_000)
    with pytest.raises(ReservationFailed):
        commit_deal(db, negotiation=second, offer=repeat, intended_use="")


# ---------------------------------------------------------------------------
# Deal lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture
def agreed_deal(client, db, scenario):
    start(client, scenario, [listing.id for listing in scenario.listings])
    db.expire_all()
    deal = db.query(models.Deal).one()
    seller_email = next(
        email
        for email, seller in zip(scenario.seller_emails, scenario.sellers, strict=True)
        if seller.id == deal.seller_business_id
    )
    return deal, seller_email


def _patch(client, deal_id, status, email):
    return client.patch(
        f"/api/v1/deals/{deal_id}/status", json={"status": status}, headers=auth(email)
    )


def test_the_happy_path_runs_agreed_to_delivered(client, scenario, agreed_deal):
    deal, seller_email = agreed_deal

    assert _patch(client, deal.id, "pickup_scheduled", seller_email).status_code == 200
    assert _patch(client, deal.id, "collected", seller_email).status_code == 200
    response = _patch(client, deal.id, "delivered", scenario.buyer_email)
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"


def test_statuses_cannot_be_skipped_or_reversed(client, scenario, agreed_deal):
    deal, seller_email = agreed_deal

    skipped = _patch(client, deal.id, "delivered", scenario.buyer_email)
    assert skipped.status_code == 409
    assert skipped.json()["error"]["code"] == "INVALID_TRANSITION"

    _patch(client, deal.id, "pickup_scheduled", seller_email)
    assert _patch(client, deal.id, "agreed", seller_email).status_code == 422


def test_each_side_can_only_set_its_own_statuses(client, scenario, agreed_deal):
    deal, seller_email = agreed_deal

    assert _patch(client, deal.id, "pickup_scheduled", scenario.buyer_email).status_code == 403
    _patch(client, deal.id, "pickup_scheduled", seller_email)
    _patch(client, deal.id, "collected", seller_email)
    assert _patch(client, deal.id, "delivered", seller_email).status_code == 403


def test_cancellation_releases_stock_exactly_once_and_reopens_the_requirement(
    client, db, scenario, agreed_deal
):
    deal, _ = agreed_deal
    listing = db.get(models.Listing, deal.listing_id)
    reserved_from = listing.available_quantity_kg

    assert _patch(client, deal.id, "cancelled", scenario.buyer_email).status_code == 200

    db.expire_all()
    listing = db.get(models.Listing, deal.listing_id)
    assert listing.available_quantity_kg == reserved_from + deal.quantity_kg
    assert db.get(models.Requirement, deal.requirement_id).status == "open"

    # Cancelling again must not credit the stock a second time.
    assert _patch(client, deal.id, "cancelled", scenario.buyer_email).status_code == 409
    db.expire_all()
    assert (
        db.get(models.Listing, deal.listing_id).available_quantity_kg
        == reserved_from + deal.quantity_kg
    )


def test_cancellation_after_collection_is_out_of_scope(client, scenario, agreed_deal):
    deal, seller_email = agreed_deal
    _patch(client, deal.id, "pickup_scheduled", seller_email)
    _patch(client, deal.id, "collected", seller_email)

    response = _patch(client, deal.id, "cancelled", scenario.buyer_email)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CANCELLATION_NOT_ALLOWED"


def test_cancellation_does_not_reopen_a_listing_the_seller_closed(db, scenario, agreed_deal):
    deal, _ = agreed_deal
    listing = db.get(models.Listing, deal.listing_id)
    listing.status = "closed"
    db.commit()

    apply_status(db, deal, "cancelled", deal.buyer_business_id)
    db.commit()

    db.expire_all()
    listing = db.get(models.Listing, deal.listing_id)
    assert listing.status == "closed"
    assert listing.available_quantity_kg > 0  # stock restored, listing still closed


def test_a_non_participant_cannot_change_a_deal(client, db, scenario, agreed_deal):
    deal, _ = agreed_deal
    make_business(db, "Bystander", "outsider@test.local", is_seller=True)
    db.commit()

    assert _patch(client, deal.id, "cancelled", "outsider@test.local").status_code == 403
    assert (
        client.get(f"/api/v1/deals/{deal.id}", headers=auth("outsider@test.local")).status_code
        == 403
    )


def test_transition_helper_rejects_an_unknown_actor(db, scenario, agreed_deal):
    deal, _ = agreed_deal
    with pytest.raises(TransitionRejected) as exc:
        apply_status(db, deal, "cancelled", "not-a-business-id")
    assert exc.value.status_code == 403
