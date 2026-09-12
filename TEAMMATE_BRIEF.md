# KIB Exchange — Teammate Frontend Brief
### Your name: B (Frontend)
### Their name: A (Backend / you + AI)

---

## Big Picture

We are adding 4 major differentiators to our hackathon project. Backend (A) is building all the Python math engines and API endpoints. You (B) are building all the frontend UI that displays and uses that math.

**The rule:** Backend does the calculation, frontend just shows it beautifully. Never compute CO₂ or prices in the frontend — always call the API.

---

## What A is Building (Backend — gives you data)

When A is done, these API endpoints will exist. You build UI against them.

| Endpoint | What it returns |
|---|---|
| `GET /negotiations/{id}` | Each offer now has `chain_hash` (SHA-256) |
| `GET /deals/{id}` | Now includes `esg_metrics` object |
| `GET /deals/{id}/certificate` | Full ESG certificate data (JSON) |
| `GET /api/v1/map/enterprises` | All 7,933 real MSME enterprises with lat/lon |
| `GET /api/v1/map/symbiosis?district=X&radius_km=150` | Compatible enterprises within radius |

---

## Your Tasks

---

### B1 — Geospatial Symbiosis Map (`/map`) ⭐ HIGHEST PRIORITY

**Goal:** The most visually striking page in the app. Shows a live map of Karnataka with all real industrial enterprises from the UDYAM dataset. This is what makes judges stop and say "wait, is that real data?". Yes. It is.

**Library:** Use `react-leaflet` + `leaflet`
```bash
npm install react-leaflet leaflet
npm install @types/leaflet
```

**Page: `src/pages/SymbiosisMap.tsx`**

**What to show:**

1. **Enterprise pins** — Call `GET /api/v1/map/enterprises`. Place a marker for every enterprise. Color by sector:
   - 🔴 NIC 10 — Food/Rice Mills
   - 🟡 NIC 16 — Wood/Sawmills
   - 🔵 NIC 23 — Brick Kilns/Ceramics
   - 🟣 NIC 13 — Textiles/Silk
   - ⚫ NIC 25 — Metal Fabrication

2. **Click to discover** — When judge clicks any pin, show a popup:
   ```
   SRI LAKSHMI VENKATESHWARA ENTERPRISES
   District: DAVANGERE | Sector: Rice Mill (NIC 10)
   Byproducts: Rice Husk (20% of paddy), Rice Bran (10%)
   [Find Compatible Buyers within 150 km →]
   ```
   When they click the button, call `GET /api/v1/map/symbiosis?district=DAVANGERE&radius_km=150` and draw blue circles connecting to all compatible enterprise pins.

3. **Active trade corridors** — Call `GET /me/deals` (existing). For each deal with `status=agreed`, draw an animated dashed line between seller district and buyer district coords. Color: green.

4. **Stats bar** at top of map:
   ```
   7,933 Real Enterprises  |  31 Districts  |  14 Symbiosis Pathways  |  [N] Active Trades
   ```

**Map center:** Karnataka centre = `lat: 15.3, lon: 75.7`, zoom: 7

**Tile layer:** Use OpenStreetMap (free):
```tsx
<TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
```

**Route:** Add `/map` to `App.tsx` routes (inside RequireAuth).
**Add to sidebar** in `Layout.tsx`: a "🗺 Symbiosis Map" nav link.

---

### B2 — ESG Certificate Page (`/deals/:id/certificate`) ⭐ HIGH PRIORITY

**Goal:** When a deal closes, the buyer/seller can view and download a "Digital Green Certificate" proving how much CO₂ they avoided. Judges love downloadable artifacts.

**What to show (`src/pages/ESGCertificate.tsx`):**

Call `GET /deals/{id}/certificate` (A builds this).

Design it like a real certificate:

```
┌─────────────────────────────────────────────────────┐
│         🌿 DIGITAL GREEN CERTIFICATE                │
│              KIB Exchange · Karnataka               │
│─────────────────────────────────────────────────────│
│                                                     │
│  Seller: SRI LAKSHMI VENKATESHWARA ENTERPRISES      │
│  Buyer:  A V S GROUPS                               │
│  Material: Rice Husk  |  Quantity: 20,000 kg        │
│  Route: DAVANGERE → MYSURU  (258 km)                │
│  Date: 12 September 2026                            │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  CO₂e Avoided:      25.3 tonnes             │   │
│  │  Landfill Diverted: 20.0 tonnes             │   │
│  │  Carbon Credits:    25.3 tCO₂e              │   │
│  │  Gross Avoided:     28.0 tonnes             │   │
│  │  Transport Emitted:  2.7 tonnes             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  Audit Hash: a3f9c2d1...  [VERIFIED ✓]             │
│                                                     │
│  [⬇ Download PDF]  [Share]                         │
└─────────────────────────────────────────────────────┘
```

**Download:** Use `window.print()` with a `@media print` CSS — simplest way to get a PDF without a library.

**Add a "View Certificate →" button** in `DealDetail.tsx` that links to this page.

**Route:** `/deals/:id/certificate` in `App.tsx`.

---

### B3 — Negotiation Strategy Slider on Forms ⭐ MEDIUM PRIORITY

**Goal:** When a seller creates a listing OR a buyer creates a requirement, they pick a negotiation personality. This UI choice flows into the game theory engine A built.

**Add to:** `src/pages/Listings.tsx` (Create Listing form) and `src/pages/Requirements.tsx` (Create Requirement form)

**UI component** — add below price/quantity fields:

```tsx
// Negotiation Strategy
<div className="strategy-selector">
  <label>Negotiation Strategy</label>
  <div className="strategy-options">
    <button
      className={strategy === 'conceder' ? 'active' : ''}
      onClick={() => setStrategy('conceder')}
    >
      🤝 Cooperative (Conceder)
      <span>Concede early — prioritise quick deal over max price</span>
    </button>
    <button
      className={strategy === 'boulware' ? 'active' : ''}
      onClick={() => setStrategy('boulware')}
    >
      💪 Aggressive (Boulware)
      <span>Hold firm until final round — maximise price, risk no-deal</span>
    </button>
  </div>
</div>
```

**API call:** Add `negotiation_strategy: strategy` to the POST body when submitting forms.

---

### B4 — ZOPA + Audit Trail in Negotiation Detail ⭐ MEDIUM PRIORITY

**Goal:** Show judges the math is real. Add two panels to `NegotiationDetail.tsx`.

**Panel 1: Audit Trail** — below the offers timeline, add:

```
🔐 Cryptographic Audit Trail
Round 1 [seller propose]  hash: a3f9c2d1...  ✓ Chain valid
Round 2 [buyer counter ]  hash: b7e2a1f4...  ✓ Chain valid
Round 3 [seller counter]  hash: c9d3b2e5...  ✓ Chain valid
Round 4 [buyer accept  ]  hash: d1e4c3f6...  ✓ Chain valid
```

Data comes from: `offer.chain_hash` on each offer in `GET /negotiations/{id}`.

**Panel 2: ZOPA Status** — at the top of the negotiation, show:

```
Zone of Possible Agreement (ZOPA)
● ZOPA Exists — a deal is mathematically possible on this route
  Theoretical overlap range: [hidden — only shown post-deal]
```

or

```
✗ ZOPA Impossible — buyer budget cannot reach seller floor on this route
  Negotiation ended before any LLM calls were made.
```

Use `negotiation.zopa_existed` field (A adds this to the response).

---

## API Client — How to Call New Endpoints

The `ApiClient` in `src/api/client.ts` already has a pattern. Add these methods:

```typescript
// In src/api/client.ts
async getMapEnterprises(): Promise<MapEnterprise[]> {
  const res = await this.fetch('/map/enterprises');
  return res.enterprises;
}

async getSymbiosisNeighbors(district: string, radiusKm = 150): Promise<SymbiosisResult> {
  return this.fetch(`/map/symbiosis?district=${encodeURIComponent(district)}&radius_km=${radiusKm}`);
}

async getDealCertificate(dealId: string): Promise<ESGCertificate> {
  return this.fetch(`/deals/${dealId}/certificate`);
}
```

Add TypeScript types in `src/api/types.ts`:

```typescript
export interface MapEnterprise {
  enterprise_id: string;
  name: string;
  district: string;
  lat: number;
  lon: number;
  sector: string;        // "NIC 10" | "NIC 16" etc.
  byproducts: string[];  // ["rice_husk", "rice_bran"]
}

export interface ESGMetrics {
  net_co2e_avoided_kg: number;
  gross_co2e_avoided_kg: number;
  transport_co2e_kg: number;
  landfill_diverted_kg: number;
  carbon_credits_estimated: number;
}

export interface ESGCertificate {
  deal_id: string;
  issued_at: string;
  seller: string;
  buyer: string;
  material: string;
  quantity_kg: number;
  distance_km: number;
  esg: ESGMetrics;
  audit_chain_root: string;
  verified: boolean;
}
```

---

## Coordination

- **Unblocking dependency:** A will finish `B3 API support` (strategy field) first — takes ~30 min.
  Message when done so you can wire the slider.
- **For B1 map:** Fully independent. Start this NOW, no waiting needed.
- **For B2 certificate:** Wait for A to push `GET /deals/{id}/certificate` endpoint.
  A will message you the exact response shape when it is live.
- **For B4:** Wait for A to push `chain_hash` on offers and `zopa_existed` on negotiations.

## Branch Strategy
Work on a branch `feature/frontend-differentiators`.
A works on `feature/backend-differentiators`.
Merge both into main when ready.

---

## Styling Notes
- Use the existing CSS variables from `src/styles/global.css` — do not introduce Tailwind or a new design system.
- For the map, override the Leaflet default blue markers with custom colored SVG dots.
- The certificate page should look premium — use the existing dark card style from `DealDetail.tsx` as a reference.

---

## Definition of Done (Your Part)
- [ ] `/map` page loads with enterprise pins, color-coded by sector
- [ ] Clicking a pin shows popup with byproduct info and radius discovery button
- [ ] Radius discovery draws lines to compatible enterprises within 150km
- [ ] Active deals show trade corridor lines on map
- [ ] `/deals/:id/certificate` page renders all ESG metrics from API
- [ ] "Download" prints certificate as PDF
- [ ] Strategy slider appears on create-listing and create-requirement forms
- [ ] Strategy value is sent in POST body
- [ ] Audit trail hashes shown in NegotiationDetail
- [ ] ZOPA status badge shown in NegotiationDetail
