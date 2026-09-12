# Karnataka Manufacturing Byproduct & Industrial Symbiosis Dataset

**Project:** BitNBuild Hackathon 2026  
**Goal:** Map industrial manufacturing byproducts across Karnataka's MSME sector and identify B2B waste-to-resource routing opportunities between industries.  
**GitHub:** https://github.com/brocxx/BitNBuild2k26

---

## What This Dataset Is About

Karnataka has over 17,000 registered small and medium manufacturing businesses (MSMEs). Every one of them produces waste — sawdust from sawmills, rice husk from rice mills, metal scrap from fabrication shops, rejected bricks from kilns, fabric offcuts from textile units.

This dataset answers two questions:
1. **Where is the waste being generated?** (which industry, which district, how much)
2. **Who can use it?** (which other industry can take that byproduct as a raw material input)

This is called **Industrial Symbiosis** — one factory's waste becomes another factory's raw material, reducing cost and pollution for both.

---

## Files in This Dataset

### `01_raw_msme_enterprises.csv`
**What it is:** The original raw pull of all Karnataka manufacturing MSMEs from the Government of India's UDYAM registration database.

| Column | Meaning |
|--------|---------|
| `EnterpriseName` | Registered name of the business |
| `State` | Always "KARNATAKA" |
| `District` | District where the enterprise is located (all 31 Karnataka districts) |
| `Pincode` | PIN code of the enterprise address |
| `RegistrationDate` | Date of UDYAM registration |
| `CommunicationAddress` | Registered address |
| `NIC5DigitCode` | 5-digit NIC-2008 industry code (e.g. `10611` = Rice milling) |
| `NICDescription` | Human-readable description of the industry type |

- **Records:** 17,437 enterprises
- **Filter applied:** Only manufacturing sectors (NIC codes 10-33); agriculture, services, etc. excluded
- **Source:** data.gov.in — "List of MSME Registered Units under UDYAM", Resource ID `8b68ae56-84cf-4728-a0a6-1be11028dea7`, API key authenticated pull. Last updated 10 Sept 2026.

---

### `02_enterprises_with_location.csv`
**What it is:** A cleaned, filtered version of the raw data — only the 5 target industries — enriched with district GPS coordinates. One row per enterprise.

| Column | Meaning |
|--------|---------|
| `enterprise_id` | Unique ID we assigned (format: `KA-ENT-000001`) |
| `enterprise_name` | Name of the business |
| `district` | District name (matches UDYAM spelling) |
| `district_hq_lat` | Latitude of the district headquarters town |
| `district_hq_lon` | Longitude of the district headquarters town |
| `pincode` | PIN code |
| `nic5_code` | 5-digit NIC-2008 code |
| `nic2_division` | 2-digit NIC division (10, 13, 16, 23, or 25) |
| `nic_description` | Industry description |
| `registration_date` | Date of UDYAM registration |
| `communication_address` | Full registered address |

- **Records:** 7,933 enterprises (subset of raw — only 5 target NIC divisions)
- **Coordinates source:** OpenStreetMap / Wikipedia — "List of districts of Karnataka"

**The 5 target industries:**

| NIC Division | Industry | Enterprises in Karnataka |
|---|---|---|
| `10` | Food Processing (rice milling, flour, dairy, spices) | 3,536 |
| `13` | Textiles & Silk (weaving, cotton, silk reeling) | 2,091 |
| `16` | Wood Products & Sawmilling | 693 |
| `23` | Non-Metallic Minerals (brick & tile manufacturing) | 617 |
| `25` | Fabricated Metal Products (sheet metal, machining) | 996 |

---

### `03_byproducts_per_enterprise.csv`
**What it is:** Every byproduct produced by every enterprise, with the estimated annual tonnage. One enterprise can have multiple rows (one per byproduct type).

| Column | Meaning |
|--------|---------|
| `enterprise_id` | Links to `02_enterprises_with_location.csv` |
| `nic2_division` | 2-digit NIC division |
| `byproduct_name` | Name of the byproduct (e.g. "Rice Husk", "Sawdust", "Sheet Metal Scrap") |
| `waste_ratio_pct` | Byproduct as % of raw material input — **from peer-reviewed literature** |
| `qty_annual_tonnes_estimated` | **Estimated** annual quantity in tonnes (see note below) |
| `unit` | Always `tonnes/year` |
| `district` | District where enterprise is located |
| `source_citation` | The academic/government source the yield ratio came from |

> **Note on `qty_annual_tonnes_estimated`:** Calculated as `waste_ratio_pct x 100 tonnes` (assuming an average input of 100 tonnes/year per MSME). The `_estimated` suffix clearly marks this assumption. The **yield ratios themselves are real and cited**.

**Byproduct yield ratios and their sources:**

| Industry | Byproduct | Waste % | Source |
|---|---|---|---|
| Food / Rice Milling (NIC 10) | Rice Husk | 20% of paddy input | IRRI Rice Knowledge Bank |
| Food / Rice Milling (NIC 10) | Rice Bran | 10% of paddy input | IRRI Rice Knowledge Bank |
| Textiles / Garment (NIC 13) | Fabric Cutting Waste | 15% of fabric input | Ellen MacArthur Foundation (2017) |
| Textiles / Silk (NIC 13) | Silk Noil / Reeling Waste | 25% of cocoon input | FAO Bulletin 136 |
| Wood / Sawmilling (NIC 16) | Sawdust | 25% of log input | IEDC Dataset 412 / Broman & Fredriksson (2015) |
| Wood / Sawmilling (NIC 16) | Wood Bark | 12% of log input | IEDC Dataset 412 |
| Wood / Sawmilling (NIC 16) | Wood Offcuts | 24% of log input | IEDC Dataset 412 |
| Bricks (NIC 23) | Broken/Rejected Bricks (Grog) | 7% of kiln output | GIZ Clean Brick Kiln Report; Elsevier DOI:10.1016/j.conbuildmat.2014.07.037 |
| Bricks (NIC 23) | Kiln Fly Ash | 3% of kiln output | GIZ Clean Brick Kiln Report |
| Fabricated Metal (NIC 25) | Sheet Metal Scrap | 22% of sheet input | IEDC Dataset 439 / Allwood & Music (2024), Royal Society A |
| Fabricated Metal (NIC 25) | Machining Swarf | 12% of bar stock | IEDC Dataset 439 |
| Fabricated Metal (NIC 25) | Mill Scale | 10% of hot-rolled input | IEDC Dataset 439 |

---

### `04_industrial_symbiosis_pairs.csv`
**What it is:** The routing table. Maps each byproduct from its producing industry to a receiving industry that can use it as raw material input.

| Column | Meaning |
|--------|---------|
| `producer_nic` | 2-digit NIC of the industry producing the waste |
| `producer_industry` | Name of the producing industry |
| `byproduct_name` | The byproduct being routed |
| `byproduct_type` | Physical category (Solid Biomass, Ferrous Metal Scrap, etc.) |
| `waste_ratio_pct` | % waste generated |
| `qty_per_100_tons_input_estimated` | Estimated qty per 100 t input (estimated) |
| `unit` | Unit of measurement |
| `receiver_nic` | 2-digit NIC of the industry that receives this byproduct |
| `receiver_industry` | Name of the receiving industry |
| `use_case` | Exactly how the byproduct is used by the receiver |
| `source_citation` | Citation for this symbiosis link |

- **Records:** 14 symbiosis pairs

**Key connections:**

| Byproduct | From | To | Use |
|---|---|---|---|
| Rice Husk | Rice mills | Brick kilns | Fuel; ash as pozzolan in brick mix |
| Rice Husk | Rice mills | Sawmills | Biomass boiler fuel for timber drying |
| Rice Bran | Rice mills | Food / feed | Edible oil extraction; animal feed |
| Sawdust | Sawmills | Brick kilns | Pore-forming additive in green brick |
| Wood Bark | Sawmills | Food processing | Boiler fuel for food plant steam |
| Wood Offcuts | Sawmills | Particle board / MDF | Core material input |
| Silk Noil | Silk reeling | Spun silk mills | Feedstock for schappe/bourette yarn |
| Silkworm Pupae | Silk reeling | Poultry / aquaculture | High-protein animal feed |
| Fabric Waste | Garment units | Recycled fibre | Re-spun as shoddy yarn; insulation |
| Broken Bricks (Grog) | Brick kilns | Ceramics / roads | Chamotte aggregate; road sub-base |
| Kiln Fly Ash | Brick kilns | Cement producers | Supplementary cementitious material |
| Sheet Metal Scrap | Fabrication | Steel foundries | Re-melt in electric arc furnace |
| Machining Swarf | Fabrication | Scrap dealers | Briquetted for remelting |
| Mill Scale | Fabrication | Cement / pigment | Iron oxide pigment; cement additive |

---

### `05_district_distance_matrix_km.csv`
**What it is:** Straight-line distances in km between every pair of Karnataka district headquarters.

| Column | Meaning |
|--------|---------|
| `from_district` | Origin district |
| `to_district` | Destination district |
| `distance_km_estimated` | Haversine distance in km (straight-line) |

- **Records:** 961 (31 x 31)
- **Formula:** Haversine great-circle distance (standard geographic formula)
- **Note:** Straight-line only — actual road distances are typically 20-40% longer

---

### `06_district_headquarters_coordinates.csv`
**What it is:** Lat/lon for all 31 Karnataka district HQs.

| Column | Meaning |
|--------|---------|
| `district` | District name (exact spelling used across all files) |
| `hq_town` | Name of the headquarters town |
| `lat` | Latitude (WGS84 decimal degrees) |
| `lon` | Longitude (WGS84 decimal degrees) |
| `source` | OpenStreetMap/Wikipedia |

- **Records:** 31 (all Karnataka districts, including Vijayanagara — HQ at Hosapete)
- **Source:** https://en.wikipedia.org/wiki/List_of_districts_of_Karnataka

---

## How This Dataset Was Built — Step by Step

| Step | What was done | Tool / Source |
|---|---|---|
| 1 | Called data.gov.in UDYAM API, filtered Karnataka manufacturing records (NIC 10-33) | data.gov.in API |
| 2 | Counted enterprises per NIC division, selected top 5 industries with best byproduct documentation | Manual analysis |
| 3 | Found process yield ratios (waste %) from peer-reviewed literature | IEDC, IRRI, FAO, GIZ |
| 4 | Built symbiosis pairing table (byproduct → receiver industry) | Literature + EMF frameworks |
| 5 | Compiled lat/lon for all 31 district HQs | OpenStreetMap / Wikipedia |
| 6 | Computed 31x31 Haversine distance matrix | Python (math.haversine) |
| 7 | Merged all data into final CSVs | Python csv module |

---

## Which Columns Are Estimated vs. Real

| Column | Status | Reason |
|--------|--------|--------|
| `waste_ratio_pct` | Real — cited literature | Peer-reviewed yield coefficients |
| `qty_annual_tonnes_estimated` | Estimated | Assumes 100 t/yr baseline per MSME |
| `qty_per_100_tons_input_estimated` | Estimated | Same baseline assumption |
| `distance_km_estimated` | Estimated | Straight-line, not road distance |
| `district_hq_lat` / `district_hq_lon` | Real | From OSM/Wikipedia |
| Enterprise names, NIC codes, addresses | Real | Directly from UDYAM API |

---

*Dataset compiled for BitNBuild Hackathon 2026. Repository: https://github.com/brocxx/BitNBuild2k26*
