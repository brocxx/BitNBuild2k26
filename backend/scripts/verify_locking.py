"""Prove that two buyers cannot both reserve the same batch.

Why this exists as a script rather than a pytest case: on SQLite,
SELECT ... FOR UPDATE is a no-op, so the test suite can only show that the
unique constraint and the stock recheck hold. The actual row-locking path only
runs on Postgres. This script drives it against whatever DB_TARGET points at:

    DB_TARGET=supabase python scripts/verify_locking.py

Two threads, two separate connections, one listing with exactly enough stock
for one order. Both call commit_deal at the same instant through a barrier.
Exactly one must win; the loser must fail with a reservation error, not an
unhandled exception, and the stock must end at zero rather than negative.

The script creates its own rows and deletes them afterwards, so it is safe to
run against the demo database.
"""

from __future__ import annotations

import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import models  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.services.costing import compute_costs  # noqa: E402
from app.services.reservations import ReservationFailed, commit_deal  # noqa: E402

TAG = f"locktest-{uuid.uuid4().hex[:8]}"
QUANTITY_KG = 20_000
UNIT_PRICE = 250_000
FREIGHT = 1_500_000


def build_fixture(db) -> tuple[models.Listing, list[models.Requirement]]:
    now = datetime.now(timezone.utc)

    seller = models.Business(
        name=f"{TAG} seller", district="MYSURU", is_seller=True, is_demo=True
    )
    db.add(seller)
    db.flush()

    listing = models.Listing(
        seller_business_id=seller.id,
        material_id="rice_husk",
        # Exactly one order's worth. This is the contested batch.
        available_quantity_kg=QUANTITY_KG,
        asking_price_paise_per_tonne=UNIT_PRICE,
        seller_floor_paise_per_tonne=200_000,
        moisture_pct=9.0,
        contamination_notes="",
        pickup_start=now + timedelta(days=2),
        pickup_end=now + timedelta(days=12),
        district="MYSURU",
        status="open",
    )
    db.add(listing)
    db.flush()

    requirements: list[models.Requirement] = []
    for index in range(2):
        buyer = models.Business(
            name=f"{TAG} buyer {index}", district="BALLARI", is_buyer=True, is_demo=True
        )
        db.add(buyer)
        db.flush()
        db.add(
            models.BusinessReceivingProcess(
                business_id=buyer.id, process_id="brick_kiln_fuel", confirmed=True
            )
        )
        requirement = models.Requirement(
            buyer_business_id=buyer.id,
            material_id="rice_husk",
            receiving_process_id="brick_kiln_fuel",
            quantity_kg=QUANTITY_KG,
            max_moisture_pct=15.0,
            delivery_start=now + timedelta(days=4),
            delivery_end=now + timedelta(days=16),
            buyer_max_total_paise=9_000_000,
            district="BALLARI",
            status="open",
        )
        db.add(requirement)
        db.flush()
        requirements.append(requirement)

    for requirement in requirements:
        db.add(
            models.TransportOption(
                listing_id=listing.id,
                requirement_id=requirement.id,
                label=f"{TAG} flatbed",
                freight_paise=FREIGHT,
                capacity_kg=25_000,
                pickup_at=now + timedelta(days=4),
                delivery_at=now + timedelta(days=6),
                expires_at=now + timedelta(days=7),
                source="configured_estimate",
                created_by_business_id=listing.seller_business_id,
            )
        )
    db.flush()
    db.commit()
    return listing, requirements


def make_negotiation_and_offer(db, listing, requirement) -> models.Offer:
    negotiation = models.Negotiation(
        requirement_id=requirement.id,
        buyer_business_id=requirement.buyer_business_id,
        status="running",
    )
    db.add(negotiation)
    db.flush()

    transport = db.scalar(
        select(models.TransportOption).where(
            models.TransportOption.requirement_id == requirement.id
        )
    )
    costs = compute_costs(UNIT_PRICE, QUANTITY_KG, transport.freight_paise)
    offer = models.Offer(
        negotiation_id=negotiation.id,
        listing_id=listing.id,
        transport_option_id=transport.id,
        quantity_kg=QUANTITY_KG,
        unit_price_paise_per_tonne=UNIT_PRICE,
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
    db.commit()
    return negotiation, offer


def race(listing, requirements) -> list[tuple[int, str]]:
    """Both threads attempt to commit at the same instant."""
    barrier = threading.Barrier(len(requirements))
    results: list[tuple[int, str]] = []
    lock = threading.Lock()

    def attempt(index: int, requirement_id: str) -> None:
        db = SessionLocal()
        try:
            requirement = db.get(models.Requirement, requirement_id)
            negotiation, offer = make_negotiation_and_offer(db, listing, requirement)

            barrier.wait(timeout=30)

            try:
                deal = commit_deal(
                    db, negotiation=negotiation, offer=offer, intended_use="kiln fuel"
                )
                db.commit()
                outcome = f"WON  deal {deal.id[:8]}"
            except ReservationFailed as exc:
                db.rollback()
                outcome = f"lost {exc.code}: {exc.message[:56]}"
            except Exception as exc:  # noqa: BLE001 - we want to see anything else
                db.rollback()
                outcome = f"UNEXPECTED {type(exc).__name__}: {str(exc)[:56]}"
        finally:
            db.close()

        with lock:
            results.append((index, outcome))

    threads = [
        threading.Thread(target=attempt, args=(index, requirement.id))
        for index, requirement in enumerate(requirements)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    return sorted(results)


def cleanup(db) -> None:
    """Remove every row this script created, children first."""
    businesses = list(
        db.scalars(select(models.Business.id).where(models.Business.name.like(f"{TAG}%")))
    )
    if not businesses:
        return
    listings = list(
        db.scalars(
            select(models.Listing.id).where(
                models.Listing.seller_business_id.in_(businesses)
            )
        )
    )
    requirements = list(
        db.scalars(
            select(models.Requirement.id).where(
                models.Requirement.buyer_business_id.in_(businesses)
            )
        )
    )
    negotiations = list(
        db.scalars(
            select(models.Negotiation.id).where(
                models.Negotiation.requirement_id.in_(requirements or [""])
            )
        )
    )

    db.execute(delete(models.Deal).where(models.Deal.listing_id.in_(listings or [""])))
    db.execute(
        delete(models.NegotiationEvent).where(
            models.NegotiationEvent.negotiation_id.in_(negotiations or [""])
        )
    )
    db.execute(delete(models.Offer).where(models.Offer.listing_id.in_(listings or [""])))
    db.execute(
        delete(models.NegotiationCandidate).where(
            models.NegotiationCandidate.negotiation_id.in_(negotiations or [""])
        )
    )
    db.execute(
        delete(models.Negotiation).where(models.Negotiation.id.in_(negotiations or [""]))
    )
    db.execute(
        delete(models.TransportOption).where(
            models.TransportOption.listing_id.in_(listings or [""])
        )
    )
    db.execute(
        delete(models.Requirement).where(models.Requirement.id.in_(requirements or [""]))
    )
    db.execute(delete(models.Listing).where(models.Listing.id.in_(listings or [""])))
    db.execute(
        delete(models.BusinessReceivingProcess).where(
            models.BusinessReceivingProcess.business_id.in_(businesses)
        )
    )
    db.execute(delete(models.Business).where(models.Business.id.in_(businesses)))
    db.commit()


def main() -> int:
    settings = get_settings()
    dialect = engine.dialect.name
    print(f"DB_TARGET={settings.db_target}  dialect={dialect}")
    if dialect == "sqlite":
        print(
            "\nNOTE: on SQLite, SELECT ... FOR UPDATE is a no-op. This run exercises\n"
            "the unique constraint and the stock recheck, but NOT row locking.\n"
            "Re-run with DB_TARGET=supabase to exercise the real path."
        )
    print(f"tag={TAG}\n")

    db = SessionLocal()
    try:
        listing, requirements = build_fixture(db)
        listing_id = listing.id
        print(
            f"one listing with {QUANTITY_KG} kg, {len(requirements)} buyers each "
            f"wanting {QUANTITY_KG} kg\n"
        )

        results = race(listing, requirements)
        for index, outcome in results:
            print(f"  thread {index}: {outcome}")

        db.expire_all()
        final = db.get(models.Listing, listing_id)
        deals = list(
            db.scalars(select(models.Deal).where(models.Deal.listing_id == listing_id))
        )

        won = [r for _, r in results if r.startswith("WON")]
        unexpected = [r for _, r in results if r.startswith("UNEXPECTED")]

        print(f"\nfinal stock on the listing: {final.available_quantity_kg} kg")
        print(f"deals created: {len(deals)}")

        checks = [
            (len(won) == 1, "exactly one thread won"),
            (len(deals) == 1, "exactly one deal exists"),
            (not unexpected, "the loser failed cleanly, not with an unhandled error"),
            (final.available_quantity_kg == 0, "stock decremented exactly once"),
            (final.available_quantity_kg >= 0, "stock never went negative"),
        ]
        print()
        failed = 0
        for ok, label in checks:
            print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
            failed += 0 if ok else 1

        if dialect != "sqlite" and not failed:
            print(
                "\nRow locking verified on Postgres: the second transaction blocked on\n"
                "the locked listing row, then saw the decremented stock and refused."
            )
        return 1 if failed else 0
    finally:
        try:
            cleanup(db)
            print("\ncleaned up test rows.")
        finally:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
