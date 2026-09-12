"""Compatibility analysis: every reason code, and what must not exclude."""

from __future__ import annotations

from datetime import timedelta

from app.services import matching
from app.services.matching import build_matches_response
from tests.conftest import make_listing, make_requirement, make_transport


def _reasons(response, listing_id: str) -> list[str]:
    for entry in response.excluded:
        if entry.listing_id == listing_id:
            return entry.reason_codes
    return []


def test_eligible_listings_become_candidates_ordered_by_delivered_cost(db, scenario):
    response = build_matches_response(db, scenario.requirement)

    assert [c.listing.id for c in response.candidates] == [
        scenario.listings[2].id,  # 7,300,000
        scenario.listings[1].id,  # 7,390,000
        scenario.listings[0].id,  # 7,600,000
    ]
    assert response.excluded == []
    assert response.candidates[0].initial_best_cost.buyer_total_paise == 7_300_000
    assert response.candidates[0].pathway_use.startswith("Fuel for brick kiln")


def test_asking_price_above_budget_does_not_exclude_a_listing(db, scenario):
    """The seller may still concede, so price is not a matching filter."""
    response = build_matches_response(db, scenario.requirement)
    over_budget = [
        c
        for c in response.candidates
        if c.initial_best_cost.buyer_total_paise > scenario.requirement.buyer_max_total_paise
    ]
    assert over_budget, "expected at least one candidate priced above the budget"


def test_material_mismatch(db, scenario):
    seller = scenario.sellers[0]
    listing = make_listing(
        db, seller, scenario.now, asking=200_000, floor=100_000, material_id="sawdust"
    )
    make_transport(db, listing, scenario.requirement, scenario.now, freight_paise=1_000_000)
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    # A different material is not even a listing for this requirement.
    assert listing.id not in [c.listing.id for c in response.candidates]


def test_quality_mismatch_on_moisture(db, scenario):
    listing = scenario.listings[0]
    listing.moisture_pct = 18.5
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    assert matching.QUALITY_MISMATCH in _reasons(response, listing.id)


def test_contamination_needing_review_does_not_pass_on_acceptable_moisture(db, scenario):
    listing = scenario.listings[0]
    listing.moisture_pct = 8.0  # comfortably within the buyer's limit
    listing.contamination_notes = "Visible field soil carry-over from yard storage."
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    reasons = _reasons(response, listing.id)
    assert matching.QUALITY_REVIEW_REQUIRED in reasons
    assert matching.QUALITY_MISMATCH not in reasons


def test_unreviewed_contamination_is_review_required_not_an_automatic_pass(db, scenario):
    listing = scenario.listings[0]
    listing.contamination_notes = "Some unusual residue nobody has assessed."
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    assert matching.QUALITY_REVIEW_REQUIRED in _reasons(response, listing.id)


def test_rejected_contamination_is_a_quality_mismatch(db, scenario):
    listing = scenario.listings[0]
    listing.contamination_notes = "Mixed with plastic sacking offcuts."
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    assert matching.QUALITY_MISMATCH in _reasons(response, listing.id)


def test_insufficient_quantity(db, scenario):
    listing = scenario.listings[0]
    listing.available_quantity_kg = scenario.requirement.quantity_kg - 1
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    assert matching.INSUFFICIENT_QUANTITY in _reasons(response, listing.id)


def test_process_unconfirmed_when_buyer_has_not_confirmed_the_process(db, scenario):
    for link in list(scenario.buyer.receiving_processes):
        link.confirmed = False
    db.commit()
    db.refresh(scenario.buyer)

    response = build_matches_response(db, scenario.requirement)
    assert response.candidates == []
    assert all(
        matching.PROCESS_UNCONFIRMED in entry.reason_codes for entry in response.excluded
    )


def test_time_window_mismatch_when_pickup_starts_after_the_delivery_deadline(db, scenario):
    listing = scenario.listings[0]
    listing.pickup_start = scenario.requirement.delivery_end + timedelta(days=1)
    listing.pickup_end = scenario.requirement.delivery_end + timedelta(days=5)
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    assert matching.TIME_WINDOW_MISMATCH in _reasons(response, listing.id)


def test_no_transport_option_is_reported_separately(db, scenario):
    seller = scenario.sellers[0]
    listing = make_listing(db, seller, scenario.now, asking=250_000, floor=200_000)
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    assert listing.id in response.missing_transport_listing_ids
    assert matching.NO_TRANSPORT_OPTION in _reasons(response, listing.id)


def test_expired_and_undersized_transport_options_are_not_usable(db, scenario):
    listing = scenario.listings[0]
    option = scenario.transport[listing.id]
    option.expires_at = scenario.now - timedelta(hours=1)
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    assert matching.NO_TRANSPORT_OPTION in _reasons(response, listing.id)

    option.expires_at = scenario.now + timedelta(days=7)
    option.capacity_kg = scenario.requirement.quantity_kg - 1
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    assert matching.NO_TRANSPORT_OPTION in _reasons(response, listing.id)


def test_transport_options_are_capped_and_cheapest_first(db, scenario):
    listing = scenario.listings[0]
    make_transport(
        db, listing, scenario.requirement, scenario.now, freight_paise=999_000, label="Cheapest"
    )
    make_transport(
        db, listing, scenario.requirement, scenario.now, freight_paise=3_000_000, label="Dearest"
    )
    db.commit()

    response = build_matches_response(db, scenario.requirement)
    candidate = next(c for c in response.candidates if c.listing.id == listing.id)
    assert len(candidate.transport_options) == 2  # MAX_TRANSPORT_OPTIONS_PER_LISTING
    assert candidate.transport_options[0].label == "Cheapest"
    assert candidate.initial_best_cost.freight_paise == 999_000


def test_a_business_cannot_match_against_its_own_listing(db, scenario):
    own = make_requirement(db, scenario.sellers[0], scenario.now, budget_paise=9_000_000)
    db.add(
        type(scenario.buyer.receiving_processes[0])(
            business_id=scenario.sellers[0].id,
            process_id="brick_kiln_fuel",
            confirmed=True,
        )
    )
    db.commit()
    db.refresh(scenario.sellers[0])

    response = build_matches_response(db, own)
    assert scenario.listings[0].id not in [c.listing.id for c in response.candidates]
