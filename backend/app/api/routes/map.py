"""Geospatial Map and Symbiosis Discovery Routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api import schemas
from app.db import models
from app.deps import CurrentUserDep, DbDep
from app.services import map_service

router = APIRouter(tags=["map"])


@router.get("/map/enterprises", response_model=schemas.EnterprisesResponse)
def list_map_enterprises(
    current: CurrentUserDep,
    district: str | None = None,
    nic2_division: Annotated[int | None, Query(ge=1, le=99)] = None,
    limit: Annotated[int, Query(ge=1, le=8000)] = 2000,
) -> schemas.EnterprisesResponse:
    total, items = map_service.get_enterprises(
        district=district, nic2_division=nic2_division, limit=limit
    )
    return schemas.EnterprisesResponse(
        total=total,
        count=len(items),
        items=[
            schemas.EnterpriseMapItem(
                enterprise_id=e.enterprise_id,
                enterprise_name=e.enterprise_name,
                district=e.district,
                lat=e.lat,
                lon=e.lon,
                pincode=e.pincode,
                nic2_division=e.nic2_division,
                nic_description=e.nic_description,
                communication_address=e.communication_address,
            )
            for e in items
        ],
    )


@router.get("/map/symbiosis", response_model=schemas.SymbiosisResponse)
def discover_symbiosis(
    current: CurrentUserDep,
    district: str = "DAVANGERE",
    radius_km: Annotated[float, Query(ge=1.0, le=1000.0)] = 150.0,
    nic2_division: Annotated[int | None, Query(ge=1, le=99)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 60,
) -> schemas.SymbiosisResponse:
    raw_matches = map_service.find_symbiosis_matches(
        query_district=district,
        radius_km=radius_km,
        nic2_division=nic2_division,
        limit=limit,
    )
    matches = [
        schemas.SymbiosisMatch(
            enterprise=schemas.EnterpriseMapItem(
                enterprise_id=m["enterprise"].enterprise_id,
                enterprise_name=m["enterprise"].enterprise_name,
                district=m["enterprise"].district,
                lat=m["enterprise"].lat,
                lon=m["enterprise"].lon,
                pincode=m["enterprise"].pincode,
                nic2_division=m["enterprise"].nic2_division,
                nic_description=m["enterprise"].nic_description,
                communication_address=m["enterprise"].communication_address,
            ),
            role=m["role"],
            byproduct_name=m["byproduct_name"],
            byproduct_type=m["byproduct_type"],
            use_case=m["use_case"],
            distance_km=m["distance_km"],
            source_citation=m["source_citation"],
        )
        for m in raw_matches
    ]
    return schemas.SymbiosisResponse(
        query_district=map_service.normalize_district(district),
        radius_km=radius_km,
        total_matches=len(matches),
        matches=matches,
    )


@router.get("/map/stats", response_model=schemas.MapStatsResponse)
def map_stats(db: DbDep, current: CurrentUserDep) -> schemas.MapStatsResponse:
    # Query count of active deals in DB
    deal_count_stmt = select(func.count(models.Deal.id)).where(
        models.Deal.status.in_(["agreed", "pickup_scheduled", "collected", "delivered"])
    )
    active_deals = db.scalar(deal_count_stmt) or 0
    stats = map_service.get_map_stats(active_trades=active_deals)
    return schemas.MapStatsResponse(**stats)
