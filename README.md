# KIB Exchange — Karnataka Industrial Byproduct Exchange

> **BitNBuild Hackathon 2026** · Built by Team `brocxx`

An autonomous B2B marketplace where Karnataka's industrial MSMEs exchange byproducts as secondary raw materials. Buyer, Seller, and Logistics-Broker AI agents negotiate prices and delivery within private owner-defined limits — powered by real government UDYAM data, peer-reviewed yield chemistry, and Google Gemini.

---

## What This Is

Karnataka has **7,933 registered small manufacturers** generating thousands of tonnes of reusable industrial byproduct daily — rice husk from rice mills, sawdust from timber units, metal scrap from fabrication shops. Most of it goes to landfills because matching compatible buyers, confirming logistics, and negotiating prices takes days of manual calls.

**KIB Exchange** eliminates that friction:

1. A seller lists available byproduct with an asking price and a **private minimum floor**
2. A buyer posts a requirement with specs and a **private maximum budget**
3. The system finds compatible matches from real Karnataka enterprises using the UDYAM registry
4. Three Gemini-powered AI agents autonomously negotiate — buyer protecting budget, seller protecting floor, logistics broker computing delivered cost
5. When both sides agree, stock is reserved in an atomic database transaction and a deal is created
6. An honest **no-deal** outcome is returned when budgets genuinely cannot meet seller floors — no hallucinated agreements

---

## Live Demo Flow

```
Seller lists 20 tonnes Rice Husk (Davangere)
    |
Buyer posts requirement: brick kiln fuel, <=15% moisture (Mysuru)
    |
Matching engine: 3 candidates pass, 3 excluded (moisture / quantity / quality)
    |
[START NEGOTIATION]
    Seller proposes  2,750/t -> Buyer counters 1,872/t
    Seller counters  2,649/t -> Buyer counters 2,078/t
    Seller counters  2,549/t -> Buyer ACCEPTS  2,549/t
    |
Deal created . Stock reserved . Delivered: 68,979 (within 70,000 budget)
    |
[NO-DEAL DEMO] Same scenario, budget 50,000 -> BUDGET_NOT_MET after 4 rounds
```

---

## Architecture

```
FRONTEND (React + Vite)
  Login . Dashboard . Listings . Requirements . Matches
  Negotiation Timeline (2s polling) . Deal Detail
  Opportunity Lab (sensitivity sliders + disruption recovery)
         |
         | HTTP /api/v1  (Bearer token)
         |
BACKEND (FastAPI + Python)
  Auth -> Matching -> Costing -> Coordinator State Machine
  [ Buyer Agent (Gemini) ] [ Seller Agent (Gemini) ] [ Logistics Broker (Gemini) ]
  Atomic stock reservation (compare-and-swap SQL)
  Privacy scrubbing (floor/budget never leak to opponent)
         |
         | SQLAlchemy / Alembic
         |
DATABASE (SQLite local / Supabase Postgres)
  Seeded from real Karnataka UDYAM MSME data (7,933 firms)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Plain CSS, React Router |
| **Backend** | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| **Database / Auth** | SQLite (local dev), Supabase Postgres + Auth (production) |
| **AI Agents** | Google Gemini (`gemini-2.5-flash`) via `google-genai` SDK |
| **Agent Mode** | Deterministic fake negotiator (tests/dev), Real Gemini (demo) |
| **Updates** | HTTP polling every 2s; stops on terminal negotiation status |

---

## Dataset

All enterprise data is sourced from the **Government of India UDYAM MSME Registry** (`data.gov.in`). Byproduct yield ratios come from peer-reviewed industrial ecology literature.

| File | Content | Rows |
|---|---|---|
| `dataset/01_raw_msme_enterprises.csv` | Raw UDYAM pull — all Karnataka manufacturing MSMEs | 17,437 |
| `dataset/02_enterprises_with_location.csv` | Cleaned, geocoded — 5 target sectors, district coords | 7,933 |
| `dataset/03_byproducts_per_enterprise.csv` | Byproduct generation per enterprise with yield ratios | 17,555 |
| `dataset/04_industrial_symbiosis_pairs.csv` | 14 verified B2B waste-to-resource routing pathways | 14 |
| `dataset/05_district_distance_matrix_km.csv` | Pairwise Haversine inter-district distances, all 31 districts | 961 |
| `dataset/06_district_headquarters_coordinates.csv` | GPS coordinates for all 31 Karnataka district HQs | 31 |

**Peer-reviewed yield ratios:**

- Rice Husk: **20% of paddy input** — IRRI Rice Knowledge Bank
- Sawdust: **25% of log input** — IEDC Dataset 412
- Sheet Metal Scrap: **22% of sheet input** — IEDC Dataset 439 / Allwood & Music (2024)
- Silk Noil: **25% of cocoon input** — FAO Agricultural Services Bulletin 136
- Broken Bricks/Grog: **7% of kiln output** — GIZ South Asia Brick Sector Guidelines

---

## Repository Structure

```
BitNBuild2k26/
|-- backend/                        # FastAPI service (owned by A)
|   |-- app/
|   |   |-- agents/                 # buyer.py, seller.py, broker.py, gemini.py, fake.py
|   |   |-- api/routes/             # listings, requirements, negotiations, deals, catalog
|   |   |-- services/               # matching, costing, coordinator, reservations
|   |   |-- db/                     # SQLAlchemy models + session
|   |   |-- data/                   # UDYAM importer, data fixes, demo seed
|   |   `-- auth/                   # Supabase JWT verification (JWKS + HS256)
|   |-- alembic/                    # Database migrations
|   |-- tests/                      # 122 tests (pytest)
|   |-- scripts/                    # smoke.py, inspect_db.py, verify_locking.py
|   |-- requests/api.http           # Full VS Code REST Client walkthrough
|   `-- requirements.txt
|-- frontend/                       # React app (owned by B)
|   `-- src/
|       |-- api/                    # types.ts, ApiClient.ts, client.ts, mock.ts
|       |-- auth/                   # Supabase + dev-token auth context
|       |-- pages/                  # Login, Dashboard, Listings, Requirements,
|       |                           # Matches, NegotiationDetail, DealDetail, OpportunityLab
|       |-- components/             # Layout, StatusBadge, CostBreakdown
|       `-- styles/global.css
|-- dataset/                        # Read-only reference data (UDYAM + literature)
|-- contracts/openapi.json          # Exported FastAPI OpenAPI schema
|-- context.md                      # Project scope definition
`-- MVP_TEAM_WORK_PLAN.md           # Full implementation contract
```

---

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows: activate venv
pip install -r requirements.txt

cp .env.example .env            # defaults: SQLite, dev auth, fake agents
python -m app.data.cli reset    # migrate + import 7,933 enterprises + seed demo
uvicorn app.main:app --reload   # http://localhost:8000
```

Interactive API docs at **http://localhost:8000/docs**

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Sign in as demo buyer (dev mode — no JWT needed)
curl -H "Authorization: Bearer dev:buyer1@demo.bitnbuild.local" \
     http://localhost:8000/api/v1/me
```

Demo accounts printed by `reset`:
- `buyer1@demo.bitnbuild.local` — Brick kiln buyer (feasible budget)
- `buyer2@demo.bitnbuild.local` — Sawmill boiler buyer
- `seller1` through `seller6` — Rice mills across 6 Karnataka districts

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# In .env: set VITE_API_MODE=real and VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev                     # http://localhost:5173
```

Click any **demo persona button** on the Login page — no password required in dev mode.

---

## Backend Environment

Three independent switches in `backend/.env`:

| Variable | Default | Alternative | Effect |
|---|---|---|---|
| `DB_TARGET` | `local` | `supabase` | SQLite vs Supabase Postgres |
| `AUTH_MODE` | `dev` | `supabase` | Dev tokens vs verified Supabase JWTs |
| `AGENT_MODE` | `fake` | `gemini` | Deterministic negotiator vs live Gemini model |

> **Gemini quota:** One negotiation across 3 sellers = up to 27 model calls. Always develop against `AGENT_MODE=fake`. Switch to `gemini` only for the live demo.

---

## API Summary

Base: `/api/v1` | Format: JSON `snake_case` | Money: integer INR paise | Quantity: integer kg

| Endpoint | What it does |
|---|---|
| `GET /health` | Liveness check |
| `GET /me` | Authenticated business profile |
| `GET /reference` | Materials, districts, receiving processes |
| `GET /listings` | Paginated public open listings |
| `POST /listings` | Create listing with private seller floor |
| `POST /requirements` | Create requirement with private buyer budget |
| `GET /requirements/{id}/matches` | Compatibility-checked candidates + transport options |
| `POST /negotiations` | Start multi-agent negotiation (idempotent) |
| `GET /negotiations/{id}/events` | Live event stream for polling UI |
| `GET /deals/{id}` | Agreed deal with cost breakdown + reserved stock |
| `PATCH /deals/{id}/status` | Manual delivery status progression |

Full schema: [`contracts/openapi.json`](contracts/openapi.json)

---

## Tests

```bash
cd backend && .venv\Scripts\python -m pytest
# 122 tests | ~60s | no network calls | no Gemini quota
```

Covers: material/spec/moisture/quantity exclusions, absent transport, budget exhaustion, concurrent reservation race condition, privacy leak prevention, idempotency, provider failure, full negotiation state machine.

---

## Team

| Member | Ownership |
|---|---|
| **A — Backend & Agents** | `backend/`, `contracts/`, Supabase config, API deployment |
| **B — Frontend & Integration** | `frontend/`, `README.md`, frontend deployment |
| **C — Demo & Polish** | Demo script, UI feedback (non-blocking) |

---

## Definition of Done

- [x] Listing and requirement creation survive page refresh
- [x] Moisture / quantity / quality filters visibly affect match results
- [x] Three sellers compared by actual configured delivered cost
- [x] Agent negotiation: offers exchange, counteroffers change terms
- [x] One accepted offer creates exactly one deal, decrements stock once
- [x] Too-low budget returns honest no-deal (BUDGET_NOT_MET)
- [x] Provider failure surfaces as an error, never as a fabricated deal
- [x] Two concurrent buyers cannot purchase the same unavailable stock
- [x] Private limits absent from all HTTP responses, events, and agent text
- [x] Frontend TypeScript compiles without errors
- [x] 122 backend tests pass
- [ ] Real Gemini agents end-to-end (set AGENT_MODE=gemini)
- [ ] Render deployment (optional)

---

*Demo prices, floors, budgets, freight charges, and quantities are configured values. Enterprises, registered names, districts, and inter-district distances are real data from the Government of India UDYAM registry.*
