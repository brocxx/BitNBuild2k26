"""The demo seed must produce a scenario that actually demonstrates something.

This is the closest thing to a rehearsal of the demo: it seeds against the real
dataset, runs the feasible requirement through to an agreement, then runs the
low-budget one and confirms an honest no-deal.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.config import DATASET_DIR
from app.data.importer import import_reference_data
from app.data.seed import seed_demo
from app.db import models
from app.services.coordinator import Coordinator
from app.services.matching import build_matches_response

pytestmark = [
    pytest.mark.skipif(
        not DATASET_DIR.exists(), reason="dataset/ directory is not present"
    ),
    pytest.mark.own_database,
]


@pytest.fixture(scope="module")
def seeded():
    from app.db.session import SessionLocal, engine

    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    import_reference_data(session)
    report = seed_demo(session)
    yield session, report
    session.close()
    models.Base.metadata.drop_all(bind=engine)


def _requirements(db) -> tuple[models.Requirement, models.Requirement]:
    """The kiln buyer's two requirements: affordable first, then low-budget."""
    rows = list(
        db.scalars(
            select(models.Requirement)
            .where(models.Requirement.receiving_process_id == "brick_kiln_fuel")
            .order_by(models.Requirement.buyer_max_total_paise.desc())
        )
    )
    assert len(rows) == 2
    return rows[0], rows[1]


def _sawmill_requirement(db) -> models.Requirement:
    row = db.scalar(
        select(models.Requirement).where(
            models.Requirement.receiving_process_id == "timber_drying_boiler_fuel"
        )
    )
    assert row is not None
    return row


def test_seed_creates_the_demo_scenario(seeded):
    _, report = seeded
    assert report.listings == 6
    assert report.requirements == 3
    # Two options per listing, per requirement.
    assert report.transport_options == 6 * 3 * 2
    assert len(report.logins) == 8


def test_the_sawmill_buyer_has_a_workable_requirement(seeded):
    """Regression: buyer2 was seeded with no requirement at all.

    Logging in as the sawmill account showed an empty Matches screen, because
    the seed only created requirements for the kiln buyer - and even with one,
    transport options were only generated for the kiln's pairs.
    """
    db, _ = seeded
    requirement = _sawmill_requirement(db)
    response = build_matches_response(db, requirement)

    assert response.candidates, "the sawmill buyer must have compatible suppliers"
    assert not response.missing_transport_listing_ids
    # The second documented pathway for this material, not the kiln one.
    assert all("boiler" in c.pathway_use.lower() for c in response.candidates)


def test_seeded_businesses_are_real_named_enterprises(seeded):
    db, _ = seeded
    for business in db.scalars(select(models.Business)):
        assert business.enterprise_id, "every demo business maps to a real enterprise"
        enterprise = db.get(models.Enterprise, business.enterprise_id)
        assert enterprise.name_source == "udyam"
        assert business.name == enterprise.name
        assert business.district == enterprise.district
        assert business.is_demo


def test_seeded_windows_are_in_the_future(seeded):
    db, _ = seeded
    now = datetime.now(timezone.utc)
    for listing in db.scalars(select(models.Listing)):
        assert listing.pickup_end.replace(tzinfo=timezone.utc) > now
    for option in db.scalars(select(models.TransportOption)):
        assert option.expires_at.replace(tzinfo=timezone.utc) > now


def test_freight_is_labelled_as_a_configured_estimate(seeded):
    db, _ = seeded
    options = list(db.scalars(select(models.TransportOption)))
    assert options
    assert all(option.source == "configured_estimate" for option in options)
    # Distance is shown for context and explicitly marked straight-line, so it
    # cannot be mistaken for the basis of the freight charge.
    assert all(option.distance_basis == "district_straight_line" for option in options)


def test_matches_show_three_candidates_and_three_distinct_exclusions(seeded):
    db, _ = seeded
    feasible, _ = _requirements(db)
    response = build_matches_response(db, feasible)

    assert len(response.candidates) == 3
    reasons = {code for entry in response.excluded for code in entry.reason_codes}
    assert "QUALITY_MISMATCH" in reasons
    assert "QUALITY_REVIEW_REQUIRED" in reasons
    assert "INSUFFICIENT_QUANTITY" in reasons

    # Candidates are ranked by delivered cost, and the nearest seller is not
    # automatically first - that is the point the demo makes.
    totals = [c.initial_best_cost.buyer_total_paise for c in response.candidates]
    assert totals == sorted(totals)
    assert all(c.pathway_use for c in response.candidates)


def _run(db, requirement) -> models.Negotiation:
    response = build_matches_response(db, requirement)
    listing_ids = [c.listing.id for c in response.candidates][:3]
    negotiation = models.Negotiation(
        requirement_id=requirement.id,
        buyer_business_id=requirement.buyer_business_id,
        status="queued",
        max_rounds=4,
    )
    db.add(negotiation)
    db.flush()
    for index, listing_id in enumerate(listing_ids):
        listing = db.get(models.Listing, listing_id)
        db.add(
            models.NegotiationCandidate(
                negotiation_id=negotiation.id,
                listing_id=listing_id,
                seller_business_id=listing.seller_business_id,
                order_index=index,
            )
        )
    db.commit()
    Coordinator(db).run(negotiation.id)
    db.commit()
    db.refresh(negotiation)
    return negotiation


def test_the_feasible_requirement_reaches_an_agreement(seeded):
    db, _ = seeded
    feasible, _ = _requirements(db)

    negotiation = _run(db, feasible)
    assert negotiation.status == "agreed", negotiation.failure_code

    deal = db.get(models.Deal, negotiation.deal_id)
    assert deal.buyer_total_paise <= feasible.buyer_max_total_paise
    listing = db.get(models.Listing, deal.listing_id)
    assert deal.unit_price_paise_per_tonne >= listing.seller_floor_paise_per_tonne
    assert "kiln" in deal.intended_use.lower()


def test_the_low_budget_requirement_produces_an_honest_no_deal(seeded):
    db, _ = seeded
    _, infeasible = _requirements(db)

    negotiation = _run(db, infeasible)
    assert negotiation.status == "no_deal"
    assert negotiation.failure_code == "BUDGET_NOT_MET"
    assert negotiation.deal_id is None
