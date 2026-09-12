# KIB.XCHANGE — Frontend

React + TypeScript + Vite frontend for the Karnataka industrial byproduct exchange MVP (rice husk, first cut).

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

Runs at http://localhost:5173. Defaults to `VITE_API_MODE=mock` — the whole app works with no backend, Supabase, or Gemini running.

## Modes

- **Mock** (`VITE_API_MODE=mock`, default): `src/api/mock.ts` serves in-memory fixtures for a rice-husk buyer/seller scenario, including a scripted negotiation with a couple of counteroffer rounds ending in an agreed deal. A banner marks the app as mock mode. Sign-in accepts anything.
- **Real** (`VITE_API_MODE=real`): talks to the backend at `VITE_API_BASE_URL`, authenticating via Supabase (`VITE_SUPABASE_URL` / `VITE_SUPABASE_PUBLISHABLE_KEY`) and attaching the access token as a Bearer header on every request.

Switching modes never requires touching a page component — both implementations satisfy the same `ApiClient` interface (`src/api/ApiClient.ts`), and `src/api/index.ts` picks one at import time.

## Structure

```text
src/api/        types.ts (contract mirror), ApiClient.ts (interface), mock.ts, client.ts, index.ts
src/auth/       Supabase wrapper + React auth context
src/pages/      Login, Dashboard, Listings, Requirements, Matches, NegotiationDetail, DealDetail, SymbiosisMap, ESGCertificate, OpportunityLab
src/components/ Layout (nav + theme toggle), StatusBadge, CostBreakdown, NegotiationStrategySelector
src/utils/      format.ts, mapUtils.ts
src/styles/     global.css
```

## Phase 2 Features Built

1. **Geospatial Symbiosis Map (`/map`)**:
   - Leaflet interactive map with **7,933 real UDYAM enterprises** categorized by NIC sector.
   - Proximity search: **"Find Compatible Buyers within 150 km"** draws symbiosis pathways.
   - Animated trade corridors for active agreed deals across Karnataka.
2. **Digital Green Certificate (`/deals/:dealId/certificate`)**:
   - Official ESG Certificate verifying **net $\text{CO}_2\text{e}$ avoided**, **landfill diverted**, and **carbon credits ($\text{tCO}_2\text{e}$)**.
   - Verifiable **SHA-256 audit fingerprint**.
   - Clean printable PDF layout with `@media print` styling (`window.print()`).
3. **Negotiation Strategy Selector**:
   - Toggle buttons (`🤝 Cooperative (Conceder)` vs `💪 Aggressive (Boulware)`) on Create Listing and Create Requirement forms.
4. **Cryptographic Audit Trail Display**:
   - Offer cards in `NegotiationDetail` display immutable `🔒 SHA-256 Hash` chains and ZOPA active badges.

## Commands

```bash
npm run dev        # local dev server
npm run typecheck  # tsc -b --noEmit
npm run build      # production build to dist/
npm run preview    # preview the production build
```

