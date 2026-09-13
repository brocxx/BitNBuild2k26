"""Listing routes.

Public reads return `Listing`, which has no seller floor field. Only the /me
route returns `OwnerListing`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api import schemas
from app.db import models
from app.deps import CurrentUserDep, DbDep
from app.errors import conflict, forbidden, invalid, not_found
from app.services.pagination import apply_cursor, build_page, clamp_limit
from app.services.serializers import to_listing, to_owner_listing

router = APIRouter(tags=["listings"])


def _load_listing(db, listing_id: str) -> models.Listing:
    listing = db.get(models.Listing, listing_id)
    if listing is None:
        raise not_found("Listing not found.", listing_id=listing_id)
    return listing


@router.get("/listings", response_model=schemas.Page[schemas.Listing])
def list_listings(
    db: DbDep,
    current: CurrentUserDep,
    material_id: str | None = None,
    district: str | None = None,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> schemas.Page[schemas.Listing]:
    page_size = clamp_limit(limit)
    stmt = select(models.Listing).where(models.Listing.status == "open")
    if material_id:
        stmt = stmt.where(models.Listing.material_id == material_id)
    if district:
        stmt = stmt.where(models.Listing.district == district)
    stmt = apply_cursor(stmt, models.Listing, cursor).limit(page_size + 1)
    rows = list(db.scalars(stmt))
    return schemas.Page[schemas.Listing](**build_page(rows, page_size, to_listing))


@router.get("/listings/{listing_id}", response_model=schemas.Listing)
def get_listing(listing_id: str, db: DbDep, current: CurrentUserDep) -> schemas.Listing:
    return to_listing(_load_listing(db, listing_id))


@router.get("/me/listings", response_model=schemas.Page[schemas.OwnerListing])
def my_listings(
    db: DbDep,
    current: CurrentUserDep,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> schemas.Page[schemas.OwnerListing]:
    page_size = clamp_limit(limit)
    stmt = select(models.Listing).where(
        models.Listing.seller_business_id == current.business_id
    )
    stmt = apply_cursor(stmt, models.Listing, cursor).limit(page_size + 1)
    rows = list(db.scalars(stmt))
    return schemas.Page[schemas.OwnerListing](
        **build_page(rows, page_size, to_owner_listing)
    )


@router.post("/listings", response_model=schemas.OwnerListing, status_code=201)
def create_listing(
    payload: schemas.ListingCreate, db: DbDep, current: CurrentUserDep
) -> schemas.OwnerListing:
    material = db.get(models.Material, payload.material_id)
    if material is None:
        raise invalid("Unknown material_id.", field="material_id")

    location = payload.location
    listing = models.Listing(
        # The owner is taken from the verified token, never from the body.
        seller_business_id=current.business_id,
        material_id=payload.material_id,
        available_quantity_kg=payload.available_quantity_kg,
        asking_price_paise_per_tonne=payload.asking_price_paise_per_tonne,
        seller_floor_paise_per_tonne=payload.seller_floor_paise_per_tonne,
        moisture_pct=payload.moisture_pct,
        contamination_notes=payload.contamination_notes,
        pickup_start=payload.pickup_window.start,
        pickup_end=payload.pickup_window.end,
        district=location.district if location else current.business.district,
        lat=location.lat if location else current.business.lat,
        lon=location.lon if location else current.business.lon,
        location_precision=(
            location.precision if location else current.business.location_precision
        ),
        negotiation_strategy=payload.negotiation_strategy,
        status="open",
    )
    if not current.business.is_seller:
        current.business.is_seller = True
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return to_owner_listing(listing)


@router.patch("/listings/{listing_id}", response_model=schemas.OwnerListing)
def update_listing(
    listing_id: str,
    payload: schemas.ListingUpdate,
    db: DbDep,
    current: CurrentUserDep,
) -> schemas.OwnerListing:
    listing = _load_listing(db, listing_id)
    if listing.seller_business_id != current.business_id:
        raise forbidden("Only the seller can modify this listing.")

    # A listing tied up in a live negotiation cannot move under the agents.
    live = db.scalar(
        select(models.NegotiationCandidate)
        .join(
            models.Negotiation,
            models.Negotiation.id == models.NegotiationCandidate.negotiation_id,
        )
        .where(
            models.NegotiationCandidate.listing_id == listing.id,
            models.Negotiation.status.in_(["queued", "running"]),
        )
    )
    if live is not None:
        raise conflict(
            "NEGOTIATION_IN_PROGRESS",
            "This listing is part of a running negotiation and cannot be changed yet.",
        )

    if payload.asking_price_paise_per_tonne is not None:
        listing.asking_price_paise_per_tonne = payload.asking_price_paise_per_tonne
    if payload.seller_floor_paise_per_tonne is not None:
        listing.seller_floor_paise_per_tonne = payload.seller_floor_paise_per_tonne
    if payload.pickup_window is not None:
        listing.pickup_start = payload.pickup_window.start
        listing.pickup_end = payload.pickup_window.end
    if payload.status is not None:
        listing.status = payload.status

    if listing.seller_floor_paise_per_tonne > listing.asking_price_paise_per_tonne:
        raise invalid(
            "seller_floor_paise_per_tonne cannot exceed asking_price_paise_per_tonne.",
            field="seller_floor_paise_per_tonne",
        )

    listing.version += 1
    db.commit()
    db.refresh(listing)
    return to_owner_listing(listing)
