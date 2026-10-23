from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class StoreOut(BaseModel):
    store_id: str
    name: str
    location: str


class CategoryOut(BaseModel):
    category_id: str
    name: str


class ItemOut(BaseModel):
    item_id: str
    item_code: str
    name: str
    category_id: str
    category_name: str
    unit: str
    min_stock: float
    safety_stock: float
    supplier_lead_time_days: int
    demand_pattern: str


class ItemDetailOut(ItemOut):
    store_id: str
    store_name: str
    current_stock: float
    avg_daily_consumption: float
    days_of_cover: float | None = None


class ForecastPointOut(BaseModel):
    date: str
    predicted: float
    lower: float | None = None
    upper: float | None = None


class ForecastOut(BaseModel):
    item_id: str
    store_id: str
    horizon_days: int
    model_id: str
    generated_at: str
    data_through: str
    data_quality: str
    points: list[ForecastPointOut]
    limitations: list[str] = Field(default_factory=list)
    mae: float | None = None
    wape: float | None = None
    bias: float | None = None


class ForecastDetailOut(ForecastOut):
    item_code: str
    item_name: str
    store_name: str
    category_name: str
    current_stock: float
    avg_daily_consumption: float
    recent_trend: str
    forecast_total: float
    estimated_days_of_cover: float | None = None
    expected_stockout_date: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


class StockoutRiskOut(BaseModel):
    item_id: str
    item_code: str
    item_name: str
    store_id: str
    store_name: str
    category_name: str
    current_usable_stock: float
    avg_daily_consumption: float
    days_of_cover: float | None
    predicted_stockout_date: str | None
    expected_incoming_stock: float
    supplier_lead_time_days: int
    risk_level: Literal["critical", "high", "medium", "low"]
    explanation: str
    data_quality: str


class ExpiryRiskOut(BaseModel):
    batch_id: str
    item_id: str
    item_code: str
    item_name: str
    store_id: str
    store_name: str
    category_name: str
    available_qty: float
    expiry_date: str
    days_until_expiry: int
    risk_status: Literal["expired", "critical", "high", "medium", "low"]
    fefo_note: str


class ReorderRecommendationOut(BaseModel):
    item_id: str
    item_code: str
    item_name: str
    store_id: str
    store_name: str
    category_name: str
    current_usable_stock: float
    forecast_demand_lead_time: float
    incoming_qty: float
    safety_stock: float
    projected_stock_at_lead: float | None
    suggested_reorder_qty: float
    estimated_days_of_cover: float | None
    reason: str
    data_quality: str
    calculation_steps: list[str]
    lead_time_days: int
    horizon_limitation: bool


class DashboardSummaryOut(BaseModel):
    active_items: int
    low_stock_items: int
    low_stock_delta_pct: float | None = None
    stockout_risk_7d: int
    stockout_risk_14d: int
    approaching_expiry: int
    expired_qty: float
    reorder_required: int
    forecasted_demand: float
    risk_distribution: dict[str, int]
    as_of_date: str
    forecast_generated_at: str | None
    provider: str


class PriorityActionOut(BaseModel):
    item_id: str
    item_code: str
    item_name: str
    category_id: str
    category_name: str
    store_id: str
    store_name: str
    current_stock: float
    days_of_cover: float | None
    predicted_stockout_date: str | None
    suggested_reorder_qty: float
    risk_status: str


class TrendsOut(BaseModel):
    aggregation: str
    history_end: str
    actual: list[dict[str, Any]]
    forecast: list[dict[str, Any]]


class HealthOut(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    app: str
    version: str
    provider: str
    provider_ready: bool
    forecast_job: dict[str, Any]
    dataset: dict[str, Any]
    checks: list[dict[str, Any]]


class ForecastRefreshOut(BaseModel):
    status: str
    started_at: str | None
    finished_at: str | None
    duration_seconds: float | None
    forecasts_generated: int
    error: str | None = None
    last_run_at: str | None = None


class ExpirySummaryOut(BaseModel):
    expired_qty: float
    expired_batches: int
    within_7_days_qty: float
    within_7_days_batches: int
    within_30_days_qty: float
    within_30_days_batches: int
    within_90_days_qty: float
    within_90_days_batches: int
    by_category: list[dict[str, Any]]