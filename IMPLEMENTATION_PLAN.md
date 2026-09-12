# KIB Exchange — Feature Upgrade Implementation Plan

## Split: You + AI vs Teammate

---

## PART A — We Build (Backend: Game Theory, ESG Math, Gemini Upgrade)

### A1. Math-Guided Gemini (ZOPA + Concession Curves + BATNA)
**Files:** `backend/app/services/zopa.py` [NEW], `backend/app/agents/prompts.py` [MODIFY]

The core insight: Gemini should receive pre-computed game theory math alongside the usual brief, so it reasons WITH the math rather than hallucinating against it.

**`app/services/zopa.py`** — new module:
- `compute_zopa(seller_floor, buyer_ceiling)` → `{exists: bool, overlap_paise: int}`
- `concession_target(strategy, round_num, max_rounds, start, end)` → recommended price this round
  - `"boulware"`: stays near start for early rounds, sharp drop in final round (1 - (t/T)^4 curve)
  - `"conceder"`: smooth linear walk toward limit (current fake agent behavior)
- `extract_batna(candidates)` → best competitor price among other sellers, or None

**`app/agents/prompts.py`** — extend `build_brief()`:
```python
# NEW fields added to every brief:
brief["zopa_exists"] = zopa.exists
brief["zopa_overlap_range_paise"] = [zopa.low, zopa.high]  # only if exists
brief["concession_target_this_round_paise"] = target  # pre-computed from strategy
brief["strategy"] = context.strategy  # "boulware" | "conceder"
if context.role == "buyer" and context.batna_price:
    brief["batna_competitor_price_paise_per_tonne"] = context.batna_price
    brief["batna_competitor_district"] = context.batna_district
```

**`app/agents/base.py`** — extend `AgentContext`:
- Add `strategy: str` (default "conceder")
- Add `batna_price_paise_per_tonne: int | None`
- Add `batna_district: str | None`

**`app/services/coordinator.py`** — wire ZOPA check before starting:
- If `not zopa.exists` → immediately return `no_deal` with reason `ZOPA_IMPOSSIBLE` (no LLM calls burned)
- Pass `strategy` from listing/requirement fields into `AgentContext`
- Extract BATNA from the candidate list before first buyer turn

---

### A2. SHA-256 Audit Trail per Offer
**Files:** `backend/app/services/coordinator.py` [MODIFY], DB migration [NEW]

Every time an offer is committed to the database, compute:
```python
import hashlib, json
payload = {
  "offer_id": offer.id,
  "negotiation_id": neg.id,
  "round": round_num,
  "author": role,
  "action": action,
  "unit_price_paise_per_tonne": price,
  "timestamp_utc": now.isoformat(),
  "prev_hash": prev_offer_hash or "GENESIS"
}
offer.chain_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
```
Each offer's hash includes the previous offer's hash → tamper-evident chain.

**API change:** `GET /negotiations/{id}` returns `chain_hash` on every offer object.

---

### A3. ESG Carbon Math Engine
**Files:** `backend/app/services/esg.py` [NEW], `backend/app/api/routes/deals.py` [MODIFY]

**`app/services/esg.py`**:
```python
# Emission factors (kg CO2e per tonne of material replaced)
EMISSION_FACTORS = {
    "rice_husk":  {"replaces": "coal", "co2e_per_tonne_avoided": 1400},  # kg
    "sawdust":    {"replaces": "coal", "co2e_per_tonne_avoided": 1350},
    "wood_bark":  {"replaces": "coal", "co2e_per_tonne_avoided": 1300},
    # etc.
}
ROAD_FREIGHT_CO2E_PER_TONNE_KM = 0.062  # kg CO2e / tonne-km (Indian avg)

def compute_esg(material_id, quantity_kg, distance_km, freight_paise):
    quantity_t = quantity_kg / 1000
    factor = EMISSION_FACTORS[material_id]
    gross_avoided = quantity_t * factor["co2e_per_tonne_avoided"]  # kg CO2e
    transport_emitted = quantity_t * distance_km * ROAD_FREIGHT_CO2E_PER_TONNE_KM
    net_co2e_avoided_kg = gross_avoided - transport_emitted
    landfill_diverted_kg = quantity_kg
    return ESGMetrics(
        net_co2e_avoided_kg=net_co2e_avoided_kg,
        gross_co2e_avoided_kg=gross_avoided,
        transport_co2e_kg=transport_emitted,
        landfill_diverted_kg=landfill_diverted_kg,
        carbon_credits_estimated=net_co2e_avoided_kg / 1000,  # 1 credit = 1 tCO2e
    )
```

**`GET /deals/{id}`** — add `esg_metrics` field to response using district distance matrix.
**`GET /deals/{id}/certificate`** — returns ESG certificate data as JSON (teammate renders it).

---

### A4. Strategy Field on Listings + Requirements
**Files:** DB migration, `listing` model, `requirement` model, API schemas

Add `negotiation_strategy: str` field (default `"conceder"`) to both `listings` and `requirements` tables.
API: `POST /listings` and `POST /requirements` accept optional `negotiation_strategy: "boulware" | "conceder"`.

---

## PART B — Teammate Builds (Frontend: Map, ESG Certificate UI, Sliders)

→ See `TEAMMATE_BRIEF.md` for full spec

### B1. Leaflet Geospatial Map page (`/map`)
### B2. ESG Certificate page (`/deals/{id}/certificate`)
### B3. Negotiation strategy slider on listing/requirement creation forms
### B4. ZOPA + Audit Trail display in NegotiationDetail and DealDetail

---

## Execution Order

### We do first (unblocks teammate):
1. `A4` — Add strategy field to DB + API (30 min) → teammate can build slider
2. `A1` — ZOPA + concession engine + prompts upgrade (2h) → core differentiator
3. `A3` — ESG engine + `/deals/{id}/certificate` endpoint (1.5h) → teammate can build certificate
4. `A2` — SHA-256 chain (45 min) → teammate adds display

### Teammate does in parallel:
1. `B3` slider (needs A4 done)
2. `B1` map (fully independent, start immediately)
3. `B4` ZOPA/audit display (needs A1 + A2 done)
4. `B2` certificate (needs A3 endpoint done)

---

## API Contracts (What Teammate Needs to Know)

### New fields on existing endpoints after our changes:

**`GET /negotiations/{id}`** — each offer now includes:
```json
{
  "offers": [{
    "chain_hash": "a3f9c2...",
    "zopa_existed": true
  }]
}
```

**`GET /deals/{id}`** — now includes:
```json
{
  "esg_metrics": {
    "net_co2e_avoided_kg": 25340,
    "gross_co2e_avoided_kg": 28000,
    "transport_co2e_kg": 2660,
    "landfill_diverted_kg": 20000,
    "carbon_credits_estimated": 25.34
  }
}
```

**`GET /deals/{id}/certificate`** — new endpoint:
```json
{
  "deal_id": "...",
  "issued_at": "2026-09-12T...",
  "seller": "SRI LAKSHMI VENKATESHWARA ENTERPRISES",
  "buyer": "A V S GROUPS",
  "material": "Rice Husk",
  "quantity_kg": 20000,
  "distance_km": 258,
  "esg": { ...same as above... },
  "audit_chain_root": "a3f9c2...",
  "verified": true
}
```

**`GET /api/v1/map/enterprises`** — new endpoint (for map):
```json
{
  "enterprises": [{
    "enterprise_id": "KA-ENT-000045",
    "name": "A V S GROUPS",
    "district": "MYSURU",
    "lat": 12.2958,
    "lon": 76.6394,
    "sector": "NIC 10",
    "byproducts": ["rice_husk", "rice_bran"]
  }]
}
```

**`GET /api/v1/map/symbiosis?district=MYSURU&radius_km=150`** — new endpoint:
```json
{
  "origin": { "district": "MYSURU", "lat": 12.2958, "lon": 76.6394 },
  "radius_km": 150,
  "compatible_enterprises": [ ... ]
}
```

---

## README Update Checklist

After each item is done, update `README.md`:
- [ ] A1 done → add "Game-Theoretic Negotiation" section
- [ ] A2 done → add "Cryptographic Audit Trail" to Definition of Done
- [ ] A3 done → add "ESG Carbon Engine" section + emission factors table
- [ ] B1 done → add map screenshot to README
- [ ] B2 done → add certificate screenshot to README
