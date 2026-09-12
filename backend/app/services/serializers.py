"""ORM row -> contract object.

Every conversion from a database row to an HTTP response goes through here.
Note there is no `to_listing(..., include_private=True)` style flag: the public
and owner serializers are separate functions returning separate types, so a
route cannot leak a private field by passing the wrong boolean.
"""

from __future__ import annotations

from app.api import schemas
from app.db import models


def to_location(
    district: str, lat: float | None, lon: float | None, precision: str
) -> schemas.Location:
    return schemas.Location(
        district=district,
        lat=lat,
        lon=lon,
        precision=precision,  # type: ignore[arg-type]
    )


def to_business(business: models.Business) -> schemas.Business:
    roles: list[str] = []
    if business.is_buyer:
        roles.append("buyer")
    if business.is_seller:
        roles.append("seller")
    return schemas.Business(
        id=business.id,
        name=business.name,
        enterprise_id=business.enterprise_id,
        roles=roles,  # type: ignore[arg-type]
        receiving_processes=sorted(
            link.process_id for link in business.receiving_processes if link.confirmed
        ),
        location=to_location(
            business.district, business.lat, business.lon, business.location_precision
        ),
    )


def to_listing(listing: models.Listing) -> schemas.Listing:
    return schemas.Listing(
        id=listing.id,
        seller=to_business(listing.seller),
        material_id=listing.material_id,
        available_quantity_kg=listing.available_quantity_kg,
        asking_price_paise_per_tonne=listing.asking_price_paise_per_tonne,
        moisture_pct=listing.moisture_pct,
        contamination_notes=listing.contamination_notes,
        pickup_window=schemas.Window(start=listing.pickup_start, end=listing.pickup_end),
        location=to_location(
            listing.district, listing.lat, listing.lon, listing.location_precision
        ),
        status=listing.status,  # type: ignore[arg-type]
    )


def to_owner_listing(listing: models.Listing) -> schemas.OwnerListing:
    return schemas.OwnerListing(
        **to_listing(listing).model_dump(),
        seller_floor_paise_per_tonne=listing.seller_floor_paise_per_tonne,
    )


def to_requirement(requirement: models.Requirement) -> schemas.Requirement:
    return schemas.Requirement(
        id=requirement.id,
        buyer=to_business(requirement.buyer),
        material_id=requirement.material_id,
        receiving_process_id=requirement.receiving_process_id,
        quantity_kg=requirement.quantity_kg,
        max_moisture_pct=requirement.max_moisture_pct,
        delivery_window=schemas.Window(
            start=requirement.delivery_start, end=requirement.delivery_end
        ),
        location=to_location(
            requirement.district,
            requirement.lat,
            requirement.lon,
            requirement.location_precision,
        ),
        status=requirement.status,  # type: ignore[arg-type]
    )


def to_owner_requirement(requirement: models.Requirement) -> schemas.OwnerRequirement:
    return schemas.OwnerRequirement(
        **to_requirement(requirement).model_dump(),
        buyer_max_total_paise=requirement.buyer_max_total_paise,
    )


def to_transport_option(option: models.TransportOption) -> schemas.TransportOption:
    return schemas.TransportOption(
        id=option.id,
        listing_id=option.listing_id,
        requirement_id=option.requirement_id,
        label=option.label,
        freight_paise=option.freight_paise,
        capacity_kg=option.capacity_kg,
        pickup_at=option.pickup_at,
        delivery_at=option.delivery_at,
        expires_at=option.expires_at,
        source=option.source,  # type: ignore[arg-type]
        distance_m=option.distance_m,
        distance_basis=option.distance_basis,  # type: ignore[arg-type]
    )


def to_costs(row: models.Offer | models.Deal) -> schemas.Costs:
    return schemas.Costs(
        material_paise=row.material_paise,
        freight_paise=row.freight_paise,
        buyer_total_paise=row.buyer_total_paise,
        seller_receives_paise=row.seller_receives_paise,
    )


def to_offer(offer: models.Offer) -> schemas.Offer:
    return schemas.Offer(
        id=offer.id,
        listing_id=offer.listing_id,
        transport_option_id=offer.transport_option_id,
        quantity_kg=offer.quantity_kg,
        unit_price_paise_per_tonne=offer.unit_price_paise_per_tonne,
        costs=to_costs(offer),
        pickup_at=offer.pickup_at,
        delivery_at=offer.delivery_at,
        author=offer.author,  # type: ignore[arg-type]
        action=offer.action,  # type: ignore[arg-type]
        responds_to_offer_id=offer.responds_to_offer_id,
        explanation=offer.explanation,
        expires_at=offer.expires_at,
    )


def to_event(event: models.NegotiationEvent) -> schemas.Event:
    return schemas.Event(
        seq=event.seq,
        type=event.type,  # type: ignore[arg-type]
        actor=event.actor,  # type: ignore[arg-type]
        message=event.message,
        offer_id=event.offer_id,
        created_at=event.created_at,
    )


def to_deal(
    deal: models.Deal,
    seller: models.Business,
    buyer: models.Business,
    transport: models.TransportOption,
) -> schemas.Deal:
    return schemas.Deal(
        id=deal.id,
        negotiation_id=deal.negotiation_id,
        requirement_id=deal.requirement_id,
        listing_id=deal.listing_id,
        seller=to_business(seller),
        buyer=to_business(buyer),
        material_id=deal.material_id,
        intended_use=deal.intended_use,
        quantity_kg=deal.quantity_kg,
        unit_price_paise_per_tonne=deal.unit_price_paise_per_tonne,
        costs=to_costs(deal),
        transport_option=to_transport_option(transport),
        status=deal.status,  # type: ignore[arg-type]
        created_at=deal.created_at,
    )


def to_negotiation(
    negotiation: models.Negotiation, offers: list[models.Offer]
) -> schemas.Negotiation:
    return schemas.Negotiation(
        id=negotiation.id,
        requirement_id=negotiation.requirement_id,
        status=negotiation.status,  # type: ignore[arg-type]
        round=negotiation.round,
        max_rounds=negotiation.max_rounds,
        current_listing_id=negotiation.current_listing_id,
        failure_code=negotiation.failure_code,
        deal_id=negotiation.deal_id,
        offers=[to_offer(offer) for offer in offers],
        created_at=negotiation.created_at,
        updated_at=negotiation.updated_at,
    )
