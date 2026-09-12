"""Demo-pathway data corrections, applied at import time.

The raw CSVs under dataset/ are read-only to the whole team, so every
correction lives here instead. Each one is stated with the evidence that
motivated it, because these change which enterprises the app is willing to
describe as producers or receivers.

1. enterprise_name is empty in all 7,933 rows of
   02_enterprises_with_location.csv. The names exist in
   01_raw_msme_enterprises.csv, and 7,932 of 7,933 rows can be matched back on
   their communication address. Unmatched rows keep their ID and are marked
   name_source="unresolved" rather than given an invented name.

2. 03_byproducts_per_enterprise.csv assigns "Rice Husk" and "Rice Bran" to all
   3,536 NIC-10 enterprises, including chocolate makers, spice units and
   starch plants. Only genuine rice millers produce rice husk. The same
   over-assignment affects wood and brick byproducts.

3. dataset/README.md states NIC 10611 is rice milling. In the data itself
   10611 is "Flour milling" and 10612 is "Rice milling" (112 enterprises in
   Karnataka). The canonical producer set follows the data, not the README.

4. "Brick kiln" receivers must be fired-brick kilns. NIC 23952 and 23954 are
   cement and RCC block makers - they have no kiln to fire rice husk in.

5. Distances in 05_district_distance_matrix_km.csv are straight-line km. They
   are imported as integer metres with an explicit
   basis="district_straight_line" and are never used to derive a freight
   charge.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

# id -> (display name, category, is_supported_end_to_end)
MATERIALS: dict[str, tuple[str, str, bool]] = {
    "rice_husk": ("Rice Husk", "Solid Biomass", True),
    "rice_bran": ("Rice Bran", "Organic Co-product", False),
    "sawdust": ("Sawdust", "Solid Biomass", False),
    "wood_bark": ("Wood Bark", "Solid Biomass", False),
    "wood_offcuts": ("Wood Offcuts", "Solid Biomass", False),
    "fabric_cutting_waste": ("Fabric Cutting Waste", "Textile Waste", False),
    "silk_noil": ("Silk Noil / Reeling Waste", "Textile Waste", False),
    "silkworm_pupae": ("Silkworm Pupae", "Organic Co-product", False),
    "broken_bricks_grog": ("Broken / Rejected Bricks (Grog)", "Mineral Aggregate", False),
    "kiln_fly_ash": ("Kiln Fly Ash", "Mineral Fines", False),
    "sheet_metal_scrap": ("Sheet Metal Scrap", "Ferrous Metal Scrap", False),
    "machining_swarf": ("Machining Swarf", "Ferrous Metal Scrap", False),
    "mill_scale": ("Mill Scale", "Iron Oxide", False),
}

# Dataset spellings, lowercased, mapped onto canonical IDs.
MATERIAL_ALIASES: dict[str, str] = {
    "rice husk": "rice_husk",
    "rice hull": "rice_husk",
    "paddy husk": "rice_husk",
    "rice bran": "rice_bran",
    "sawdust": "sawdust",
    "saw dust": "sawdust",
    "wood bark": "wood_bark",
    "bark": "wood_bark",
    "wood offcuts": "wood_offcuts",
    "fabric cutting waste": "fabric_cutting_waste",
    "fabric waste": "fabric_cutting_waste",
    "silk noil / reeling waste": "silk_noil",
    "silk noil": "silk_noil",
    "silkworm pupae": "silkworm_pupae",
    "broken/rejected bricks (grog)": "broken_bricks_grog",
    "broken bricks (grog)": "broken_bricks_grog",
    "kiln fly ash": "kiln_fly_ash",
    "sheet metal scrap": "sheet_metal_scrap",
    "machining swarf": "machining_swarf",
    "mill scale": "mill_scale",
}


def resolve_material(name: str) -> str | None:
    return MATERIAL_ALIASES.get((name or "").strip().lower())


# ---------------------------------------------------------------------------
# Fix 2 and 3: who actually produces what
# ---------------------------------------------------------------------------

# NIC5 codes whose enterprises genuinely generate each material. A material
# absent from this map is accepted for any enterprise in its NIC division.
PRODUCER_NIC5: dict[str, set[str]] = {
    # 10612 "Rice milling" is the real code; 10611 is flour milling.
    # 10619 "Other grain milling and processing n.e.c." can include paddy.
    "rice_husk": {"10612", "10619"},
    "rice_bran": {"10612", "10619"},
    # Sawing and planing of wood, and activities related to saw milling.
    "sawdust": {"16101", "16109"},
    "wood_bark": {"16101", "16109"},
    "wood_offcuts": {"16101", "16109"},
    # Fired kilns only. Cement/RCC block makers (23952, 23954) have no kiln.
    "broken_bricks_grog": {"23921", "23912"},
    "kiln_fly_ash": {"23921", "23912"},
}

# ---------------------------------------------------------------------------
# Fix 4: receiving processes
# ---------------------------------------------------------------------------

# id -> (name, description, NIC5 codes that genuinely operate this process)
RECEIVING_PROCESSES: dict[str, tuple[str, str, set[str]]] = {
    "brick_kiln_fuel": (
        "Brick kiln firing (biomass fuel)",
        "Fired-clay brick kiln burning biomass; ash is retained as a filler in "
        "the brick mix.",
        {"23921", "23912"},
    ),
    "timber_drying_boiler_fuel": (
        "Timber drying kiln boiler (biomass fuel)",
        "Biomass boiler raising steam or hot air for a timber drying kiln at a "
        "sawmilling unit.",
        {"16101", "16109"},
    ),
    "food_process_steam_boiler": (
        "Food processing steam boiler (biomass fuel)",
        "Biomass boiler raising process steam in a food processing plant.",
        {"10795", "10796", "10799", "10712", "10719"},
    ),
}

# material -> receiving process, for the pathways in
# 04_industrial_symbiosis_pairs.csv that the app supports operationally.
# (producer NIC2, material id, receiver NIC2) -> process id
PATHWAY_PROCESS: dict[tuple[str, str, str], str] = {
    ("10", "rice_husk", "23"): "brick_kiln_fuel",
    ("10", "rice_husk", "16"): "timber_drying_boiler_fuel",
    ("16", "sawdust", "23"): "brick_kiln_fuel",
    ("16", "wood_bark", "10"): "food_process_steam_boiler",
}

PROCESS_MATERIALS: dict[str, set[str]] = {
    "brick_kiln_fuel": {"rice_husk", "sawdust"},
    "timber_drying_boiler_fuel": {"rice_husk", "sawdust"},
    "food_process_steam_boiler": {"wood_bark", "rice_husk"},
}

# ---------------------------------------------------------------------------
# Reviewed compatibility flags
# ---------------------------------------------------------------------------

# (material, process, contamination keyword, verdict, note). An empty keyword
# is the baseline verdict for a listing with no contamination notes. Anything
# not covered here is REVIEW_REQUIRED - this table is a short list of reviewed
# statements, not a claim of universal certification.
COMPATIBILITY_FLAGS: list[tuple[str, str, str, str, str]] = [
    (
        "rice_husk",
        "brick_kiln_fuel",
        "",
        "accept",
        "Clean milled rice husk is an established biomass fuel for fired-clay "
        "brick kilns (IRRI Rice Knowledge Bank; GIZ brick sector guidance).",
    ),
    (
        "rice_husk",
        "brick_kiln_fuel",
        "paddy straw",
        "accept",
        "Residual paddy straw is combustible and acceptable in a kiln fuel blend.",
    ),
    (
        "rice_husk",
        "brick_kiln_fuel",
        "field soil",
        "review",
        "Soil carry-over raises ash content; the kiln operator must confirm the "
        "ash is tolerable in the brick mix.",
    ),
    (
        "rice_husk",
        "brick_kiln_fuel",
        "plastic",
        "reject",
        "Plastic contamination is not acceptable in an open brick kiln fire.",
    ),
    (
        "rice_husk",
        "timber_drying_boiler_fuel",
        "",
        "accept",
        "Rice husk is an established biomass boiler feedstock, commonly blended "
        "with sawdust for timber drying.",
    ),
    (
        "rice_husk",
        "timber_drying_boiler_fuel",
        "field soil",
        "review",
        "Soil increases boiler ash handling; the operator must confirm capacity.",
    ),
    (
        "rice_husk",
        "timber_drying_boiler_fuel",
        "plastic",
        "reject",
        "Plastic contamination is not acceptable in a biomass boiler.",
    ),
    (
        "sawdust",
        "brick_kiln_fuel",
        "",
        "accept",
        "Sawdust is a documented pore-forming additive and fuel in green brick "
        "production.",
    ),
    (
        "sawdust",
        "brick_kiln_fuel",
        "treated timber",
        "reject",
        "Preservative-treated timber dust must not be burned in an open kiln.",
    ),
]
