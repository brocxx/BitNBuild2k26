"""Private limits must not leak: not in responses, events, or agent prose."""

from __future__ import annotations

import json

from app.agents.privacy import claims_market_knowledge, scrub_explanation
from app.db import models
from tests.conftest import auth
from tests.test_negotiation import start

FLOOR_FIELD = "seller_floor_paise_per_tonne"
BUDGET_FIELD = "buyer_max_total_paise"


def test_public_listing_has_no_seller_floor(client, scenario):
    listing_id = scenario.listings[0].id

    detail = client.get(f"/api/v1/listings/{listing_id}", headers=auth(scenario.buyer_email))
    assert detail.status_code == 200
    assert FLOOR_FIELD not in detail.json()

    listed = client.get("/api/v1/listings", headers=auth(scenario.buyer_email)).json()
    assert listed["items"]
    assert all(FLOOR_FIELD not in item for item in listed["items"])


def test_owner_listing_does_include_the_floor(client, scenario):
    mine = client.get(
        "/api/v1/me/listings", headers=auth(scenario.seller_emails[0])
    ).json()
    assert mine["items"]
    assert all(FLOOR_FIELD in item for item in mine["items"])
    # And it is only the seller's own listing.
    assert {item["id"] for item in mine["items"]} == {scenario.listings[0].id}


def test_a_seller_cannot_read_another_businesss_requirement(client, scenario):
    response = client.get(
        f"/api/v1/requirements/{scenario.requirement.id}",
        headers=auth(scenario.seller_emails[0]),
    )
    assert response.status_code == 403
    assert BUDGET_FIELD not in response.text


def test_a_seller_cannot_read_another_businesss_matches(client, scenario):
    response = client.get(
        f"/api/v1/requirements/{scenario.requirement.id}/matches",
        headers=auth(scenario.seller_emails[0]),
    )
    assert response.status_code == 403


def test_matches_response_carries_no_private_limits(client, scenario):
    body = client.get(
        f"/api/v1/requirements/{scenario.requirement.id}/matches",
        headers=auth(scenario.buyer_email),
    ).text
    assert FLOOR_FIELD not in body
    assert BUDGET_FIELD not in body
    for listing in scenario.listings:
        assert str(listing.seller_floor_paise_per_tonne) not in body


def test_no_private_value_appears_in_any_negotiation_response_or_event(
    client, db, scenario
):
    floors = [listing.seller_floor_paise_per_tonne for listing in scenario.listings]
    budget = scenario.requirement.buyer_max_total_paise

    response = start(client, scenario, [listing.id for listing in scenario.listings])
    negotiation_id = response.json()["id"]

    for email in [scenario.buyer_email, *scenario.seller_emails]:
        detail = client.get(
            f"/api/v1/negotiations/{negotiation_id}", headers=auth(email)
        )
        events = client.get(
            f"/api/v1/negotiations/{negotiation_id}/events", headers=auth(email)
        )
        for body in (detail.json(), events.json()):
            text = json.dumps(body)
            assert FLOOR_FIELD not in text
            assert BUDGET_FIELD not in text

    # Explanations specifically: prose is where a limit is most likely to slip.
    for offer in db.query(models.Offer).all():
        for value in [*floors, budget]:
            assert str(value) not in offer.explanation
    for event in db.query(models.NegotiationEvent).all():
        for value in floors:
            assert str(value) not in event.message


def test_a_seller_sees_only_its_own_candidate_conversation(client, db, scenario):
    listing_ids = [listing.id for listing in scenario.listings]
    response = start(client, scenario, listing_ids)
    negotiation_id = response.json()["id"]

    buyer_view = client.get(
        f"/api/v1/negotiations/{negotiation_id}", headers=auth(scenario.buyer_email)
    ).json()
    assert len({offer["listing_id"] for offer in buyer_view["offers"]}) > 1

    for index, email in enumerate(scenario.seller_emails):
        seller_view = client.get(
            f"/api/v1/negotiations/{negotiation_id}", headers=auth(email)
        ).json()
        seen = {offer["listing_id"] for offer in seller_view["offers"]}
        assert seen <= {listing_ids[index]}, "seller saw a competitor's offers"

        events = client.get(
            f"/api/v1/negotiations/{negotiation_id}/events", headers=auth(email)
        ).json()
        for other in listing_ids:
            if other == listing_ids[index]:
                continue
            assert other not in json.dumps(events)


def test_a_losing_seller_is_not_told_a_deal_happened(client, db, scenario):
    listing_ids = [listing.id for listing in scenario.listings]
    negotiation_id = start(client, scenario, listing_ids).json()["id"]

    deal = db.query(models.Deal).one()
    losers = [
        email
        for email, listing in zip(scenario.seller_emails, scenario.listings, strict=True)
        if listing.id != deal.listing_id
    ]
    assert losers

    for email in losers:
        view = client.get(
            f"/api/v1/negotiations/{negotiation_id}", headers=auth(email)
        ).json()
        assert view["deal_id"] is None
        assert view["current_listing_id"] is None
        assert client.get(f"/api/v1/deals/{deal.id}", headers=auth(email)).status_code == 403


def test_an_uninvolved_business_cannot_read_the_negotiation(client, db, scenario):
    from tests.conftest import make_business

    make_business(db, "Bystander Ltd", "nobody@test.local", is_seller=True)
    db.commit()

    negotiation_id = start(client, scenario, [scenario.listings[0].id]).json()["id"]
    response = client.get(
        f"/api/v1/negotiations/{negotiation_id}", headers=auth("nobody@test.local")
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# The scrubber itself
# ---------------------------------------------------------------------------


def test_scrubber_removes_paise_rupee_and_grouped_renderings():
    floor = 242_000  # INR 2,420
    for phrasing in (
        "We cannot go below 242000 paise per tonne.",
        "Our minimum is 242,000.",
        "That works out to INR 2420 per tonne for us.",
        "We need about 2,420 a tonne.",
    ):
        assert "[redacted limit]" in scrub_explanation(phrasing, [floor])
        assert "242000" not in scrub_explanation(phrasing, [floor])


def test_scrubber_leaves_ordinary_commercial_prose_alone():
    text = "The delivered cost fits our kiln programme for this quarter."
    assert scrub_explanation(text, [242_000]) == text


# ---------------------------------------------------------------------------
# Market claims
# ---------------------------------------------------------------------------


def test_invented_market_claims_are_removed():
    """This application has no pricing feed, so an agent cannot cite one.

    Gemini produced the first of these verbatim on the first live run.
    """
    for phrasing in (
        "I have adjusted my unit price to reflect current market conditions.",
        "This is below the going rate for clean husk.",
        "Our price is in line with the prevailing rates this season.",
        "That figure is under fair market value.",
        "We price against the industry standard for biomass fuel.",
        "The benchmark price for this grade is higher.",
    ):
        cleaned = scrub_explanation(phrasing, [])
        assert not claims_market_knowledge(cleaned), cleaned
        assert "market" not in cleaned.lower() or "the terms of this shipment" in cleaned


def test_legitimate_commercial_reasons_survive():
    for phrasing in (
        "The freight charge on this route leaves little room on the material itself.",
        "We can improve slightly given the full truckload and the collection date.",
        "Moisture at 9.5 percent suits our kiln without extra drying.",
        "This lot is ready for collection inside your window.",
    ):
        assert scrub_explanation(phrasing, []) == phrasing


def test_market_claim_detector_does_not_fire_on_ordinary_words():
    assert not claims_market_knowledge("We supply the local brick market in Ballari.")
    assert not claims_market_knowledge("Delivered cost is what matters to us.")
