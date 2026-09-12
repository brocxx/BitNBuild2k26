"""Request and response models.

These mirror MVP_TEAM_WORK_PLAN.md section 4 field for field. The frontend's
`frontend/src/api/types.ts` is generated from the same contract, so renaming
anything here is a contract change that must be announced.

The privacy rule is enforced structurally rather than by remembering to strip
fields: `Listing` has no floor field at all, so a public response physically
cannot carry one. `OwnerListing` subclasses it and adds the private field, and
only /me routes return that type.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Annotated[int, Field(ge=0, description="INR paise")]
PricePerTonne = Annotated[int, Field(ge=0, description="INR paise per tonne")]
Kilograms = Annotated[int, Field(ge=0, description="kilograms")]
PositiveKilograms = Annotated[int, Field(gt=0, description="kilograms")]

LocationPrecision = Literal["district", "confirmed_site"]
BusinessRole = Literal["buyer", "seller"]
ListingStatus = Literal["open", "closed"]
RequirementStatus = Literal["open", "fulfilled", "closed"]
TransportSource = Literal["entered_quote", "configured_estimate"]
DistanceBasis = Literal["road", "district_straight_line", "unknown"]
NegotiationStatus = Literal["queued", "running", "agreed", "no_deal", "failed"]
OfferAuthor = Literal["buyer", "seller", "broker"]
OfferAction = Literal["propose", "counter", "accept", "reject"]
EventType = Literal[
    "started", "offer", "candidate_rejected", "agreed", "no_deal", "failed"
]
EventActor = Literal["buyer", "seller", "broker", "system"]
DealStatus = Literal[
    "agreed", "pickup_scheduled", "collected", "delivered", "cancelled"
]

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None


class Window(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def _ordered(self) -> Window:
        if self.start >= self.end:
            raise ValueError("window start must be before window end")
        return self


class Location(BaseModel):
    district: str
    lat: float | None = None
    lon: float | None = None
    precision: LocationPrecision = "district"


class Business(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    enterprise_id: str | None = None
    roles: list[BusinessRole]
    receiving_processes: list[str]
    location: Location


class Costs(BaseModel):
    material_paise: Money
    freight_paise: Money
    buyer_total_paise: Money
    seller_receives_paise: Money


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------


class Listing(BaseModel):
    """Public listing. Deliberately has no seller floor field."""

    id: str
    seller: Business
    material_id: str
    available_quantity_kg: Kilograms
    asking_price_paise_per_tonne: PricePerTonne
    moisture_pct: float
    contamination_notes: str
    pickup_window: Window
    location: Location
    status: ListingStatus


class OwnerListing(Listing):
    seller_floor_paise_per_tonne: PricePerTonne


class ListingCreate(BaseModel):
    material_id: str
    available_quantity_kg: PositiveKilograms
    asking_price_paise_per_tonne: PricePerTonne
    seller_floor_paise_per_tonne: PricePerTonne
    moisture_pct: float = Field(ge=0, le=100)
    contamination_notes: str = ""
    pickup_window: Window
    location: Location | None = None

    @model_validator(mode="after")
    def _floor_not_above_asking(self) -> ListingCreate:
        if self.seller_floor_paise_per_tonne > self.asking_price_paise_per_tonne:
            raise ValueError(
                "seller_floor_paise_per_tonne cannot exceed asking_price_paise_per_tonne"
            )
        return self


class ListingUpdate(BaseModel):
    asking_price_paise_per_tonne: PricePerTonne | None = None
    seller_floor_paise_per_tonne: PricePerTonne | None = None
    pickup_window: Window | None = None
    status: ListingStatus | None = None


# ---------------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------------


class Requirement(BaseModel):
    id: str
    buyer: Business
    material_id: str
    receiving_process_id: str
    quantity_kg: Kilograms
    max_moisture_pct: float
    delivery_window: Window
    location: Location
    status: RequirementStatus


class OwnerRequirement(Requirement):
    buyer_max_total_paise: Money


class RequirementCreate(BaseModel):
    material_id: str
    receiving_process_id: str
    quantity_kg: PositiveKilograms
    max_moisture_pct: float = Field(ge=0, le=100)
    delivery_window: Window
    buyer_max_total_paise: Money
    location: Location | None = None


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class TransportOption(BaseModel):
    id: str
    listing_id: str
    requirement_id: str
    label: str
    freight_paise: Money
    capacity_kg: Kilograms
    pickup_at: datetime
    delivery_at: datetime
    expires_at: datetime
    source: TransportSource
    distance_m: int | None = None
    distance_basis: DistanceBasis = "unknown"


class TransportOptionCreate(BaseModel):
    listing_id: str
    requirement_id: str
    label: str = Field(min_length=1, max_length=200)
    freight_paise: Money
    capacity_kg: Annotated[int, Field(gt=0)]
    pickup_at: datetime
    delivery_at: datetime
    expires_at: datetime
    source: TransportSource
    distance_m: int | None = Field(default=None, ge=0)
    distance_basis: DistanceBasis = "unknown"

    @model_validator(mode="after")
    def _schedule_ordered(self) -> TransportOptionCreate:
        if self.pickup_at >= self.delivery_at:
            raise ValueError("pickup_at must be before delivery_at")
        return self


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


class MatchCandidate(BaseModel):
    listing: Listing
    pathway_use: str
    transport_options: list[TransportOption]
    initial_best_cost: Costs


class ExcludedListing(BaseModel):
    listing_id: str
    reason_codes: list[str]


class MatchesResponse(BaseModel):
    requirement_id: str
    candidates: list[MatchCandidate]
    excluded: list[ExcludedListing]
    missing_transport_listing_ids: list[str]


# ---------------------------------------------------------------------------
# Negotiation
# ---------------------------------------------------------------------------


class Offer(BaseModel):
    id: str
    listing_id: str
    transport_option_id: str
    quantity_kg: Kilograms
    unit_price_paise_per_tonne: PricePerTonne
    costs: Costs
    pickup_at: datetime
    delivery_at: datetime
    author: OfferAuthor
    action: OfferAction
    responds_to_offer_id: str | None = None
    explanation: str
    expires_at: datetime


class Negotiation(BaseModel):
    id: str
    requirement_id: str
    status: NegotiationStatus
    round: int
    max_rounds: int
    current_listing_id: str | None = None
    failure_code: str | None = None
    deal_id: str | None = None
    offers: list[Offer]
    created_at: datetime
    updated_at: datetime


class NegotiationSummary(BaseModel):
    id: str
    requirement_id: str
    status: NegotiationStatus
    created_at: datetime
    deal_id: str | None = None


class NegotiationCreate(BaseModel):
    requirement_id: str
    listing_ids: list[str] = Field(min_length=1, max_length=3)


class NegotiationAccepted(BaseModel):
    id: str
    status: NegotiationStatus


class Event(BaseModel):
    seq: int
    type: EventType
    actor: EventActor
    message: str
    offer_id: str | None = None
    created_at: datetime


class EventsResponse(BaseModel):
    items: list[Event]
    last_seq: int


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------


class Deal(BaseModel):
    id: str
    negotiation_id: str
    requirement_id: str
    listing_id: str
    seller: Business
    buyer: Business
    material_id: str
    intended_use: str
    quantity_kg: Kilograms
    unit_price_paise_per_tonne: PricePerTonne
    costs: Costs
    transport_option: TransportOption
    status: DealStatus
    created_at: datetime


class DealStatusUpdate(BaseModel):
    status: Literal["pickup_scheduled", "collected", "delivered", "cancelled"]


# ---------------------------------------------------------------------------
# Reference and identity
# ---------------------------------------------------------------------------


class MaterialRef(BaseModel):
    id: str
    name: str


class DistrictRef(BaseModel):
    name: str
    lat: float
    lon: float


class ReceivingProcessRef(BaseModel):
    id: str
    name: str
    material_ids: list[str]


class ReferenceResponse(BaseModel):
    materials: list[MaterialRef]
    districts: list[DistrictRef]
    receiving_processes: list[ReceivingProcessRef]


class MeResponse(BaseModel):
    user_id: str
    business: Business


class HealthResponse(BaseModel):
    status: Literal["ok"]
