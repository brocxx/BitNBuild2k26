"""Geospatial Symbiosis and Enterprise Directory Service.

Loads the 7,933 real Karnataka MSME enterprises from the UDYAM dataset,
indexes them by district and NIC division, and matches potential industrial
symbiosis trading partners based on road distance matrix and byproduct compatibility.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Find dataset directory relative to project root with fallbacks
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_POSSIBLE_DIRS = [
    _BACKEND_DIR.parent / "dataset",
    _BACKEND_DIR / "dataset",
    Path.cwd().parent / "dataset",
    Path.cwd() / "dataset",
]
_DATASET_DIR = next((d for d in _POSSIBLE_DIRS if d.exists()), _BACKEND_DIR.parent / "dataset")



@dataclass
class EnterpriseRecord:
    enterprise_id: str
    enterprise_name: str
    district: str
    lat: float
    lon: float
    pincode: str | None
    nic2_division: int
    nic_description: str
    communication_address: str | None


@dataclass
class SymbiosisPathway:
    producer_nic: int
    producer_industry: str
    byproduct_name: str
    byproduct_type: str
    receiver_nic: int
    receiver_industry: str
    use_case: str
    source_citation: str


class MapDataStore:
    """In-memory singleton store for MSME enterprises and symbiosis pathways."""

    _instance: MapDataStore | None = None

    def __init__(self) -> None:
        self.enterprises: list[EnterpriseRecord] = []
        self.enterprises_by_id: dict[str, EnterpriseRecord] = {}
        self.enterprises_by_district: dict[str, list[EnterpriseRecord]] = {}
        self.enterprises_by_nic: dict[int, list[EnterpriseRecord]] = {}
        self.distance_matrix: dict[tuple[str, str], float] = {}
        self.symbiosis_pathways: list[SymbiosisPathway] = []
        self._load_data()

    @classmethod
    def get_instance(cls) -> MapDataStore:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_data(self) -> None:
        try:
            # 1. Load enterprise names from 01_raw_msme_enterprises.csv
            raw_names: list[str] = []
            raw_file = _DATASET_DIR / "01_raw_msme_enterprises.csv"
            if raw_file.exists():
                with open(raw_file, encoding="utf-8-sig") as f:
                    for row in csv.DictReader(f):
                        name = row.get("EnterpriseName") or ""
                        raw_names.append(name.strip())

            # 2. Load enterprises with geo coordinates
            loc_file = _DATASET_DIR / "02_enterprises_with_location.csv"
            if loc_file.exists():
                with open(loc_file, encoding="utf-8") as f:
                    for i, row in enumerate(csv.DictReader(f)):
                        ent_id = row.get("enterprise_id", f"KA-ENT-{i+1:06d}")
                        name = (
                            raw_names[i]
                            if i < len(raw_names) and raw_names[i]
                            else row.get("enterprise_name", "").strip()
                        )
                        if not name:
                            addr = row.get("communication_address", "")
                            first_part = addr.split(",")[0].strip()
                            name = (
                                first_part
                                if (first_part and not first_part.isdigit())
                                else f"MSME Enterprise {ent_id}"
                            )

                        district = row.get("district", "BENGALURU (URBAN)").strip().upper()
                        lat = float(row.get("district_hq_lat") or 12.9716)
                        lon = float(row.get("district_hq_lon") or 77.5946)
                        pincode = (
                            row.get("pincode", "").replace(".0", "").strip()
                            if row.get("pincode")
                            else None
                        )
                        nic2 = int(row.get("nic2_division") or 10)
                        desc = row.get("nic_description", "").strip()
                        addr = row.get("communication_address", "").strip() or None

                        rec = EnterpriseRecord(
                            enterprise_id=ent_id,
                            enterprise_name=name,
                            district=district,
                            lat=lat,
                            lon=lon,
                            pincode=pincode,
                            nic2_division=nic2,
                            nic_description=desc,
                            communication_address=addr,
                        )
                        self.enterprises.append(rec)
                        self.enterprises_by_id[ent_id] = rec
                        self.enterprises_by_district.setdefault(district, []).append(rec)
                        self.enterprises_by_nic.setdefault(nic2, []).append(rec)

            # 3. Load distance matrix
            dist_file = _DATASET_DIR / "05_district_distance_matrix_km.csv"
            if dist_file.exists():
                with open(dist_file, encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        d_from = row.get("from_district", "").strip().upper()
                        d_to = row.get("to_district", "").strip().upper()
                        dist = float(row.get("distance_km_estimated") or 0.0)
                        self.distance_matrix[(d_from, d_to)] = dist

            # 4. Load symbiosis pairs
            sym_file = _DATASET_DIR / "04_industrial_symbiosis_pairs.csv"
            if sym_file.exists():
                with open(sym_file, encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        pathway = SymbiosisPathway(
                            producer_nic=int(row.get("producer_nic") or 10),
                            producer_industry=row.get("producer_industry", "").strip(),
                            byproduct_name=row.get("byproduct_name", "").strip(),
                            byproduct_type=row.get("byproduct_type", "").strip(),
                            receiver_nic=int(row.get("receiver_nic") or 23),
                            receiver_industry=row.get("receiver_industry", "").strip(),
                            use_case=row.get("use_case", "").strip(),
                            source_citation=row.get("source_citation", "").strip(),
                        )
                        self.symbiosis_pathways.append(pathway)

            logger.info(
                "Loaded %d MSME enterprises, %d pathways, %d distance pairs",
                len(self.enterprises),
                len(self.symbiosis_pathways),
                len(self.distance_matrix),
            )
        except Exception as exc:
            logger.error("Failed to load map dataset: %s", exc)

    def get_distance(self, district_a: str, district_b: str) -> float:
        da = district_a.strip().upper()
        db = district_b.strip().upper()
        if da == db:
            return 0.0
        dist = self.distance_matrix.get((da, db))
        if dist is not None:
            return dist
        dist_rev = self.distance_matrix.get((db, da))
        if dist_rev is not None:
            return dist_rev
        return 150.0  # Conservative Karnataka district average default


# ---------------------------------------------------------------------------
# Query Functions
# ---------------------------------------------------------------------------


DISTRICT_ALIASES = {
    "DAVANAGERE": "DAVANGERE",
    "BANGALORE": "BENGALURU (URBAN)",
    "BENGALURU": "BENGALURU (URBAN)",
    "BANGALORE URBAN": "BENGALURU (URBAN)",
    "BANGALORE RURAL": "BENGALURU (RURAL)",
    "MYSORE": "MYSURU",
    "BELLARY": "BALLARI",
    "BELGAUM": "BELAGAVI",
    "GULBARGA": "KALABURAGI",
    "BIJAPUR": "VIJAYAPURA",
    "SHIMOGA": "SHIVAMOGGA",
    "CHIKMAGALUR": "CHIKKAMAGALURU",
    "CHIKKABALLAPUR": "CHIKBALLAPUR",
    "TUMKUR": "TUMAKURU",
}


def normalize_district(name: str) -> str:
    cleaned = name.strip().upper()
    return DISTRICT_ALIASES.get(cleaned, cleaned)


def get_enterprises(
    district: str | None = None,
    nic2_division: int | None = None,
    limit: int = 1000,
) -> tuple[int, list[EnterpriseRecord]]:
    store = MapDataStore.get_instance()
    results = store.enterprises

    if district:
        d_norm = normalize_district(district)
        results = store.enterprises_by_district.get(d_norm, [])
    elif nic2_division:
        results = store.enterprises_by_nic.get(nic2_division, [])

    if nic2_division and district:
        results = [r for r in results if r.nic2_division == nic2_division]

    total = len(results)
    return total, results[:limit]


def find_symbiosis_matches(
    query_district: str,
    radius_km: float = 150.0,
    nic2_division: int | None = None,
    limit: int = 60,
) -> list[dict[str, Any]]:
    store = MapDataStore.get_instance()
    query_dist_clean = normalize_district(query_district)


    matches: list[dict[str, Any]] = []

    for pathway in store.symbiosis_pathways:
        # If nic2_division is specified, filter for pathways where this enterprise is producer or receiver
        if nic2_division is not None:
            if pathway.producer_nic != nic2_division and pathway.receiver_nic != nic2_division:
                continue

        # Look for target receiver candidates if querying from producer perspective
        receiver_enterprises = store.enterprises_by_nic.get(pathway.receiver_nic, [])
        for ent in receiver_enterprises:
            dist = store.get_distance(query_dist_clean, ent.district)
            if dist <= radius_km:
                matches.append(
                    {
                        "enterprise": ent,
                        "role": "receiver",
                        "byproduct_name": pathway.byproduct_name,
                        "byproduct_type": pathway.byproduct_type,
                        "use_case": pathway.use_case,
                        "distance_km": round(dist, 1),
                        "source_citation": pathway.source_citation,
                    }
                )

        # Look for producer candidates if querying from receiver perspective
        producer_enterprises = store.enterprises_by_nic.get(pathway.producer_nic, [])
        for ent in producer_enterprises:
            dist = store.get_distance(query_dist_clean, ent.district)
            if dist <= radius_km:
                matches.append(
                    {
                        "enterprise": ent,
                        "role": "producer",
                        "byproduct_name": pathway.byproduct_name,
                        "byproduct_type": pathway.byproduct_type,
                        "use_case": pathway.use_case,
                        "distance_km": round(dist, 1),
                        "source_citation": pathway.source_citation,
                    }
                )

    # Sort matches by distance
    matches.sort(key=lambda m: m["distance_km"])

    # Deduplicate by enterprise_id + byproduct_name to keep top diverse results
    seen = set()
    deduped = []
    for m in matches:
        key = (m["enterprise"].enterprise_id, m["byproduct_name"])
        if key not in seen:
            seen.add(key)
            deduped.append(m)
            if len(deduped) >= limit:
                break

    return deduped


def get_map_stats(active_trades: int = 0) -> dict[str, int]:
    store = MapDataStore.get_instance()
    return {
        "total_enterprises": len(store.enterprises),
        "total_districts": len(store.enterprises_by_district),
        "total_symbiosis_pathways": len(store.symbiosis_pathways),
        "active_trades": active_trades,
    }
