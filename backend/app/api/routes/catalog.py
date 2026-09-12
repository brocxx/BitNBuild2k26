"""Health, identity and reference data."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api import schemas
from app.db import models
from app.deps import CurrentUserDep, DbDep
from app.services.serializers import to_business

router = APIRouter()


@router.get("/health", response_model=schemas.HealthResponse, tags=["health"])
def health() -> schemas.HealthResponse:
    """Liveness only. Deliberately exposes nothing about dependencies."""
    return schemas.HealthResponse(status="ok")


@router.get("/me", response_model=schemas.MeResponse, tags=["identity"])
def me(current: CurrentUserDep) -> schemas.MeResponse:
    return schemas.MeResponse(
        user_id=current.user.id, business=to_business(current.business)
    )


@router.get("/reference", response_model=schemas.ReferenceResponse, tags=["reference"])
def reference(db: DbDep, current: CurrentUserDep) -> schemas.ReferenceResponse:
    materials = list(db.scalars(select(models.Material).order_by(models.Material.name)))
    districts = list(db.scalars(select(models.District).order_by(models.District.name)))
    processes = list(
        db.scalars(select(models.ReceivingProcess).order_by(models.ReceivingProcess.name))
    )

    materials_by_process: dict[str, list[str]] = {}
    for link in db.scalars(select(models.ReceivingProcessMaterial)):
        materials_by_process.setdefault(link.process_id, []).append(link.material_id)

    return schemas.ReferenceResponse(
        materials=[schemas.MaterialRef(id=m.id, name=m.name) for m in materials],
        districts=[
            schemas.DistrictRef(name=d.name, lat=d.lat, lon=d.lon) for d in districts
        ],
        receiving_processes=[
            schemas.ReceivingProcessRef(
                id=p.id,
                name=p.name,
                material_ids=sorted(materials_by_process.get(p.id, [])),
            )
            for p in processes
        ],
    )
