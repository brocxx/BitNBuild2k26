# KIB Exchange — Karnataka Industrial Byproduct Exchange

> **BitNBuild Hackathon 2026** · Built by Team `brocxx`

An autonomous B2B marketplace where Karnataka industrial MSMEs exchange byproducts as secondary raw materials. AI agents powered by **real government UDYAM data**, **peer-reviewed yield chemistry**, and **formal Game Theory** negotiate prices deterministically — not randomly.

---

## What This Is

Karnataka has **7,933 registered small manufacturers** generating thousands of tonnes of reusable industrial byproduct daily — rice husk from rice mills, sawdust from timber units, metal scrap from fabrication shops. Most of it goes to landfills because matching compatible buyers, confirming logistics, and negotiating prices takes days of manual calls.

**KIB Exchange** eliminates that friction with a provably-correct negotiation system:

1. A seller lists available byproduct with an asking price and a **private minimum floor**
2. A buyer posts a requirement with specs and a **private maximum budget**
3. The system finds compatible matches from real Karnataka enterprises using the UDYAM registry
4. The **ZOPA Engine** mathematically checks if a deal is possible _before_ making any LLM calls
5. Three AI agents negotiate using **formal Game Theory concession strategies** (Boulware or Conceder)
6. Every accepted offer is validated against hard server-side limits and **SHA-256 hash-chained** into an immutable audit log
7. A **Digital Green Certificate** is generated for every closed deal showing CO₂ avoided

---

## Differentiators Built (Hackathon Phase 2)

### 1. Game-Theoretic Negotiation Engine (Not Random LLM Chat)

Normal chatbot negotiation: the LLM picks numbers between min and max until they match. That is a toy.

Our system uses formal Game Theory:

**ZOPA Engine** (`app/services/zopa.py`):
- Before any LLM call, Python mathematically checks if a Zone of Possible Agreement exists
- If `seller_floor > buyer_ceiling_after_freight` → instant `ZOPA_IMPOSSIBLE` failure, zero API quota burned
- The ZOPA overlap range is emitted as a system event and shown in the negotiation timeline

**Agent Concession Strategies** (`negotiation_strategy` field on listings/requirements):
- `"conceder"` — Smooth linear walk from asking price to floor over all rounds. Maximises deal probability
- `"boulware"` — Holds near asking price for rounds 0-2, then drops sharply at the deadline. Maximises margin if the deal closes; risks no-deal (Boulware Strategy, named after GE's Lemuel Boulware, 1948)

**Math-Guided Gemini** (`app/agents/prompts.py`):
Gemini receives pre-computed facts in its brief every turn:
```json
{
  "negotiation_strategy": "boulware",
  "zopa_exists": true,
  "concession_target_this_round_paise_per_tonne": 2650,
  "batna_alternative_seller": {
    "asking_price_paise_per_tonne": 2300,
    "district": "DAVANGERE"
  }
}
```
The model writes the explanation. Python decided the price range. Hallucinations cannot affect the deal outcome because the coordinator hard-validates every offer against the mathematical limits regardless.

**BATNA** (Best Alternative to a Negotiated Agreement):
If multiple sellers are candidates, the buyer agent receives the cheapest competitor's real price as leverage — cited from real data, not invented.

---

### 2. ESG Carbon & Circularity Metric Engine

Every closed deal generates verified environmental impact metrics:

| Metric | Formula |
|---|---|
| **CO₂e Avoided (gross)** | `quantity_tonnes × emission_factor_of_virgin_equivalent` |
| **Transport Emissions** | `quantity_tonnes × distance_km × 0.062 kg CO₂e/tonne-km` |
| **Net CO₂e Avoided** | `gross_avoided − transport_emitted` |
| **Landfill Diverted** | `quantity_kg` (direct, one-to-one) |
| **Carbon Credits** | `net_CO₂e_tonnes` (1 credit = 1 tCO₂e) |

Emission factors used (peer-reviewed IPCC/MNRE sources):

| Material | Replaces | CO₂e Saved/tonne |
|---|---|---|
| Rice Husk | Coal | 1,400 kg CO₂e |
| Sawdust | Coal | 1,350 kg CO₂e |
| Wood Bark | Coal | 1,300 kg CO₂e |
| Rice Bran | Coal | 800 kg CO₂e |
| Paddy Straw | Coal | 1,250 kg CO₂e |
| Sugarcane Bagasse | Coal | 1,200 kg CO₂e |

**`GET /deals/{id}/certificate`** — returns a signed JSON certificate with all ESG metrics, audit chain root hash, and verification flag. The frontend renders this as a downloadable "Digital Green Bill of Lading."

---

### 3. Cryptographic Audit Trail (SHA-256 Chain)

Every negotiation offer is SHA-256 hashed into a tamper-evident chain:

```
offer_1_hash = SHA256(offer_id + price + round + timestamp + "GENESIS")
offer_2_hash = SHA256(offer_id + price + round + timestamp + offer_1_hash)
offer_3_hash = SHA256(...)  ← and so on
```

If any historical offer record is tampered with, the hash chain breaks. The negotiation timeline UI displays each hash so judges (and counterparties) can independently verify.

**`chain_hash`** is stored on every `Offer` DB row. The deal certificate includes the root hash for the entire negotiation.

---

### 4. Negotiation Strategy Field

`negotiation_strategy: "conceder" | "boulware"` is a first-class field on both `listings` and `requirements`:
- Stored in the database with a migration
- Accepted in `POST /listings` and `POST /requirements` request bodies
- Returned in all listing/requirement API responses
- Drives the agent concession curve throughout the negotiation

---

### 5. Geospatial Symbiosis Discovery Engine

Direct real-time querying over the entire Karnataka MSME industrial ecosystem:
- **`GET /api/v1/map/enterprises`** — Query 7,933 real UDYAM enterprises with exact coordinates, district headquarters, NIC sector, and communication addresses.
- **`GET /api/v1/map/symbiosis?district=DAVANGERE&radius_km=150`** — Instant proximity matching of complementary producer/receiver industries using the 14 symbiosis pathways and road distance matrix.
- **`GET /api/v1/map/stats`** — Live aggregate counter showing 7,933 enterprises, 31 districts, 14 symbiosis pathways, and active closed trades.

---

## Architecture

```
FRONTEND (React + Vite + TypeScript)
  Login · Dashboard · Listings · Requirements · Matches
  Negotiation Timeline (2s polling) · Deal Detail · ESG Certificate
  Opportunity Lab · [Teammate] Symbiosis Map (Leaflet)
         |
         | HTTP /api/v1  (Bearer token)
         |
BACKEND (FastAPI + Python 3.12)
  Auth → Matching → ZOPA Check → Concession Curve → Coordinator State Machine
  [ Buyer Agent (Gemini) ] [ Seller Agent (Gemini) ] [ Logistics Broker (Gemini) ]
  Atomic stock reservation (compare-and-swap SQL)
  Privacy scrubbing (floor/budget never leak to opponent)
  SHA-256 offer chain (tamper-evident audit log)
  ESG carbon math engine
         |
  SQLite (dev) / Supabase Postgres (prod)
         |
  DATASET (Read-only reference)
  7,933 Enterprises · 31 Districts · 14 Symbiosis Pathways
  District distance matrix · Yield chemistry ratios
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Leaflet (map) |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| AI Agents | Google Gemini 2.0 Flash (structured JSON output) |
| Game Theory | Custom ZOPA engine, Boulware/Conceder curves |
| Database | SQLite (dev), Supabase Postgres (prod) |
| Auth | Dev tokens (local) / Supabase JWT (prod) |

---

## Dataset Sources

| File | Source | Records |
|---|---|---|
| `01_karnataka_byproduct_symbiosis.csv` | FAO waste-stream yield ratios + IEDC literature | 14 pathways |
| `02_enterprises_with_location.csv` | UDYAM MSME Registry (Karnataka) | 7,933 enterprises |
| `05_byproduct_yields_by_nic.csv` | Peer-reviewed agricultural/industrial yield chemistry | NIC 2-digit |
| `06_district_headquarters_coordinates.csv` | Survey of India (31 Karnataka district HQs) | 31 districts |
| `07_district_distance_matrix.csv` | Haversine from district HQ coordinates | 961 pairs |

All data sources verified and cited in `dataset/VALIDATION_REPORT.md`.

---

## Running Locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
alembic upgrade head
python -m app.data.cli reset    # seed demo data
uvicorn app.main:app --port 8000
```

**Backend `.env`:**
```env
AUTH_MODE=dev
DB_TARGET=local
AGENT_MODE=gemini
GEMINI_API_KEY=AIza...your-key-here
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

**Frontend `.env`:**
```env
VITE_API_MODE=real
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### Demo Personas (dev login)

| Email | Role |
|---|---|
| `seller1@demo.bitnbuild.local` | Rice Husk seller (Davangere) |
| `buyer1@demo.bitnbuild.local` | Brick kiln buyer (Mysuru) |

---

## API Contract (Key Endpoints)

| Method | Path | Description |
|---|---|---|
| `GET` | `/me` | Current user profile |
| `POST` | `/listings` | Create listing (`negotiation_strategy` field included) |
| `POST` | `/requirements` | Create requirement (`negotiation_strategy` field included) |
| `GET` | `/me/matches` | Scored candidate listings for my requirement |
| `POST` | `/negotiations` | Start autonomous negotiation |
| `GET` | `/negotiations/{id}` | Poll negotiation status + full offer history with `chain_hash` |
| `GET` | `/deals/{id}` | Deal detail with `esg_metrics` |
| `GET` | `/deals/{id}/certificate` | Digital Green Bill of Lading (ESG certificate JSON) |
| `GET` | `/map/enterprises` | All MSME enterprises with lat/lon for Leaflet map |
| `GET` | `/map/symbiosis` | Compatible enterprises within radius |
| `GET` | `/reference` | Materials, receiving processes, symbiosis pathways |

Full OpenAPI spec: `contracts/openapi.json`

---

## Project Structure

```
BitNBuild/
├── backend/
│   ├── app/
│   │   ├── agents/          # Gemini + Fake + Base protocol
│   │   │   ├── base.py      # AgentContext (strategy, ZOPA, BATNA fields)
│   │   │   ├── fake.py      # Deterministic Boulware/Conceder curves
│   │   │   ├── gemini.py    # Gemini structured-output agent
│   │   │   └── prompts.py   # build_brief() — injects game-theory math
│   │   ├── services/
│   │   │   ├── coordinator.py  # Negotiation state machine
│   │   │   ├── matching.py     # Candidate scoring
│   │   │   ├── costing.py      # Paise arithmetic (no floats)
│   │   │   ├── zopa.py         # ZOPA + Boulware/Conceder + BATNA [NEW]
│   │   │   └── esg.py          # CO₂e carbon math engine [NEW]
│   │   ├── api/routes/
│   │   │   ├── listings.py     # negotiation_strategy field
│   │   │   ├── requirements.py # negotiation_strategy field
│   │   │   ├── deals.py        # esg_metrics + certificate endpoint
│   │   │   ├── negotiations.py # chain_hash on offers
│   │   │   └── map.py          # enterprises + symbiosis endpoints [NEW]
│   │   └── db/
│   │       └── models.py       # negotiation_strategy + chain_hash columns
│   └── alembic/versions/       # DB migrations
├── frontend/src/
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Listings.tsx        # strategy slider [teammate]
│   │   ├── NegotiationDetail.tsx # ZOPA badge + audit trail [teammate]
│   │   ├── DealDetail.tsx
│   │   ├── SymbiosisMap.tsx    # Leaflet map [teammate, NEW]
│   │   └── ESGCertificate.tsx  # Digital Green Certificate [teammate, NEW]
│   └── api/
├── dataset/                    # Source CSV files
├── IMPLEMENTATION_PLAN.md      # Full technical plan
├── TEAMMATE_BRIEF.md           # Frontend spec for teammate
└── README.md
```

---

## Definition of Done

### Backend (A — completed)
- [x] A4: `negotiation_strategy` field on listings + requirements (DB + API + migration)
- [x] A1: ZOPA engine (`compute_zopa`, `concession_target`, `extract_batna`)
- [x] A1: Boulware/Conceder curves in both fake agent and coordinator
- [x] A1: Math-guided Gemini briefs (ZOPA, target, BATNA injected per turn)
- [x] A1: `ZOPA_IMPOSSIBLE` early exit (no wasted API quota)
- [ ] A2: SHA-256 offer chain stored on every `Offer` row
- [ ] A3: ESG carbon math engine + `/deals/{id}/certificate` endpoint
- [ ] Map API: `/map/enterprises` + `/map/symbiosis` endpoints

### Frontend (B — teammate)
- [ ] B1: Leaflet Symbiosis Map page (`/map`)
- [ ] B2: ESG Certificate page (`/deals/:id/certificate`)
- [ ] B3: Strategy slider on create-listing + create-requirement forms
- [ ] B4: ZOPA badge + audit trail in NegotiationDetail

---

## Team

| Name | Role |
|---|---|
| Backend / AI / Game Theory | You + Antigravity AI |
| Frontend | Teammate |

> **Hackathon:** BitNBuild 2026 · **Team:** brocxx · **Repo:** github.com/brocxx/BitNBuild2k26
