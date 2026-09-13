"""Requirement routes, transport options, and the matches analysis.

A requirement is only ever returned to its owner: it carries the buyer's
private budget, and even without it a competitor should not be able to read
another business's sourcing plans through an ID guess.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api import schemas
from app.db import models
from app.deps import CurrentUserDep, DbDep
from app.errors import forbidden, invalid, not_found
from app.services.matching import build_matches_response
from app.services.pagination import apply_cursor, build_page, clamp_limit
from app.services.serializers import to_owner_requirement, to_transport_option

router = APIRouter(tags=["requirements"])


def load_owned_requirement(db, requirement_id: str, business_id: str) -> models.Requirement:
    requirement = db.get(models.Requirement, requirement_id)
    if requirement is None:
        raise not_found("Requirement not found.", requirement_id=requirement_id)
    if requirement.buyer_business_id != business_id:
        # 403 rather than 404: the plan specifies forbidden for cross-business
        # access to private settings.
        raise forbidden("Only the buyer can view this requirement.")
    return requirement


@router.get("/me/requirements", response_model=schemas.Page[schemas.OwnerRequirement])
def my_requirements(
    db: DbDep,
    current: CurrentUserDep,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> schemas.Page[schemas.OwnerRequirement]:
    page_size = clamp_limit(limit)
    stmt = select(models.Requirement).where(
        models.Requirement.buyer_business_id == current.business_id
    )
    stmt = apply_cursor(stmt, models.Requirement, cursor).limit(page_size + 1)
    rows = list(db.scalars(stmt))
    return schemas.Page[schemas.OwnerRequirement](
        **build_page(rows, page_size, to_owner_requirement)
    )


@router.post("/requirements", response_model=schemas.OwnerRequirement, status_code=201)
def create_requirement(
    payload: schemas.RequirementCreate, db: DbDep, current: CurrentUserDep
) -> schemas.OwnerRequirement:
    if db.get(models.Material, payload.material_id) is None:
        raise invalid("Unknown material_id.", field="material_id")

    process = db.get(models.ReceivingProcess, payload.receiving_process_id)
    if process is None:
        raise invalid("Unknown receiving_process_id.", field="receiving_process_id")

    confirmed = {
        link.process_id for link in current.business.receiving_processes if link.confirmed
    }
    if payload.receiving_process_id not in confirmed:
        raise invalid(
            "Your business has not confirmed this receiving process.",
            code="PROCESS_UNCONFIRMED",
            field="receiving_process_id",
        )

    location = payload.location
    requirement = models.Requirement(
        buyer_business_id=current.business_id,
        material_id=payload.material_id,
        receiving_process_id=payload.receiving_process_id,
        quantity_kg=payload.quantity_kg,
        max_moisture_pct=payload.max_moisture_pct,
        delivery_start=payload.delivery_window.start,
        delivery_end=payload.delivery_window.end,
        buyer_max_total_paise=payload.buyer_max_total_paise,
        district=location.district if location else current.business.district,
        lat=location.lat if location else current.business.lat,
        lon=location.lon if location else current.business.lon,
        location_precision=(
            location.precision if location else current.business.location_precision
        ),
        negotiation_strategy=payload.negotiation_strategy,
        status="open",
    )
    if not current.business.is_buyer:
        current.business.is_buyer = True
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return to_owner_requirement(requirement)


@router.get("/requirements/{requirement_id}", response_model=schemas.OwnerRequirement)
def get_requirement(
    requirement_id: str, db: DbDep, current: CurrentUserDep
) -> schemas.OwnerRequirement:
    requirement = load_owned_requirement(db, requirement_id, current.business_id)
    return to_owner_requirement(requirement)


@router.get("/requirements/{requirement_id}/matches", response_model=schemas.MatchesResponse)
def get_matches(
    requirement_id: str, db: DbDep, current: CurrentUserDep
) -> schemas.MatchesResponse:
    requirement = load_owned_requirement(db, requirement_id, current.business_id)
    return build_matches_response(db, requirement)


@router.post("/transport-options", response_model=schemas.TransportOption, status_code=201)
def create_transport_option(
    payload: schemas.TransportOptionCreate, db: DbDep, current: CurrentUserDep
) -> schemas.TransportOption:
    listing = db.get(models.Listing, payload.listing_id)
    if listing is None:
        raise invalid("Unknown listing_id.", field="listing_id")

    requirement = db.get(models.Requirement, payload.requirement_id)
    if requirement is None:
        raise invalid("Unknown requirement_id.", field="requirement_id")

    # Only the two parties to this pair may enter freight for it.
    is_seller = listing.seller_business_id == current.business_id
    is_buyer = requirement.buyer_business_id == current.business_id
    if not (is_seller or is_buyer):
        raise forbidden(
            "Only the seller of this listing or the buyer of this requirement may "
            "enter a transport option for the pair."
        )

    option = models.TransportOption(
        listing_id=payload.listing_id,
        requirement_id=payload.requirement_id,
        label=payload.label,
        freight_paise=payload.freight_paise,
        capacity_kg=payload.capacity_kg,
        pickup_at=payload.pickup_at,
        delivery_at=payload.delivery_at,
        expires_at=payload.expires_at,
        source=payload.source,
        distance_m=payload.distance_m,
        distance_basis=payload.distance_basis,
        created_by_business_id=current.business_id,
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    return to_transport_option(option)
