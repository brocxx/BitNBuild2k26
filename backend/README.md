# Backend — Karnataka Industrial Byproduct Exchange

FastAPI service implementing the API contract in
[`docs/MVP_TEAM_WORK_PLAN.md` §4](../docs/MVP_TEAM_WORK_PLAN.md). Owned by A.

**Status: feature-complete.** Every route in the contract is implemented, and
all three external dependencies are verified working:

| Dependency | Verified |
| --- | --- |
| Supabase Postgres | migrations, 7,933-enterprise import and seed all run against it |
| Supabase Auth | real ES256 tokens verified via JWKS, resolved to businesses |
| Gemini agents | `gemini-3.1-flash-lite` negotiating live, three sellers, ~45s |

122 tests pass. Day-to-day the defaults stay on SQLite, dev tokens and the
deterministic negotiator so nothing costs quota; each is a one-variable flip.
See [Switching modes](#switching-modes).

---

## Run it

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows.  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

cp .env.example .env            # defaults work as-is: SQLite, dev auth, fake agents
python -m app.data.cli reset    # migrate + import dataset + seed the demo scenario
uvicorn app.main:app --reload   # http://localhost:8000
```

Interactive docs at <http://localhost:8000/docs>. Health check:

```bash
curl http://localhost:8000/api/v1/health     # {"status":"ok"}
```

`reset` prints the demo logins. Everything else needs a token:

```bash
curl -H "Authorization: Bearer dev:buyer1@demo.bitnbuild.local" \
     http://localhost:8000/api/v1/me
```

---

## Four ways to exercise it without a frontend

**1. Swagger UI — <http://localhost:8000/docs>**

Click **Authorize**, paste `dev:buyer1@demo.bitnbuild.local`, and every route
becomes clickable with a schema-aware form. Fastest way to see the shape of a
response.

**2. `requests/api.http` — VS Code REST Client**

Install the `humao.rest-client` extension and open the file. Eleven numbered
stages from health check to deal lifecycle, each saying what you should see and
what it proves. Requests chain — IDs captured from one response feed the next —
so you can walk the whole pipeline by clicking "Send Request" down the file.
Includes the failure cases: 401s, 403s, 422s, 409 idempotency conflicts.

**3. `scripts/inspect_db.py` — see what actually happened**

HTTP responses are deliberately filtered per business, so they cannot show you
whether stock decremented exactly once or what each losing candidate did.

```bash
python scripts/inspect_db.py                    # full state dump
python scripts/inspect_db.py --check            # invariant checks, exit 1 on failure
python scripts/inspect_db.py --negotiation 1c84 # one run: candidates, offers, events
python scripts/inspect_db.py --reference        # what the dataset import produced
```

`--check` verifies the properties that matter against whatever state you just
created by hand: one deal per requirement, no oversold listing, every agreed
price at or above its floor, every delivered total within budget, cost
arithmetic adding up, no seller offer below its own floor, and no private limit
in any persisted explanation or event.

**4. `scripts/smoke.py` — the scripted walkthrough**

```bash
python scripts/smoke.py
```

Matches → negotiation → agreement → reservation for the feasible requirement,
then the low-budget requirement to show the honest no-deal.

### Tests

```bash
python -m pytest          # 122 tests, ~2 min (no Gemini quota, no network)
```

---

## Switching modes

Three independent switches in `.env`. Each was verified end to end; each
defaults to the cheap local option so ordinary development costs nothing.

| Variable | Default | Flip to | Effect |
| --- | --- | --- | --- |
| `DB_TARGET` | `local` | `supabase` | Shared team Postgres instead of a local SQLite file |
| `AUTH_MODE` | `dev` | `supabase` | Real access tokens instead of `dev:<email>` |
| `AGENT_MODE` | `fake` | `gemini` | Real LLM agents instead of the deterministic negotiator |

A teammate without Supabase credentials leaves all three alone and still gets a
complete, working backend.

### Before the demo

1. `DB_TARGET=supabase python -m app.data.cli reset` — fresh data.
2. `DB_TARGET=supabase python scripts/provision_supabase_users.py --verify` —
   recreate the auth accounts and confirm a real token still works.
3. Flip `AGENT_MODE=gemini`.
4. `python scripts/smoke.py` — full walkthrough; it signs in for real when
   `AUTH_MODE=supabase`.

Supabase free projects pause after about a week of inactivity, so do step 1 the
day before, not on the morning.

### Gemini quota is the real constraint

One negotiation against three sellers costs up to **27 model calls**: per
candidate, one broker call plus four rounds of two agents.

- Full Flash models are capped near **20 requests/day** on the free tier, which
  cannot complete even one demo negotiation. This is why `GEMINI_MODEL` is
  `gemini-3.1-flash-lite` (~500/day), not a headline Flash model.
- That leaves roughly **18 full runs per day**. Develop against
  `AGENT_MODE=fake`; the test suite already does, so `pytest` costs nothing.
- If quota gets tight, drop `MAX_CANDIDATES_PER_NEGOTIATION` to 2 and
  `MAX_ROUNDS_PER_CANDIDATE` to 3 — a full run becomes 14 calls.

A live three-seller run takes about 45 seconds. The timeline fills in
progressively while it runs, so the polling UI has something to show.

---

## Auth

`AUTH_MODE=dev` (the default) accepts `Authorization: Bearer dev:<email>` for
the seeded demo accounts. It never parses a JWT, so a real Supabase token
cannot be accepted unverified by accident. **Local development only.**

`AUTH_MODE=supabase` verifies the access token's signature before reading any
claim — JWKS for asymmetric keys (the current Supabase default), or
`SUPABASE_JWT_SECRET` for a legacy HS256 project. The user is resolved by
`sub`, falling back to `email` on first login, which then binds the subject to
the seeded demo account. Set `SUPABASE_URL` and flip the one variable; no code
changes.

The backend always resolves the caller's business from the verified token. A
create request never supplies an owner ID.

---

## Layout

```text
app/
  api/routes/        catalog, listings, requirements, negotiations, deals
  api/schemas.py     the contract, field for field
  agents/            provider interface, fake negotiator, Gemini adapter, prompts
  services/          costing, matching, coordinator, reservations, serializers
  db/                models and session
  data/              importer (with the data fixes), seed, CLI
  auth/              Supabase token verification
alembic/             migrations
requests/api.http    manual walkthrough for the VS Code REST Client
scripts/             export_openapi.py, smoke.py, inspect_db.py,
                     verify_locking.py, provision_supabase_users.py
tests/               122 tests
```

---

## Things worth knowing before you change something

**Units, everywhere.** Money is integer INR paise. Price is paise per tonne.
Quantity is kilograms. Distance is metres. Timestamps are UTC ISO 8601. The UI
converts for display; nothing in the backend stores rupees or tonnes.

**Private fields are separated structurally, not by a flag.** `Listing` has no
`seller_floor_paise_per_tonne` field to leak — `OwnerListing` subclasses it and
adds one, and only `/me/*` routes return the owner types. `scripts/export_openapi.py`
fails the export if a public schema ever grows a private field.

**Agent explanations are scrubbed.** `app/agents/privacy.py` strips any
rendering of a private limit — paise, rupees, grouped, rounded — from every
explanation before it is persisted. This runs on all providers, so the tests
exercise the same path the demo will.

**Agents never compute totals or touch the database.** They return a validated
`AgentDecision` (action, listing, transport option, unit price, explanation);
the coordinator attaches the fixed quantity, schedule, computed costs and
expiry. Unknown IDs, out-of-range prices, and accepting a superseded offer all
end the run as `INVALID_MODEL_OUTPUT`.

**A failed provider never becomes a fabricated agreement.** `AGENT_MODE=gemini`
without a key raises rather than falling back to the fake negotiator. There is
no automatic downgrade path anywhere.

**Arithmetic belongs to code, not the model.** The buyer's brief carries a
precomputed price ceiling and a boolean saying whether the standing offer may
be accepted. Both exist because live Gemini runs produced a buyer that accepted
a delivered total above its own budget — the server caught it and discarded an
otherwise winnable candidate. Never move a comparison back into the prompt.

**Agents cannot cite a market.** This system has no pricing feed, benchmark or
index; prices come only from what participants entered. The prompt forbids
market language and `app/agents/privacy.py` strips it anyway, because Gemini
wrote "current market conditions" on the very first live run. That claim would
have been false, and on screen.

**Only the winner reserves stock, and the decrement is a compare-and-swap.**
Candidates that provisionally accept hold nothing. The commit rechecks stock,
quote expiry and both limits, then decrements with a conditional UPDATE whose
predicate the database re-evaluates at write time:

```sql
UPDATE listings SET available_quantity_kg = available_quantity_kg - :qty
 WHERE id = :id AND status = 'open' AND available_quantity_kg >= :qty
```

Do not turn this back into `listing.available_quantity_kg -= qty`. It was
written that way originally and two concurrent buyers could both take the same
batch: the checks pass in both transactions before either writes. The unique
constraint on `deals.requirement_id` does not cover it, because two *different*
requirements are competing. `scripts/verify_locking.py` reproduces the race on
either database, and `tests/test_reservations.py` has it as a regression test.

The whole reservation runs inside a SAVEPOINT so a failed commit discards only
the reservation, not the negotiation's offers and events.

**Freight never comes from the distance matrix.** District distances are
straight-line, imported as metres with `basis="district_straight_line"`, and
shown as context only. A transport option always states a complete
per-shipment charge, tagged `entered_quote` or `configured_estimate`.

---

## Data corrections

The CSVs under `dataset/` are read-only to the team, so every fix is applied in
`app/data/fixes.py` at import time and covered by `tests/test_import.py`.

| # | Problem in the dataset | What the importer does |
| --- | --- | --- |
| 1 | `enterprise_name` is **empty in all 7,933 rows** of `02_enterprises_with_location.csv` | Recovers names by joining `communication_address` against `01_raw_msme_enterprises.csv`. **7,883 recovered**; an address mapping to more than one name is dropped rather than guessed. The remaining 50 get `Unnamed MSME (KA-ENT-…)` and `name_source="unresolved"` — never an invented name. |
| 2 | `03_byproducts_per_enterprise.csv` gives **Rice Husk to all 3,536 NIC-10 enterprises**, including chocolate makers, spice units and starch plants | Keeps a byproduct only where the NIC5 code supports it. 9,172 over-assigned rows dropped across rice, wood and brick byproducts. |
| 3 | `dataset/README.md` says NIC **10611 is rice milling. It isn't** — in the data 10611 is *Flour milling* and **10612 is *Rice milling*** (112 enterprises) | Canonical rice-husk producers are `10612` plus `10619` ("other grain milling"), following the data rather than the README. |
| 4 | "Brick kiln" is ambiguous: NIC 23952 and 23954 are **cement and RCC block makers with no kiln** | `brick_kiln_fuel` receivers are `23921` (fired bricks) and `23912` (refractory) only. The seed additionally skips units whose registered *name* says cement/RCC/concrete, since the NIC code alone cannot tell them apart. |
| 5 | Distances are straight-line km, floats | Imported as integer metres with an explicit basis, and never used to derive freight. |

Inferred annual tonnage lives in `enterprise_byproducts` with `is_estimate=True`
and is structurally separate from listing stock.

---

## Demo scenario

`python -m app.data.cli seed` builds it from real, named enterprises. All dates
are generated relative to the run, so fixtures cannot expire before the demo.

- **6 rice-husk listings** from real rice mills in distinct districts.
  Three qualify; three demonstrate a distinct exclusion reason
  (`QUALITY_MISMATCH`, `QUALITY_REVIEW_REQUIRED`, `INSUFFICIENT_QUANTITY`).
- **2 requirements** from a real brick kiln: one with a budget that admits an
  agreement, one that cannot be met without breaching a seller floor.
- **24 transport options**, two per listing/requirement pair, all tagged
  `configured_estimate`.
- The seller with the **lowest freight is deliberately not the cheapest
  delivered**, so the Matches screen makes the point that the nearest seller is
  not automatically the best option.

Prices, floors, budgets, quantities, moisture readings and freight charges are
configured demo values. No supplier or transporter has quoted them. The
enterprises, their names, districts and the straight-line distances are real.

---

## Contract changes

`contracts/openapi.json` is exported from the live app:

```bash
python scripts/export_openapi.py
```

Per the work plan, contract changes go through A: adjust `app/api/schemas.py`,
re-export, and tell B the exact change. B alone updates the frontend types,
client and mocks. Prefer additive changes now that the first checkpoint is done.

---

## What is left

Nothing blocking. Remaining items are integration and polish:

1. **Frontend integration.** B builds against `contracts/openapi.json`.
   Expect small additive contract requests once real screens exist; those go
   through A, get re-exported, and are announced to B.
2. **Deployment.** No Render configuration yet. Local runs are the supported
   path, and the plan treats hosting as optional.
3. **Optional:** openrouteservice road distances to replace the straight-line
   district figures shown as context on match and deal screens.

### Known limitations, stated plainly

- **Gemini free-tier quota** caps realistic use at roughly 18 full negotiations
  per day. See above.
- **A buyer bidding its exact ceiling** makes the delivered total equal its
  budget, which an attentive seller could infer from. The prompt tells the
  buyer to stay below the ceiling until the final round, but this is mitigation,
  not a guarantee — it is inherent to any negotiation where a party bids its
  maximum.
- **Flash-Lite is a small model.** It has held the JSON schema on every live
  run so far, but `INVALID_MODEL_OUTPUT` handling and bounded retries exist
  because that is not guaranteed.
