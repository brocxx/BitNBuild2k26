"""Test fixtures.

Environment is configured before any app module is imported, because the
engine is built at import time from the settings.

Tests build a small hand-made reference set rather than importing the full
7,933-enterprise dataset; test_import.py covers the real importer separately.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_TMP_DB = Path(tempfile.mkdtemp(prefix="bitnbuild-tests-")) / "test.db"

# DB_TARGET must be pinned, not just DATABASE_URL. Settings.active_database_url
# follows DB_TARGET, so a developer whose .env says DB_TARGET=supabase would
# otherwise run this suite against the shared team database - and the
# fresh_database fixture below calls drop_all() before every single test.
# That happened once during development and wiped the Supabase project.
os.environ["DB_TARGET"] = "local"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["AUTH_MODE"] = "dev"
os.environ["AGENT_MODE"] = "fake"
os.environ["NEGOTIATION_RUN_INLINE"] = "true"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["MAX_ROUNDS_PER_CANDIDATE"] = "4"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.data import fixes  # noqa: E402
from app.db import models  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

# Belt and braces: whatever the environment says, refuse to run destructive
# fixtures against anything that is not a throwaway local file. Pinning the
# env var above is the fix; this is the guard that makes it impossible to
# regress silently.
_RESOLVED_URL = get_settings().active_database_url
if not _RESOLVED_URL.startswith("sqlite"):
    raise RuntimeError(
        "The test suite drops and recreates every table, so it refuses to run "
        f"against a non-SQLite database. Resolved to: {_RESOLVED_URL.split('@')[-1]}"
    )
if engine.url.get_backend_name() != "sqlite":
    raise RuntimeError(
        f"Test engine is bound to {engine.url.get_backend_name()}, not sqlite."
    )

QUANTITY_KG = 20_000


@pytest.fixture(autouse=True)
def fresh_database(request):
    """Empty schema per test.

    Tests marked `own_database` manage their own schema - the importer tests
    load the full dataset once per module and must not have it dropped between
    assertions.
    """
    if "own_database" in request.keywords:
        yield
        return
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def auth(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer dev:{email}"}


@dataclass
class Scenario:
    buyer: models.Business
    buyer_email: str
    sellers: list[models.Business]
    seller_emails: list[str]
    listings: list[models.Listing]
    requirement: models.Requirement
    transport: dict[str, models.TransportOption]
    now: datetime


def seed_reference(db: Session) -> None:
    for material_id, (name, category, supported) in fixes.MATERIALS.items():
        db.add(
            models.Material(id=material_id, name=name, category=category, is_supported=supported)
        )
    for process_id, (name, description, codes) in fixes.RECEIVING_PROCESSES.items():
        db.add(
            models.ReceivingProcess(
                id=process_id,
                name=name,
                description=description,
                nic5_codes=",".join(sorted(codes)),
            )
        )
    db.flush()

    for process_id, material_ids in fixes.PROCESS_MATERIALS.items():
        for material_id in material_ids:
            db.add(
                models.ReceivingProcessMaterial(process_id=process_id, material_id=material_id)
            )

    for material_id, process_id, keyword, verdict, note in fixes.COMPATIBILITY_FLAGS:
        db.add(
            models.MaterialCompatibilityFlag(
                material_id=material_id,
                receiving_process_id=process_id,
                contamination_keyword=keyword,
                verdict=verdict,
                note=note,
            )
        )

    db.add(
        models.SymbiosisPathway(
            producer_nic2="10",
            producer_industry="Food Processing (Rice Milling)",
            material_id="rice_husk",
            byproduct_name="Rice Husk",
            byproduct_type="Solid Biomass",
            receiver_nic2="23",
            receiver_industry="Non-Metallic Minerals (Brick Manufacturing)",
            use_case="Fuel for brick kiln firing; ash used as filler in the brick mix",
            receiving_process_id="brick_kiln_fuel",
        )
    )
    db.add(models.District(name="MYSURU", hq_town="Mysuru", lat=12.2958, lon=76.6394))
    db.add(models.District(name="DAVANGERE", hq_town="Davangere", lat=14.4644, lon=75.9218))
    db.flush()


def make_business(
    db: Session,
    name: str,
    email: str,
    *,
    is_buyer: bool = False,
    is_seller: bool = False,
    district: str = "MYSURU",
    processes: tuple[str, ...] = (),
) -> models.Business:
    business = models.Business(
        name=name,
        is_buyer=is_buyer,
        is_seller=is_seller,
        district=district,
        lat=12.2958,
        lon=76.6394,
        location_precision="district",
    )
    db.add(business)
    db.flush()
    for process_id in processes:
        db.add(
            models.BusinessReceivingProcess(
                business_id=business.id, process_id=process_id, confirmed=True
            )
        )
    db.add(models.AppUser(email=email, business_id=business.id))
    db.flush()
    db.refresh(business)
    return business


def make_listing(
    db: Session,
    seller: models.Business,
    now: datetime,
    *,
    asking: int,
    floor: int,
    quantity_kg: int = 60_000,
    moisture_pct: float = 10.0,
    contamination_notes: str = "",
    material_id: str = "rice_husk",
    status: str = "open",
) -> models.Listing:
    listing = models.Listing(
        seller_business_id=seller.id,
        material_id=material_id,
        available_quantity_kg=quantity_kg,
        asking_price_paise_per_tonne=asking,
        seller_floor_paise_per_tonne=floor,
        moisture_pct=moisture_pct,
        contamination_notes=contamination_notes,
        pickup_start=now + timedelta(days=2),
        pickup_end=now + timedelta(days=12),
        district=seller.district,
        lat=seller.lat,
        lon=seller.lon,
        status=status,
    )
    db.add(listing)
    db.flush()
    return listing


def make_requirement(
    db: Session,
    buyer: models.Business,
    now: datetime,
    *,
    budget_paise: int,
    quantity_kg: int = QUANTITY_KG,
    max_moisture_pct: float = 15.0,
    material_id: str = "rice_husk",
    process_id: str = "brick_kiln_fuel",
) -> models.Requirement:
    requirement = models.Requirement(
        buyer_business_id=buyer.id,
        material_id=material_id,
        receiving_process_id=process_id,
        quantity_kg=quantity_kg,
        max_moisture_pct=max_moisture_pct,
        delivery_start=now + timedelta(days=4),
        delivery_end=now + timedelta(days=16),
        buyer_max_total_paise=budget_paise,
        district=buyer.district,
        lat=buyer.lat,
        lon=buyer.lon,
        status="open",
    )
    db.add(requirement)
    db.flush()
    return requirement


def make_transport(
    db: Session,
    listing: models.Listing,
    requirement: models.Requirement,
    now: datetime,
    *,
    freight_paise: int,
    capacity_kg: int = 25_000,
    label: str = "Standard flatbed",
    expires_in_days: int = 7,
    delivery_offset_days: int = 6,
) -> models.TransportOption:
    option = models.TransportOption(
        listing_id=listing.id,
        requirement_id=requirement.id,
        label=label,
        freight_paise=freight_paise,
        capacity_kg=capacity_kg,
        pickup_at=now + timedelta(days=4),
        delivery_at=now + timedelta(days=delivery_offset_days),
        expires_at=now + timedelta(days=expires_in_days),
        source="configured_estimate",
        distance_m=180_000,
        distance_basis="district_straight_line",
        created_by_business_id=listing.seller_business_id,
    )
    db.add(option)
    db.flush()
    return option


@pytest.fixture
def scenario(db: Session) -> Scenario:
    """Three eligible sellers, one buyer with a budget that admits a deal.

    Delivered cost at asking price:
        seller1  305000*20 + 1500000 = 7,600,000   (nearest, dearest)
        seller2  262000*20 + 2150000 = 7,390,000
        seller3  275000*20 + 1800000 = 7,300,000
    At the floors, all three can land under the 7,000,000 budget.

    Every private floor is deliberately a value that appears nowhere in public
    data, so the privacy tests can assert on the literal numbers without a
    coincidental collision with some other listing's asking price.
    """
    now = datetime.now(timezone.utc)
    seed_reference(db)

    buyer = make_business(
        db,
        "Demo Brick Kiln",
        "buyer@test.local",
        is_buyer=True,
        processes=("brick_kiln_fuel",),
    )

    specs = [
        ("Mill One", 305_000, 263_500, 1_500_000),
        ("Mill Two", 262_000, 241_700, 2_150_000),
        ("Mill Three", 275_000, 237_300, 1_800_000),
    ]

    requirement = make_requirement(db, buyer, now, budget_paise=7_000_000)

    sellers, emails, listings = [], [], []
    transport: dict[str, models.TransportOption] = {}
    for index, (name, asking, floor, freight) in enumerate(specs, start=1):
        email = f"seller{index}@test.local"
        seller = make_business(
            db, name, email, is_seller=True, district="DAVANGERE"
        )
        listing = make_listing(db, seller, now, asking=asking, floor=floor)
        transport[listing.id] = make_transport(
            db, listing, requirement, now, freight_paise=freight
        )
        sellers.append(seller)
        emails.append(email)
        listings.append(listing)

    db.commit()
    return Scenario(
        buyer=buyer,
        buyer_email="buyer@test.local",
        sellers=sellers,
        seller_emails=emails,
        listings=listings,
        requirement=requirement,
        transport=transport,
        now=now,
    )
