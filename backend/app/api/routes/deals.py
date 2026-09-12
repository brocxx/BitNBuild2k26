"""Deal routes. Visible to the two participating businesses only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import schemas
from app.db import models
from app.deps import CurrentUserDep, DbDep
from app.errors import ApiError, forbidden, not_found
from app.services.pagination import apply_cursor, build_page, clamp_limit
from app.services.reservations import TransitionRejected, apply_status
from app.services.serializers import to_deal

router = APIRouter(tags=["deals"])


def _serialize(db: Session, deal: models.Deal) -> schemas.Deal:
    seller = db.get(models.Business, deal.seller_business_id)
    buyer = db.get(models.Business, deal.buyer_business_id)
    transport = db.get(models.TransportOption, deal.transport_option_id)
    if seller is None or buyer is None or transport is None:
        raise not_found("Deal references a missing record.", deal_id=deal.id)
    return to_deal(deal, seller, buyer, transport)


def _load_participating_deal(db: Session, deal_id: str, business_id: str) -> models.Deal:
    deal = db.get(models.Deal, deal_id)
    if deal is None:
        raise not_found("Deal not found.", deal_id=deal_id)
    if business_id not in (deal.seller_business_id, deal.buyer_business_id):
        raise forbidden("Only a participant can view this deal.")
    return deal


@router.get("/me/deals", response_model=schemas.Page[schemas.Deal])
def my_deals(
    db: DbDep,
    current: CurrentUserDep,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> schemas.Page[schemas.Deal]:
    page_size = clamp_limit(limit)
    stmt = select(models.Deal).where(
        (models.Deal.seller_business_id == current.business_id)
        | (models.Deal.buyer_business_id == current.business_id)
    )
    stmt = apply_cursor(stmt, models.Deal, cursor).limit(page_size + 1)
    rows = list(db.scalars(stmt))
    return schemas.Page[schemas.Deal](
        **build_page(rows, page_size, lambda deal: _serialize(db, deal))
    )


@router.get("/deals/{deal_id}", response_model=schemas.Deal)
def get_deal(deal_id: str, db: DbDep, current: CurrentUserDep) -> schemas.Deal:
    return _serialize(db, _load_participating_deal(db, deal_id, current.business_id))


@router.patch("/deals/{deal_id}/status", response_model=schemas.Deal)
def update_deal_status(
    deal_id: str,
    payload: schemas.DealStatusUpdate,
    db: DbDep,
    current: CurrentUserDep,
) -> schemas.Deal:
    deal = _load_participating_deal(db, deal_id, current.business_id)
    try:
        apply_status(db, deal, payload.status, current.business_id)
    except TransitionRejected as exc:
        raise ApiError(exc.status_code, exc.code, exc.message) from exc
    db.commit()
    db.refresh(deal)
    return _serialize(db, deal)
