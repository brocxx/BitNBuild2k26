import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(",");
  return lines.slice(1).map((line) => {
    const cols = [];
    let cur = "";
    let inQ = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') {
        inQ = !inQ;
        continue;
      }
      if (c === "," && !inQ) {
        cols.push(cur);
        cur = "";
        continue;
      }
      cur += c;
    }
    cols.push(cur);
    const row = {};
    headers.forEach((h, i) => {
      row[h.trim()] = (cols[i] ?? "").trim();
    });
    return row;
  });
}

const BYPRODUCT_MAP = {
  rice_husk: "rice_husk",
  rice_bran: "rice_bran",
  sawdust: "sawdust",
  wood_bark: "wood_bark",
  wood_offcuts: "wood_offcuts",
  fabric_cutting_waste: "fabric_cutting_waste",
  silk_noil_reeling_waste: "silk_noil_reeling_waste",
  broken_rejected_bricks_grog: "broken_rejected_bricks_grog",
  kiln_fly_ash: "kiln_fly_ash",
  sheet_metal_scrap: "sheet_metal_scrap",
  machining_swarf: "machining_swarf",
  mill_scale: "mill_scale",
};

const entRows = parseCsv(
  fs.readFileSync(path.join(root, "dataset/02_enterprises_with_location.csv"), "utf8")
);
const bpRows = parseCsv(
  fs.readFileSync(path.join(root, "dataset/03_byproducts_per_enterprise.csv"), "utf8")
);

const byEnt = {};
for (const r of bpRows) {
  const id = r.enterprise_id;
  if (!byEnt[id]) byEnt[id] = new Set();
  const mat = r.byproduct_name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
  byEnt[id].add(BYPRODUCT_MAP[mat] || mat);
}

const enterprises = entRows
  .map((r) => {
    const nic2 = String(r.nic2_division || "").padStart(2, "0");
    const sector = `NIC ${parseInt(nic2, 10)}`;
    const lat = parseFloat(r.district_hq_lat);
    const lon = parseFloat(r.district_hq_lon);
    const id = r.enterprise_id;
    return {
      enterprise_id: id,
      name: r.enterprise_name || `Enterprise ${id}`,
      district: r.district,
      lat,
      lon,
      sector,
      byproducts: [...(byEnt[id] || [])],
    };
  })
  .filter((e) => !Number.isNaN(e.lat) && !Number.isNaN(e.lon));

const out = path.join(root, "frontend/src/data/mapEnterprises.json");
fs.writeFileSync(out, JSON.stringify({ enterprises }));
console.log(`Wrote ${enterprises.length} enterprises to ${out}`);
