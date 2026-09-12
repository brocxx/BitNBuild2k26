"""Import dataset/*.csv into the reference tables.

Idempotent: it clears the reference tables and rebuilds them, so it can be
re-run after a dataset refresh. It never writes to the operational tables and
never modifies the source CSVs.

Everything it corrects is documented in app/data/fixes.py.
"""

from __future__ import annotations

import csv
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import DATASET_DIR
from app.data import fixes
from app.db import models

logger = logging.getLogger(__name__)

RAW_ENTERPRISES = "01_raw_msme_enterprises.csv"
ENTERPRISES = "02_enterprises_with_location.csv"
BYPRODUCTS = "03_byproducts_per_enterprise.csv"
PATHWAYS = "04_industrial_symbiosis_pairs.csv"
DISTANCES = "05_district_distance_matrix_km.csv"
DISTRICTS = "06_district_headquarters_coordinates.csv"


@dataclass
class ImportReport:
    districts: int = 0
    distances: int = 0
    materials: int = 0
    processes: int = 0
    enterprises: int = 0
    names_recovered: int = 0
    names_unresolved: int = 0
    byproducts_kept: int = 0
    byproducts_reclassified: int = 0
    pathways: int = 0
    compatibility_flags: int = 0
    reclassified_by_material: Counter = field(default_factory=Counter)

    def summary(self) -> str:
        lines = [
            f"districts           {self.districts}",
            f"district distances  {self.distances}",
            f"materials           {self.materials}",
            f"receiving processes {self.processes}",
            f"enterprises         {self.enterprises} "
            f"(names recovered {self.names_recovered}, unresolved {self.names_unresolved})",
            f"byproduct streams   {self.byproducts_kept} kept, "
            f"{self.byproducts_reclassified} dropped as misclassified",
            f"symbiosis pathways  {self.pathways}",
            f"compatibility flags {self.compatibility_flags}",
        ]
        if self.reclassified_by_material:
            lines.append("dropped byproduct rows by material:")
            for material, count in sorted(self.reclassified_by_material.items()):
                lines.append(f"  {material:<24} {count}")
        return "\n".join(lines)


def _read(path: Path, encoding: str = "utf-8") -> list[dict[str, str]]:
    with path.open(newline="", encoding=encoding) as handle:
        return list(csv.DictReader(handle))


def _to_int_metres(km: str) -> int:
    try:
        return int(round(float(km) * 1000))
    except (TypeError, ValueError):
        return 0


def _to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Fix 1: enterprise name recovery
# ---------------------------------------------------------------------------


def build_name_index(dataset_dir: Path) -> dict[str, str]:
    """Map communication address -> registered name, from the raw registry.

    The raw file is BOM-prefixed, hence utf-8-sig. Addresses are unique enough
    to recover 7,932 of 7,933 names; an address that maps to more than one
    distinct name is dropped rather than guessed at.
    """
    rows = _read(dataset_dir / RAW_ENTERPRISES, encoding="utf-8-sig")
    candidates: dict[str, set[str]] = {}
    for row in rows:
        address = (row.get("CommunicationAddress") or "").strip()
        name = (row.get("EnterpriseName") or "").strip()
        if address and name:
            candidates.setdefault(address, set()).add(name)
    return {address: next(iter(names)) for address, names in candidates.items() if len(names) == 1}


# ---------------------------------------------------------------------------
# Import steps
# ---------------------------------------------------------------------------


def _clear_reference_tables(db: Session) -> None:
    for model in (
        models.MaterialCompatibilityFlag,
        models.SymbiosisPathway,
        models.EnterpriseByproduct,
        models.ReceivingProcessMaterial,
        models.DistrictDistance,
        models.District,
    ):
        db.execute(delete(model))
    db.flush()


def _import_materials_and_processes(db: Session, report: ImportReport) -> None:
    existing_materials = set(db.scalars(select(models.Material.id)))
    for material_id, (name, category, supported) in fixes.MATERIALS.items():
        if material_id in existing_materials:
            continue
        db.add(
            models.Material(
                id=material_id, name=name, category=category, is_supported=supported
            )
        )
        report.materials += 1
    db.flush()

    existing_aliases = set(db.scalars(select(models.MaterialAlias.alias)))
    for alias, material_id in fixes.MATERIAL_ALIASES.items():
        if alias not in existing_aliases:
            db.add(models.MaterialAlias(alias=alias, material_id=material_id))
    db.flush()

    existing_processes = set(db.scalars(select(models.ReceivingProcess.id)))
    for process_id, (name, description, nic5_codes) in fixes.RECEIVING_PROCESSES.items():
        if process_id not in existing_processes:
            db.add(
                models.ReceivingProcess(
                    id=process_id,
                    name=name,
                    description=description,
                    nic5_codes=",".join(sorted(nic5_codes)),
                )
            )
            report.processes += 1
    db.flush()

    for process_id, material_ids in fixes.PROCESS_MATERIALS.items():
        for material_id in material_ids:
            db.add(
                models.ReceivingProcessMaterial(
                    process_id=process_id, material_id=material_id
                )
            )
    db.flush()


def _import_districts(db: Session, dataset_dir: Path, report: ImportReport) -> None:
    for row in _read(dataset_dir / DISTRICTS):
        db.add(
            models.District(
                name=row["district"].strip(),
                hq_town=row.get("hq_town", "").strip(),
                lat=_to_float(row["lat"]),
                lon=_to_float(row["lon"]),
                source=row.get("source", ""),
            )
        )
        report.districts += 1
    db.flush()

    for row in _read(dataset_dir / DISTANCES):
        db.add(
            models.DistrictDistance(
                from_district=row["from_district"].strip(),
                to_district=row["to_district"].strip(),
                # Fix 5: straight-line km -> integer metres, basis recorded.
                distance_m=_to_int_metres(row["distance_km_estimated"]),
                basis="district_straight_line",
            )
        )
        report.distances += 1
    db.flush()


def _import_enterprises(db: Session, dataset_dir: Path, report: ImportReport) -> None:
    names = build_name_index(dataset_dir)
    existing = set(db.scalars(select(models.Enterprise.id)))

    for row in _read(dataset_dir / ENTERPRISES):
        enterprise_id = row["enterprise_id"].strip()
        if enterprise_id in existing:
            continue

        address = (row.get("communication_address") or "").strip()
        raw_name = (row.get("enterprise_name") or "").strip()
        recovered = raw_name or names.get(address, "")

        if recovered:
            report.names_recovered += 1
            name, name_source = recovered, "udyam"
        else:
            report.names_unresolved += 1
            # No invented name. The ID is what we can honestly display.
            name, name_source = f"Unnamed MSME ({enterprise_id})", "unresolved"

        db.add(
            models.Enterprise(
                id=enterprise_id,
                name=name,
                name_source=name_source,
                district=row["district"].strip(),
                lat=_to_float(row.get("district_hq_lat", ""), 0.0) or None,
                lon=_to_float(row.get("district_hq_lon", ""), 0.0) or None,
                pincode=(row.get("pincode") or "").strip(),
                nic5_code=(row.get("nic5_code") or "").strip(),
                nic2_division=(row.get("nic2_division") or "").strip(),
                nic_description=(row.get("nic_description") or "").strip(),
                registration_date=(row.get("registration_date") or "").strip(),
                address=address,
            )
        )
        report.enterprises += 1
    db.flush()


def _import_byproducts(db: Session, dataset_dir: Path, report: ImportReport) -> None:
    """Fixes 2 and 3: keep a byproduct only where the NIC5 code supports it."""
    nic5_by_enterprise = dict(
        db.execute(select(models.Enterprise.id, models.Enterprise.nic5_code)).all()
    )

    for row in _read(dataset_dir / BYPRODUCTS):
        enterprise_id = row["enterprise_id"].strip()
        byproduct_name = row["byproduct_name"].strip()
        material_id = fixes.resolve_material(byproduct_name)

        allowed = fixes.PRODUCER_NIC5.get(material_id or "")
        if allowed is not None and nic5_by_enterprise.get(enterprise_id) not in allowed:
            report.byproducts_reclassified += 1
            report.reclassified_by_material[material_id or byproduct_name] += 1
            continue

        db.add(
            models.EnterpriseByproduct(
                enterprise_id=enterprise_id,
                material_id=material_id,
                byproduct_name=byproduct_name,
                waste_ratio_pct=_to_float(row.get("waste_ratio_pct", "")),
                # Inferred annual generation. Never treated as sellable stock.
                annual_tonnes_estimated=_to_float(
                    row.get("qty_annual_tonnes_estimated", "")
                ),
                is_estimate=True,
                source_citation=row.get("source_citation", ""),
            )
        )
        report.byproducts_kept += 1
    db.flush()


def _import_pathways(db: Session, dataset_dir: Path, report: ImportReport) -> None:
    for row in _read(dataset_dir / PATHWAYS):
        material_id = fixes.resolve_material(row["byproduct_name"])
        producer_nic = row["producer_nic"].strip()
        receiver_nic = row["receiver_nic"].strip()
        process_id = fixes.PATHWAY_PROCESS.get(
            (producer_nic, material_id or "", receiver_nic)
        )
        db.add(
            models.SymbiosisPathway(
                producer_nic2=producer_nic,
                producer_industry=row.get("producer_industry", ""),
                material_id=material_id,
                byproduct_name=row["byproduct_name"].strip(),
                byproduct_type=row.get("byproduct_type", ""),
                receiver_nic2=receiver_nic,
                receiver_industry=row.get("receiver_industry", ""),
                use_case=row.get("use_case", ""),
                source_citation=row.get("source_citation", ""),
                receiving_process_id=process_id,
            )
        )
        report.pathways += 1
    db.flush()


def _import_compatibility_flags(db: Session, report: ImportReport) -> None:
    for material_id, process_id, keyword, verdict, note in fixes.COMPATIBILITY_FLAGS:
        db.add(
            models.MaterialCompatibilityFlag(
                material_id=material_id,
                receiving_process_id=process_id,
                contamination_keyword=keyword,
                verdict=verdict,
                note=note,
            )
        )
        report.compatibility_flags += 1
    db.flush()


def import_reference_data(db: Session, dataset_dir: Path | None = None) -> ImportReport:
    dataset_dir = dataset_dir or DATASET_DIR
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    report = ImportReport()
    _clear_reference_tables(db)
    _import_materials_and_processes(db, report)
    _import_districts(db, dataset_dir, report)
    _import_enterprises(db, dataset_dir, report)
    _import_byproducts(db, dataset_dir, report)
    _import_pathways(db, dataset_dir, report)
    _import_compatibility_flags(db, report)
    db.commit()
    return report
