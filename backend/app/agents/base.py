"""The agent interface.

Deliberately separate from the HTTP schemas: an agent returns a decision, not a
response body. The coordinator attaches the fixed requirement quantity, the
quote schedule, the computed costs, the offer ID and the expiry - so an agent
can never move a number it was not authorised to move.

An agent sees only its own private limits. The seller view carries the floor,
the buyer view carries the budget, and neither carries the other's.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import BaseModel, Field

AgentRole = Literal["buyer", "seller", "broker"]


class AgentDecision(BaseModel):
    """Exactly the structured output an agent is allowed to return."""

    action: Literal["propose", "counter", "accept", "reject"]
    listing_id: str
    transport_option_id: str
    unit_price_paise_per_tonne: int = Field(ge=0)
    responds_to_offer_id: str | None = None
    explanation: str = Field(default="", max_length=1200)


class ProviderUnavailable(RuntimeError):
    """The model provider could not be reached, or refused the request."""


class InvalidModelOutput(ValueError):
    """The provider replied, but not with a usable decision."""


@dataclass
class OfferView:
    """One prior offer, as an agent is permitted to see it."""

    offer_id: str
    author: AgentRole
    action: str
    unit_price_paise_per_tonne: int
    buyer_total_paise: int
    seller_receives_paise: int
    explanation: str


@dataclass
class TransportView:
    transport_option_id: str
    label: str
    freight_paise: int
    pickup_at: str
    delivery_at: str
    source: str


@dataclass
class AgentContext:
    """Everything an agent is allowed to know, and nothing else."""

    role: AgentRole
    round_number: int
    max_rounds: int
    listing_id: str
    material_id: str
    quantity_kg: int
    asking_price_paise_per_tonne: int
    transport: TransportView
    seller_district: str
    buyer_district: str
    intended_use: str
    history: list[OfferView] = field(default_factory=list)

    # Exactly one of these is populated, according to role.
    seller_floor_paise_per_tonne: int | None = None
    buyer_max_total_paise: int | None = None

    # Game theory fields — set by the coordinator before every agent turn.
    # strategy: which concession curve this side is using.
    strategy: str = "conceder"  # "conceder" | "boulware"
    # Pre-computed recommended price for this round (from zopa.concession_target).
    concession_target_paise_per_tonne: int | None = None
    # ZOPA: does a deal exist at all given both limits?
    zopa_exists: bool | None = None
    # BATNA: the buyer's best outside option (populated only on buyer turns).
    batna_price_paise_per_tonne: int | None = None
    batna_district: str | None = None
    batna_listing_id: str | None = None

    @property
    def private_values(self) -> list[int]:
        return [
            value
            for value in (self.seller_floor_paise_per_tonne, self.buyer_max_total_paise)
            if value is not None
        ]



class AgentProvider(Protocol):
    """Implemented by FakeAgentProvider and GeminiAgentProvider."""

    name: str

    def decide(self, context: AgentContext) -> AgentDecision: ...
