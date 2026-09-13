# KIB Exchange — Frontend

> React 18 + TypeScript + Vite frontend for the Karnataka Industrial Byproduct Exchange.

The UI serves three roles — **Buyer**, **Seller**, and **Regulator/Viewer** — through a dark-mode, responsive interface that communicates with the FastAPI backend over a clean `ApiClient` interface. Every page works in pure mock mode with no backend required.

---

## Quick Start

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
# → http://localhost:5174
```

The default `.env` ships with `VITE_API_MODE=real` pointed at `http://localhost:8000/api/v1`. To run with no backend at all, set `VITE_API_MODE=mock`.

---

## Environment Variables

```env
VITE_API_MODE=real                          # 'real' | 'mock'
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

For Supabase production auth, also add:
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=eyJ...
```

---

## API Modes

| Mode | How to activate | What it does |
|---|---|---|
| **`real`** | `VITE_API_MODE=real` (default) | Calls the FastAPI backend. Uses `Authorization: Bearer dev:<email>` in local dev, or a Supabase JWT in production. |
| **`mock`** | `VITE_API_MODE=mock` | Serves in-memory fixtures from `src/api/mock.ts`. Includes a scripted rice-husk buyer/seller negotiation with multi-round counteroffers ending in an agreed deal. A banner labels the app as mock mode. Sign-in accepts any input. |

Both modes satisfy the same `ApiClient` TypeScript interface (`src/api/ApiClient.ts`). Switching modes never requires touching a page component — `src/api/index.ts` selects the implementation at import time.

---

## Pages & Features

### Core Pages
| Route | Page | Description |
|---|---|---|
| `/` | Dashboard | KPI tiles (enterprises, listings, match rate, CO₂e avoided), Sankey byproduct flow diagram, live transaction ledger |
| `/listings` | Listings | Browse and create byproduct listings with chemical specs, price/tonne, and negotiation strategy selector |
| `/requirements` | Requirements | Post procurement requirements with private budget, moisture tolerance, and delivery window |
| `/requirements/:id/matches` | Match Results | Scored candidate suppliers ranked by delivered cost; each exclusion shows the specific failed check |
| `/negotiations/:id` | Negotiation Timeline | Round-by-round agent offer feed with live ZOPA convergence chart, SHA-256 hash chain badges, and 2-second polling |
| `/deals/:id` | Deal Detail | Settlement summary, ESG impact preview, inventory reservation status, and link to Green Certificate |

### Phase 2 Feature Pages
| Route | Page | Description |
|---|---|---|
| `/map` | Geospatial Symbiosis Map | Leaflet canvas rendering 7,933 real UDYAM enterprises by NIC sector; configurable symbiosis radius draws compatible producer/receiver connections across Karnataka districts |
| `/deals/:id/certificate` | Digital Green Certificate | Verifiable ESG certificate showing net CO₂e avoided, landfill diverted (kg), and estimated carbon credits. Includes SHA-256 audit fingerprint and IPCC disclaimer. Supports `window.print()` with `@media print` layout. |
| `/opportunities` | Opportunity Lab | Interactive parameter sensitivity matrix — drag sliders for price, moisture %, batch size, and freight rate to simulate deal viability. Generates logistics disruption rerouting recommendations. |

---

## Structure

```
src/
├── api/
│   ├── ApiClient.ts       # TypeScript interface (both modes must satisfy this)
│   ├── client.ts          # Real HTTP client (Fetch + Bearer token)
│   ├── mock.ts            # In-memory mock implementation
│   ├── index.ts           # Mode selector
│   └── types.ts           # API contract types (mirror of backend schemas)
├── auth/
│   └── AuthContext.tsx    # Supabase auth context + dev token passthrough
├── pages/
│   ├── Dashboard.tsx
│   ├── Login.tsx
│   ├── Listings.tsx              # Strategy selector (Conceder / Boulware)
│   ├── Requirements.tsx          # Strategy selector + private budget field
│   ├── Matches.tsx
│   ├── NegotiationDetail.tsx     # ZOPA chart + SHA-256 audit trail badges
│   ├── DealDetail.tsx            # ESG preview + link to certificate
│   ├── SymbiosisMap.tsx          # Leaflet map (Phase 2)
│   ├── ESGCertificate.tsx        # Digital Green Certificate (Phase 2)
│   └── OpportunityLab.tsx        # Sensitivity lab (Phase 2)
├── components/
│   ├── Layout.tsx                # Nav, dark mode toggle, role badge
│   ├── StatusBadge.tsx
│   ├── CostBreakdown.tsx
│   └── NegotiationStrategySelector.tsx  # Conceder / Boulware / Balanced toggle
├── utils/
│   ├── format.ts          # Paise → rupees, kg → tonnes, distance formatting
│   └── mapUtils.ts        # Haversine distance, cluster helpers, map styling
├── data/
│   └── mapEnterprises.json  # Pre-processed GeoJSON-compatible UDYAM enterprise dataset
└── styles/
    └── global.css         # Design system: CSS custom properties, dark mode, animations
```

---

## Negotiation Timeline

The negotiation detail page polls `GET /negotiations/:id` every **2 seconds** and progressively renders:

1. **Round cards** — each offer shows agent role, unit price, total delivered cost, round number, and the agent's reasoning text
2. **ZOPA Chart** — a live convergence visualisation of the buyer's descending ceiling and seller's ascending floor, with the overlap zone highlighted
3. **SHA-256 Hash Chain** — each offer card displays its `chain_hash` value. A broken chain is flagged with a red warning badge
4. **Terminal Events** — `DEAL_CLOSED`, `ZOPA_IMPOSSIBLE`, `NO_DEAL` are rendered with distinct colours and icons

---

## Commands

```bash
npm run dev        # Start local development server (hot reload)
npm run typecheck  # TypeScript strict type check (tsc --noEmit)
npm run build      # Production build to dist/ (runs typecheck first)
npm run preview    # Preview the production build locally
```

---

## Design System

The UI uses a dark-mode-first design with:
- **CSS custom properties** for the full colour palette, spacing, and typography scale
- **Glassmorphism** card surfaces with `backdrop-filter: blur()`
- **Micro-animations** on hover and state transitions
- **Google Fonts** — Inter for body, monospace for hash values and code
- **Responsive layout** using CSS Grid and Flexbox — no external CSS framework

---

## Demo Personas

| Email | Role | Scenario |
|---|---|---|
| `buyer1@demo.bitnbuild.local` | Buyer (Brick kiln, Mysuru) | Open the ₹70,000 rice husk requirement to see a 3-supplier negotiation resolve |
| `seller1@demo.bitnbuild.local` | Seller (Rice mill, Davangere) | View active listings, accepted offers, and deal history |
