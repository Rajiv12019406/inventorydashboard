"""MediStock Intelligence API routes."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from app.api.deps import get_analytics, get_engine, get_provider, paginate
from app.core.config import settings
from app.schemas.common import FilterOptions, PaginatedResponse
from app.schemas.inventory import (
    CategoryOut,
    DashboardSummaryOut,
    ExpiryRiskOut,
    ExpirySummaryOut,
    ForecastDetailOut,
    ForecastOut,
    ForecastPointOut,
    ForecastRefreshOut,
    HealthOut,
    ItemOut,
    PriorityActionOut,
    ReorderRecommendationOut,
    StockoutRiskOut,
    StoreOut,
    TrendsOut,
)

router = APIRouter()


def _iso(dt: Any) -> str | None:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


@router.get("/system/health", response_model=HealthOut)
def system_health() -> HealthOut:
    provider = get_provider()
    engine = get_engine()
    checks: list[dict[str, Any]] = []
    status: Literal["healthy", "degraded", "unhealthy"] = "healthy"

    try:
        snapshot = provider.load_snapshot()
        checks.append({"name": "data_provider", "status": "ok", "detail": provider.provider_name()})
        provider_ready = True
    except Exception as exc:  # noqa: BLE001
        checks.append({"name": "data_provider", "status": "error", "detail": str(exc)})
        provider_ready = False
        status = "unhealthy"
        snapshot = None

    job = engine.job_status
    if job.status == "failed":
        status = "degraded" if status == "healthy" else status
        checks.append({"name": "forecast_job", "status": "error", "detail": job.error or "failed"})
    else:
        checks.append({"name": "forecast_job", "status": "ok", "detail": job.status})

    dataset: dict[str, Any] = {}
    if snapshot:
        dataset = {
            "provider": snapshot.metadata.provider_name,
            "generated_at": _iso(snapshot.metadata.generated_at),
            "history_start": snapshot.metadata.history_start.isoformat(),
            "history_end": snapshot.metadata.history_end.isoformat(),
            "item_count": snapshot.metadata.item_count,
            "store_count": snapshot.metadata.store_count,
            "category_count": snapshot.metadata.category_count,
            "missing_observations": snapshot.metadata.missing_observation_count,
            "insufficient_history_pairs": snapshot.metadata.insufficient_history_item_count,
            "seed": snapshot.metadata.seed,
            "assumptions": snapshot.metadata.assumptions,
        }

    return HealthOut(
        status=status,
        app=settings.app_name,
        version=settings.app_version,
        provider=provider.provider_name() if provider_ready else "unavailable",
        provider_ready=provider_ready,
        forecast_job={
            "status": job.status,
            "started_at": _iso(job.started_at),
            "finished_at": _iso(job.finished_at),
            "duration_seconds": job.duration_seconds,
            "forecasts_generated": job.forecasts_generated,
            "error": job.error,
            "last_run_at": _iso(job.last_run_at),
        },
        dataset=dataset,
        checks=checks,
    )


@router.get("/filters", response_model=FilterOptions)
def filter_options() -> FilterOptions:
    snap = get_provider().load_snapshot()
    return FilterOptions(
        stores=[{"store_id": s.store_id, "name": s.name} for s in snap.stores],
        categories=[{"category_id": c.category_id, "name": c.name} for c in snap.categories],
        horizons=[7, 14],
    )


@router.get("/dashboard/summary", response_model=DashboardSummaryOut)
def dashboard_summary(
    store_id: str | None = None,
    category_id: str | None = None,
    horizon: int = Query(14, ge=7, le=14),
) -> DashboardSummaryOut:
    analytics = get_analytics()
    return DashboardSummaryOut(**analytics.summary(store_id=store_id, category_id=category_id, horizon=horizon))


@router.get("/dashboard/trends", response_model=TrendsOut)
def dashboard_trends(
    store_id: str | None = None,
    category_id: str | None = None,
    item_id: str | None = None,
    aggregation: Literal["daily", "weekly"] = "daily",
    lookback_days: int = Query(56, ge=14, le=365),
    horizon: int = Query(14, ge=7, le=14),
) -> TrendsOut:
    analytics = get_analytics()
    return TrendsOut(
        **analytics.trends(
            store_id=store_id,
            category_id=category_id,
            item_id=item_id,
            aggregation=aggregation,
            lookback_days=lookback_days,
            horizon=horizon,
        )
    )


@router.get("/dashboard/stockout-ranking")
def stockout_ranking(
    store_id: str | None = None,
    category_id: str | None = None,
    by: Literal["category", "item"] = "category",
    horizon: int = Query(14, ge=7, le=14),
    limit: int = Query(10, ge=1, le=50),
) -> list[dict[str, Any]]:
    return get_analytics().stockout_ranking(store_id, category_id, by=by, horizon=horizon, limit=limit)


@router.get("/dashboard/priority-actions", response_model=PaginatedResponse[PriorityActionOut])
def priority_actions(
    store_id: str | None = None,
    category_id: str | None = None,
    search: str | None = None,
    horizon: int = Query(14, ge=7, le=14),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PriorityActionOut]:
    rows = get_analytics().priority_actions(store_id, category_id, search, horizon)
    page_items, total, pages = paginate(rows, page, page_size)
    return PaginatedResponse(
        items=[PriorityActionOut(**r) for r in page_items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/inventory/stores", response_model=list[StoreOut])
def list_stores() -> list[StoreOut]:
    return [StoreOut(**s.__dict__) for s in get_provider().load_snapshot().stores]


@router.get("/inventory/categories", response_model=list[CategoryOut])
def list_categories() -> list[CategoryOut]:
    return [CategoryOut(**c.__dict__) for c in get_provider().load_snapshot().categories]


@router.get("/inventory/items", response_model=PaginatedResponse[ItemOut])
def list_items(
    store_id: str | None = None,
    category_id: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[ItemOut]:
    analytics = get_analytics()
    snap = analytics.snapshot
    cats = {c.category_id: c.name for c in snap.categories}
    items = snap.items
    if category_id:
        items = [i for i in items if i.category_id == category_id]
    if search:
        q = search.lower()
        items = [i for i in items if q in i.name.lower() or q in i.item_code.lower()]
    # Optional: only items present in store
    if store_id:
        present = {b.item_id for b in snap.balances if b.store_id == store_id}
        items = [i for i in items if i.item_id in present]

    page_items, total, pages = paginate(items, page, page_size)
    out = [
        ItemOut(
            item_id=i.item_id,
            item_code=i.item_code,
            name=i.name,
            category_id=i.category_id,
            category_name=cats[i.category_id],
            unit=i.unit,
            min_stock=i.min_stock,
            safety_stock=i.safety_stock,
            supplier_lead_time_days=i.supplier_lead_time_days,
            demand_pattern=i.demand_pattern,
        )
        for i in page_items
    ]
    return PaginatedResponse(items=out, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/inventory/forecasts", response_model=PaginatedResponse[ForecastOut])
def list_forecasts(
    store_id: str | None = None,
    item_id: str | None = None,
    horizon: int = Query(14, ge=7, le=14),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[ForecastOut]:
    analytics = get_analytics()
    analytics.ensure_ready()
    results = analytics.engine.list_forecasts(horizon=horizon, item_id=item_id, store_id=store_id)
    page_items, total, pages = paginate(results, page, page_size)
    out = [_forecast_out(f) for f in page_items]
    return PaginatedResponse(items=out, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/inventory/forecasts/{item_id}", response_model=ForecastDetailOut)
def get_forecast_detail(
    item_id: str,
    store_id: str = Query(...),
    horizon: int = Query(14, ge=7, le=14),
) -> ForecastDetailOut:
    analytics = get_analytics()
    analytics.ensure_ready()
    snap = analytics.snapshot
    item = next((i for i in snap.items if i.item_id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    store = next((s for s in snap.stores if s.store_id == store_id), None)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    bal = next((b for b in snap.balances if b.item_id == item_id and b.store_id == store_id), None)
    if not bal:
        raise HTTPException(status_code=404, detail="No stock balance for item/store")

    fc = analytics.engine.get_forecast(item_id, store_id, horizon)
    if not fc:
        raise HTTPException(status_code=404, detail="Forecast not available")

    # Recent avg + trend
    end = snap.metadata.history_end
    recent = [
        r.quantity
        for r in snap.consumption
        if r.item_id == item_id and r.store_id == store_id and not r.is_missing and r.date > end - timedelta(days=14)
    ]
    prior = [
        r.quantity
        for r in snap.consumption
        if r.item_id == item_id
        and r.store_id == store_id
        and not r.is_missing
        and end - timedelta(days=28) < r.date <= end - timedelta(days=14)
    ]
    avg = float(np.mean(recent)) if recent else 0.0
    prior_avg = float(np.mean(prior)) if prior else avg
    if avg > prior_avg * 1.1:
        trend = "increasing"
    elif avg < prior_avg * 0.9:
        trend = "decreasing"
    else:
        trend = "stable"

    forecast_total = sum(p.predicted for p in fc.points)
    cover = (bal.usable_qty / avg) if avg > 0 else None

    # Stockout from risk service
    from app.services.risk import assess_stockout

    assessment = assess_stockout(item, bal, fc, snap.incoming, avg)

    history_payload: list[dict[str, Any]] = []
    hist = analytics.engine.get_history_series(item_id, store_id)
    if hist:
        dates, series = hist
        # last 56 days
        for d, v in list(zip(dates, series))[-56:]:
            history_payload.append(
                {
                    "date": d.isoformat(),
                    "actual": None if np.isnan(v) else round(float(v), 1),
                }
            )

    cats = {c.category_id: c.name for c in snap.categories}
    base = _forecast_out(fc)
    return ForecastDetailOut(
        **base.model_dump(),
        item_code=item.item_code,
        item_name=item.name,
        store_name=store.name,
        category_name=cats[item.category_id],
        current_stock=bal.usable_qty,
        avg_daily_consumption=round(avg, 2),
        recent_trend=trend,
        forecast_total=round(forecast_total, 1),
        estimated_days_of_cover=round(cover, 1) if cover is not None else None,
        expected_stockout_date=assessment.predicted_stockout_date.isoformat()
        if assessment.predicted_stockout_date
        else None,
        history=history_payload,
    )


@router.get("/inventory/stockout-risks", response_model=PaginatedResponse[StockoutRiskOut])
def stockout_risks(
    store_id: str | None = None,
    category_id: str | None = None,
    risk_level: Literal["critical", "high", "medium", "low"] | None = None,
    search: str | None = None,
    horizon: int = Query(14, ge=7, le=14),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[StockoutRiskOut]:
    analytics = get_analytics()
    assessments = analytics.stockout_assessments(store_id, category_id, risk_level, search, horizon)
    snap = analytics.snapshot
    items = {i.item_id: i for i in snap.items}
    stores = {s.store_id: s for s in snap.stores}
    cats = {c.category_id: c.name for c in snap.categories}

    rows = [
        StockoutRiskOut(
            item_id=a.item_id,
            item_code=items[a.item_id].item_code,
            item_name=items[a.item_id].name,
            store_id=a.store_id,
            store_name=stores[a.store_id].name,
            category_name=cats[items[a.item_id].category_id],
            current_usable_stock=a.current_usable_stock,
            avg_daily_consumption=a.avg_daily_consumption,
            days_of_cover=a.days_of_cover,
            predicted_stockout_date=a.predicted_stockout_date.isoformat() if a.predicted_stockout_date else None,
            expected_incoming_stock=a.expected_incoming,
            supplier_lead_time_days=a.supplier_lead_time_days,
            risk_level=a.risk_level,
            explanation=a.explanation,
            data_quality=a.data_quality,
        )
        for a in assessments
    ]
    page_items, total, pages = paginate(rows, page, page_size)
    return PaginatedResponse(items=page_items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/inventory/expiry-risks", response_model=PaginatedResponse[ExpiryRiskOut])
def expiry_risks(
    store_id: str | None = None,
    category_id: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[ExpiryRiskOut]:
    analytics = get_analytics()
    assessments = analytics.expiry_assessments(store_id, category_id, search)
    snap = analytics.snapshot
    items = {i.item_id: i for i in snap.items}
    stores = {s.store_id: s for s in snap.stores}
    cats = {c.category_id: c.name for c in snap.categories}
    rows = [
        ExpiryRiskOut(
            batch_id=a.batch_id,
            item_id=a.item_id,
            item_code=items[a.item_id].item_code,
            item_name=items[a.item_id].name,
            store_id=a.store_id,
            store_name=stores[a.store_id].name,
            category_name=cats[items[a.item_id].category_id],
            available_qty=a.available_qty,
            expiry_date=a.expiry_date.isoformat(),
            days_until_expiry=a.days_until_expiry,
            risk_status=a.risk_status,
            fefo_note=a.fefo_note,
        )
        for a in assessments
    ]
    page_items, total, pages = paginate(rows, page, page_size)
    return PaginatedResponse(items=page_items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/inventory/expiry-summary", response_model=ExpirySummaryOut)
def expiry_summary(
    store_id: str | None = None,
    category_id: str | None = None,
) -> ExpirySummaryOut:
    analytics = get_analytics()
    assessments = analytics.expiry_assessments(store_id, category_id)
    snap = analytics.snapshot
    items = {i.item_id: i for i in snap.items}
    cats = {c.category_id: c.name for c in snap.categories}

    expired = [a for a in assessments if a.risk_status == "expired"]
    d7 = [a for a in assessments if 0 <= a.days_until_expiry <= 7]
    d30 = [a for a in assessments if 0 <= a.days_until_expiry <= 30]
    d90 = [a for a in assessments if 0 <= a.days_until_expiry <= 90]

    by_cat: dict[str, float] = {}
    for a in assessments:
        if a.days_until_expiry > 90:
            continue
        cat = cats[items[a.item_id].category_id]
        by_cat[cat] = by_cat.get(cat, 0.0) + a.available_qty

    return ExpirySummaryOut(
        expired_qty=round(sum(a.available_qty for a in expired), 1),
        expired_batches=len(expired),
        within_7_days_qty=round(sum(a.available_qty for a in d7), 1),
        within_7_days_batches=len(d7),
        within_30_days_qty=round(sum(a.available_qty for a in d30), 1),
        within_30_days_batches=len(d30),
        within_90_days_qty=round(sum(a.available_qty for a in d90), 1),
        within_90_days_batches=len(d90),
        by_category=[{"category": k, "qty": round(v, 1)} for k, v in sorted(by_cat.items(), key=lambda x: -x[1])],
    )


@router.get("/inventory/reorder-recommendations", response_model=PaginatedResponse[ReorderRecommendationOut])
def reorder_recommendations(
    store_id: str | None = None,
    category_id: str | None = None,
    search: str | None = None,
    horizon: int = Query(14, ge=7, le=14),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[ReorderRecommendationOut]:
    analytics = get_analytics()
    recs = analytics.reorder_recommendations(store_id, category_id, search, horizon)
    snap = analytics.snapshot
    items = {i.item_id: i for i in snap.items}
    stores = {s.store_id: s for s in snap.stores}
    cats = {c.category_id: c.name for c in snap.categories}
    rows = [
        ReorderRecommendationOut(
            item_id=r.item_id,
            item_code=items[r.item_id].item_code,
            item_name=items[r.item_id].name,
            store_id=r.store_id,
            store_name=stores[r.store_id].name,
            category_name=cats[items[r.item_id].category_id],
            current_usable_stock=r.current_usable_stock,
            forecast_demand_lead_time=r.forecast_demand_lead_time,
            incoming_qty=r.incoming_qty,
            safety_stock=r.safety_stock,
            projected_stock_at_lead=r.projected_stock_at_lead,
            suggested_reorder_qty=r.suggested_reorder_qty,
            estimated_days_of_cover=r.estimated_days_of_cover,
            reason=r.reason,
            data_quality=r.data_quality,
            calculation_steps=r.calculation_steps,
            lead_time_days=r.lead_time_days,
            horizon_limitation=r.horizon_limitation,
        )
        for r in recs
    ]
    page_items, total, pages = paginate(rows, page, page_size)
    return PaginatedResponse(items=page_items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/forecast-evaluations")
def forecast_evaluations(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    return get_analytics().forecast_evaluations(limit=limit)


@router.post("/forecasts/refresh", response_model=ForecastRefreshOut)
def refresh_forecasts(horizon: int = Query(14, ge=7, le=14)) -> ForecastRefreshOut:
    provider = get_provider()
    engine = get_engine()
    snapshot = provider.load_snapshot()
    # Clear cache to force regeneration
    with engine._lock:
        if engine._job.status == "running":
            job = engine._job
            return ForecastRefreshOut(
                status=job.status,
                started_at=_iso(job.started_at),
                finished_at=_iso(job.finished_at),
                duration_seconds=job.duration_seconds,
                forecasts_generated=job.forecasts_generated,
                error=job.error,
                last_run_at=_iso(job.last_run_at),
            )
        engine._forecasts.clear()
    job = engine.refresh(snapshot, horizons=[7, 14])
    return ForecastRefreshOut(
        status=job.status,
        started_at=_iso(job.started_at),
        finished_at=_iso(job.finished_at),
        duration_seconds=job.duration_seconds,
        forecasts_generated=job.forecasts_generated,
        error=job.error,
        last_run_at=_iso(job.last_run_at),
    )


def _forecast_out(f: Any) -> ForecastOut:
    return ForecastOut(
        item_id=f.item_id,
        store_id=f.store_id,
        horizon_days=f.horizon_days,
        model_id=f.model_id,
        generated_at=_iso(f.generated_at) or "",
        data_through=f.data_through.isoformat(),
        data_quality=f.data_quality,
        points=[
            ForecastPointOut(date=p.date.isoformat(), predicted=p.predicted, lower=p.lower, upper=p.upper)
            for p in f.points
        ],
        limitations=f.limitations,
        mae=round(f.eval_metrics.mae, 3) if f.eval_metrics else None,
        wape=round(f.eval_metrics.wape, 4) if f.eval_metrics and f.eval_metrics.wape is not None else None,
        bias=round(f.eval_metrics.bias, 3) if f.eval_metrics else None,
    )