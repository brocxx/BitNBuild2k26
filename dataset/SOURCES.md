# Sources Log — Karnataka Manufacturing Dataset

> Running log of every data source used. Format: Source | URL | Date Accessed | Data Pulled

---

## Phase 1 — Karnataka Enterprise Registry

| # | Source Name | URL | Date Accessed | Data Pulled |
|---|-------------|-----|---------------|-------------|
| 1 | data.gov.in — List of MSME Registered Units under UDYAM (Karnataka filter) | https://data.gov.in/catalog/list-msme-registered-units-under-udyog-aadhaar-memorandum | 2026-09-12 | 17,437 manufacturing enterprise records (NIC 10–33), pulled via API (resource ID: `8b68ae56-84cf-4728-a0a6-1be11028dea7`), fields: EnterpriseName, State, District, Pincode, RegistrationDate, CommunicationAddress, NIC5DigitCode, NICDescription. Total Karnataka records in dataset: 2,411,947. API last updated 10/09/2026. |

**File saved:** `karnataka_msme_raw.csv` / `dataset/01_raw_msme_enterprises.csv`  
**Records:** 17,437 manufacturing enterprises (NIC 10–33 only)  
**Districts covered:** All 31 Karnataka districts  

---

## Phase 2 — Target Industries & NIC 2008 Classification

| # | Source Name | URL | Date Accessed | Data Pulled |
|---|-------------|-----|---------------|-------------|
| 2 | MoSPI National Industrial Classification (NIC-2008) / ISIC Rev. 4 Standard | https://mospi.gov.in/classification-and-standards | 2026-09-12 | 2-digit Division & 5-digit Sub-class hierarchy for 5 target manufacturing categories: NIC 10 (Food Processing), NIC 13 (Textiles/Silk), NIC 16 (Wood/Sawmilling), NIC 23 (Non-Metallic Minerals/Bricks), NIC 25 (Fabricated Metals). |

---

## Phase 3 — Byproduct Yield Ratios & Process Waste Factors

| # | Industry / Byproduct | Yield / Waste Ratio | Source Name | Source Reference / URL | Date Accessed |
|---|----------------------|---------------------|-------------|------------------------|---------------|
| 3 | Wood & Sawmilling (NIC 16) | Sawn timber yield: 39%; Sawdust: 25%; Wood bark: 12%; Offcuts: 24% | Industrial Ecology Data Commons (IEDC) | Dataset 412 (`4_PY_Fabrication_Furniture_CIRCOMOD`), Broman & Fredriksson (2015), *22nd International Wood Machining Seminar* | 2026-09-12 |
| 4 | Fabricated Metal (NIC 25) | Sheet cutting scrap: 22%; Bar turning swarf: 12%; Hot rolling mill scale: 10% | Industrial Ecology Data Commons (IEDC) | Dataset 439 (`4_PY_Manufacturing_Allwood_2024`), Allwood & Music (2024), *Phil. Trans. Royal Society A*, DOI: 10.1098/rsta.2023.0135 | 2026-09-12 |
| 5 | Food Processing - Rice Milling (NIC 10) | Milled Rice: 70%; Rice Husk: 20%; Rice Bran: 10% | International Rice Research Institute (IRRI) | IRRI Rice Knowledge Bank: *Milling and Processing* (http://www.knowledgebank.irri.org/step-by-step-production/postharvest/milling) | 2026-09-12 |
| 6 | Textiles & Silk (NIC 13) | Fabric cutting waste: 15%; Cotton spinning waste: 15–20%; Silk reeling waste/noil: 25% | FAO & Ellen MacArthur Foundation | FAO Agricultural Services Bulletin 136 (*Silk Reeling and Testing Manual*, Ch. 10) & EMF Textile Benchmarks (2017) | 2026-09-12 |
| 7 | Bricks & Ceramics (NIC 23) | Defective brick / grog scrap rate: 5–10% (avg 7%); Kiln fly ash: 3% | GIZ South Asia & ScienceDirect | GIZ Clean Brick Kiln Sector Report; *Construction and Building Materials* (Elsevier, DOI: 10.1016/j.conbuildmat.2014.07.037) | 2026-09-12 |

---

## Phase 4 — Industrial Symbiosis Pairing Logic

| # | Byproduct Route | Sourcing & Routing Validation | Source Reference / URL | Date Accessed |
|---|-----------------|-------------------------------|------------------------|---------------|
| 8 | Rice Husk & Bark → Brick Kilns / Biomass Boilers (Fuel & Pozzolan) | Co-firing of agricultural and timber biomass in clay brick kilns and process steam boilers | GIZ Clean Brick Kiln Guidelines / Bureau of Energy Efficiency (BEE) India | 2026-09-12 |
| 9 | Sawdust → Clay Brick Manufacturing (Pore-Forming Additive) | Sawdust incorporated into raw clay matrix to decrease thermal conductivity and brick weight | *Construction and Building Materials* (Elsevier, DOI: 10.1016/j.conbuildmat.2014.07.037) | 2026-09-12 |
| 10 | Silk Noil & Pupae → Spun Silk & Aquafeed | Reeling waste spun into schappe yarn; pupae used for high-protein aquafeed | FAO Bulletin 136 (*Silk Reeling and Testing Manual*) & Central Silk Board Karnataka | 2026-09-12 |
| 11 | Fabric Offcuts → Shoddy Yarn & Insulation | Pre-consumer fabric cutting waste shredded and re-spun into yarn and non-woven felts | Ellen MacArthur Foundation (2017), *A New Textiles Economy* | 2026-09-12 |
| 12 | Sheet Metal Scrap & Swarf → Foundries / Arc Furnaces | Secondary ferrous and non-ferrous remelting | Royal Society A / Bureau of International Recycling (BIR) ferrous scrap specs | 2026-09-12 |
| 13 | Broken Bricks (Grog) → Ceramics / Road Aggregates | Crushed defective fired clay used as chamotte temper in refractory/tile mixes and road sub-base | ASTM C326 / IS 1077 Indian Standard for Burnt Clay Bricks | 2026-09-12 |

---

## Phase 5 — Geography, Geocoding & Logistics Distance

| # | Data Element | Source / Method | Reference / URL | Date Accessed |
|---|--------------|-----------------|-----------------|---------------|
| 14 | 31 Karnataka District HQ Coordinates | OpenStreetMap Nominatim & Survey of India / Wikipedia District Registry | https://en.wikipedia.org/wiki/List_of_districts_of_Karnataka | 2026-09-12 |
| 15 | Pairwise Inter-District Distance Matrix (31x31 = 961 pairs) | Spherical Haversine Great-Circle Distance Calculation (straight-line km) | Standard Haversine formula implemented in Python `math` module | 2026-09-12 |
