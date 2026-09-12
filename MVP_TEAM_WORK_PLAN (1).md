# Industrial Byproduct Exchange — MVP Team Work Plan

This is the implementation handoff for three teammates and their coding agents. It supersedes earlier proposals involving Groq, external price feeds, price scraping, and standout features. The current `dataset/` directory is the reference dataset; `datasetLegacy/` is a duplicate reference, not another import source.

## 1. Product and fixed scope

Build a Karnataka B2B exchange where sellers list available industrial byproducts and buyers request compatible secondary inputs. Buyer, seller, and logistics-broker agents use Gemini to negotiate material prices and delivery choices within user-defined limits. The system compares complete sourcing options by delivered cost, selects a mutually acceptable option, and reserves material in an in-app agreement.

Prices come from listings. Seller floors and buyer budgets come from their owners. Transport charges come from explicitly configured transport options. There is no market-price API, benchmark database, web search, or automatic carrier booking. Display configured freight estimates as estimates. Do not assume the district distance matrix determines a freight charge.

MVP boundaries:
- One supported material end to end initially: rice husk. Canonical material ID: `rice_husk`.
- One seller, one buyer, one listing, and one transport option per deal.
- Buyer requests an exact quantity; partial orders, pooling, and quantity negotiation are deferred.
- Negotiate material unit price and select among offered pickup/delivery slots. Buyer pays the listed freight charge in this version; the broker can propose a different option but cannot invent a carrier discount.
- Compare at most three eligible sellers and two transport options per seller. Maximum four counteroffer rounds per candidate seller.
- Profiles can buy and sell; there are no separate applications or transporter accounts.
- Automatic in-app acceptance is authorized when the owner starts a request/enables a listing with its limits. Real external bookings are outside scope.
- No external pricing, emissions claims, payments, OCR, voice, forecasting, ratings, or advanced optimization.

### Required features and screens

| Screen | Required behavior |
|---|---|
| Login/profile | Supabase email/password login; select the user's business and its confirmed receiving processes. Use prepared demo accounts; public signup is optional. |
| Dashboard | Own listings, requirements, negotiations, and deals. Derived from list endpoints; no separate dashboard API is needed. |
| Listings & requirements | Create listings/requests, enter specifications and time windows, and privately configure seller floor/buyer budget. Seller can close a listing. |
| Matches | Show compatible seller listings, intended production use, quantity, selected transport choices, and initial delivered cost. Explain exclusions. Start negotiation. |
| Negotiation detail | Poll persisted events. Display offers, counteroffers, delivery choices, final result, and errors. Never expose private opponent limits. |
| Deal detail | Agreed terms, cost breakdown, location/route summary, reserved quantity, manual delivery status, downloadable JSON summary. |

The map is secondary. A location summary is sufficient for the first integration. District coordinates must be labeled approximate; route geometry is optional and uses confirmed pins when available.

## 2. Stack

- Frontend: React, TypeScript, Vite, plain CSS, React Router, Supabase JS for authentication.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic.
- Database/auth: Supabase Postgres and Auth, Free plan. FastAPI owns application data access and verifies Supabase access tokens. The frontend never directly reads private business tables.
- Agents: Gemini Developer API through the official Python `google-genai` SDK; configurable `GEMINI_MODEL`. Select a Flash model available on the team's Free tier and verify a structured-output call during setup. No Groq dependency.
- Coordinator: ordinary Python state machine with persisted steps, not a fourth LLM agent.
- Updates: HTTP polling every two seconds while a negotiation is queued/running; stop polling at a terminal status.
- Optional map/routing: Leaflet and openrouteservice Free plan. Missing routing credentials must not break negotiation; use labeled district approximations and separately entered freight costs.
- Tests: pytest for backend logic; frontend typecheck/build and browser walkthrough.
- Development: localhost. Optional hosting: Render static frontend + Python service, with Supabase persistence. A owns backend deployment; B owns frontend deployment.

Gemini Free tier is quota-limited. Keep keys on the backend, bound retries, and surface provider failures. A fake provider is permitted only for automated tests and an explicitly labeled mock mode; never silently replace a failed Gemini run with a fabricated live negotiation.

Official references, checked for this handoff:
- Gemini pricing/free access: https://ai.google.dev/gemini-api/docs/pricing
- Python SDK: https://ai.google.dev/gemini-api/docs/libraries
- Structured outputs: https://ai.google.dev/gemini-api/docs/structured-output
- Supabase free plan: https://supabase.com/pricing
- Render free limitations: https://render.com/docs/free

## 3. Ownership and parallel work

| Person | Availability | Exclusive ownership | Deliverable |
|---|---|---|---|
| A — Backend and agents | Fully available | `backend/**`, `contracts/**`, backend deployment settings | Running API, authentication, database, seed, matching, Gemini agents, reservations, backend tests |
| B — Frontend and integration | Fully available | `frontend/**`, `README.md`, `.gitignore`, `docs/INTEGRATION_CHECKLIST.md`, frontend deployment settings | Complete UI against mocks first, then real API; browser verification and final integration coordination |
| C — Light presentation support | Very limited time; traveling | `docs/DEMO_SCRIPT.md`, `docs/UI_FEEDBACK.md` | A short demo script and optional wording/usability feedback; no application code or critical deliverables |

Nobody edits another person's directory. A owns API contracts and backend dependency files. B owns frontend dependency files and its lockfile. Do not create or edit a root package manifest. Existing raw CSVs are read-only to all three; A applies necessary data corrections in the importer or backend-owned overlays rather than changing the source files. C has no data-cleaning, agent, API, testing, deployment, or integration responsibility.

Allocate approximately 50% of the work to A, 45% to B, and at most 5% to C. C's work is optional polish and must never be on the critical path.

### A: exact task sequence

1. Scaffold FastAPI, settings, database migrations, Supabase token verification, health endpoint, and `/api/v1` routes. Read this contract before choosing field names.
2. Create `contracts/openapi.json` from FastAPI and commit it early. This document is the initial contract until the exported schema exists. Explicit public/owner response schemas must prevent leaking private fields.
3. Import district/material/pathway references. Own all necessary demo-pathway data fixes: material aliases, rice-milling classification, and safe enterprise-name recovery (use IDs when unresolved). Seed a small working rice-husk scenario immediately, using clearly labeled demo business profiles and user-entered operational fields. Do not wait for C.
4. Implement CRUD, specification/window filters, cost comparison, and owner checks before Gemini integration.
5. Implement the three agent types and coordinator. Use a fake model in tests while developing; connect real Gemini before the live demo.
6. Persist events/offers, implement request idempotency, reserve inventory transactionally, and support valid deal transitions.
7. Add meaningful tests: incompatible material/specifications, absent freight, no feasible price, invalid model output, provider failure, repeated negotiation start, and competing stock reservations.
8. Publish backend URL, allowed frontend origin, health response, and exported OpenAPI to B. Own any remaining data fixes; do not delegate core completion to C.

Suggested backend layout:
```text
backend/app/api/          # routes and request/response schemas
backend/app/agents/       # buyer.py, seller.py, broker.py, gemini.py
backend/app/services/     # matching, costing, coordinator, reservations
backend/app/db/           # models and repositories
backend/app/data/         # import and seed logic
backend/tests/
backend/alembic/
backend/.env.example
contracts/openapi.json
```

### B: exact task sequence

1. Scaffold Vite/React/TypeScript and the screens above. Create `frontend/src/api/types.ts` from the contract below, then `client.ts` and `mock.ts` with the same interface.
2. Build every screen using `VITE_API_MODE=mock`; this must work without A's server, Supabase, or Gemini. Mock mode is visibly labeled and local-development only.
3. Implement Supabase login for real mode. Route all application requests through `client.ts`, attaching the access token. Never embed Gemini/database service keys.
4. Implement forms, owner-only private settings, cost formatting, event polling, terminal/error states, and deal summary download.
5. Switch to `VITE_API_MODE=real` once A's initial routes are ready. First integrate login/listing/request/matches; then negotiation/deal endpoints.
6. Run typecheck/build and the acceptance checklist against the combined app. Own root setup instructions and collect both deployment URLs.

Suggested frontend layout:
```text
frontend/src/api/{types,client,mock}.ts
frontend/src/auth/
frontend/src/pages/
frontend/src/components/
frontend/src/styles/
frontend/.env.example
```

### C: small, non-critical tasks only

Budget about 30–60 minutes total if available; this is a suggested cap, not a prerequisite for completion.

1. Main small task: write `docs/DEMO_SCRIPT.md`, no more than one page, describing a 3–5 minute walkthrough: seller listing -> buyer request -> alternatives -> negotiation -> deal, followed by a low-budget no-deal case. Use this plan as context; running the application is unnecessary.
2. Optional, only if time remains: review screenshots or a short recording supplied by B. Record up to five confusing labels, missing loading/error messages, or wording improvements in `docs/UI_FEEDBACK.md`. This is optional feedback, not release testing or sign-off.
3. Deliver either document whenever convenient. C does not edit frontend files to apply feedback. B chooses whether to incorporate suggestions.

If C does nothing, A and B still finish, test, merge, and present the app using the walkthrough already included in this document. Do not assign C a required screen, data cleanup, test suite, integration task, or deployment task.

## 4. HTTP API contract — freeze before parallel implementation

Base: `/api/v1`. JSON uses `snake_case`. IDs are opaque strings (UUIDs for new records; retain existing enterprise IDs). Datetimes are ISO 8601 UTC strings. Money is integer INR paise, quantity is integer kilograms, distance is integer meters. UI converts to rupees and tonnes. Example: `250000` paise/tonne is INR 2,500/tonne.

All routes except `/health` require `Authorization: Bearer <Supabase access token>`. Backend resolves the user's business; never accept an owner ID from a create request. Cross-business access to private settings returns 403. Paginated lists use `{items: [...], next_cursor: null|string}` with `limit` default 20/max 100. Detail/create responses return the object directly.

Errors: `{ "error": { "code": "INSUFFICIENT_STOCK", "message": "...", "details": {} } }`. Use 401 unauthenticated, 403 forbidden, 404 missing, 409 conflict, 422 invalid input, 503 unavailable dependency. Validation errors use the same envelope.

### Shared object schemas

Notation: `?` means optional request field; nullable fields are stated explicitly. Request windows must start before they end. Quantities/prices are nonnegative; requested/available quantity must be positive at creation. Freight is a complete per-shipment charge, not a per-kilometer rate.

```typescript
type Window = { start: string; end: string };
type Location = {
  district: string;
  lat: number | null;
  lon: number | null;
  precision: "district" | "confirmed_site";
};
type Business = {
  id: string; name: string; enterprise_id: string | null;
  roles: ("buyer" | "seller")[];
  receiving_processes: string[]; // seeded IDs such as brick_kiln_fuel
  location: Location;
};
type Listing = {
  id: string; seller: Business; material_id: string;
  available_quantity_kg: number;
  asking_price_paise_per_tonne: number;
  moisture_pct: number; contamination_notes: string;
  pickup_window: Window; location: Location;
  status: "open" | "closed";
};
type Requirement = {
  id: string; buyer: Business; material_id: string;
  receiving_process_id: string; quantity_kg: number;
  max_moisture_pct: number; delivery_window: Window;
  location: Location; status: "open" | "fulfilled" | "closed";
};
type TransportOption = {
  id: string; listing_id: string; requirement_id: string;
  label: string; freight_paise: number; capacity_kg: number;
  pickup_at: string; delivery_at: string; expires_at: string;
  source: "entered_quote" | "configured_estimate";
  distance_m: number | null;
  distance_basis: "road" | "district_straight_line" | "unknown";
};
type Costs = {
  material_paise: number; freight_paise: number;
  buyer_total_paise: number; seller_receives_paise: number;
};
```

For this version listing price includes seller-side handling; transport options must state a complete freight amount, including any included loading/unloading. No processing fee or tax engine. All compared entries must use the same explicitly declared tax basis; demo data uses amounts before tax. Display this basis on totals.

Private fields are never part of public `Listing`/`Requirement`: `seller_floor_paise_per_tonne` and `buyer_max_total_paise`. `/me/listings` adds the former; `/me/requirements` adds the latter. Offer explanations/events must also avoid disclosing these limits.

### Routes

| Method and path | Input / output |
|---|---|
| `GET /health` | `{status:"ok"}`; no secrets or dependency credentials |
| `GET /me` | `{user_id, business: Business}` |
| `GET /reference` | `{materials:[{id,name}], districts:[{name,lat,lon}], receiving_processes:[{id,name,material_ids:string[]}]}` |
| `GET /listings?material_id=&district=&cursor=&limit=` | Paginated public `Listing` objects; open only by default |
| `GET /listings/{id}` | Public `Listing` |
| `GET /me/listings` | Paginated own listings including private floor |
| `POST /listings` | Listing fields excluding ID/seller/status, plus `seller_floor_paise_per_tonne`; returns 201 owner listing. `location` defaults to own business location if omitted. |
| `PATCH /listings/{id}` | Owner only: optional `asking_price_paise_per_tonne`, `seller_floor_paise_per_tonne`, `pickup_window`, `status`. Revalidate negotiation state at commit. No direct stock editing in MVP. |
| `GET /me/requirements` | Paginated own requirements including private budget |
| `POST /requirements` | Requirement fields excluding ID/buyer/status, plus `buyer_max_total_paise`; returns 201 owner requirement. `location` defaults to own business location. |
| `GET /requirements/{id}` | Owner requirement; other users cannot retrieve private request details through this endpoint |
| `GET /requirements/{id}/matches` | Owner only. `{requirement_id, candidates:[{listing:Listing, pathway_use:string, transport_options:TransportOption[], initial_best_cost:Costs}], excluded:[{listing_id,reason_codes:string[]}], missing_transport_listing_ids:string[]}` |
| `POST /transport-options` | Seller of listing or buyer of requirement can enter an option for that pair; input all TransportOption fields except `id`; returns 201 object. A small form on Matches is sufficient. Other users cannot edit pair data. |
| `POST /negotiations` | `{requirement_id, listing_ids:string[]}` plus required `Idempotency-Key` header; max three unique listing IDs. Returns 202 `{id,status:"queued"}`. Only owner of requirement may start. |
| `GET /me/negotiations` | Paginated `{id,requirement_id,status,created_at,deal_id}`; own/participating runs only |
| `GET /negotiations/{id}` | Negotiation object below; participant access, appropriately filtered by business |
| `GET /negotiations/{id}/events?after_seq=0` | `{items:Event[], last_seq:number}`; polling, ascending sequence, no duplicates |
| `GET /me/deals` | Paginated Deal objects; involved business only |
| `GET /deals/{id}` | Deal object; involved business only |
| `PATCH /deals/{id}/status` | `{status:"pickup_scheduled"|"collected"|"delivered"|"cancelled"}`; allowed transitions below |

`GET /negotiations/{id}` returns:
```typescript
type Negotiation = {
  id: string; requirement_id: string;
  status: "queued" | "running" | "agreed" | "no_deal" | "failed";
  round: number; max_rounds: number; // round within current candidate
  current_listing_id: string | null;
  failure_code: string | null; deal_id: string | null;
  offers: Offer[]; created_at: string; updated_at: string;
};
type Offer = {
  id: string; listing_id: string; transport_option_id: string;
  quantity_kg: number; unit_price_paise_per_tonne: number;
  costs: Costs; pickup_at: string; delivery_at: string;
  author: "buyer" | "seller" | "broker";
  action: "propose" | "counter" | "accept" | "reject";
  responds_to_offer_id: string | null;
  explanation: string; expires_at: string;
};
type Event = {
  seq: number; type: "started" | "offer" | "candidate_rejected" |
    "agreed" | "no_deal" | "failed";
  actor: "buyer" | "seller" | "broker" | "system";
  message: string; offer_id: string | null; created_at: string;
};
type Deal = {
  id: string; negotiation_id: string; requirement_id: string;
  listing_id: string; seller: Business; buyer: Business;
  material_id: string; intended_use: string; quantity_kg: number;
  unit_price_paise_per_tonne: number; costs: Costs;
  transport_option: TransportOption;
  status: "agreed" | "pickup_scheduled" | "collected" |
    "delivered" | "cancelled";
  created_at: string;
};
```

Buyer sees evaluated offers for its request. Each seller sees only its own candidate conversation and resulting deal, not competitors' offers. Events must be filtered consistently; sequence gaps are allowed. Unknown/missing information must produce a reason or incomplete state, not an assumed pass.

Matching reason codes: `MATERIAL_MISMATCH`, `PROCESS_UNCONFIRMED`, `QUALITY_MISMATCH`, `QUALITY_REVIEW_REQUIRED`, `INSUFFICIENT_QUANTITY`, `TIME_WINDOW_MISMATCH`, `NO_TRANSPORT_OPTION`. Contamination notes that need review do not automatically pass because moisture is acceptable. Seed a small reviewed material-compatibility flag in the backend rather than claiming universal material certification.

Price comparison before negotiation may exceed the buyer budget because the seller may concede. Do not exclude a listing solely because its asking price exceeds the budget. Negotiation outcomes include `BUDGET_NOT_MET`, `SELLER_DECLINED`, `QUOTE_EXPIRED`, `STALE_STOCK`, `ROUND_LIMIT`, `PROVIDER_UNAVAILABLE`, `INVALID_MODEL_OUTPUT`, and `INTERRUPTED`. Terminal `no_deal` is a business outcome; terminal `failed` is an execution error.

### Request example

`POST /requirements`:
```json
{
  "material_id": "rice_husk",
  "receiving_process_id": "brick_kiln_fuel",
  "quantity_kg": 2000,
  "max_moisture_pct": 15,
  "delivery_window": {"start":"2026-10-01T03:30:00Z","end":"2026-10-03T12:30:00Z"},
  "buyer_max_total_paise": 700000
}
```
These example values are scenario inputs, not sourced market facts. Seed scripts should generate future dates relative to execution so fixtures do not expire before the demo.

## 5. Agent interface, costs, and consistency

A keeps the internal agent interface separate from HTTP schemas. Each agent receives only its permitted view and returns Pydantic-validated structured JSON:
```text
action: propose | counter | accept | reject
listing_id
transport_option_id
unit_price_paise_per_tonne
responds_to_offer_id: nullable
explanation
```
The coordinator attaches the fixed requirement quantity, quote schedule, computed costs, offer ID, and expiry. Unknown listing/quote IDs, out-of-range prices, invalid actions, and acceptance of a superseded offer are rejected. Agents never compute authoritative totals or mutate the database themselves.

Use Decimal/integer arithmetic with round-half-up to the nearest paise:
```text
material_paise = round_half_up(unit_price_paise_per_tonne * quantity_kg / 1000)
buyer_total_paise = material_paise + freight_paise
seller_receives_paise = material_paise
```
Accept only if unit price meets seller floor, total meets buyer budget, the exact same complete offer is accepted by both sides, material/quality/process checks pass, quote capacity/schedule/expiry pass, and stock is available. No price benchmark is needed.

The broker ranks feasible offers by `buyer_total_paise`, then earlier delivery, then listing ID for deterministic ties. Seller and buyer limits remain isolated from opponents; trusted server validation can use both.

Candidate acceptance is provisional until one winner is committed. In a single database transaction, lock the requirement and selected listing, recheck quote/listing versions and available stock, decrement available quantity once, mark the requirement fulfilled, and create the deal. A unique deal constraint per requirement plus idempotency prevents duplicate allocations. Do not reserve stock for every candidate that provisionally accepts.

Transitions: agreed -> pickup_scheduled -> collected -> delivered. Either participant can cancel before collection; seller marks scheduled/collected, buyer marks delivered. Cancellation releases reserved stock exactly once and reopens the requirement. Cancellation after collection is outside this MVP and returns 409. If listing is closed, restored stock remains closed.

Persist negotiation state and events after each step. On backend restart, safely mark abandoned runs failed with `INTERRUPTED` or resume from the last persisted step without reapplying side effects. An HTTP retry with the same idempotency key/body returns the original run; a changed body with that key returns 409. Permit only one queued/running negotiation per requirement. A terminal failed/no_deal run can be retried with a new key.

## 6. Environment and parallel development

A's `backend/.env.example`:
```text
DATABASE_URL=
SUPABASE_URL=
GEMINI_API_KEY=
GEMINI_MODEL=
CORS_ORIGINS=http://localhost:5173
AGENT_MODE=gemini
```
A configures JWT verification using the project's supported Supabase signing mechanism; never trust decoded-but-unverified token contents. Any admin/service credential needed for demo-user provisioning stays in a backend-only seed environment and out of source control.

B's `frontend/.env.example`:
```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_API_MODE=mock
VITE_SUPABASE_URL=
VITE_SUPABASE_PUBLISHABLE_KEY=
```
Supabase's public/publishable frontend key is distinct from service credentials. Real-mode errors never trigger automatic mock fallback.

B can implement all views immediately from these schemas. A can test the API and agents without any frontend. C can write a short walkthrough from this document without either implementation. Application code must never import or depend on C's deliverables.

## 7. Merge and integration plan

1. Commit this handoff to the shared base. Create separate branches/checkouts: `feat/backend-agents` (A), `feat/frontend` (B), `docs/demo-polish` (C, only if contributing). Each teammate works in its own clone/worktree; do not switch branches in a shared working directory.
2. A exports initial OpenAPI after scaffolding. B compares it with the mock types immediately. Freeze names, units, enums, and error envelope before building additional screens.
3. First checkpoint: A has health/auth/seed/listings/requirements/matches; B has the corresponding UI in mock mode. Integrate those endpoints while A continues agents and B builds negotiation/deal views.
4. Second checkpoint: A completes fake-provider tests then real Gemini execution; B wires polling and deals. This should happen before optional map/deployment polish.
5. B coordinates merge requests into the integration branch: backend/API first, frontend second. Use ordinary merge commits or the team's standard merge method, no force pushes. Directory ownership should eliminate most conflicts.
6. B optionally merges C's documentation branch whenever ready. B alone applies any chosen UI feedback in a frontend commit. C's absence does not delay either checkpoint or the presentation.
7. Contract changes go through A: add/adjust backend schema, regenerate OpenAPI, notify B with the exact change. B alone updates frontend types/mocks/client. Prefer additive changes after the first checkpoint.
8. Run migrations and seed once against a dedicated demo database. B records local launch commands and URLs in README. Run the final acceptance checks together.

### Definition of done

- A new seller listing and buyer request can be created through the UI and survive refresh.
- Process/specification/quantity/schedule checks visibly affect candidates.
- At least two listing/transport combinations can be compared by actual configured delivered cost.
- Real Gemini-backed agents exchange validated offers; at least one counteroffer changes terms.
- One mutually accepted offer creates one persistent deal and reserves stock once.
- Too-low budget produces no_deal without violating a seller floor.
- Provider failure is visible and never creates an agreement.
- Two competing requests cannot buy the same unavailable stock.
- Seller/buyer private limits do not leak in opposing HTTP responses, events, or agent explanations.
- Basic manual status flow works; configured estimates and simulated fulfillment are labeled.
- Frontend typecheck/build and focused backend tests pass. Combined app works locally before deployment.

## 8. Demo and presentation wording

Show: seller listing -> buyer request -> compatible alternatives and listing-derived cost comparison -> live negotiation -> agreed delivery plan and reservation. Then lower the budget for a separate request and show an honest no-deal outcome.

Describe the result as "lowest delivered cost among evaluated feasible offers." Listings and budgets are user-entered; freight may be a labeled configured estimate. Do not call these market prices, verified industry offers, guaranteed savings, actual bookings, or actual deliveries.
