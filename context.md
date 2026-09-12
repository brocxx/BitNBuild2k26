# Karnataka Industrial Byproduct Exchange — Hackathon MVP

## Goal

Help manufacturers buy compatible industrial byproducts from other businesses. Analyze material suitability, compare sourcing alternatives, autonomously negotiate terms, and create an agreed delivery plan.

## Scope

Start with rice husk and several seller listings.

Each deal involves one seller, one buyer, and one transport option. The buyer requests a fixed quantity. Pooling and partial fulfillment are out of scope for the MVP.

## Pricing

Use seller-entered asking prices, private seller minimum prices, private buyer budgets, and configured transport charges.

Compare total delivered cost. Do not use external pricing feeds or benchmarks. Clearly label estimated freight charges.

## Features

- Business profiles supporting buying and selling.
- Material listings and buyer requirements.
- Compatibility checks for material, receiving process, specifications, available quantity, and timing.
- Comparison of eligible listing and transport combinations.
- Autonomous offers and counteroffers within owner-defined limits.
- Persistent agreement, stock reservation, and manual delivery status.
- Explicit no-deal and provider-error outcomes.

## Agents

1. **Buyer agent:** negotiates within budget and receiving requirements.
2. **Seller agent:** protects minimum price and pickup constraints.
3. **Logistics-broker agent:** compares transport options and coordinates delivery choices.

Use Gemini for proposals and explanations. A Python coordinator controls execution. Backend code validates offers, computes costs, and reserves inventory. Never expose private limits to counterparties.

## UI

The UI includes:

- Login and profile
- Dashboard
- Listings and requirements
- Match results
- Negotiation timeline
- Deal details

A map is optional for the first working version.

## Tech stack

- **Frontend:** React + TypeScript + Vite + plain CSS
- **Backend:** Python + FastAPI + Pydantic + SQLAlchemy + Alembic
- **Database and authentication:** Supabase Postgres and Auth, Free plan
- **LLM:** Gemini Developer API through `google-genai`, using a configurable Flash model
- **Updates:** HTTP polling
- **Optional maps:** Leaflet + openrouteservice
- **Hosting:** Local development; optional Render free hosting

## Data

Use the current `dataset/` CSV files as reference data. Keep inferred annual quantities separate from actual listed inventory. Apply necessary demo-pathway data fixes during implementation.

## Demo

Create a listing → create a buyer request → compare compatible alternatives → watch Gemini agents negotiate → show the agreement and reserved stock.

Then demonstrate a no-deal outcome with an insufficient buyer budget.

## Implementation contract

Follow [`docs/MVP_TEAM_WORK_PLAN.md`](docs/MVP_TEAM_WORK_PLAN.md).

- API base: `/api/v1`
- JSON uses `snake_case`
- IDs are opaque strings
- Timestamps are UTC ISO 8601 strings
- Money uses integer INR paise
- Quantity uses integer kilograms
- Frontend uses contract-matching mocks until backend endpoints are ready
