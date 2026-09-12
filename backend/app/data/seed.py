"""A working rice-husk scenario, built from real enterprises in the dataset.

What is real: the businesses are genuine UDYAM-registered rice mills, brick
kilns and sawmills, with their registered names recovered by the importer, in
their registered districts, and the straight-line district distances shown
alongside each transport option.

What is configured demo data, and is labelled as such everywhere it appears:
asking prices, seller floors, buyer budgets, batch quantities, moisture
readings and freight charges. No supplier or transporter has quoted these. The
freight amounts are entered as `configured_estimate`, never derived from the
district distance matrix.

All dates are generated relative to the moment the seed runs, so the demo
fixtures cannot expire before the presentation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import models

logger = logging.getLogger(__name__)

DEMO_DOMAIN = "demo.bitnbuild.local"

RICE_MILL_NIC5 = ("10612", "10619")
BRICK_KILN_NIC5 = ("23921", "23912")
SAWMILL_NIC5 = ("16101", "16109")

REQUESTED_QUANTITY_KG = 20_000


@dataclass(frozen=True)
class ListingPlan:
    """One seeded listing. Every money value here is configured demo data."""

    asking_price_paise_per_tonne: int
    seller_floor_paise_per_tonne: int
    available_quantity_kg: int
    moisture_pct: float
    contamination_notes: str
    # Full-shipment freight for the standard slot, and for the expedited slot.
    standard_freight_paise: int
    expedited_freight_paise: int
    note: str


# Six listings: three that qualify, three that demonstrate a distinct exclusion
# reason on the Matches screen. The first mill is the closest to the buyer and
# deliberately the most expensive delivered, so the demo can show that the
# nearest seller is not automatically the best option.
#
# Every seller floor is chosen to be a number that appears nowhere in public
# data - not as another listing's asking price, not as a freight charge, not as
# a quantity. Without that, a floor value could show up legitimately in an
# offer (as some other seller's public asking price) and there would be no way
# to tell a real leak from a coincidence. scripts/inspect_db.py --check relies
# on this.
LISTING_PLANS: list[ListingPlan] = [
    ListingPlan(305_000, 263_500, 60_000, 9.5, "", 1_500_000, 1_850_000, "nearest, priciest"),
    ListingPlan(262_000, 241_700, 45_000, 11.0, "", 2_150_000, 2_500_000, "mid"),
    ListingPlan(275_000, 237_300, 40_000, 10.2, "", 1_800_000, 2_100_000, "cheapest at floor"),
    ListingPlan(
        250_000, 229_100, 50_000, 18.5, "", 1_700_000, 2_000_000, "excluded: moisture"
    ),
    ListingPlan(
        255_000,
        234_600,
        38_000,
        10.0,
        "Visible field soil carry-over from open yard storage.",
        1_900_000,
        2_200_000,
        "excluded: needs quality review",
    ),
    ListingPlan(
        248_000, 227_400, 8_000, 9.8, "", 1_600_000, 1_900_000, "excluded: quantity"
    ),
]

# Configured demo budgets. The first comfortably admits an agreement against at
# least one seller floor; the second cannot be met without breaching a floor,
# which is the honest no-deal case in the demo.
FEASIBLE_BUDGET_PAISE = 7_000_000
INFEASIBLE_BUDGET_PAISE = 5_000_000


@dataclass
class SeedReport:
    businesses: int = 0
    users: int = 0
    listings: int = 0
    requirements: int = 0
    transport_options: int = 0
    logins: list[str] = None  # type: ignore[assignment]

    def summary(self) -> str:
        lines = [
            f"businesses        {self.businesses}",
            f"users             {self.users}",
            f"listings          {self.listings}",
            f"requirements      {self.requirements}",
            f"transport options {self.transport_options}",
            "",
            "Demo logins (AUTH_MODE=dev) - send as: Authorization: Bearer dev:<email>",
        ]
        lines.extend(f"  dev:{email}" for email in (self.logins or []))
        return "\n".join(lines)


def _distance_m(db: Session, from_district: str, to_district: str) -> int | None:
    row = db.scalar(
        select(models.DistrictDistance).where(
            models.DistrictDistance.from_district == from_district,
            models.DistrictDistance.to_district == to_district,
        )
    )
    return row.distance_m if row else None


# A unit registered under NIC 23921 ("Manufacture of bricks") but trading as a
# cement or RCC block maker has no kiln to burn husk in. The NIC code alone
# cannot tell them apart, so the demo avoids picking one as the kiln buyer -
# otherwise the screen would show a cement business buying kiln fuel.
NON_KILN_NAME_KEYWORDS = ("CEMENT", "RCC", "CONCRETE", "HUME", "INTERLOCK", "PAVER")


def _pick_enterprises(
    db: Session,
    nic5_codes: tuple[str, ...],
    count: int,
    exclude_ids: set[str],
    exclude_name_keywords: tuple[str, ...] = (),
) -> list[models.Enterprise]:
    """Deterministically choose enterprises, preferring distinct districts."""
    rows = list(
        db.scalars(
            select(models.Enterprise)
            .where(
                models.Enterprise.nic5_code.in_(nic5_codes),
                models.Enterprise.name_source == "udyam",
            )
            .order_by(models.Enterprise.id)
        )
    )
    if exclude_name_keywords:
        rows = [
            row
            for row in rows
            if not any(keyword in row.name.upper() for keyword in exclude_name_keywords)
        ]
    chosen: list[models.Enterprise] = []
    seen_districts: set[str] = set()
    for row in rows:
        if row.id in exclude_ids or row.district in seen_districts:
            continue
        chosen.append(row)
        seen_districts.add(row.district)
        if len(chosen) == count:
            break
    # Fall back to same-district enterprises only if the dataset is too thin.
    if len(chosen) < count:
        for row in rows:
            if row.id in exclude_ids or row in chosen:
                continue
            chosen.append(row)
            if len(chosen) == count:
                break
    return chosen


def _business_from_enterprise(
    enterprise: models.Enterprise, *, is_buyer: bool, is_seller: bool
) -> models.Business:
    return models.Business(
        name=enterprise.name,
        enterprise_id=enterprise.id,
        is_buyer=is_buyer,
        is_seller=is_seller,
        district=enterprise.district,
        lat=enterprise.lat,
        lon=enterprise.lon,
        location_precision="district",
        is_demo=True,
    )


def clear_operational_data(db: Session) -> None:
    """Wipe operational tables so the seed is repeatable. Reference data stays."""
    for model in (
        models.Deal,
        models.NegotiationEvent,
        models.Offer,
        models.NegotiationCandidate,
        models.Negotiation,
        models.IdempotencyKey,
        models.TransportOption,
        models.Requirement,
        models.Listing,
        models.AppUser,
        models.BusinessReceivingProcess,
        models.Business,
    ):
        db.execute(delete(model))
    db.flush()


def seed_demo(db: Session, now: datetime | None = None) -> SeedReport:
    now = now or datetime.now(timezone.utc)
    report = SeedReport(logins=[])

    clear_operational_data(db)

    mills = _pick_enterprises(db, RICE_MILL_NIC5, len(LISTING_PLANS), set())
    if not mills:
        raise RuntimeError(
            "No rice milling enterprises found. Run the reference import first."
        )
    kilns = _pick_enterprises(
        db,
        BRICK_KILN_NIC5,
        1,
        {m.id for m in mills},
        exclude_name_keywords=NON_KILN_NAME_KEYWORDS,
    )
    sawmills = _pick_enterprises(
        db, SAWMILL_NIC5, 1, {m.id for m in mills} | {k.id for k in kilns}
    )
    if not kilns or not sawmills:
        raise RuntimeError("Could not find a brick kiln and a sawmill to act as buyers.")

    kiln_enterprise = kilns[0]
    sawmill_enterprise = sawmills[0]

    # Order the mills by straight-line distance to the buyer so the listing
    # plans line up with the "nearest is not cheapest" story.
    mills.sort(
        key=lambda e: (
            _distance_m(db, e.district, kiln_enterprise.district) or 10**9,
            e.id,
        )
    )

    # -- buyers ------------------------------------------------------------
    kiln = _business_from_enterprise(kiln_enterprise, is_buyer=True, is_seller=False)
    sawmill = _business_from_enterprise(
        sawmill_enterprise, is_buyer=True, is_seller=False
    )
    db.add_all([kiln, sawmill])
    db.flush()
    db.add_all(
        [
            models.BusinessReceivingProcess(
                business_id=kiln.id, process_id="brick_kiln_fuel", confirmed=True
            ),
            models.BusinessReceivingProcess(
                business_id=sawmill.id,
                process_id="timber_drying_boiler_fuel",
                confirmed=True,
            ),
        ]
    )
    report.businesses += 2

    # -- sellers and listings ---------------------------------------------
    listings: list[models.Listing] = []
    for enterprise, plan in zip(mills, LISTING_PLANS, strict=False):
        seller = _business_from_enterprise(enterprise, is_buyer=False, is_seller=True)
        db.add(seller)
        db.flush()
        report.businesses += 1

        listing = models.Listing(
            seller_business_id=seller.id,
            material_id="rice_husk",
            available_quantity_kg=plan.available_quantity_kg,
            asking_price_paise_per_tonne=plan.asking_price_paise_per_tonne,
            seller_floor_paise_per_tonne=plan.seller_floor_paise_per_tonne,
            moisture_pct=plan.moisture_pct,
            contamination_notes=plan.contamination_notes,
            pickup_start=now + timedelta(days=2),
            pickup_end=now + timedelta(days=12),
            district=enterprise.district,
            lat=enterprise.lat,
            lon=enterprise.lon,
            location_precision="district",
            status="open",
        )
        db.add(listing)
        listings.append(listing)
        report.listings += 1

        email = f"seller{report.listings}@{DEMO_DOMAIN}"
        db.add(models.AppUser(email=email, business_id=seller.id, is_demo=True))
        report.users += 1
        report.logins.append(email)
    db.flush()

    # -- requirements ------------------------------------------------------
    feasible = models.Requirement(
        buyer_business_id=kiln.id,
        material_id="rice_husk",
        receiving_process_id="brick_kiln_fuel",
        quantity_kg=REQUESTED_QUANTITY_KG,
        max_moisture_pct=15.0,
        delivery_start=now + timedelta(days=4),
        delivery_end=now + timedelta(days=16),
        buyer_max_total_paise=FEASIBLE_BUDGET_PAISE,
        district=kiln.district,
        lat=kiln.lat,
        lon=kiln.lon,
        location_precision="district",
        status="open",
    )
    infeasible = models.Requirement(
        buyer_business_id=kiln.id,
        material_id="rice_husk",
        receiving_process_id="brick_kiln_fuel",
        quantity_kg=REQUESTED_QUANTITY_KG,
        max_moisture_pct=15.0,
        delivery_start=now + timedelta(days=4),
        delivery_end=now + timedelta(days=16),
        buyer_max_total_paise=INFEASIBLE_BUDGET_PAISE,
        district=kiln.district,
        lat=kiln.lat,
        lon=kiln.lon,
        location_precision="district",
        status="open",
    )
    db.add_all([feasible, infeasible])
    db.flush()
    report.requirements = 2

    for business, index in ((kiln, 1), (sawmill, 2)):
        email = f"buyer{index}@{DEMO_DOMAIN}"
        db.add(models.AppUser(email=email, business_id=business.id, is_demo=True))
        report.users += 1
        report.logins.append(email)

    # -- transport options -------------------------------------------------
    for listing, plan in zip(listings, LISTING_PLANS, strict=False):
        distance_m = _distance_m(db, listing.district, kiln.district)
        for requirement in (feasible, infeasible):
            db.add(
                models.TransportOption(
                    listing_id=listing.id,
                    requirement_id=requirement.id,
                    label="Standard flatbed, 2-day transit",
                    freight_paise=plan.standard_freight_paise,
                    capacity_kg=25_000,
                    pickup_at=now + timedelta(days=4),
                    delivery_at=now + timedelta(days=6),
                    expires_at=now + timedelta(days=7),
                    source="configured_estimate",
                    distance_m=distance_m,
                    distance_basis="district_straight_line",
                    created_by_business_id=listing.seller_business_id,
                )
            )
            db.add(
                models.TransportOption(
                    listing_id=listing.id,
                    requirement_id=requirement.id,
                    label="Expedited flatbed, next-day transit",
                    freight_paise=plan.expedited_freight_paise,
                    capacity_kg=25_000,
                    pickup_at=now + timedelta(days=4),
                    delivery_at=now + timedelta(days=5),
                    expires_at=now + timedelta(days=7),
                    source="configured_estimate",
                    distance_m=distance_m,
                    distance_basis="district_straight_line",
                    created_by_business_id=listing.seller_business_id,
                )
            )
            report.transport_options += 2

    db.commit()
    return report
