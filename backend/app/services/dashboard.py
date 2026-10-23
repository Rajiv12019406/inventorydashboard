"""Dashboard aggregation service."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import numpy as np

from app.data.models import InventorySnapshot
from app.forecasting.engine import ForecastEngine, ForecastResult
from app.services.risk import (
    ExpiryAssessment,
    ReorderRecommendation,
    StockoutAssessment,
    assess_expiry,
    assess_stockout,
    recommend_reorder,
)


def _avg_daily(snapshot: InventorySnapshot, item_id: str, store_id: str, lookback: int = 28) -> float:
    end = snapshot.metadata.history_end
    start = end - timedelta(days=lookback - 1)
    vals = [
        r.quantity
        for r in snapshot.consumption
        if r.item_id == item_id
        and r.store_id == store_id
        and not r.is_missing
        and start <= r.date <= end
    ]
    return float(np.mean(vals)) if vals else 0.0


class InventoryAnalyticsService:
    def __init__(self, snapshot: InventorySnapshot, engine: ForecastEngine) -> None:
        self.snapshot = snapshot
        self.engine = engine
        self._items = {i.item_id: i for i in snapshot.items}
        self._stores = {s.store_id: s for s in snapshot.stores}
        self._categories = {c.category_id: c for c in snapshot.categories}
        self._balances = {(b.item_id, b.store_id): b for b in snapshot.balances}

    def ensure_ready(self, horizons: list[int] | None = None) -> None:
        self.engine.ensure_forecasts(self.snapshot, horizons=horizons or [7, 14])

    def filter_balances(
        self,
        store_id: str | None = None,
        category_id: str | None = None,
        search: str | None = None,
    ) -> list[tuple[Any, Any]]:
        results = []
        q = (search or "").strip().lower()
        for bal in self.snapshot.balances:
            item = self._items[bal.item_id]
            if store_id and bal.store_id != store_id:
                continue
            if category_id and item.category_id != category_id:
                continue
            if q and q not in item.name.lower() and q not in item.item_code.lower():
                continue
            results.append((item, bal))
        return results

    def stockout_assessments(
        self,
        store_id: str | None = None,
        category_id: str | None = None,
        risk_level: str | None = None,
        search: str | None = None,
        horizon: int = 14,
    ) -> list[StockoutAssessment]:
        self.ensure_ready()
        out: list[StockoutAssessment] = []
        for item, bal in self.filter_balances(store_id, category_id, search):
            fc = self.engine.get_forecast(item.item_id, bal.store_id, horizon)
            if fc is None:
                fc = self.engine.get_forecast(item.item_id, bal.store_id, 7)
            if fc is None:
                continue
            avg = _avg_daily(self.snapshot, item.item_id, bal.store_id)
            assessment = assess_stockout(item, bal, fc, self.snapshot.incoming, avg)
            if risk_level and assessment.risk_level != risk_level:
                continue
            out.append(assessment)
        severity = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        out.sort(key=lambda a: (severity.get(a.risk_level, 9), a.days_of_cover or 999))
        return out

    def expiry_assessments(
        self,
        store_id: str | None = None,
        category_id: str | None = None,
        search: str | None = None,
    ) -> list[ExpiryAssessment]:
        as_of = self.snapshot.metadata.history_end
        out: list[ExpiryAssessment] = []
        q = (search or "").strip().lower()
        for batch in self.snapshot.batches:
            item = self._items[batch.item_id]
            if store_id and batch.store_id != store_id:
                continue
            if category_id and item.category_id != category_id:
                continue
            if q and q not in item.name.lower() and q not in item.item_code.lower() and q not in batch.batch_id.lower():
                continue
            out.append(assess_expiry(batch, as_of))
        out.sort(key=lambda e: e.days_until_expiry)
        return out

    def reorder_recommendations(
        self,
        store_id: str | None = None,
        category_id: str | None = None,
        search: str | None = None,
        horizon: int = 14,
    ) -> list[ReorderRecommendation]:
        self.ensure_ready()
        out: list[ReorderRecommendation] = []
        for item, bal in self.filter_balances(store_id, category_id, search):
            fc = self.engine.get_forecast(item.item_id, bal.store_id, horizon)
            if fc is None:
                fc = self.engine.get_forecast(item.item_id, bal.store_id, 7)
            if fc is None:
                continue
            avg = _avg_daily(self.snapshot, item.item_id, bal.store_id)
            rec = recommend_reorder(item, bal, fc, self.snapshot.incoming, avg)
            if rec:
                out.append(rec)
        out.sort(key=lambda r: -r.suggested_reorder_qty)
        return out

    def summary(
        self,
        store_id: str | None = None,
        category_id: str | None = None,
        horizon: int = 14,
    ) -> dict[str, Any]:
        self.ensure_ready()
        stockouts = self.stockout_assessments(store_id=store_id, category_id=category_id, horizon=horizon)
        expiries = self.expiry_assessments(store_id=store_id, category_id=category_id)
        reorders = self.reorder_recommendations(store_id=store_id, category_id=category_id, horizon=horizon)

        active_items = len({i.item_id for i, _ in self.filter_balances(store_id, category_id)})
        low_stock = sum(
            1
            for item, bal in self.filter_balances(store_id, category_id)
            if bal.usable_qty <= item.min_stock
        )
        risk_7 = sum(1 for s in stockouts if s.risk_level in {"critical", "high"})
        risk_14 = sum(1 for s in stockouts if s.risk_level in {"critical", "high", "medium"})
        approaching_expiry = sum(1 for e in expiries if 0 <= e.days_until_expiry <= 30)
        expired = sum(e.available_qty for e in expiries if e.risk_status == "expired")

        # Forecasted demand over horizon (sum of point forecasts for filtered pairs)
        forecasted_demand = 0.0
        for item, bal in self.filter_balances(store_id, category_id):
            fc = self.engine.get_forecast(item.item_id, bal.store_id, horizon)
            if fc:
                forecasted_demand += sum(p.predicted for p in fc.points)

        risk_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for s in stockouts:
            risk_dist[s.risk_level] += 1

        # Previous-period comparison for low stock — compare avg stock cover using last 28d vs prior 28d demand
        # Only emit deltas we can actually compute from the synthetic ledger
        low_stock_delta = None  # omitted unless computable; keep honest

        return {
            "active_items": active_items,
            "low_stock_items": low_stock,
            "low_stock_delta_pct": low_stock_delta,
            "stockout_risk_7d": risk_7,
            "stockout_risk_14d": risk_14,
            "approaching_expiry": approaching_expiry,
            "expired_qty": round(expired, 1),
            "reorder_required": len(reorders),
            "forecasted_demand": round(forecasted_demand, 1),
            "risk_distribution": risk_dist,
            "as_of_date": self.snapshot.metadata.history_end.isoformat(),
            "forecast_generated_at": self.engine.job_status.last_run_at.isoformat()
            if self.engine.job_status.last_run_at
            else None,
            "provider": self.snapshot.metadata.provider_name,
        }

    def trends(
        self,
        store_id: str | None = None,
        category_id: str | None = None,
        item_id: str | None = None,
        aggregation: str = "daily",
        lookback_days: int = 56,
        horizon: int = 14,
    ) -> dict[str, Any]:
        self.ensure_ready()
        end = self.snapshot.metadata.history_end
        start = end - timedelta(days=lookback_days - 1)

        # Aggregate actual consumption
        daily: dict[date, float] = defaultdict(float)
        for rec in self.snapshot.consumption:
            if rec.is_missing:
                continue
            if rec.date < start or rec.date > end:
                continue
            if store_id and rec.store_id != store_id:
                continue
            if item_id and rec.item_id != item_id:
                continue
            if category_id:
                item = self._items.get(rec.item_id)
                if not item or item.category_id != category_id:
                    continue
            daily[rec.date] += rec.quantity

        actual = [{"date": d.isoformat(), "actual": round(daily.get(d, 0.0), 1)} for d in sorted(daily.keys())]

        # Forecast aggregate for matching pairs
        forecast_daily: dict[date, float] = defaultdict(float)
        lower_daily: dict[date, float] = defaultdict(float)
        upper_daily: dict[date, float] = defaultdict(float)
        pairs = self.filter_balances(store_id, category_id)
        if item_id:
            pairs = [(i, b) for i, b in pairs if i.item_id == item_id]

        for item, bal in pairs:
            fc = self.engine.get_forecast(item.item_id, bal.store_id, horizon)
            if not fc:
                continue
            for pt in fc.points:
                forecast_daily[pt.date] += pt.predicted
                if pt.lower is not None:
                    lower_daily[pt.date] += pt.lower
                if pt.upper is not None:
                    upper_daily[pt.date] += pt.upper

        forecast = [
            {
                "date": d.isoformat(),
                "predicted": round(forecast_daily[d], 1),
                "lower": round(lower_daily[d], 1) if d in lower_daily else None,
                "upper": round(upper_daily[d], 1) if d in upper_daily else None,
            }
            for d in sorted(forecast_daily.keys())
        ]

        if aggregation == "weekly":
            actual = _to_weekly(actual, value_key="actual")
            forecast = _to_weekly(forecast, value_key="predicted", extra_keys=("lower", "upper"))

        return {
            "aggregation": aggregation,
            "history_end": end.isoformat(),
            "actual": actual,
            "forecast": forecast,
        }

    def stockout_ranking(
        self,
        store_id: str | None = None,
        category_id: str | None = None,
        by: str = "category",
        horizon: int = 14,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        assessments = self.stockout_assessments(store_id=store_id, category_id=category_id, horizon=horizon)
        at_risk = [a for a in assessments if a.risk_level in {"critical", "high", "medium"}]
        buckets: dict[str, float] = defaultdict(float)
        labels: dict[str, str] = {}

        for a in at_risk:
            item = self._items[a.item_id]
            if by == "item":
                key = a.item_id
                labels[key] = item.name
            else:
                key = item.category_id
                labels[key] = self._categories[item.category_id].name
            # Exposure proxy: inverse days of cover weighted
            exposure = 1.0 / max(a.days_of_cover or 0.5, 0.5)
            buckets[key] += exposure

        ranked = sorted(buckets.items(), key=lambda kv: -kv[1])[:limit]
        return [{"id": k, "label": labels[k], "exposure": round(v, 2)} for k, v in ranked]

    def priority_actions(
        self,
        store_id: str | None = None,
        category_id: str | None = None,
        search: str | None = None,
        horizon: int = 14,
    ) -> list[dict[str, Any]]:
        stockouts = self.stockout_assessments(store_id, category_id, search=search, horizon=horizon)
        reorders = {
            (r.item_id, r.store_id): r
            for r in self.reorder_recommendations(store_id, category_id, search=search, horizon=horizon)
        }
        rows = []
        for s in stockouts:
            if s.risk_level == "low" and (s.item_id, s.store_id) not in reorders:
                continue
            item = self._items[s.item_id]
            store = self._stores[s.store_id]
            rec = reorders.get((s.item_id, s.store_id))
            rows.append(
                {
                    "item_id": s.item_id,
                    "item_code": item.item_code,
                    "item_name": item.name,
                    "category_id": item.category_id,
                    "category_name": self._categories[item.category_id].name,
                    "store_id": s.store_id,
                    "store_name": store.name,
                    "current_stock": s.current_usable_stock,
                    "days_of_cover": s.days_of_cover,
                    "predicted_stockout_date": s.predicted_stockout_date.isoformat()
                    if s.predicted_stockout_date
                    else None,
                    "suggested_reorder_qty": rec.suggested_reorder_qty if rec else 0,
                    "risk_status": s.risk_level,
                }
            )
        return rows

    def forecast_evaluations(self, limit: int = 50) -> dict[str, Any]:
        self.ensure_ready()
        forecasts = [f for f in self.engine.list_forecasts(horizon=7) if f.eval_metrics]
        if not forecasts:
            return {
                "status": "insufficient_evaluation_history",
                "message": "Insufficient evaluation history for a reliable score.",
                "models": [],
                "overall": None,
            }

        by_model: dict[str, list[ForecastResult]] = defaultdict(list)
        for f in forecasts:
            by_model[f.model_id].append(f)

        models = []
        all_mae = []
        all_wape = []
        all_bias = []
        n_obs = 0
        for model_id, group in by_model.items():
            maes = [g.eval_metrics.mae for g in group if g.eval_metrics]
            wapes = [g.eval_metrics.wape for g in group if g.eval_metrics and g.eval_metrics.wape is not None]
            biases = [g.eval_metrics.bias for g in group if g.eval_metrics]
            obs = sum(g.eval_metrics.n_obs for g in group if g.eval_metrics)
            models.append(
                {
                    "model_id": model_id,
                    "series_count": len(group),
                    "mae": round(float(np.mean(maes)), 3) if maes else None,
                    "wape": round(float(np.mean(wapes)), 4) if wapes else None,
                    "bias": round(float(np.mean(biases)), 3) if biases else None,
                    "n_obs": obs,
                }
            )
            all_mae.extend(maes)
            all_wape.extend(wapes)
            all_bias.extend(biases)
            n_obs += obs

        models.sort(key=lambda m: m["mae"] if m["mae"] is not None else 999)

        # Error trend: sample up to `limit` series MAE
        series_errors = [
            {
                "item_id": f.item_id,
                "store_id": f.store_id,
                "model_id": f.model_id,
                "mae": round(f.eval_metrics.mae, 3) if f.eval_metrics else None,
                "wape": round(f.eval_metrics.wape, 4) if f.eval_metrics and f.eval_metrics.wape is not None else None,
                "bias": round(f.eval_metrics.bias, 3) if f.eval_metrics else None,
                "n_obs": f.eval_metrics.n_obs if f.eval_metrics else 0,
            }
            for f in forecasts[:limit]
        ]

        return {
            "status": "ok",
            "message": "Metrics from chronological rolling-origin backtests on historical data — not future confidence.",
            "evaluation_period": {
                "start": self.snapshot.metadata.history_start.isoformat(),
                "end": self.snapshot.metadata.history_end.isoformat(),
            },
            "models": models,
            "overall": {
                "mae": round(float(np.mean(all_mae)), 3) if all_mae else None,
                "wape": round(float(np.mean(all_wape)), 4) if all_wape else None,
                "bias": round(float(np.mean(all_bias)), 3) if all_bias else None,
                "n_obs": n_obs,
                "series_evaluated": len(forecasts),
            },
            "series": series_errors,
        }


def _to_weekly(rows: list[dict[str, Any]], value_key: str, extra_keys: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, float]] = {}
    for row in rows:
        d = date.fromisoformat(row["date"])
        week_start = d - timedelta(days=d.weekday())
        key = week_start.isoformat()
        if key not in buckets:
            buckets[key] = {value_key: 0.0, **{k: 0.0 for k in extra_keys}}
        buckets[key][value_key] += float(row.get(value_key) or 0)
        for k in extra_keys:
            if row.get(k) is not None:
                buckets[key][k] += float(row[k])
    out = []
    for key in sorted(buckets.keys()):
        entry = {"date": key, value_key: round(buckets[key][value_key], 1)}
        for k in extra_keys:
            entry[k] = round(buckets[key][k], 1)
        out.append(entry)
    return out