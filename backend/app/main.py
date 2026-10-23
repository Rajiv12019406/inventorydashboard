"""MediStock Intelligence FastAPI application."""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_engine, get_provider
from app.api.routes import router
from app.core.config import settings


def _warm_forecasts_async() -> None:
    """Load synthetic data immediately; generate forecasts in a background thread."""
    provider = get_provider()
    snapshot = provider.load_snapshot()
    engine = get_engine()

    def _run() -> None:
        engine.ensure_forecasts(snapshot, horizons=[7, 14])

    thread = threading.Thread(target=_run, name="forecast-warmup", daemon=True)
    thread.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dataset loads synchronously; forecast pipeline runs in background so /health is available immediately
    _warm_forecasts_async()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Hospital Inventory Forecasting & Risk Analytics API. "
        "DEMO MODE — synthetic data only. No SQL Server connection."
    ),
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "mode": "DEMO · SYNTHETIC DATA",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/system/health",
    }