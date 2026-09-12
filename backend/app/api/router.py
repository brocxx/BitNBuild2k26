"""Assembles /api/v1."""

from fastapi import APIRouter

from app.api.routes import catalog, deals, listings, negotiations, requirements

api_router = APIRouter()
api_router.include_router(catalog.router)
api_router.include_router(listings.router)
api_router.include_router(requirements.router)
api_router.include_router(negotiations.router)
api_router.include_router(deals.router)
