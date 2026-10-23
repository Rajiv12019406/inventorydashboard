"""Shared FastAPI dependencies."""

from __future__ import annotations

from functools import lru_cache

from app.data.provider import InventoryDataProvider, get_data_provider
from app.forecasting.engine import ForecastEngine, forecast_engine
from app.services.dashboard import InventoryAnalyticsService


@lru_cache
def get_provider() -> InventoryDataProvider:
    return get_data_provider()


def get_engine() -> ForecastEngine:
    return forecast_engine


def get_analytics() -> InventoryAnalyticsService:
    provider = get_provider()
    snapshot = provider.load_snapshot()
    return InventoryAnalyticsService(snapshot, get_engine())


def paginate(items: list, page: int, page_size: int) -> tuple[list, int, int]:
    total = len(items)
    pages = max(1, (total + page_size - 1) // page_size) if page_size else 1
    page = max(1, min(page, pages))
    start = (page - 1) * page_size
    return items[start : start + page_size], total, pages