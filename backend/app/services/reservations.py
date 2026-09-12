"""Committing one winning offer into a deal, and the deal status lifecycle.

Only the single winner is committed. Candidates that provisionally accept do
not hold stock - reserving for every provisional acceptance would let one
requirement lock three sellers' inventory at once.

The commit is one transaction that locks the requirement and listing, rechecks
everything the agents were told, decrements stock exactly once, and relies on a
unique constraint on deals.requirement_id as the final guard. Two requests
racing for the last batch therefore cannot both win: whichever commits second
sees the decremented quantity, or trips the constraint.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, lazyload

from app.config import get_settings
from app.db import models

STALE_STOCK = "STALE_STOCK"
QUOTE_EXPIRED = "QUOTE_EXPIRED"
INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"


class ReservationFailed(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _lock(db: Session, model, row_id: str):
    """Row lock where the database supports it; a plain read on SQLite.

    lazyload("*") matters: Listing.seller and Requirement.buyer are
    lazy="joined", so without it the statement becomes a LEFT OUTER JOIN and
    Postgres rejects it with "FOR UPDATE cannot be applied to the nullable
    side of an outer join".
    """
    stmt = select(model).where(model.id == row_id).options(lazyload("*"))
    if not get_settings().is_sqlite:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def commit_deal(
    db: Session,
    *,
    negotiation: models.Negotiation,
    offer: models.Offer,
    intended_use: str,
    now: datetime | None = None,
) -> models.Deal:
    """Reserve stock and create the deal, or raise ReservationFailed."""
    now = now or datetime.now(timezone.utc)

    requirement = _lock(db, models.Requirement, negotiation.requirement_id)
    listing = _lock(db, models.Listing, offer.listing_id)
    transport = _lock(db, models.TransportOption, offer.transport_option_id)

    if requirement is None or listing is None or transport is None:
        raise ReservationFailed(STALE_STOCK, "A record in this offer no longer exists.")

    existing = db.scalar(
        select(models.Deal).where(models.Deal.requirement_id == requirement.id)
    )
    if existing is not None:
        raise ReservationFailed(
            STALE_STOCK, "This requirement has already been allocated to a deal."
        )

    if requirement.status != "open":
        raise ReservationFailed(
            STALE_STOCK, f"Requirement is no longer open (status={requirement.status})."
        )

    if listing.status != "open":
        raise ReservationFailed(STALE_STOCK, "Listing was closed during negotiation.")

    if listing.available_quantity_kg < requirement.quantity_kg:
        raise ReservationFailed(
            INSUFFICIENT_STOCK,
            "Available quantity fell below the requested quantity during negotiation.",
        )

    if _aware(transport.expires_at) <= now:
        raise ReservationFailed(
            QUOTE_EXPIRED, "The selected transport quote expired before commit."
        )

    if transport.capacity_kg < requirement.quantity_kg:
        raise ReservationFailed(
            QUOTE_EXPIRED, "The selected transport option cannot carry this quantity."
        )

    if offer.unit_price_paise_per_tonne < listing.seller_floor_paise_per_tonne:
        raise ReservationFailed(
            STALE_STOCK, "Agreed unit price is below the seller's current floor."
        )

    if offer.buyer_total_paise > requirement.buyer_max_total_paise:
        raise ReservationFailed(
            STALE_STOCK, "Agreed delivered total is above the buyer's current budget."
        )

    # The mutations below are conditional UPDATEs rather than read-modify-write
    # on the ORM objects, and the condition is re-evaluated by the database at
    # write time. That is what actually prevents two concurrent requirements
    # from both taking the last batch: the checks above can all pass in two
    # transactions at once, but only one UPDATE can find the stock still there.
    #
    # The unique constraint on deals.requirement_id does NOT cover this case -
    # it stops one requirement getting two deals, not two requirements taking
    # the same stock.
    #
    # A SAVEPOINT keeps a failed reservation from discarding the negotiation's
    # offers and events, which live in this same session and are not committed
    # until the run finishes.
    try:
        with db.begin_nested():
            reserved = db.execute(
                update(models.Listing)
                .where(
                    models.Listing.id == listing.id,
                    models.Listing.status == "open",
                    models.Listing.available_quantity_kg >= requirement.quantity_kg,
                )
                .values(
                    available_quantity_kg=models.Listing.available_quantity_kg
                    - requirement.quantity_kg,
                    version=models.Listing.version + 1,
                )
            ).rowcount
            if reserved != 1:
                raise ReservationFailed(
                    INSUFFICIENT_STOCK,
                    "The batch was allocated to another buyer during this negotiation.",
                )

            claimed = db.execute(
                update(models.Requirement)
                .where(
                    models.Requirement.id == requirement.id,
                    models.Requirement.status == "open",
                )
                .values(status="fulfilled", version=models.Requirement.version + 1)
            ).rowcount
            if claimed != 1:
                raise ReservationFailed(
                    STALE_STOCK, "This requirement was fulfilled by another run."
                )

            deal = _build_deal(listing, requirement, transport, offer, negotiation, intended_use)
            db.add(deal)
            db.flush()
    except IntegrityError as exc:
        raise ReservationFailed(
            STALE_STOCK, "Another negotiation allocated this requirement first."
        ) from exc

    # The rows were changed behind the ORM's back; drop the stale copies so a
    # later read of listing.available_quantity_kg sees the new value.
    db.expire(listing)
    db.expire(requirement)
    return deal


def _build_deal(
    listing: models.Listing,
    requirement: models.Requirement,
    transport: models.TransportOption,
    offer: models.Offer,
    negotiation: models.Negotiation,
    intended_use: str,
) -> models.Deal:
    return models.Deal(
        negotiation_id=negotiation.id,
        requirement_id=requirement.id,
        listing_id=listing.id,
        offer_id=offer.id,
        seller_business_id=listing.seller_business_id,
        buyer_business_id=requirement.buyer_business_id,
        material_id=listing.material_id,
        intended_use=intended_use,
        quantity_kg=requirement.quantity_kg,
        unit_price_paise_per_tonne=offer.unit_price_paise_per_tonne,
        material_paise=offer.material_paise,
        freight_paise=offer.freight_paise,
        buyer_total_paise=offer.buyer_total_paise,
        seller_receives_paise=offer.seller_receives_paise,
        transport_option_id=transport.id,
        status="agreed",
    )


# ---------------------------------------------------------------------------
# Deal status lifecycle
# ---------------------------------------------------------------------------

# status -> (allowed next statuses, which side may set them)
TRANSITIONS: dict[str, dict[str, str]] = {
    "agreed": {"pickup_scheduled": "seller", "cancelled": "either"},
    "pickup_scheduled": {"collected": "seller", "cancelled": "either"},
    "collected": {"delivered": "buyer"},
    "delivered": {},
    "cancelled": {},
}


class TransitionRejected(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def apply_status(db: Session, deal: models.Deal, new_status: str, business_id: str) -> models.Deal:
    """Move a deal along its lifecycle, releasing stock exactly once on cancel."""
    allowed = TRANSITIONS.get(deal.status, {})

    if new_status not in allowed:
        if deal.status in ("collected", "delivered") and new_status == "cancelled":
            raise TransitionRejected(
                "CANCELLATION_NOT_ALLOWED",
                "Cancellation after collection is outside the scope of this version.",
            )
        raise TransitionRejected(
            "INVALID_TRANSITION",
            f"Cannot move a deal from '{deal.status}' to '{new_status}'.",
        )

    actor = allowed[new_status]
    is_seller = business_id == deal.seller_business_id
    is_buyer = business_id == deal.buyer_business_id

    if actor == "seller" and not is_seller:
        raise TransitionRejected(
            "FORBIDDEN", "Only the seller can set this status.", status_code=403
        )
    if actor == "buyer" and not is_buyer:
        raise TransitionRejected(
            "FORBIDDEN", "Only the buyer can set this status.", status_code=403
        )
    if actor == "either" and not (is_seller or is_buyer):
        raise TransitionRejected(
            "FORBIDDEN", "Only a participant can change this deal.", status_code=403
        )

    if new_status == "cancelled" and not deal.stock_released:
        # Guarded by stock_released so a repeated cancel cannot credit the
        # batch twice, and written as conditional UPDATEs for the same reason
        # the reservation is: read-modify-write loses concurrent changes.
        released = db.execute(
            update(models.Deal)
            .where(models.Deal.id == deal.id, models.Deal.stock_released.is_(False))
            .values(stock_released=True)
        ).rowcount
        if released == 1:
            # Restoring stock never reopens a listing the seller closed.
            db.execute(
                update(models.Listing)
                .where(models.Listing.id == deal.listing_id)
                .values(
                    available_quantity_kg=models.Listing.available_quantity_kg
                    + deal.quantity_kg,
                    version=models.Listing.version + 1,
                )
            )
            db.execute(
                update(models.Requirement)
                .where(
                    models.Requirement.id == deal.requirement_id,
                    models.Requirement.status == "fulfilled",
                )
                .values(status="open", version=models.Requirement.version + 1)
            )
            db.expire(deal)

    deal.status = new_status
    db.flush()
    return deal
