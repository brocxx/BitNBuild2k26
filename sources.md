# Sources Log — Karnataka Manufacturing Dataset

> Running log of every data source used. Format: Source | URL | Date Accessed | Data Pulled

---

## Phase 1 — Karnataka Enterprise Registry

| # | Source Name | URL | Date Accessed | Data Pulled |
|---|-------------|-----|---------------|-------------|
| 1 | data.gov.in — List of MSME Registered Units under UDYAM (Karnataka filter) | https://data.gov.in/catalog/list-msme-registered-units-under-udyog-aadhaar-memorandum | 2026-09-12 | 17,437 manufacturing enterprise records (NIC 10–33), pulled via API (resource ID: `8b68ae56-84cf-4728-a0a6-1be11028dea7`), fields: EnterpriseName, State, District, Pincode, RegistrationDate, CommunicationAddress, NIC5DigitCode, NICDescription. Total Karnataka records in dataset: 2,411,947. API last updated 10/09/2026. |

**File saved:** `karnataka_msme_raw.csv`
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
| 3 | Wood & Sawmilling (NIC 16) | Product Yield: 39% (sawn timber); Byproduct / Loss: 61% (sawdust, offcuts, bark) | Industrial Ecology Data Commons (IEDC) | Dataset 412 (`4_PY_Fabrication_Furniture_CIRCOMOD`), Broman & Fredriksson (2015), *22nd International Wood Machining Seminar* | 2026-09-12 |
| 4 | Fabricated Metal (NIC 25) | Sheet cutting scrap: 22%; Bar turning swarf: 12%; Hot rolling mill scale: 10% | Industrial Ecology Data Commons (IEDC) | Dataset 439 (`4_PY_Manufacturing_Allwood_2024`), Allwood & Music (2024), *Phil. Trans. Royal Society A*, DOI: 10.1098/rsta.2023.0135 | 2026-09-12 |
| 5 | Food Processing - Rice Milling (NIC 10) | Milled Rice: 70%; Rice Husk: 20%; Rice Bran: 10% | International Rice Research Institute (IRRI) | IRRI Rice Knowledge Bank: *Milling and Processing* (http://www.knowledgebank.irri.org/step-by-step-production/postharvest/milling) | 2026-09-12 |
| 6 | Textiles & Silk (NIC 13) | Fabric cutting waste: 15%; Cotton spinning waste: 15–20%; Silk reeling waste/noil: 20–30% | FAO & Ellen MacArthur Foundation | FAO Agricultural Services Bulletin 136 (*Silk Reeling and Testing Manual*, Ch. 10) & EMF Textile Benchmarks | 2026-09-12 |
| 7 | Bricks & Ceramics (NIC 23) | Defective brick / grog scrap rate: 5–10% (avg 7%); Firing/drying mass loss: 10–15% | GIZ South Asia & ScienceDirect | GIZ Clean Brick Kiln Sector Report; *Construction and Building Materials* (Elsevier, DOI: 10.1016/j.conbuildmat.2014.07.037) | 2026-09-12 |

---

## Phase 4 — Symbiosis Pairs
*(to be filled)*

## Phase 5 — Geography / Coordinates
*(to be filled)*

