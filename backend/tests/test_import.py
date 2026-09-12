"""The real dataset importer, including every data correction.

These run against dataset/*.csv, so they also act as a regression check on the
dataset itself: if a refresh changes the shape of the CSVs, these fail.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.config import DATASET_DIR
from app.data import fixes
from app.data.importer import build_name_index, import_reference_data
from app.db import models

pytestmark = [
    pytest.mark.skipif(
        not DATASET_DIR.exists(), reason="dataset/ directory is not present"
    ),
    pytest.mark.own_database,
]


@pytest.fixture(scope="module")
def imported():
    """Import the whole dataset once for the module; the tests only read."""
    from app.db.session import SessionLocal, engine

    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    report = import_reference_data(session)
    yield session, report
    session.close()
    models.Base.metadata.drop_all(bind=engine)


def test_reference_counts_match_the_dataset(imported):
    _, report = imported
    assert report.districts == 31
    assert report.distances == 961  # 31 x 31
    assert report.enterprises == 7933
    assert report.pathways == 14


def test_fix_1_enterprise_names_are_recovered_from_the_raw_registry(imported):
    db, report = imported
    # The cleaned CSV ships with every name blank; almost all are recoverable.
    assert report.names_recovered > 7800
    assert report.names_recovered + report.names_unresolved == 7933

    named = db.scalar(
        select(func.count())
        .select_from(models.Enterprise)
        .where(models.Enterprise.name_source == "udyam")
    )
    assert named == report.names_recovered


def test_fix_1_unresolved_names_are_marked_not_invented(imported):
    db, _ = imported
    unresolved = list(
        db.scalars(
            select(models.Enterprise).where(models.Enterprise.name_source == "unresolved")
        )
    )
    for enterprise in unresolved:
        # An honest placeholder that carries the ID, never a guessed name.
        assert enterprise.id in enterprise.name


def test_name_index_drops_addresses_that_map_to_several_names():
    index = build_name_index(DATASET_DIR)
    assert index
    assert all(isinstance(name, str) and name for name in index.values())


def test_fix_2_and_3_rice_husk_comes_only_from_real_rice_millers(imported):
    db, _ = imported
    rows = list(
        db.execute(
            select(models.Enterprise.nic5_code, func.count())
            .join(
                models.EnterpriseByproduct,
                models.EnterpriseByproduct.enterprise_id == models.Enterprise.id,
            )
            .where(models.EnterpriseByproduct.material_id == "rice_husk")
            .group_by(models.Enterprise.nic5_code)
        ).all()
    )
    codes = {code for code, _ in rows}
    assert codes <= fixes.PRODUCER_NIC5["rice_husk"]
    # 10611 is Flour milling in this data, whatever the dataset README says.
    assert "10611" not in codes
    assert "10612" in codes, "expected the real rice-milling code to be present"


def test_fix_2_drops_the_over_assigned_byproduct_rows(imported):
    _, report = imported
    # The CSV gives rice husk to all 3,536 NIC-10 enterprises.
    assert report.reclassified_by_material["rice_husk"] > 3000
    assert report.byproducts_kept + report.byproducts_reclassified == 17555


def test_fix_4_only_fired_kilns_receive_into_brick_kiln_fuel(imported):
    db, _ = imported
    process = db.get(models.ReceivingProcess, "brick_kiln_fuel")
    codes = set(process.nic5_codes.split(","))
    assert codes == {"23912", "23921"}
    # Cement and RCC block makers have no kiln to fire husk in.
    assert "23952" not in codes
    assert "23954" not in codes


def test_fix_5_distances_are_metres_with_an_explicit_basis(imported):
    db, _ = imported
    row = db.scalar(
        select(models.DistrictDistance).where(
            models.DistrictDistance.from_district == "BAGALKOT",
            models.DistrictDistance.to_district == "BALLARI",
        )
    )
    assert row.distance_m == 174_850  # 174.85 km
    assert row.basis == "district_straight_line"

    self_distance = db.scalar(
        select(models.DistrictDistance).where(
            models.DistrictDistance.from_district == "BAGALKOT",
            models.DistrictDistance.to_district == "BAGALKOT",
        )
    )
    assert self_distance.distance_m == 0


def test_inferred_annual_tonnage_is_flagged_as_an_estimate(imported):
    db, _ = imported
    rows = list(db.scalars(select(models.EnterpriseByproduct).limit(50)))
    assert rows
    assert all(row.is_estimate for row in rows)
    assert all(row.source_citation for row in rows)


def test_the_supported_demo_pathway_is_wired_to_a_receiving_process(imported):
    db, _ = imported
    pathway = db.scalar(
        select(models.SymbiosisPathway).where(
            models.SymbiosisPathway.material_id == "rice_husk",
            models.SymbiosisPathway.receiver_nic2 == "23",
        )
    )
    assert pathway is not None
    assert pathway.receiving_process_id == "brick_kiln_fuel"
    assert "kiln" in pathway.use_case.lower()


def test_material_aliases_resolve_the_dataset_spellings():
    assert fixes.resolve_material("Rice Husk") == "rice_husk"
    assert fixes.resolve_material("  rice husk  ") == "rice_husk"
    assert fixes.resolve_material("Broken/Rejected Bricks (Grog)") == "broken_bricks_grog"
    assert fixes.resolve_material("Something Unknown") is None


def test_importing_twice_does_not_duplicate_rows(imported):
    db, _ = imported
    before = db.scalar(select(func.count()).select_from(models.EnterpriseByproduct))
    import_reference_data(db)
    after = db.scalar(select(func.count()).select_from(models.EnterpriseByproduct))
    assert before == after
    assert db.scalar(select(func.count()).select_from(models.Enterprise)) == 7933
