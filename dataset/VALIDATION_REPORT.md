# Phase 7 — Final Validation Report
## Karnataka Manufacturing Byproduct & Industrial Symbiosis Dataset

**Project:** BitNBuild Hackathon 2026  
**Repository:** https://github.com/brocxx/BitNBuild2k26  
**Date:** September 12, 2026  
**Status:** Completed & Validated  

---

## 1. Executive Summary

This validation report concludes **Phases 1 through 7** of the data pipeline for the BitNBuild 2026 Hackathon goal:
> *"Develop agents that analyze industrial manufacturing byproduct data and autonomously negotiate alternative B2B logistics to route waste material into production pipelines."*

Every enterprise record represents a real, legally registered MSME in Karnataka from the official Government of India UDYAM registry. Byproduct yield ratios are derived from peer-reviewed industrial ecology literature and institutional sources (IEDC, IRRI, FAO, GIZ, Ellen MacArthur Foundation). Geographic coordinates cover all 31 Karnataka districts with a pairwise distance matrix computed via spherical trigonometry.

---

## 2. Dataset Inventory & Verification Metrics

| # | File Name | Description | Verified Rows | Columns | Primary Key / Linking Key |
|---|-----------|-------------|---------------|---------|---------------------------|
| 1 | `01_raw_msme_enterprises.csv` | Raw manufacturing MSME registry | 17,437 | 8 | Pincode, NIC5DigitCode |
| 2 | `02_enterprises_with_location.csv` | Cleaned target enterprises with district coords | 7,933 | 11 | `enterprise_id` (`KA-ENT-000001` to `KA-ENT-007933`) |
| 3 | `03_byproducts_per_enterprise.csv` | Byproduct generation streams per enterprise | 17,555 | 8 | `enterprise_id` (foreign key) |
| 4 | `04_industrial_symbiosis_pairs.csv` | B2B byproduct routing table | 14 | 11 | `producer_nic` → `receiver_nic` |
| 5 | `05_district_distance_matrix_km.csv` | Pairwise inter-district Haversine distances | 961 | 3 | `from_district`, `to_district` |
| 6 | `06_district_headquarters_coordinates.csv` | GPS lat/lon for district headquarters | 31 | 5 | `district` |

---

## 3. Industry Coverage & Enterprise Breakdown

Out of 17,437 total manufacturing enterprises in Karnataka, **7,933 enterprises** across **5 high-impact circular economy sectors** were extracted:

| NIC Division | Sector Name | Enterprises | % of Dataset | Documented Byproducts |
|--------------|-------------|-------------|--------------|-----------------------|
| **NIC 10** | Food Products & Agro-Processing | 3,536 | 44.6% | Rice Husk (20%), Rice Bran (10%) |
| **NIC 13** | Manufacture of Textiles & Silk | 2,091 | 26.4% | Fabric Cutting Waste (15%), Silk Noil (25%) |
| **NIC 16** | Wood Products & Sawmilling | 693 | 8.7% | Sawdust (25%), Wood Bark (12%), Offcuts (24%) |
| **NIC 23** | Other Non-Metallic Mineral Products (Bricks/Ceramics) | 617 | 7.8% | Rejected Bricks / Grog (7%), Kiln Fly Ash (3%) |
| **NIC 25** | Fabricated Metal Products | 996 | 12.6% | Sheet Metal Scrap (22%), Machining Swarf (12%), Mill Scale (10%) |
| **Total** | | **7,933** | **100%** | **17,555 byproduct generation instances** |

---

## 4. Geographic Distribution (All 31 Karnataka Districts)

Every registered enterprise belongs to one of Karnataka's 31 administrative districts, fully geocoded to district headquarters:

- **Top Districts by Manufacturing Enterprise Density:**
  - BENGALURU (URBAN): 2,140+ enterprises
  - BELAGAVI: 780+ enterprises
  - DAKSHIN KANNAD (Mangaluru): 490+ enterprises
  - MYSURU: 430+ enterprises
  - TUMAKURU: 370+ enterprises
- **Complete Coverage:** Bagalkot, Ballari, Belagavi, Bengaluru Rural, Bengaluru Urban, Bidar, Chamarajanagar, Chikballapur, Chikkamagaluru, Chitradurga, Dakshin Kannad, Davangere, Dharwad, Gadag, Hassan, Haveri, Kalaburagi, Kodagu, Kolar, Koppal, Mandya, Mysuru, Raichur, Ramanagara, Shivamogga, Tumakuru, Udupi, Uttar Kannad, Vijayanagar, Vijayapura, Yadgir.

---

## 5. Peer-Reviewed Byproduct Yield Ratios (Phase 3 Audit)

| Industry | Byproduct | Yield / Waste Ratio | Benchmark Type | Cited Primary Source |
|----------|-----------|---------------------|----------------|----------------------|
| **Wood / Sawmilling (NIC 16)** | Sawdust | 25% of log input | Empirical conversion factor | IEDC Dataset 412 / Broman & Fredriksson (2015), *22nd Intl. Wood Machining Seminar* |
| **Wood / Sawmilling (NIC 16)** | Wood Bark | 12% of log input | Mass fraction | IEDC Dataset 412 / CIRCOMOD |
| **Wood / Sawmilling (NIC 16)** | Wood Offcuts | 24% of log input | Trim loss fraction | IEDC Dataset 412 |
| **Fabricated Metal (NIC 25)** | Sheet Metal Scrap | 22% of sheet input | Scrap coefficient | IEDC Dataset 439 / Allwood & Music (2024), *Royal Society A* (DOI: 10.1098/rsta.2023.0135) |
| **Fabricated Metal (NIC 25)** | Machining Swarf | 12% of bar stock | Material loss factor | IEDC Dataset 439 |
| **Fabricated Metal (NIC 25)** | Mill Scale | 10% of hot-rolled input | Oxidation loss factor | IEDC Dataset 439 |
| **Food / Rice Milling (NIC 10)** | Rice Husk | 20% of paddy input | Postharvest milling standard | IRRI (International Rice Research Institute) Rice Knowledge Bank |
| **Food / Rice Milling (NIC 10)** | Rice Bran | 10% of paddy input | Postharvest milling standard | IRRI Rice Knowledge Bank |
| **Textiles & Silk (NIC 13)** | Fabric Cutting Waste | 15% of fabric input | Apparel cutting room loss | Ellen MacArthur Foundation (2017), *A New Textiles Economy* |
| **Textiles & Silk (NIC 13)** | Silk Reeling Waste (Noil) | 25% of cocoon input | Filature reeling factor | FAO Agricultural Services Bulletin 136 (*Silk Reeling and Testing Manual*) |
| **Bricks & Ceramics (NIC 23)** | Broken Bricks (Grog) | 7% of kiln output | Firing defect rate | GIZ South Asia Brick Sector Guidelines; Elsevier *ConBuildMat* (DOI: 10.1016/j.conbuildmat.2014.07.037) |
| **Bricks & Ceramics (NIC 23)** | Kiln Fly Ash | 3% of kiln output | Combustion particulate yield | GIZ Clean Brick Kiln Guidelines |

---

## 6. Documented Industrial Symbiosis Routing Map (Phase 4 Audit)

Fourteen (14) B2B waste-to-resource pathways were verified and structured in `04_industrial_symbiosis_pairs.csv`:

```
[NIC 10 Food / Rice Milling]
  ├── Rice Husk (20%) ──────────► [NIC 23 Brick Kilns] (Kiln fuel & silica pozzolan)
  ├── Rice Husk (20%) ──────────► [NIC 16 Sawmills] (Boiler fuel for timber drying kilns)
  └── Rice Bran (10%) ──────────► [NIC 10 Food / Animal Feed] (Edible oil extraction & animal feed)

[NIC 16 Wood & Sawmilling]
  ├── Sawdust (25%) ────────────► [NIC 23 Brick Kilns] (Pore-forming thermal insulating additive)
  ├── Wood Bark (12%) ──────────► [NIC 10 Food Processing] (Biomass boiler fuel for process steam)
  └── Wood Offcuts (24%) ───────► [NIC 16 Particle Board / Furniture] (Core material / finger-jointing)

[NIC 13 Textiles & Silk]
  ├── Fabric Waste (15%) ───────► [NIC 13 Recycled Textiles] (Shoddy yarn, acoustic & thermal insulation)
  ├── Silk Noil (25%) ──────────► [NIC 13 Spun Silk Mills] (Feedstock for premium schappe / bourette yarn)
  └── Silkworm Pupae ───────────► [Aquaculture & Poultry] (High-protein animal feed)

[NIC 23 Bricks & Minerals]
  ├── Broken Bricks / Grog (7%) ► [NIC 23 Ceramics / Civil Works] (Chamotte grog, road sub-base aggregate)
  └── Kiln Fly Ash (3%) ────────► [NIC 23 Cement & Concrete] (Supplementary cementitious material)

[NIC 25 Fabricated Metal]
  ├── Sheet Metal Scrap (22%) ──► [Foundries / Steel Mills] (Electric Arc Furnace secondary remelting)
  ├── Machining Swarf (12%) ────► [Secondary Metal Dealers] (Briquetted feedstock for remelt)
  └── Mill Scale (10%) ─────────► [Cement & Pigment Works] (Iron source in clinker, iron oxide pigment)
```

---

## 7. Audit of Real vs. Estimated Data (Rule 4 Compliance)

| Field | Classification | Verification / Assumption Basis |
|-------|----------------|---------------------------------|
| `enterprise_name`, `district`, `pincode`, `communication_address` | **REAL** | Pulled directly from official UDYAM registration API (`data.gov.in`) |
| `nic5_code`, `nic_description` | **REAL** | Government registered NIC-2008 classification |
| `waste_ratio_pct` | **REAL** | Peer-reviewed literature conversion ratios |
| `qty_annual_tonnes_estimated` | **ESTIMATED** | Standardized baseline assumption of 100 t/year input per MSME unit. Clearly marked with `_estimated` suffix. |
| `qty_per_100_tons_input_estimated`| **ESTIMATED** | Standardized baseline assumption. Clearly marked with `_estimated` suffix. |
| `district_hq_lat`, `district_hq_lon` | **REAL** | OpenStreetMap / Survey of India district coordinates |
| `distance_km_estimated` | **ESTIMATED** | Spherical Haversine distance (straight-line); road logistics is typically +20-40%. Marked with `_estimated` suffix. |

---

## 8. Manual vs. Automated Retrieval Audit (Rule 2 Compliance)

In strict accordance with Hard Rule #2, the following audit details what was fetched autonomously versus what required manual user input:

1. **User Input / Manual Provision:**
   - **UDYAM API Key & Resource ID:** `data.gov.in` and `aikosh.indiaai.gov.in` enforce bot-blocking and required human authentication. The user generated a free personal API key on `data.gov.in` and provided the resource ID (`8b68ae56-84cf-4728-a0a6-1be11028dea7`).
   - **Target Industry Selection:** The agent analyzed the enterprise counts across all manufacturing divisions and proposed the top candidate sectors. The user reviewed and confirmed the 5 target manufacturing categories.

2. **Automated Pipeline Execution:**
   - **API Pagination & Filter:** Automated script queried the `data.gov.in` API with the key, extracted 17,437 manufacturing records (NIC 10–33), and saved `01_raw_msme_enterprises.csv`.
   - **Literature Harvesting:** Yield ratios and symbiosis pathways were harvested from IEDC datasets (412, 439), IRRI, FAO Bulletin 136, GIZ, and Ellen MacArthur Foundation publications.
   - **Geocoding & Haversine Matrix:** Automated generation of 31 district coordinates and calculation of the 961-pair straight-line distance matrix.
   - **Dataset Normalization & Packaging:** Clean merge into relational CSV schemas with explicit foreign keys (`enterprise_id`, `district`, `producer_nic`).

---

## 9. Next Steps: Agent Development & Autonomous B2B Waste Routing

With the data layer complete, verified, and pushed to GitHub, the foundational dataset is ready to power the hackathon agents:

1. **Agent Architecture:**
   - **Seller / Generator Agents:** Represent MSMEs generating byproducts (e.g. rice mill with 20 tonnes of rice husk or sawmill with 25 tonnes of sawdust).
   - **Buyer / Receiver Agents:** Represent factories requiring secondary raw materials or biomass fuel (e.g. brick kilns needing husk for fuel or sawdust for porosity).
   - **Logistics & Broker Agent:** Evaluates candidate buyer-seller pairs using `04_industrial_symbiosis_pairs.csv` and `05_district_distance_matrix_km.csv`, calculates transport viability, and conducts automated multi-agent price/delivery negotiation.

2. **Immediate Implementation Readiness:**
   - The agents can now consume `02_enterprises_with_location.csv` and `03_byproducts_per_enterprise.csv` as input environments to simulate and demonstrate autonomous circular economy transactions across Karnataka.
