export type DatasetMaterial = {
  id: string;
  name: string;
};

export type DatasetPathway = {
  material_id: string;
  material_name: string;
  process_id: string;
  receiver_nic: number;
  receiver_industry: string;
  use_case: string;
  source_citation: string;
};

// Exact byproduct names present in 03_byproducts_per_enterprise.csv.
// No material is preselected in the UI.
export const DATASET_MATERIALS: DatasetMaterial[] = [
  {
    "id": "sheet_metal_scrap",
    "name": "Sheet Metal Scrap"
  },
  {
    "id": "machining_swarf",
    "name": "Machining Swarf"
  },
  {
    "id": "mill_scale",
    "name": "Mill Scale"
  },
  {
    "id": "rice_husk",
    "name": "Rice Husk"
  },
  {
    "id": "rice_bran",
    "name": "Rice Bran"
  },
  {
    "id": "broken_rejected_bricks_grog",
    "name": "Broken/Rejected Bricks (Grog)"
  },
  {
    "id": "kiln_fly_ash",
    "name": "Kiln Fly Ash"
  },
  {
    "id": "fabric_cutting_waste",
    "name": "Fabric Cutting Waste"
  },
  {
    "id": "silk_noil_reeling_waste",
    "name": "Silk Noil / Reeling Waste"
  },
  {
    "id": "sawdust",
    "name": "Sawdust"
  },
  {
    "id": "wood_bark",
    "name": "Wood Bark"
  },
  {
    "id": "wood_offcuts",
    "name": "Wood Offcuts"
  }
];

// Exact receiver-industry / use-case rows from 04_industrial_symbiosis_pairs.csv.
// Silkworm pupae is not offered as a selectable material because it is not present
// in 03_byproducts_per_enterprise.csv.
export const DATASET_PATHWAYS: DatasetPathway[] = [
  {
    "material_id": "rice_husk",
    "material_name": "Rice Husk",
    "process_id": "brick_kiln_fuel",
    "receiver_nic": 23,
    "receiver_industry": "Non-Metallic Minerals (Brick Manufacturing)",
    "use_case": "Fuel for brick kiln firing; ash used as filler / pozzolan in brick mix",
    "source_citation": "IRRI Rice Knowledge Bank — Milling & Processing; GIZ Clean Brick Kiln Sector Report"
  },
  {
    "material_id": "rice_husk",
    "material_name": "Rice Husk",
    "process_id": "boiler_fuel",
    "receiver_nic": 16,
    "receiver_industry": "Wood Products & Sawmilling",
    "use_case": "Biomass briquette co-feedstock blended with sawdust; boiler fuel for timber drying kilns",
    "source_citation": "IRRI Rice Knowledge Bank; Ellen MacArthur Foundation — Industrial Symbiosis Toolkit"
  },
  {
    "material_id": "rice_bran",
    "material_name": "Rice Bran",
    "process_id": "rice_bran_oil_feed",
    "receiver_nic": 10,
    "receiver_industry": "Food Processing (Edible Oil / Animal Feed)",
    "use_case": "Rice bran oil extraction feedstock; residual defatted bran as livestock feed supplement",
    "source_citation": "IRRI Rice Knowledge Bank — Milling & Processing; FAO Agro-industrial Utilization of Paddy"
  },
  {
    "material_id": "fabric_cutting_waste",
    "material_name": "Fabric Cutting Waste",
    "process_id": "recycled_fibre_shoddy",
    "receiver_nic": 13,
    "receiver_industry": "Textiles (Recycled Fibre / Shoddy Production)",
    "use_case": "Shredded and re-spun as recycled yarn (shoddy/mungo process); insulation batting",
    "source_citation": "Ellen MacArthur Foundation — A New Textiles Economy (2017); FAO Bulletin 136"
  },
  {
    "material_id": "silk_noil_reeling_waste",
    "material_name": "Silk Noil / Reeling Waste",
    "process_id": "spun_silk_schappe",
    "receiver_nic": 13,
    "receiver_industry": "Textiles (Spun Silk / Schappe Yarn Production)",
    "use_case": "Spun silk yarn feedstock (schappe/bourette process); lower-grade textile input",
    "source_citation": "FAO Agricultural Services Bulletin 136 — Silk Reeling and Testing Manual, Ch. 10"
  },
  {
    "material_id": "sawdust",
    "material_name": "Sawdust",
    "process_id": "brick_pore_forming_agent",
    "receiver_nic": 23,
    "receiver_industry": "Non-Metallic Minerals (Brick Manufacturing)",
    "use_case": "Pore-forming agent mixed into green brick body; combustion creates lightweight / porous brick",
    "source_citation": "IEDC Dataset 412 / Broman & Fredriksson (2015); GIZ Clean Brick Kiln Report"
  },
  {
    "material_id": "wood_bark",
    "material_name": "Wood Bark",
    "process_id": "biomass_boiler_heat",
    "receiver_nic": 10,
    "receiver_industry": "Food Processing (Boiler / Heat Generation)",
    "use_case": "Biomass boiler fuel for steam generation in food processing facilities (drying, sterilisation)",
    "source_citation": "IEDC Dataset 412 / Broman & Fredriksson (2015); Ellen MacArthur Foundation Biomass Loops"
  },
  {
    "material_id": "wood_offcuts",
    "material_name": "Wood Offcuts",
    "process_id": "particle_board_mdf_feedstock",
    "receiver_nic": 16,
    "receiver_industry": "Wood Products (Particle Board / MDF Manufacturing)",
    "use_case": "Chipped and pressed as particle board or MDF core material",
    "source_citation": "IEDC Dataset 412 / Broman & Fredriksson (2015)"
  },
  {
    "material_id": "broken_rejected_bricks_grog",
    "material_name": "Broken/Rejected Bricks (Grog)",
    "process_id": "ceramics_refractories_grog",
    "receiver_nic": 23,
    "receiver_industry": "Non-Metallic Minerals (Ceramics / Refractories)",
    "use_case": "Crushed grog as chamotte aggregate in ceramic body or refractory mix; road sub-base material",
    "source_citation": "GIZ Clean Brick Kiln Sector Report; Construction & Building Materials, Elsevier DOI:10.1016/j.conbuildmat.2014.07.037"
  },
  {
    "material_id": "kiln_fly_ash",
    "material_name": "Kiln Fly Ash",
    "process_id": "cement_pozzolanic_products",
    "receiver_nic": 23,
    "receiver_industry": "Non-Metallic Minerals (Cement / Pozzolanic Products)",
    "use_case": "Supplementary cementitious material (SCM); partial Portland cement replacement",
    "source_citation": "GIZ Clean Brick Kiln Sector Report; IS 3812 (Pulverised Fuel Ash Specification, BIS India)"
  },
  {
    "material_id": "sheet_metal_scrap",
    "material_name": "Sheet Metal Scrap",
    "process_id": "secondary_steelmaking_foundry",
    "receiver_nic": 25,
    "receiver_industry": "Fabricated Metal (Secondary Steelmaking / Foundry)",
    "use_case": "Direct re-melt feedstock in electric arc furnace (EAF) or induction furnace for secondary steel",
    "source_citation": "IEDC Dataset 439 / Allwood & Music (2024), Phil. Trans. Royal Society A, DOI:10.1098/rsta.2023.0135"
  },
  {
    "material_id": "machining_swarf",
    "material_name": "Machining Swarf",
    "process_id": "scrap_trading_remelting",
    "receiver_nic": 25,
    "receiver_industry": "Fabricated Metal (Scrap Trading / Remelting)",
    "use_case": "Briquetted swarf or loose turnings sold to scrap dealers / foundries for remelting",
    "source_citation": "IEDC Dataset 439 / Allwood & Music (2024), Phil. Trans. Royal Society A, DOI:10.1098/rsta.2023.0135"
  },
  {
    "material_id": "mill_scale",
    "material_name": "Mill Scale",
    "process_id": "pigment_cement_additive",
    "receiver_nic": 23,
    "receiver_industry": "Non-Metallic Minerals (Pigment / Cement Additive)",
    "use_case": "Iron oxide pigment feedstock for construction products; cement colour additive; anti-corrosive primer",
    "source_citation": "IEDC Dataset 439 / Allwood & Music (2024); Journal of Cleaner Production (Elsevier)"
  }
];

export const DATASET_ENTERPRISE_ESTIMATES: Record<string, Record<string, number>> = {
  "KA-ENT-000020": { rice_husk: 20, rice_bran: 10 },
  "KA-ENT-000089": { rice_husk: 20, rice_bran: 10 },
  "KA-ENT-001312": { rice_husk: 20, rice_bran: 10 },
  "KA-ENT-000478": { rice_husk: 20, rice_bran: 10 },
  "KA-ENT-000179": { broken_rejected_bricks_grog: 7, kiln_fly_ash: 3 },
};

export function getMaterialName(materialId: string): string {
  return DATASET_MATERIALS.find((m) => m.id === materialId)?.name ?? materialId.replace(/_/g, " ");
}

export function getPathwaysForMaterial(materialId: string): DatasetPathway[] {
  return DATASET_PATHWAYS.filter((p) => p.material_id === materialId);
}

export function getPathwayByProcessId(processId: string): DatasetPathway | undefined {
  return DATASET_PATHWAYS.find((p) => p.process_id === processId);
}

export function getEstimatedAnnualTonnes(enterpriseId: string | null, materialId: string): number | null {
  if (!enterpriseId) return null;
  return DATASET_ENTERPRISE_ESTIMATES[enterpriseId]?.[materialId] ?? null;
}
