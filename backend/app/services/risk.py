"""Stockout, expiry, and reorder risk calculations.

Projected stock formula
-----------------------
projected_stock[t] = current_usable_stock
                   + sum(incoming receipts with expected_date <= t)
                   - sum(forecasted demand from day 1..t)

Days of cover = largest t such that projected_stock[t] > 0, else 0.
Stockout date = first date where projected_stock <= 0, if any within horizon.

Reorder suggestion (target-stock policy)
----------------------------------------
target_stock = forecast_demand_during_lead_time + safety_stock
projected_position_at_lead = projected_stock[lead_time]
suggested_qty = max(0, ceil(target_stock - projected_position_at_lead - incoming_beyond_lead?))

If lead_time > forecast_horizon, we do NOT silently extrapolate; the limitation
is surfaced and suggested_qty uses only the available horizon with a clear note.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from app.core.config import settings
from app.data.models import BatchLot, IncomingReceipt, InventoryItem, StockBalance
from app.forecasting.engine import ForecastResult

RiskLevel = Literal["critical", "high", "medium", "low"]
ExpiryRisk = Literal["expired", "critical", "high", "medium", "low"]


@dataclass
class ProjectedStockDay:
    date: date
    opening: float
    forecast_demand: float
    incoming: float
    closing: float


@dataclass
class StockoutAssessment:
    item_id: str
    store_id: str
    current_usable_stock: float
    avg_daily_consumption: float
    days_of_cover: float | None
    predicted_stockout_date: date | None
    expected_incoming: float
    supplier_lead_time_days: int
    risk_level: RiskLevel
    explanation: str
    projection: list[ProjectedStockDay]
    data_quality: str


@dataclass
class ExpiryAssessment:
    batch_id: str
    item_id: str
    store_id: str
    available_qty: float
    expiry_date: date
    days_until_expiry: int
    risk_status: ExpiryRisk
    fefo_note: str


@dataclass
class ReorderRecommendation:
    item_id: str
    store_id: str
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


def classify_stockout_risk(days_until: int | None, horizon: int) -> RiskLevel:
    if days_until is None:
        return "low"
    if days_until <= settings.stockout_critical_days:
        return "critical"
    if days_until <= settings.stockout_high_days:
        return "high"
    if days_until <= settings.stockout_medium_days:
        return "medium"
    if days_until <= horizon:
        return "medium"
    return "low"


def project_stock(
    current_stock: float,
    forecast: ForecastResult,
    incoming: list[IncomingReceipt],
    as_of: date,
) -> list[ProjectedStockDay]:
    receipts_by_date: dict[date, float] = {}
    for r in incoming:
        if r.expected_date > as_of:
            receipts_by_date[r.expected_date] = receipts_by_date.get(r.expected_date, 0.0) + r.expected_qty

    stock = current_stock
    projection: list[ProjectedStockDay] = []
    for pt in forecast.points:
        inc = receipts_by_date.get(pt.date, 0.0)
        opening = stock + inc
        closing = opening - pt.predicted
        projection.append(
            ProjectedStockDay(
                date=pt.date,
                opening=round(opening, 1),
                forecast_demand=pt.predicted,
                incoming=inc,
                closing=round(closing, 1),
            )
        )
        stock = closing
    return projection


def assess_stockout(
    item: InventoryItem,
    balance: StockBalance,
    forecast: ForecastResult,
    incoming: list[IncomingReceipt],
    avg_daily: float,
) -> StockoutAssessment:
    as_of = balance.as_of_date
    pair_incoming = [r for r in incoming if r.item_id == item.item_id and r.store_id == balance.store_id]
    projection = project_stock(balance.usable_qty, forecast, pair_incoming, as_of)

    stockout_date: date | None = None
    days_until: int | None = None
    for i, day in enumerate(projection):
        if day.closing <= 0:
            stockout_date = day.date
            days_until = i + 1
            break

    # Days of cover from avg daily if no stockout in horizon
    if avg_daily > 0:
        cover = balance.usable_qty / avg_daily
    else:
        cover = None

    if stockout_date is not None:
        # Prefer projection-based cover
        cover = float(days_until) if days_until is not None else cover

    risk = classify_stockout_risk(days_until, forecast.horizon_days)
    expected_incoming = sum(r.expected_qty for r in pair_incoming if r.expected_date <= as_of + timedelta(days=forecast.horizon_days))

    if forecast.data_quality == "insufficient_history":
        explanation = (
            "History is insufficient for a reliable stockout date. "
            "Risk is estimated from current stock and limited recent demand only."
        )
    elif stockout_date is None:
        explanation = (
            f"Projected stock remains positive across the {forecast.horizon_days}-day forecast horizon "
            f"after accounting for {expected_incoming:.0f} units of expected incoming stock."
        )
    else:
        explanation = (
            f"At current usable stock of {balance.usable_qty:.0f} and forecast demand "
            f"({sum(p.predicted for p in forecast.points):.0f} over {forecast.horizon_days}d), "
            f"stock is projected to reach zero on {stockout_date.isoformat()} "
            f"(model: {forecast.model_id})."
        )

    return StockoutAssessment(
        item_id=item.item_id,
        store_id=balance.store_id,
        current_usable_stock=balance.usable_qty,
        avg_daily_consumption=round(avg_daily, 2),
        days_of_cover=round(cover, 1) if cover is not None else None,
        predicted_stockout_date=stockout_date,
        expected_incoming=round(expected_incoming, 1),
        supplier_lead_time_days=item.supplier_lead_time_days,
        risk_level=risk,
        explanation=explanation,
        projection=projection,
        data_quality=forecast.data_quality,
    )


def assess_expiry(batch: BatchLot, as_of: date) -> ExpiryAssessment:
    days = (batch.expiry_date - as_of).days
    if days < 0:
        status: ExpiryRisk = "expired"
        note = "Expired — do not issue. Quarantine / dispose per policy. Never recommend issuing expired stock."
    elif days <= settings.expiry_high_days:
        status = "critical"
        note = "FEFO: prioritize issuance immediately; verify clinical suitability before expiry."
    elif days <= settings.expiry_medium_days:
        status = "high"
        note = "FEFO: schedule usage within the next month; avoid new bulk receipts of the same SKU if possible."
    elif days <= settings.expiry_low_days:
        status = "medium"
        note = "FEFO: issue ahead of longer-dated batches."
    else:
        status = "low"
        note = "Healthy dating — maintain FEFO rotation."

    return ExpiryAssessment(
        batch_id=batch.batch_id,
        item_id=batch.item_id,
        store_id=batch.store_id,
        available_qty=batch.available_qty,
        expiry_date=batch.expiry_date,
        days_until_expiry=days,
        risk_status=status,
        fefo_note=note,
    )


def recommend_reorder(
    item: InventoryItem,
    balance: StockBalance,
    forecast: ForecastResult,
    incoming: list[IncomingReceipt],
    avg_daily: float,
) -> ReorderRecommendation | None:
    """Return a reorder recommendation when projected position falls below target policy."""
    lead = item.supplier_lead_time_days
    horizon = forecast.horizon_days
    as_of = balance.as_of_date
    pair_incoming = [r for r in incoming if r.item_id == item.item_id and r.store_id == balance.store_id]
    projection = project_stock(balance.usable_qty, forecast, pair_incoming, as_of)

    horizon_limitation = lead > horizon
    effective_lead = min(lead, horizon)

    # Demand during lead time from forecast points
    lead_points = forecast.points[:effective_lead]
    forecast_demand_lt = float(sum(p.predicted for p in lead_points))
    if horizon_limitation and avg_daily > 0:
        # Do NOT silently extrapolate — note limitation; use available horizon demand only
        pass

    incoming_within_lead = sum(
        r.expected_qty for r in pair_incoming if as_of < r.expected_date <= as_of + timedelta(days=effective_lead)
    )

    # Projected stock at lead time (closing of day effective_lead)
    projected_at_lead: float | None = None
    if projection and effective_lead <= len(projection):
        projected_at_lead = projection[effective_lead - 1].closing
    else:
        projected_at_lead = balance.usable_qty + incoming_within_lead - forecast_demand_lt

    safety = item.safety_stock
    target = forecast_demand_lt + safety
    suggested = max(0.0, math.ceil(target - (projected_at_lead or 0.0)))

    steps = [
        f"1. Lead time = {lead} day(s)"
        + (f" (capped to forecast horizon {horizon}d — limitation)" if horizon_limitation else ""),
        f"2. Forecast demand during lead window = {forecast_demand_lt:.1f} (sum of daily predictions)",
        f"3. Safety stock assumption = {safety:.1f}",
        f"4. Target stock = forecast_demand_lt + safety_stock = {target:.1f}",
        f"5. Incoming within lead window = {incoming_within_lead:.1f}",
        f"6. Projected stock at lead = {projected_at_lead:.1f}" if projected_at_lead is not None else "6. Projected stock unavailable",
        f"7. Suggested reorder qty = max(0, ceil(target − projected)) = {suggested:.0f}",
    ]

    # Only recommend when action is needed
    needs_reorder = suggested > 0 and (
        (projected_at_lead is not None and projected_at_lead < target)
        or balance.usable_qty <= item.min_stock
    )
    if not needs_reorder:
        return None

    cover = None
    if avg_daily > 0:
        cover = (balance.usable_qty + suggested) / avg_daily

    reason = (
        f"Projected position at lead time ({projected_at_lead:.0f}) is below target stock ({target:.0f}) "
        f"based on {forecast.model_id} demand forecast and safety stock of {safety:.0f}."
    )
    if horizon_limitation:
        reason += f" Lead time exceeds {horizon}-day forecast; suggestion uses available horizon only."

    return ReorderRecommendation(
        item_id=item.item_id,
        store_id=balance.store_id,
        current_usable_stock=balance.usable_qty,
        forecast_demand_lead_time=round(forecast_demand_lt, 1),
        incoming_qty=round(incoming_within_lead, 1),
        safety_stock=safety,
        projected_stock_at_lead=round(projected_at_lead, 1) if projected_at_lead is not None else None,
        suggested_reorder_qty=float(suggested),
        estimated_days_of_cover=round(cover, 1) if cover is not None else None,
        reason=reason,
        data_quality=forecast.data_quality,
        calculation_steps=steps,
        lead_time_days=lead,
        horizon_limitation=horizon_limitation,
    )