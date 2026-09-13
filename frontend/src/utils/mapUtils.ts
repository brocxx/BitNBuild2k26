import type { MapEnterprise } from "../api/types";
import { DATASET_PATHWAYS } from "../data/datasetReference";

export const KARNATAKA_CENTER = { lat: 15.3, lon: 75.7, zoom: 7 };

export const SECTOR_COLORS: Record<string, string> = {
  "NIC 10": "#c0392b",
  "NIC 16": "#d4a017",
  "NIC 23": "#2471a3",
  "NIC 13": "#8e44ad",
  "NIC 25": "#2c3e50",
};

export const SECTOR_LABELS: Record<string, string> = {
  "NIC 10": "Food / Rice Mills",
  "NIC 16": "Wood / Sawmills",
  "NIC 23": "Brick Kilns / Ceramics",
  "NIC 13": "Textiles / Silk",
  "NIC 25": "Metal Fabrication",
};

export function sectorColor(sector: string): string {
  return SECTOR_COLORS[sector] ?? "#6b716a";
}

export function jitterCoords(id: string, lat: number, lon: number): [number, number] {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash << 5) - hash + id.charCodeAt(i);
    hash |= 0;
  }
  const dx = ((hash % 100) - 50) / 2500;
  const dy = (((hash >> 8) % 100) - 50) / 2500;
  return [lat + dx, lon + dy];
}

export function haversineKm(aLat: number, aLon: number, bLat: number, bLon: number): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const r = 6371;
  const dLat = toRad(bLat - aLat);
  const dLon = toRad(bLon - aLon);
  const lat1 = toRad(aLat);
  const lat2 = toRad(bLat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(h));
}

export function nicFromSector(sector: string): number | null {
  const match = sector.match(/NIC\s+(\d+)/i);
  return match ? parseInt(match[1], 10) : null;
}

export function findCompatibleInRadius(
  origin: MapEnterprise,
  all: MapEnterprise[],
  radiusKm: number
): MapEnterprise[] {
  const producerMaterials = new Set(origin.byproducts);
  if (!producerMaterials.size) return [];

  const receiverNics = new Set<number>();
  for (const pathway of DATASET_PATHWAYS) {
    if (producerMaterials.has(pathway.material_id)) {
      receiverNics.add(pathway.receiver_nic);
    }
  }
  if (!receiverNics.size) return [];

  const [oLat, oLon] = jitterCoords(origin.enterprise_id, origin.lat, origin.lon);

  return all.filter((candidate) => {
    if (candidate.enterprise_id === origin.enterprise_id) return false;
    const nic = nicFromSector(candidate.sector);
    if (nic == null || !receiverNics.has(nic)) return false;
    const [cLat, cLon] = jitterCoords(candidate.enterprise_id, candidate.lat, candidate.lon);
    return haversineKm(oLat, oLon, cLat, cLon) <= radiusKm;
  });
}

export function findCompatibleByDistrict(
  district: string,
  all: MapEnterprise[],
  radiusKm: number
): MapEnterprise[] {
  const inDistrict = all.filter((e) => e.district === district);
  if (!inDistrict.length) return [];

  const materials = new Set<string>();
  for (const e of inDistrict) {
    for (const bp of e.byproducts) materials.add(bp);
  }

  const receiverNics = new Set<number>();
  for (const pathway of DATASET_PATHWAYS) {
    if (materials.has(pathway.material_id)) receiverNics.add(pathway.receiver_nic);
  }
  if (!receiverNics.size) return [];

  const districtEnterprises = inDistrict;
  const avgLat = districtEnterprises.reduce((s, e) => s + e.lat, 0) / districtEnterprises.length;
  const avgLon = districtEnterprises.reduce((s, e) => s + e.lon, 0) / districtEnterprises.length;

  return all.filter((candidate) => {
    if (candidate.district === district) return false;
    const nic = nicFromSector(candidate.sector);
    if (nic == null || !receiverNics.has(nic)) return false;
    const [cLat, cLon] = jitterCoords(candidate.enterprise_id, candidate.lat, candidate.lon);
    return haversineKm(avgLat, avgLon, cLat, cLon) <= radiusKm;
  });
}

export function countUniqueDistricts(enterprises: MapEnterprise[]): number {
  return new Set(enterprises.map((e) => e.district)).size;
}
