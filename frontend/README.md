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
src/pages/      one file per screen: Login, Dashboard, Listings, Requirements, Matches, NegotiationDetail, DealDetail
src/components/ Layout (nav + mock banner), StatusBadge, CostBreakdown
src/utils/      paise/kg/meter → display formatting
src/styles/     global.css
```

## Commands

```bash
npm run dev        # local dev server
npm run typecheck  # tsc -b --noEmit
npm run build      # production build to dist/
npm run preview    # preview the production build
```

## Notes for integration with the backend (A)

- Compare `contracts/openapi.json` against `src/api/types.ts` as soon as it's exported — freeze field names/units/enums before building further screens on top.
- `POST /negotiations` requires an `Idempotency-Key` header; `client.ts` already threads this through `startNegotiation`.
- Private fields (`seller_floor_paise_per_tonne`, `buyer_max_total_paise`) only ever appear in `Own*` types returned from `/me/listings` and `/me/requirements` — never render them on a screen the counterparty could see.
- Negotiation and deal screens poll every 2s (`POLL_MS` in `NegotiationDetail.tsx`) and stop on any terminal status (`agreed`, `no_deal`, `failed`).
