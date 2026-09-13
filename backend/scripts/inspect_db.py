"""Look at what the backend actually did, and check it holds together.

HTTP responses show you one view at a time, deliberately filtered per business.
This shows the whole database, plus the invariants that matter:

    python scripts/inspect_db.py              # full state dump
    python scripts/inspect_db.py --check      # invariant checks; exit 1 on failure
    python scripts/inspect_db.py --negotiation <id>   # one run in detail
    python scripts/inspect_db.py --reference  # what the dataset import produced

Run --check after any manual walkthrough. It is the same set of properties the
test suite enforces, applied to whatever state you have just created by hand.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402

from app.db import models  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

RULE = "-" * 78


def rupees(paise: int | None) -> str:
    return "-" if paise is None else f"{paise / 100:>12,.2f}"


def heading(text: str) -> None:
    print(f"\n{text}\n{RULE}")


# ---------------------------------------------------------------------------
# State dump
# ---------------------------------------------------------------------------


def dump_businesses(db) -> None:
    heading("BUSINESSES AND LOGINS")
    users = {u.business_id: u for u in db.scalars(select(models.AppUser))}
    for business in db.scalars(select(models.Business).order_by(models.Business.name)):
        user = users.get(business.id)
        roles = ",".join(
            role for role, on in (("buyer", business.is_buyer), ("seller", business.is_seller)) if on
        )
        processes = ",".join(
            link.process_id for link in business.receiving_processes if link.confirmed
        )
        print(f"{business.name[:42]:<44} {business.district[:16]:<18} {roles:<14}")
        print(
            f"    login: dev:{user.email if user else '(none)':<36} "
            f"processes: {processes or '-'}"
        )


def dump_listings(db) -> None:
    heading("LISTINGS   (floor is private - it is shown here, never over HTTP)")
    print(
        f"{'id':<10}{'seller':<30}{'district':<16}{'stock kg':>10}"
        f"{'asking/t':>14}{'floor/t':>14}  status"
    )
    for listing in db.scalars(select(models.Listing).order_by(models.Listing.created_at)):
        print(
            f"{listing.id[:8]:<10}{listing.seller.name[:28]:<30}{listing.district[:14]:<16}"
            f"{listing.available_quantity_kg:>10}{rupees(listing.asking_price_paise_per_tonne)}"
            f"{rupees(listing.seller_floor_paise_per_tonne)}  {listing.status}"
            f"   moisture {listing.moisture_pct}%"
        )
        if listing.contamination_notes:
            print(f"          notes: {listing.contamination_notes[:64]}")


def dump_requirements(db) -> None:
    heading("REQUIREMENTS   (budget is private)")
    print(f"{'id':<10}{'buyer':<30}{'qty kg':>9}{'budget':>14}  process / status")
    for requirement in db.scalars(
        select(models.Requirement).order_by(models.Requirement.created_at)
    ):
        print(
            f"{requirement.id[:8]:<10}{requirement.buyer.name[:28]:<30}"
            f"{requirement.quantity_kg:>9}{rupees(requirement.buyer_max_total_paise)}"
            f"  {requirement.receiving_process_id} / {requirement.status}"
        )


def dump_transport(db) -> None:
    heading("TRANSPORT OPTIONS")
    total = db.scalar(select(func.count()).select_from(models.TransportOption))
    print(f"{total} option(s). Freight is a complete per-shipment charge.")
    for option in db.scalars(
        select(models.TransportOption).order_by(models.TransportOption.created_at).limit(12)
    ):
        print(
            f"  {option.id[:8]}  listing {option.listing_id[:8]}  req {option.requirement_id[:8]}"
            f"  {rupees(option.freight_paise)}  cap {option.capacity_kg:>6} kg  "
            f"[{option.source}]  distance_basis={option.distance_basis}"
        )
    if total > 12:
        print(f"  ... and {total - 12} more")


def dump_negotiations(db, negotiation_id: str | None = None) -> None:
    heading("NEGOTIATIONS")
    stmt = select(models.Negotiation).order_by(models.Negotiation.created_at)
    if negotiation_id:
        stmt = stmt.where(models.Negotiation.id.startswith(negotiation_id))

    for negotiation in db.scalars(stmt):
        print(
            f"\n{negotiation.id}  status={negotiation.status}  "
            f"failure={negotiation.failure_code}  round={negotiation.round}/"
            f"{negotiation.max_rounds}  agent_mode={negotiation.agent_mode}"
        )
        print(f"  requirement {negotiation.requirement_id[:8]}  deal {negotiation.deal_id or '-'}")

        candidates = db.scalars(
            select(models.NegotiationCandidate)
            .where(models.NegotiationCandidate.negotiation_id == negotiation.id)
            .order_by(models.NegotiationCandidate.order_index)
        )
        print("  candidates:")
        for candidate in candidates:
            print(
                f"    #{candidate.order_index} listing {candidate.listing_id[:8]}  "
                f"{candidate.status:<22} reason={candidate.reason_code or '-':<18} "
                f"rounds={candidate.rounds_used}"
            )

        offers = list(
            db.scalars(
                select(models.Offer)
                .where(models.Offer.negotiation_id == negotiation.id)
                .order_by(models.Offer.created_at, models.Offer.id)
            )
        )
        if offers:
            print("  offers:")
            print(
                f"    {'listing':<10}{'author':<8}{'action':<9}{'unit/t':>14}"
                f"{'delivered':>14}  explanation"
            )
            for offer in offers:
                print(
                    f"    {offer.listing_id[:8]:<10}{offer.author:<8}{offer.action:<9}"
                    f"{rupees(offer.unit_price_paise_per_tonne)}"
                    f"{rupees(offer.buyer_total_paise)}  {offer.explanation[:44]}"
                )

        events = db.scalars(
            select(models.NegotiationEvent)
            .where(models.NegotiationEvent.negotiation_id == negotiation.id)
            .order_by(models.NegotiationEvent.seq)
        )
        print("  events   (listing column is what scopes a seller's view):")
        for event in events:
            print(
                f"    {event.seq:>3} {event.type:<20}{event.actor:<8}"
                f"{(event.listing_id or '-')[:8]:<10}{event.message[:58]}"
            )


def dump_deals(db) -> None:
    heading("DEALS")
    deals = list(db.scalars(select(models.Deal).order_by(models.Deal.created_at)))
    if not deals:
        print("(none)")
        return
    for deal in deals:
        seller = db.get(models.Business, deal.seller_business_id)
        buyer = db.get(models.Business, deal.buyer_business_id)
        print(
            f"\n{deal.id}  status={deal.status}  stock_released={deal.stock_released}"
        )
        print(f"  {seller.name[:40]}  ->  {buyer.name[:40]}")
        print(
            f"  {deal.quantity_kg} kg {deal.material_id} at "
            f"{rupees(deal.unit_price_paise_per_tonne)}/t"
        )
        print(
            f"  material {rupees(deal.material_paise)}  + freight "
            f"{rupees(deal.freight_paise)}  = buyer pays {rupees(deal.buyer_total_paise)}"
        )
        print(f"  seller receives {rupees(deal.seller_receives_paise)}")
        print(f"  intended use: {deal.intended_use[:70]}")


def dump_reference(db) -> None:
    heading("REFERENCE DATA (from dataset/, after the importer's fixes)")
    counts = [
        ("districts", models.District),
        ("district distances", models.DistrictDistance),
        ("materials", models.Material),
        ("receiving processes", models.ReceivingProcess),
        ("enterprises", models.Enterprise),
        ("enterprise byproducts", models.EnterpriseByproduct),
        ("symbiosis pathways", models.SymbiosisPathway),
        ("compatibility flags", models.MaterialCompatibilityFlag),
    ]
    for label, model in counts:
        print(f"  {label:<24}{db.scalar(select(func.count()).select_from(model)):>8}")

    resolved = db.scalar(
        select(func.count())
        .select_from(models.Enterprise)
        .where(models.Enterprise.name_source == "udyam")
    )
    unresolved = db.scalar(
        select(func.count())
        .select_from(models.Enterprise)
        .where(models.Enterprise.name_source == "unresolved")
    )
    print(f"\n  enterprise names recovered {resolved}, unresolved {unresolved}")

    print("\n  rice husk producers by NIC5 (fix 2 and 3 - only real rice millers):")
    rows = db.execute(
        select(models.Enterprise.nic5_code, models.Enterprise.nic_description, func.count())
        .join(
            models.EnterpriseByproduct,
            models.EnterpriseByproduct.enterprise_id == models.Enterprise.id,
        )
        .where(models.EnterpriseByproduct.material_id == "rice_husk")
        .group_by(models.Enterprise.nic5_code, models.Enterprise.nic_description)
    ).all()
    for code, description, count in rows:
        print(f"    {code}  {description[:44]:<46}{count:>6}")


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------


def check(db) -> int:
    heading("INVARIANT CHECKS")
    failures: list[str] = []

    def assert_(condition: bool, message: str) -> None:
        status = "ok  " if condition else "FAIL"
        print(f"  [{status}] {message}")
        if not condition:
            failures.append(message)

    # One deal per requirement, ever.
    duplicates = db.execute(
        select(models.Deal.requirement_id, func.count())
        .group_by(models.Deal.requirement_id)
        .having(func.count() > 1)
    ).all()
    assert_(not duplicates, "no requirement has more than one deal")

    # No listing was oversold.
    negative = db.scalar(
        select(func.count())
        .select_from(models.Listing)
        .where(models.Listing.available_quantity_kg < 0)
    )
    assert_(negative == 0, "no listing has negative available stock")

    deals = list(db.scalars(select(models.Deal)))
    for deal in deals:
        listing = db.get(models.Listing, deal.listing_id)
        requirement = db.get(models.Requirement, deal.requirement_id)

        assert_(
            deal.unit_price_paise_per_tonne >= listing.seller_floor_paise_per_tonne,
            f"deal {deal.id[:8]}: agreed price is at or above the seller's floor",
        )
        assert_(
            deal.buyer_total_paise <= requirement.buyer_max_total_paise,
            f"deal {deal.id[:8]}: delivered total is within the buyer's budget",
        )
        assert_(
            deal.material_paise + deal.freight_paise == deal.buyer_total_paise,
            f"deal {deal.id[:8]}: cost arithmetic adds up",
        )
        assert_(
            deal.seller_receives_paise == deal.material_paise,
            f"deal {deal.id[:8]}: seller proceeds equal the material cost",
        )
        expected = round(
            deal.unit_price_paise_per_tonne * deal.quantity_kg / 1000 + 1e-9
        )
        assert_(
            abs(deal.material_paise - expected) <= 1,
            f"deal {deal.id[:8]}: material cost matches price x quantity",
        )
        if deal.status != "cancelled":
            assert_(
                requirement.status == "fulfilled",
                f"deal {deal.id[:8]}: its requirement is marked fulfilled",
            )

    # A terminal negotiation either has a deal or a reason it does not.
    for negotiation in db.scalars(select(models.Negotiation)):
        if negotiation.status == "agreed":
            assert_(
                negotiation.deal_id is not None,
                f"negotiation {negotiation.id[:8]}: agreed run has a deal",
            )
        elif negotiation.status in ("no_deal", "failed"):
            assert_(
                negotiation.failure_code is not None and negotiation.deal_id is None,
                f"negotiation {negotiation.id[:8]}: "
                f"{negotiation.status} run has a reason and no deal",
            )

    # No seller offer ever went below that seller's own floor.
    below_floor = []
    for offer in db.scalars(select(models.Offer).where(models.Offer.author == "seller")):
        listing = db.get(models.Listing, offer.listing_id)
        if offer.unit_price_paise_per_tonne < listing.seller_floor_paise_per_tonne:
            below_floor.append(offer.id[:8])
    assert_(not below_floor, "no seller offer is below that seller's floor")

    # No private limit appears in any persisted prose.
    #
    # A private floor that happens to equal some *public* asking price cannot be
    # judged by a substring search: seeing it in an offer proves nothing either
    # way. Those values are reported as ambiguous rather than counted as a leak,
    # and the seed deliberately avoids creating any.
    listings = list(db.scalars(select(models.Listing)))
    requirements = list(db.scalars(select(models.Requirement)))
    offers = list(db.scalars(select(models.Offer)))

    public_values = {listing.asking_price_paise_per_tonne for listing in listings}
    public_values |= {listing.available_quantity_kg for listing in listings}
    public_values |= {
        option.freight_paise for option in db.scalars(select(models.TransportOption))
    }
    # An offer's price and delivered total are disclosed to the counterparty by
    # definition - that is what an offer is. They belong in the public set, or
    # every event line quoting an offer reads as a leak.
    public_values |= {offer.unit_price_paise_per_tonne for offer in offers}
    public_values |= {offer.buyer_total_paise for offer in offers}

    private_values = {listing.seller_floor_paise_per_tonne for listing in listings}
    private_values |= {r.buyer_max_total_paise for r in requirements}

    ambiguous = private_values & public_values
    checkable = private_values - public_values

    leaked = []
    for offer in offers:
        for value in checkable:
            if str(value) in offer.explanation:
                leaked.append(f"offer {offer.id[:8]} mentions {value}")
    for event in db.scalars(select(models.NegotiationEvent)):
        for value in checkable:
            if str(value) in event.message:
                leaked.append(f"event seq {event.seq} mentions {value}")

    assert_(not leaked, "no private limit appears in an explanation or event message")
    for item in leaked:
        print(f"         {item}")
    if ambiguous:
        print(
            f"         note: {len(ambiguous)} private value(s) also occur as public "
            f"prices and could not be checked: {sorted(ambiguous)}"
        )

    # The SHA-256 audit chain must recompute from the stored rows alone.
    from app.services.coordinator import verify_offer_chain

    for negotiation in db.scalars(select(models.Negotiation)):
        intact, detail = verify_offer_chain(db, negotiation.id)
        assert_(
            intact,
            f"negotiation {negotiation.id[:8]}: offer audit chain intact ({detail})",
        )

    # Event sequences are unique and ascending per negotiation.
    for negotiation in db.scalars(select(models.Negotiation)):
        seqs = [
            event.seq
            for event in db.scalars(
                select(models.NegotiationEvent)
                .where(models.NegotiationEvent.negotiation_id == negotiation.id)
                .order_by(models.NegotiationEvent.seq)
            )
        ]
        if seqs:
            assert_(
                seqs == sorted(set(seqs)),
                f"negotiation {negotiation.id[:8]}: event sequence is unique and ascending",
            )

    print(f"\n{len(failures)} failure(s).")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="inspect_db")
    parser.add_argument("--check", action="store_true", help="run invariant checks only")
    parser.add_argument("--reference", action="store_true", help="reference data only")
    parser.add_argument("--negotiation", help="focus one negotiation (id or prefix)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.check:
            return check(db)
        if args.reference:
            dump_reference(db)
            return 0
        if args.negotiation:
            dump_negotiations(db, args.negotiation)
            return 0

        dump_businesses(db)
        dump_listings(db)
        dump_requirements(db)
        dump_transport(db)
        dump_negotiations(db)
        dump_deals(db)
        return check(db)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
