"""SQLAlchemy models.

Two groups, as required by MVP_TEAM_WORK_PLAN.md section 6:

Reference tables   - imported from dataset/*.csv. Read-mostly. Inferred annual
                     tonnage lives here and never touches listing stock.
Operational tables - what can actually be exchanged now, and under what terms.

Units, everywhere, without exception:
    money    integer INR paise
    price    integer INR paise per tonne
    quantity integer kilograms
    distance integer meters
    time     timezone-aware UTC datetimes
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


# ---------------------------------------------------------------------------
# Reference tables (imported from dataset/)
# ---------------------------------------------------------------------------


class District(Base):
    __tablename__ = "districts"

    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    hq_town: Mapped[str] = mapped_column(String(80))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(120), default="")


class DistrictDistance(Base):
    """Straight-line district-HQ distances.

    Deliberately stored with an explicit basis. Freight charges are never
    derived from this table - a transport option must state a complete
    per-shipment charge.
    """

    __tablename__ = "district_distances"

    from_district: Mapped[str] = mapped_column(String(80), primary_key=True)
    to_district: Mapped[str] = mapped_column(String(80), primary_key=True)
    distance_m: Mapped[int] = mapped_column(Integer)
    basis: Mapped[str] = mapped_column(String(32), default="district_straight_line")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "rice_husk"
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(64), default="")
    is_supported: Mapped[bool] = mapped_column(Boolean, default=False)


class MaterialAlias(Base):
    """Dataset spellings mapped onto canonical material IDs."""

    __tablename__ = "material_aliases"

    alias: Mapped[str] = mapped_column(String(160), primary_key=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id"))


class ReceivingProcess(Base):
    __tablename__ = "receiving_processes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # "brick_kiln_fuel"
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    # NIC5 codes whose enterprises genuinely operate this process, comma separated.
    nic5_codes: Mapped[str] = mapped_column(String(240), default="")


class ReceivingProcessMaterial(Base):
    __tablename__ = "receiving_process_materials"

    process_id: Mapped[str] = mapped_column(ForeignKey("receiving_processes.id"), primary_key=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id"), primary_key=True)


class Enterprise(Base):
    """A real UDYAM-registered MSME from the dataset."""

    __tablename__ = "enterprises"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)  # KA-ENT-000001
    name: Mapped[str] = mapped_column(String(400))
    # "udyam" when recovered from the raw registry, "unresolved" when we fell
    # back to the ID. Never silently invent a name.
    name_source: Mapped[str] = mapped_column(String(24), default="unresolved")
    district: Mapped[str] = mapped_column(String(80), index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    pincode: Mapped[str] = mapped_column(String(16), default="")
    nic5_code: Mapped[str] = mapped_column(String(8), index=True)
    nic2_division: Mapped[str] = mapped_column(String(4), index=True)
    nic_description: Mapped[str] = mapped_column(Text, default="")
    registration_date: Mapped[str] = mapped_column(String(24), default="")
    address: Mapped[str] = mapped_column(Text, default="")


class EnterpriseByproduct(Base):
    """Inferred annual byproduct generation.

    This is an estimate derived from a published yield ratio and an assumed
    100 t/year input. It is discovery data only - it is never treated as
    sellable inventory.
    """

    __tablename__ = "enterprise_byproducts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    enterprise_id: Mapped[str] = mapped_column(ForeignKey("enterprises.id"), index=True)
    material_id: Mapped[str | None] = mapped_column(ForeignKey("materials.id"), nullable=True)
    byproduct_name: Mapped[str] = mapped_column(String(120))
    waste_ratio_pct: Mapped[float] = mapped_column(Float)
    annual_tonnes_estimated: Mapped[float] = mapped_column(Float)
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=True)
    source_citation: Mapped[str] = mapped_column(Text, default="")


class SymbiosisPathway(Base):
    __tablename__ = "symbiosis_pathways"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    producer_nic2: Mapped[str] = mapped_column(String(4))
    producer_industry: Mapped[str] = mapped_column(String(160))
    material_id: Mapped[str | None] = mapped_column(ForeignKey("materials.id"), nullable=True)
    byproduct_name: Mapped[str] = mapped_column(String(120))
    byproduct_type: Mapped[str] = mapped_column(String(80), default="")
    receiver_nic2: Mapped[str] = mapped_column(String(4))
    receiver_industry: Mapped[str] = mapped_column(String(160))
    use_case: Mapped[str] = mapped_column(Text)
    source_citation: Mapped[str] = mapped_column(Text, default="")
    receiving_process_id: Mapped[str | None] = mapped_column(
        ForeignKey("receiving_processes.id"), nullable=True
    )


class MaterialCompatibilityFlag(Base):
    """A small, explicitly reviewed compatibility table.

    The plan forbids claiming universal material certification. Each row is one
    reviewed statement about one contamination keyword for one material and
    receiving process. Anything not covered here is REVIEW_REQUIRED, never an
    automatic pass.
    """

    __tablename__ = "material_compatibility_flags"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id"), index=True)
    receiving_process_id: Mapped[str] = mapped_column(ForeignKey("receiving_processes.id"))
    # Empty keyword = the baseline verdict for a listing with no contamination notes.
    contamination_keyword: Mapped[str] = mapped_column(String(80), default="")
    verdict: Mapped[str] = mapped_column(String(16))  # accept | review | reject
    note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(120), default="demo_reference_review")


# ---------------------------------------------------------------------------
# Operational tables
# ---------------------------------------------------------------------------


class Business(Base, TimestampMixin):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(400))
    enterprise_id: Mapped[str | None] = mapped_column(
        ForeignKey("enterprises.id"), nullable=True, index=True
    )
    is_buyer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_seller: Mapped[bool] = mapped_column(Boolean, default=False)
    district: Mapped[str] = mapped_column(String(80))
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_precision: Mapped[str] = mapped_column(String(24), default="district")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    receiving_processes: Mapped[list[BusinessReceivingProcess]] = relationship(
        back_populates="business", cascade="all, delete-orphan", lazy="selectin"
    )


class BusinessReceivingProcess(Base):
    """A process this business has confirmed it can actually receive into."""

    __tablename__ = "business_receiving_processes"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), primary_key=True)
    process_id: Mapped[str] = mapped_column(ForeignKey("receiving_processes.id"), primary_key=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=True)

    business: Mapped[Business] = relationship(back_populates="receiving_processes")


class AppUser(Base, TimestampMixin):
    __tablename__ = "app_users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    # Supabase auth.users.id. Populated once real Supabase accounts exist.
    supabase_user_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    business: Mapped[Business] = relationship(lazy="joined")


class Listing(Base, TimestampMixin):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("available_quantity_kg >= 0", name="ck_listing_qty_nonneg"),
        CheckConstraint("asking_price_paise_per_tonne >= 0", name="ck_listing_price_nonneg"),
        Index("ix_listings_material_status", "material_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    seller_business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id"))

    available_quantity_kg: Mapped[int] = mapped_column(Integer)
    asking_price_paise_per_tonne: Mapped[int] = mapped_column(Integer)
    # Private. Never serialised into a public Listing.
    seller_floor_paise_per_tonne: Mapped[int] = mapped_column(Integer)

    moisture_pct: Mapped[float] = mapped_column(Float, default=0.0)
    contamination_notes: Mapped[str] = mapped_column(Text, default="")

    pickup_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pickup_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    district: Mapped[str] = mapped_column(String(80), index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_precision: Mapped[str] = mapped_column(String(24), default="district")

    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    # Bumped on every mutation; the commit step rechecks it before reserving.
    version: Mapped[int] = mapped_column(Integer, default=1)
    # Game theory: concession curve strategy for this listing's seller agent.
    # "conceder" = linear walk to floor (cooperative, quick deal)
    # "boulware" = hold near asking until final round, sharp drop at deadline
    negotiation_strategy: Mapped[str] = mapped_column(String(16), default="conceder")

    seller: Mapped[Business] = relationship(lazy="joined")


class Requirement(Base, TimestampMixin):
    __tablename__ = "requirements"
    __table_args__ = (CheckConstraint("quantity_kg > 0", name="ck_requirement_qty_positive"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    buyer_business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id"))
    receiving_process_id: Mapped[str] = mapped_column(ForeignKey("receiving_processes.id"))

    quantity_kg: Mapped[int] = mapped_column(Integer)
    max_moisture_pct: Mapped[float] = mapped_column(Float, default=100.0)

    delivery_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivery_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Private. Never serialised into anything a seller can read.
    buyer_max_total_paise: Mapped[int] = mapped_column(Integer)

    district: Mapped[str] = mapped_column(String(80), index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_precision: Mapped[str] = mapped_column(String(24), default="district")

    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    # Game theory: concession curve strategy for this requirement's buyer agent.
    negotiation_strategy: Mapped[str] = mapped_column(String(16), default="conceder")

    buyer: Mapped[Business] = relationship(lazy="joined")


class TransportOption(Base, TimestampMixin):
    """A complete per-shipment freight charge for one listing/requirement pair.

    source distinguishes a real collected quotation from a configured demo
    estimate, and the UI is required to label the latter as an estimate.
    """

    __tablename__ = "transport_options"
    __table_args__ = (
        CheckConstraint("freight_paise >= 0", name="ck_transport_freight_nonneg"),
        CheckConstraint("capacity_kg > 0", name="ck_transport_capacity_positive"),
        Index("ix_transport_pair", "listing_id", "requirement_id"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)

    label: Mapped[str] = mapped_column(String(200))
    freight_paise: Mapped[int] = mapped_column(Integer)
    capacity_kg: Mapped[int] = mapped_column(Integer)

    pickup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivery_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    source: Mapped[str] = mapped_column(String(32))  # entered_quote | configured_estimate
    distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_basis: Mapped[str] = mapped_column(String(32), default="unknown")

    created_by_business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)


class Negotiation(Base, TimestampMixin):
    __tablename__ = "negotiations"
    __table_args__ = (Index("ix_negotiations_requirement_status", "requirement_id", "status"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    buyer_business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)

    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    round: Mapped[int] = mapped_column(Integer, default=0)
    max_rounds: Mapped[int] = mapped_column(Integer, default=4)
    current_listing_id: Mapped[str | None] = mapped_column(
        ForeignKey("listings.id"), nullable=True
    )
    failure_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    deal_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    agent_mode: Mapped[str] = mapped_column(String(16), default="fake")
    last_seq: Mapped[int] = mapped_column(Integer, default=0)


class NegotiationCandidate(Base):
    __tablename__ = "negotiation_candidates"
    __table_args__ = (
        UniqueConstraint("negotiation_id", "listing_id", name="uq_candidate_per_negotiation"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    negotiation_id: Mapped[str] = mapped_column(ForeignKey("negotiations.id"), index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"))
    seller_business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    # pending | accepted_provisional | rejected | won | superseded
    status: Mapped[str] = mapped_column(String(24), default="pending")
    reason_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rounds_used: Mapped[int] = mapped_column(Integer, default=0)
    best_offer_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    negotiation_id: Mapped[str] = mapped_column(ForeignKey("negotiations.id"), index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    transport_option_id: Mapped[str] = mapped_column(ForeignKey("transport_options.id"))

    quantity_kg: Mapped[int] = mapped_column(Integer)
    unit_price_paise_per_tonne: Mapped[int] = mapped_column(Integer)

    # Server-computed. Agents never supply these.
    material_paise: Mapped[int] = mapped_column(Integer)
    freight_paise: Mapped[int] = mapped_column(Integer)
    buyer_total_paise: Mapped[int] = mapped_column(Integer)
    seller_receives_paise: Mapped[int] = mapped_column(Integer)

    pickup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivery_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    author: Mapped[str] = mapped_column(String(16))  # buyer | seller | broker
    action: Mapped[str] = mapped_column(String(16))  # propose | counter | accept | reject
    responds_to_offer_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    explanation: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    round: Mapped[int] = mapped_column(Integer, default=0)
    # SHA-256 hash of this offer chained with the previous offer's hash.
    # Forms a tamper-evident audit log for the entire negotiation.
    chain_hash: Mapped[str] = mapped_column(String(64), default="")


class NegotiationEvent(Base):
    __tablename__ = "negotiation_events"
    __table_args__ = (
        UniqueConstraint("negotiation_id", "seq", name="uq_event_seq_per_negotiation"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    negotiation_id: Mapped[str] = mapped_column(ForeignKey("negotiations.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    offer_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Which candidate conversation this belongs to. A seller only ever sees
    # events for its own listing; the buyer sees all of them.
    listing_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        # One deal per requirement. This is the hard guard against allocating
        # the same requirement twice.
        UniqueConstraint("requirement_id", name="uq_deal_per_requirement"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    negotiation_id: Mapped[str] = mapped_column(ForeignKey("negotiations.id"))
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    offer_id: Mapped[str] = mapped_column(ForeignKey("offers.id"))

    seller_business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    buyer_business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)

    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id"))
    intended_use: Mapped[str] = mapped_column(Text, default="")
    quantity_kg: Mapped[int] = mapped_column(Integer)
    unit_price_paise_per_tonne: Mapped[int] = mapped_column(Integer)

    material_paise: Mapped[int] = mapped_column(Integer)
    freight_paise: Mapped[int] = mapped_column(Integer)
    buyer_total_paise: Mapped[int] = mapped_column(Integer)
    seller_receives_paise: Mapped[int] = mapped_column(Integer)

    transport_option_id: Mapped[str] = mapped_column(ForeignKey("transport_options.id"))

    status: Mapped[str] = mapped_column(String(24), default="agreed", index=True)
    # Set exactly once when a cancellation returns stock to the listing.
    stock_released: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("business_id", "endpoint", "key", name="uq_idempotency_scope"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(String(40), index=True)
    endpoint: Mapped[str] = mapped_column(String(80))
    key: Mapped[str] = mapped_column(String(200))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_id: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
