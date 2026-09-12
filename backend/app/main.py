"""FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.errors import install_error_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # No negotiation may survive a restart in a pending state: a queued or
    # running row left behind by a crash is closed as INTERRUPTED rather than
    # silently resumed with side effects reapplied.
    from app.services.coordinator import recover_interrupted_runs

    try:
        recovered = recover_interrupted_runs()
        if recovered:
            logger.warning("Marked %s interrupted negotiation(s) as failed", recovered)
    except Exception:  # a fresh database with no tables yet
        logger.info("Skipped interrupted-run recovery (database not ready).")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Karnataka Industrial Byproduct Exchange",
        description=(
            "B2B exchange for secondary industrial materials. Prices are entered by "
            "participants; freight charges are entered or configured estimates. No "
            "market price feed, benchmark, or carrier booking is involved."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)
    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()
