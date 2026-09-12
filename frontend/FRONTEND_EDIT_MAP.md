# KIB Exchange — where to edit what

## Run
```bash
npm install
npm run dev
```

The frontend defaults to mock mode unless your existing environment configuration switches it to the real API.

## Main files

### `src/styles/global.css`
All colors, light/dark theme, typography, cards, sidebar, responsive UI.
- Light palette: off-white / yellowish white + greens + black
- Dark palette: near-black + muted greens
- Fonts: Manrope + Sacramento

### `src/components/Layout.tsx`
Sidebar, navigation, brand, dark/light toggle, demo badge and current enterprise chip.

### `src/pages/Dashboard.tsx`
Main landing dashboard, KPI cards, top circular opportunity, agent cards and feature summary.

### `src/pages/Listings.tsx`
Seller flow.
- actual available quantity
- asking price in normal INR
- PRIVATE minimum price
- moisture / contamination
- pickup window

The component converts INR to integer paise before calling the API.

### `src/pages/Requirements.tsx`
Buyer flow.
- intended receiving process
- required quantity
- moisture limit
- PRIVATE maximum delivered budget in normal INR
- delivery window

The component converts INR to integer paise before calling the API.

### `src/pages/Matches.tsx`
Opportunity/match results.
- pathway evidence
- quantity / moisture checks
- nearby-first ranking
- district-distance display
- delivered-cost breakdown
- start negotiation button

### `src/pages/OpportunityLab.tsx`
Hackathon differentiator screen.
- interactive sensitivity / what-if simulator
- “what would make this deal work?” logic
- disruption recovery demo
- nearby supplier comparison
- feature prototypes: pooling, preparation pathways, material passport, sample-before-bulk, recurring agreements, expiring-stock rescue, backhaul, replay, receipt, overlooked partners, cluster map, voice listing

### `src/pages/NegotiationDetail.tsx`
Buyer Agent ↔ Seller Agent ↔ Logistics Broker negotiation timeline and offers.

### `src/pages/DealDetail.tsx`
Agreement summary, route/costs, manual fulfilment status and downloadable JSON summary.

### `src/api/mock.ts`
Mock-mode data + mock business logic.
Dataset-derived demo identities used here:
- Buyer: `KA-ENT-000179`, Kolar, manufacture of bricks
- Nearby rice-mill supplier: `KA-ENT-000020`, Kolar
- Alternative: `KA-ENT-001312`, Bengaluru Rural
- Alternative: `KA-ENT-000089`, Bengaluru Urban

Commercial prices, live stock, private limits and freight are explicitly demo inputs rather than dataset facts.

Important behavior:
- compatible suppliers are ordered by district distance (nearby first)
- negotiation protects seller floor and buyer budget
- insufficient budget produces `no_deal / BUDGET_NOT_MET`
- successful negotiation reserves inventory

### `src/api/types.ts`
Existing API contract. Keep snake_case, paise, kg and UTC timestamps unless the backend contract changes.

### `src/App.tsx`
Routes. `OpportunityLab` is at `/opportunities`.

## Dataset rules followed
- Estimated annual generation is reference data, not sellable inventory.
- Seller must enter actual available quantity.
- Commercial prices are user/demo inputs; not inferred from the CSVs.
- Industrial-symbiosis pathways are potential pathways, not guaranteed technical approval.
- District matrix distances are estimates.
- Missing company names are displayed as `Enterprise <enterprise_id>` rather than fabricated names.
