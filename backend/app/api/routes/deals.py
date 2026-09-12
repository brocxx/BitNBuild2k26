"""Deal routes. Visible to the two participating businesses only."""

from __future__ import annotations

import hashlib
import json
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


@router.get("/deals/{deal_id}/certificate", response_model=schemas.GreenCertificate)
def get_deal_certificate(
    deal_id: str, db: DbDep, current: CurrentUserDep
) -> schemas.GreenCertificate:
    deal = _load_participating_deal(db, deal_id, current.business_id)
    serialized = _serialize(db, deal)
    transport = db.get(models.TransportOption, deal.transport_option_id)
    distance_km = (
        (transport.distance_m / 1000.0) if (transport and transport.distance_m) else 120.0
    )

    cert_id = f"CERT-KIB-{deal.id[:8].upper()}-{deal.created_at.year}"

    offer = db.get(models.Offer, deal.offer_id)
    verification_payload = {
        "certificate_id": cert_id,
        "deal_id": deal.id,
        "negotiation_id": deal.negotiation_id,
        "offer_chain_hash": offer.chain_hash if (offer and offer.chain_hash) else "GENESIS",
        "seller_business_id": deal.seller_business_id,
        "buyer_business_id": deal.buyer_business_id,
        "material_id": deal.material_id,
        "quantity_kg": deal.quantity_kg,
        "net_co2e_avoided_kg": (
            serialized.esg_metrics.net_co2e_avoided_kg if serialized.esg_metrics else 0.0
        ),
        "timestamp_utc": deal.created_at.isoformat(),
    }
    verification_hash = hashlib.sha256(
        json.dumps(verification_payload, sort_keys=True).encode()
    ).hexdigest()

    return schemas.GreenCertificate(
        certificate_id=cert_id,
        issuer="Karnataka Industrial Byproduct Exchange (KIB) & Circular Economy Authority",
        deal_id=deal.id,
        trade_date=deal.created_at,
        seller=serialized.seller,
        buyer=serialized.buyer,
        material_id=deal.material_id,
        material_display_name=deal.material_id.replace("_", " ").title(),
        quantity_kg=deal.quantity_kg,
        transport_distance_km=round(distance_km, 1),
        esg_metrics=serialized.esg_metrics,  # type: ignore[arg-type]
        verification_hash=verification_hash,
        methodology="IPCC 2006 Guidelines for National Greenhouse Gas Inventories (Vol 2 Energy) & MoRTH India Freight Factor 2022",
    )


