"""Negotiation routes.

Start is idempotent and single-flight: one queued/running negotiation per
requirement, and a repeated Idempotency-Key returns the original run rather
than starting a second one.

Read access is participant-scoped and filtered by business. The buyer sees the
whole run; a seller sees only its own candidate conversation, never a
competitor's offers.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, Query, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import schemas
from app.config import get_settings
from app.db import models
from app.deps import CurrentUserDep, DbDep
from app.errors import conflict, forbidden, invalid, not_found
from app.services.coordinator import Coordinator, run_negotiation
from app.services.matching import evaluate_listing
from app.services.pagination import apply_cursor, build_page, clamp_limit
from app.services.serializers import to_negotiation, to_event

router = APIRouter(tags=["negotiations"])

ENDPOINT = "POST /negotiations"


def _hash_body(payload: schemas.NegotiationCreate) -> str:
    canonical = json.dumps(
        {
            "requirement_id": payload.requirement_id,
            "listing_ids": sorted(set(payload.listing_ids)),
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _visible_listing_ids(
    db: Session, negotiation: models.Negotiation, business_id: str
) -> set[str] | None:
    """None means "every listing" (the buyer). A set means seller-scoped."""
    if negotiation.buyer_business_id == business_id:
        return None
    own = {
        candidate.listing_id
        for candidate in db.scalars(
            select(models.NegotiationCandidate).where(
                models.NegotiationCandidate.negotiation_id == negotiation.id,
                models.NegotiationCandidate.seller_business_id == business_id,
            )
        )
    }
    if not own:
        raise forbidden("You are not a participant in this negotiation.")
    return own


def _load_negotiation(db: Session, negotiation_id: str) -> models.Negotiation:
    negotiation = db.get(models.Negotiation, negotiation_id)
    if negotiation is None:
        raise not_found("Negotiation not found.", negotiation_id=negotiation_id)
    return negotiation


@router.post("/negotiations", response_model=schemas.NegotiationAccepted, status_code=202)
def start_negotiation(
    payload: schemas.NegotiationCreate,
    db: DbDep,
    current: CurrentUserDep,
    background: BackgroundTasks,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> schemas.NegotiationAccepted:
    if not idempotency_key:
        raise invalid("An Idempotency-Key header is required.", field="Idempotency-Key")

    settings = get_settings()
    requirement = db.get(models.Requirement, payload.requirement_id)
    if requirement is None:
        raise not_found("Requirement not found.", requirement_id=payload.requirement_id)
    if requirement.buyer_business_id != current.business_id:
        raise forbidden("Only the buyer of this requirement can start a negotiation.")

    request_hash = _hash_body(payload)
    existing_key = db.scalar(
        select(models.IdempotencyKey).where(
            models.IdempotencyKey.business_id == current.business_id,
            models.IdempotencyKey.endpoint == ENDPOINT,
            models.IdempotencyKey.key == idempotency_key,
        )
    )
    if existing_key is not None:
        if existing_key.request_hash != request_hash:
            raise conflict(
                "IDEMPOTENCY_KEY_REUSED",
                "This Idempotency-Key was already used with a different request body.",
            )
        original = _load_negotiation(db, existing_key.response_id)
        response.status_code = 200
        return schemas.NegotiationAccepted(id=original.id, status=original.status)

    if requirement.status != "open":
        raise conflict(
            "REQUIREMENT_NOT_OPEN",
            f"This requirement is {requirement.status} and cannot be negotiated.",
        )

    live = db.scalar(
        select(models.Negotiation).where(
            models.Negotiation.requirement_id == requirement.id,
            models.Negotiation.status.in_(["queued", "running"]),
        )
    )
    if live is not None:
        raise conflict(
            "NEGOTIATION_IN_PROGRESS",
            "A negotiation for this requirement is already in progress.",
            negotiation_id=live.id,
        )

    listing_ids = list(dict.fromkeys(payload.listing_ids))
    if len(listing_ids) > settings.max_candidates_per_negotiation:
        raise invalid(
            f"At most {settings.max_candidates_per_negotiation} listings per negotiation.",
            field="listing_ids",
        )

    listings = []
    for listing_id in listing_ids:
        listing = db.get(models.Listing, listing_id)
        if listing is None:
            raise invalid(f"Unknown listing_id '{listing_id}'.", field="listing_ids")
        if listing.seller_business_id == current.business_id:
            raise invalid(
                "You cannot negotiate against your own listing.", field="listing_ids"
            )
        listings.append(listing)

    negotiation = models.Negotiation(
        requirement_id=requirement.id,
        buyer_business_id=current.business_id,
        status="queued",
        round=0,
        max_rounds=settings.max_rounds_per_candidate,
        agent_mode=settings.agent_mode,
    )
    db.add(negotiation)
    db.flush()

    # Order candidates by the same delivered-cost ranking the Matches screen
    # shows, so the run works through the most promising seller first.
    ordered = _order_candidates(db, requirement, listings)
    for index, listing in enumerate(ordered):
        db.add(
            models.NegotiationCandidate(
                negotiation_id=negotiation.id,
                listing_id=listing.id,
                seller_business_id=listing.seller_business_id,
                order_index=index,
            )
        )

    db.add(
        models.IdempotencyKey(
            business_id=current.business_id,
            endpoint=ENDPOINT,
            key=idempotency_key,
            request_hash=request_hash,
            response_id=negotiation.id,
        )
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise conflict(
            "NEGOTIATION_IN_PROGRESS",
            "A negotiation for this requirement was started concurrently.",
        ) from exc

    negotiation_id = negotiation.id
    if settings.negotiation_run_inline:
        Coordinator(db).run(negotiation_id)
        db.commit()
        db.refresh(negotiation)
        return schemas.NegotiationAccepted(id=negotiation_id, status=negotiation.status)

    background.add_task(run_negotiation, negotiation_id)
    return schemas.NegotiationAccepted(id=negotiation_id, status="queued")


def _order_candidates(
    db: Session, requirement: models.Requirement, listings: list[models.Listing]
) -> list[models.Listing]:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    scored: list[tuple[int, str, models.Listing]] = []
    for listing in listings:
        options = list(
            db.scalars(
                select(models.TransportOption).where(
                    models.TransportOption.listing_id == listing.id,
                    models.TransportOption.requirement_id == requirement.id,
                )
            )
        )
        evaluation = evaluate_listing(db, listing, requirement, options, now)
        if evaluation.usable_transport:
            freight = evaluation.usable_transport[0].freight_paise
            delivered = (
                listing.asking_price_paise_per_tonne * requirement.quantity_kg // 1000
            ) + freight
        else:
            delivered = 2**62  # no route: evaluate last
        scored.append((delivered, listing.id, listing))
    scored.sort(key=lambda row: (row[0], row[1]))
    return [row[2] for row in scored]


@router.get("/me/negotiations", response_model=schemas.Page[schemas.NegotiationSummary])
def my_negotiations(
    db: DbDep,
    current: CurrentUserDep,
    cursor: str | None = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> schemas.Page[schemas.NegotiationSummary]:
    page_size = clamp_limit(limit)
    participating = select(models.NegotiationCandidate.negotiation_id).where(
        models.NegotiationCandidate.seller_business_id == current.business_id
    )
    stmt = select(models.Negotiation).where(
        (models.Negotiation.buyer_business_id == current.business_id)
        | (models.Negotiation.id.in_(participating))
    )
    stmt = apply_cursor(stmt, models.Negotiation, cursor).limit(page_size + 1)
    rows = list(db.scalars(stmt))

    def serialize(negotiation: models.Negotiation) -> schemas.NegotiationSummary:
        return schemas.NegotiationSummary(
            id=negotiation.id,
            requirement_id=negotiation.requirement_id,
            status=negotiation.status,  # type: ignore[arg-type]
            created_at=negotiation.created_at,
            # A seller learns a deal exists only if it is the one that won it.
            deal_id=_deal_id_for(db, negotiation, current.business_id),
        )

    return schemas.Page[schemas.NegotiationSummary](
        **build_page(rows, page_size, serialize)
    )


def _deal_id_for(
    db: Session, negotiation: models.Negotiation, business_id: str
) -> str | None:
    if negotiation.deal_id is None:
        return None
    if negotiation.buyer_business_id == business_id:
        return negotiation.deal_id
    deal = db.get(models.Deal, negotiation.deal_id)
    if deal is not None and deal.seller_business_id == business_id:
        return deal.id
    return None


@router.get("/negotiations/{negotiation_id}", response_model=schemas.Negotiation)
def get_negotiation(
    negotiation_id: str, db: DbDep, current: CurrentUserDep
) -> schemas.Negotiation:
    negotiation = _load_negotiation(db, negotiation_id)
    visible = _visible_listing_ids(db, negotiation, current.business_id)

    stmt = select(models.Offer).where(models.Offer.negotiation_id == negotiation.id)
    if visible is not None:
        stmt = stmt.where(models.Offer.listing_id.in_(visible))
    offers = list(db.scalars(stmt.order_by(models.Offer.created_at, models.Offer.id)))

    result = to_negotiation(negotiation, offers)
    if visible is not None:
        # Sellers must not learn which competitor won, or that one did.
        result.deal_id = _deal_id_for(db, negotiation, current.business_id)
        if negotiation.current_listing_id not in visible:
            result.current_listing_id = None
    return result


@router.get("/negotiations/{negotiation_id}/events", response_model=schemas.EventsResponse)
def get_events(
    negotiation_id: str,
    db: DbDep,
    current: CurrentUserDep,
    after_seq: Annotated[int, Query(ge=0)] = 0,
) -> schemas.EventsResponse:
    negotiation = _load_negotiation(db, negotiation_id)
    visible = _visible_listing_ids(db, negotiation, current.business_id)

    stmt = select(models.NegotiationEvent).where(
        models.NegotiationEvent.negotiation_id == negotiation.id,
        models.NegotiationEvent.seq > after_seq,
    )
    if visible is not None:
        # Sequence gaps are permitted by the contract; filtering by candidate
        # is what produces them.
        stmt = stmt.where(models.NegotiationEvent.listing_id.in_(visible))
    rows = list(db.scalars(stmt.order_by(models.NegotiationEvent.seq)))

    last_seq = rows[-1].seq if rows else after_seq
    return schemas.EventsResponse(
        items=[to_event(row) for row in rows], last_seq=last_seq
    )
