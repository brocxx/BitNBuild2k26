# KIB Exchange — Karnataka Industrial Byproduct Exchange

> **One factory's waste is another factory's raw material — and we prove it.**

[![Tests](https://img.shields.io/badge/tests-122%20passed-brightgreen)](#testing)
[![License](https://img.shields.io/badge/license-MIT-blue)](#)
[![Built at](https://img.shields.io/badge/Built%20at-BitNBuild%202026-orange)](#)

---

## About the Project

### The Problem

Karnataka's 7,933+ registered small manufacturers collectively discard millions of tonnes of reusable industrial byproduct every year — rice mills in Davangere pay to dump rice husk, while brick kilns forty kilometres away burn diesel to buy coal for the same furnace that husk could feed.

The transaction never happens — not because the match is impossible, but because the **discovery is broken**, the **pricing trust doesn't exist**, and **no one can verify what was agreed**.

Traditional B2B directories are dumb classifieds. They have zero chemical compatibility intelligence, zero real freight cost logic, and zero accountability chain. Every deal requires days of cold calls, manual negotiation, and handshake agreements with no audit trail.

### The Solution

**KIB Exchange** is India's first autonomous, game-theoretic industrial symbiosis marketplace for Karnataka MSMEs.

It combines real government-registered enterprise data with peer-reviewed chemistry, a mathematically-grounded negotiation engine, and cryptographic deal verification — replacing cold calls and manual brokers with an end-to-end platform that:

1. **Finds** compatible buyers and sellers from 7,933 real UDYAM-registered Karnataka factories across 14 IPCC/FAO-validated circular economy pathways
2. **Matches** them by seven compatibility checks ranked by true *delivered* cost — not just proximity
3. **Negotiates** through autonomous AI agents using formal Game Theory concession strategies (Boulware and Conceder curves), with all financial arithmetic enforced deterministically in Python — never inside the LLM
4. **Protects** every party's private limits: a buyer's budget and a seller's floor price sit behind separate response schemas that structurally cannot carry them, and are never exposed to the other side or its agent
5. **Certifies** every closed deal with a SHA-256 chained audit trail and a Digital Green Certificate quantifying CO₂e avoided, landfill diverted, and carbon credits earned

---

## Key Features

### 🗺️ Geospatial Industrial Symbiosis Map
An interactive Leaflet canvas rendering 7,933 real Karnataka MSME enterprises — sourced from the Government of India's UDYAM registry — categorised by NIC industrial sector and mapped onto 14 circular economy byproduct pathways validated against IPCC, FAO, and IRRI literature. A configurable proximity radius engine instantly surfaces compatible producer-receiver pairs for any district in Karnataka.

### ⚖️ Game-Theoretic Negotiation Engine
A formal Zone of Possible Agreement (ZOPA) engine mathematically determines deal feasibility *before* any LLM call is made — if no price satisfies both sides after freight, the system returns an honest `ZOPA_IMPOSSIBLE` result and burns zero API quota. When a deal is viable, three autonomous Gemini agents (Buyer, Seller, Logistics Broker) negotiate using configurable concession strategies — `"conceder"` (collaborative, linear walk to floor) or `"boulware"` (firm hold, deadline-driven drop, named after GE's Lemuel Boulware, 1948).

**The critical constraint**: Gemini proposes natural language reasoning; Python decides every price boundary. Hard server-side validation discards any offer that violates either party's registered limit, regardless of what the model produced.

### 🔒 Cryptographic SHA-256 Audit Trail
Every negotiation offer is chained with SHA-256 into a tamper-evident ledger:
```
offer_1_hash = SHA256(offer_id + price + round + timestamp + "GENESIS")
offer_2_hash = SHA256(offer_id + price + round + timestamp + offer_1_hash)
```
Modifying any historical offer breaks the chain. The full hash sequence is displayed in the negotiation timeline and included in the deal certificate — independently verifiable by any counterparty or regulator.

### 🌿 ESG Carbon & Circularity Engine
Every closed deal automatically generates a Digital Green Certificate quantifying:
- **Net CO₂e Avoided**: gross displacement of the virgin material's emissions, minus transport freight emissions (IPCC 2006 emission factors)
- **Landfill Diverted**: direct quantity in kilograms kept out of disposal
- **Carbon Credits**: net CO₂e tonnes (1 tCO₂e = 1 credit)

The certificate is labelled accurately as an IPCC-factor-based estimate, not a third-party verified carbon credit.

### 🧪 Opportunity Lab & Disruption Recovery
An interactive parameter sensitivity simulator lets plant managers model price, moisture, batch size, and freight sensitivity in real time — and generates dynamic rerouting recommendations when logistics disruptions (e.g. truck cancellations) occur mid-negotiation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite + TypeScript)      │
│  Dashboard · Symbiosis Map (Leaflet) · Listings · Requirements │
│  Negotiation Timeline · Deal Detail · ESG Certificate        │
│  Opportunity Lab · Role-aware auth (Buyer / Seller)          │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTP /api/v1  (Bearer token)
┌─────────────────▼───────────────────────────────────────────┐
│                    BACKEND (FastAPI + Python)                 │
│                                                               │
│  Auth → Matching (7-check compatibility) → ZOPA Check        │
│       → Concession Curve → Coordinator State Machine         │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Buyer Agent (Gemini) │ Seller Agents (Gemini) │      │    │
│  │ Logistics Broker (Gemini) — all math-guided          │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  Atomic stock reservation (compare-and-swap SQL)             │
│  Privacy scrubbing (floor/budget never leave their owner)    │
│  SHA-256 offer chain (tamper-evident audit log)              │
│  ESG carbon math engine (IPCC 2006 factors)                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│               DATABASE                                        │
│  SQLite (local dev) · Supabase Postgres (production)         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│               DATASET (read-only reference)                   │
│  7,933 Enterprises · 31 Districts · 14 Symbiosis Pathways    │
│  District distance matrix · Yield chemistry ratios           │
│  Sources: UDYAM Registry, IPCC 2006, FAO, IRRI, Survey of India │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

**Backend**
- Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2
- Custom ZOPA engine — pure Python, no ML dependencies
- Google Gemini 2.0 Flash (structured JSON output mode)

**Frontend**
- React 18, Vite, TypeScript
- Leaflet.js (interactive geospatial map)
- Vanilla CSS with CSS custom properties (dark mode, glassmorphism)

**Data & Intelligence**
- Government UDYAM MSME Registry (Karnataka) — 7,933 enterprises
- IPCC 2006 emission factors (carbon math)
- FAO / IRRI byproduct yield chemistry ratios (14 validated pathways)
- SHA-256 cryptographic audit chaining (Python `hashlib`)

**Infrastructure**
- SQLite (local dev), Supabase Postgres + Auth (production)
- Dev token system for zero-friction local development

---

## Challenges We Overcame

**Dirty Government Data — The Classification Problem**

The UDYAM dataset listed rice husk as a byproduct of all 3,536 NIC-10 food enterprises — including chocolate factories, spice units, and starch plants. We rebuilt the classification from NIC5 sub-codes: rice husk is only valid for NIC 10612 (Rice Milling) and 10619 (Other Grain Milling). 9,172 over-assigned rows were dropped across rice, wood, and brick byproducts. The dataset's own README incorrectly stated NIC 10611 is rice milling — the actual data disagrees. Every fix is applied in `app/data/fixes.py` and tested in `tests/test_import.py`.

**LLM Hallucination in Financial Constraints**

On the first live Gemini run, the buyer agent accepted a delivered total above its own registered budget. The model had been instructed not to — but instruction is not enforcement. We moved all arithmetic and all limit comparisons into the Python coordinator, which validates every `AgentDecision` server-side before persisting it. Gemini proposes; Python decides. A failed constraint disqualifies the candidate entirely rather than silently passing a bad number through.

**Atomic Inventory Under Race Conditions**

With multiple buyers competing for the same batch simultaneously, an ORM-level `listing.quantity -= qty` allows both to pass the availability check before either writes. We replaced it with a database-level compare-and-swap:
```sql
UPDATE listings SET available_quantity_kg = available_quantity_kg - :qty
 WHERE id = :id AND status = 'open' AND available_quantity_kg >= :qty
```
`tests/test_reservations.py` contains a regression test that reproduces the race and confirms it cannot produce an oversold listing.

---

## Installation & Usage

### Prerequisites
- Python 3.12+
- Node.js 20+
- A free [Google AI Studio](https://aistudio.google.com/) API key (for live Gemini agents; not needed for local dev)

### Backend

```bash
# Clone the repository
git clone https://github.com/brocxx/BitNBuild2k26.git
cd BitNBuild2k26/backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment (defaults work out of the box — SQLite, dev auth, fake agents)
cp .env.example .env

# Migrate database, import dataset, and seed demo scenario
python -m app.data.cli reset

# Start the API server
uvicorn app.main:app --reload --port 8000
```

API documentation available at `http://localhost:8000/docs`

Health check:
```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok"}
```

### Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev
# → http://localhost:5173
```

### Demo Login Credentials

| Email | Role |
|---|---|
| `buyer1@demo.bitnbuild.local` | Brick kiln buyer (Mysuru) |
| `seller1@demo.bitnbuild.local` | Rice husk seller (Bengaluru Urban) |

Use token format: `Authorization: Bearer dev:<email>`

### Environment Variables

**Backend `.env`:**
```env
AUTH_MODE=dev           # Use 'supabase' for production JWT verification
DB_TARGET=local         # Use 'supabase' for Postgres
AGENT_MODE=fake         # Use 'gemini' for live LLM agents (requires GEMINI_API_KEY)
GEMINI_API_KEY=         # Your Google AI Studio key (only needed for AGENT_MODE=gemini)
```

**Frontend `.env`:**
```env
VITE_API_MODE=real
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## Testing

The backend has **122 automated tests** covering all core subsystems:

```bash
cd backend
python -m pytest
# ======================= 122 passed, 1 warning in 55.81s =======================
```

| Test Suite | Tests | Coverage |
|---|---|---|
| `test_agent_brief.py` | 16 | Agent briefing, prompt construction, ZOPA injection |
| `test_api.py` | 19 | REST endpoints, auth, error envelopes |
| `test_costing.py` | 7 | Paise arithmetic, freight formulas, delivered cost |
| `test_import.py` | 12 | Dataset pipeline, data fixes, NIC classification |
| `test_matching.py` | 14 | Compatibility checks, scoring, exclusion reasons |
| `test_negotiation.py` | 19 | Multi-round loops, ZOPA boundaries, concession curves |
| `test_privacy.py` | 14 | Floor/budget isolation, agent scrubbing |
| `test_reservations.py` | 14 | Concurrency safety, compare-and-swap, race regression |
| `test_seed.py` | 7 | Demo scenario integrity |

All tests run against SQLite with the deterministic fake agent — **zero API quota used**.

---

## Project Structure

```
BitNBuild/
├── backend/
│   ├── app/
│   │   ├── agents/                # Gemini + Fake + Base agent protocol
│   │   │   ├── base.py            # AgentContext (strategy, ZOPA, BATNA fields)
│   │   │   ├── fake.py            # Deterministic Boulware/Conceder curves
│   │   │   ├── gemini.py          # Gemini structured-output adapter
│   │   │   └── prompts.py         # build_brief() — math-guided per-turn brief
│   │   ├── services/
│   │   │   ├── coordinator.py     # Negotiation state machine
│   │   │   ├── matching.py        # 7-check compatibility scoring
│   │   │   ├── costing.py         # Paise integer arithmetic (no floats)
│   │   │   ├── zopa.py            # ZOPA + Boulware/Conceder + BATNA engine
│   │   │   └── esg.py             # CO₂e carbon math (IPCC 2006 factors)
│   │   ├── api/routes/
│   │   │   ├── listings.py        # negotiation_strategy field
│   │   │   ├── requirements.py    # negotiation_strategy field
│   │   │   ├── deals.py           # esg_metrics + /certificate endpoint
│   │   │   ├── negotiations.py    # chain_hash on all offers
│   │   │   └── map.py             # /enterprises + /symbiosis + /stats
│   │   └── db/
│   │       └── models.py          # negotiation_strategy + chain_hash columns
│   ├── alembic/versions/          # Database migrations
│   ├── scripts/                   # smoke.py, inspect_db.py, verify_locking.py
│   └── tests/                     # 122 automated tests
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── SymbiosisMap.tsx   # Leaflet geospatial map
│       │   ├── ESGCertificate.tsx # Digital Green Certificate
│       │   ├── NegotiationDetail.tsx # ZOPA chart + SHA-256 audit trail
│       │   └── OpportunityLab.tsx # Sensitivity simulation
│       └── components/
│           └── NegotiationStrategySelector.tsx
├── dataset/
│   ├── 01_karnataka_byproduct_symbiosis.csv   # 14 pathways
│   ├── 02_enterprises_with_location.csv       # 7,933 MSMEs
│   ├── 05_byproduct_yields_by_nic.csv         # yield chemistry
│   ├── 06_district_headquarters_coordinates.csv
│   ├── 07_district_distance_matrix.csv
│   └── VALIDATION_REPORT.md                   # Source citations
├── contracts/
│   └── openapi.json               # Full API contract
└── README.md
```

---

## What's Next

- **Verified ESG Credits**: Integration with a third-party carbon registry (Verra or Gold Standard) to convert IPCC-estimated impact into tradeable, independently audited carbon credits
- **Production Auth & Payments**: UPI-integrated payment escrow triggered on deal close, with Aadhaar-linked business verification
- **Multi-State Expansion**: Extending the UDYAM dataset pipeline to Tamil Nadu, Maharashtra, and Andhra Pradesh — the symbiosis pathways are already state-agnostic
- **Price Intelligence Layer**: Real commodity price feeds (rice husk, coal, scrap metal) to dynamically calibrate BATNA values instead of entered demo prices
- **Regulatory Compliance API**: KSPCB / CPCB compliance module allowing State Pollution Control Boards to audit closed deals in real time via the SHA-256 chain

---

## Team

| Name | Role |
|---|---|
| **RS Raksha** | Backend architecture · Dataset pipeline & data corrections · Compatibility matching engine · Delivered-cost calculator · Multi-agent coordinator |
| **Ekansh Nandan Sharma** | Geospatial Symbiosis Map · Game-theoretic ZOPA engine · SHA-256 cryptographic audit trail · ESG carbon impact engine · Testing (122 tests) |
| **Aadya Dhuri** | Complete frontend (React + TypeScript + Vite) · Leaflet map UI · Negotiation timeline · ESG Certificate page · Opportunity Lab |

---

> **Hackathon:** BitNBuild 2026 · **Team:** R.A.E · **Repo:** [github.com/brocxx/BitNBuild2k26](https://github.com/brocxx/BitNBuild2k26)
