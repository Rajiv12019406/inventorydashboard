"""Forecast generation engine — independent of data provider implementation."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Literal

import numpy as np

from app.data.models import ConsumptionRecord, InventoryItem, InventorySnapshot
from app.forecasting.evaluation import EvalMetrics, select_best_model
from app.forecasting.models import candidate_models_for_series


DataQuality = Literal["ok", "insufficient_history", "sparse", "missing_observations"]


@dataclass
class ForecastPoint:
    date: date
    predicted: float
    lower: float | None
    upper: float | None


@dataclass
class ForecastResult:
    item_id: str
    store_id: str
    horizon_days: int
    model_id: str
    generated_at: datetime
    data_through: date
    data_quality: DataQuality
    points: list[ForecastPoint]
    eval_metrics: EvalMetrics | None = None
    limitations: list[str] = field(default_factory=list)


@dataclass
class ForecastJobStatus:
    status: Literal["idle", "running", "completed", "failed"]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    forecasts_generated: int = 0
    error: str | None = None
    last_run_at: datetime | None = None


class ForecastEngine:
    """Generate and cache item-store demand forecasts."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._forecasts: dict[tuple[str, str, int], ForecastResult] = {}
        self._job = ForecastJobStatus(status="idle")
        self._series_cache: dict[tuple[str, str], np.ndarray] = {}
        self._date_index: list[date] = []

    @property
    def job_status(self) -> ForecastJobStatus:
        return self._job

    def clear(self) -> None:
        with self._lock:
            self._forecasts.clear()
            self._series_cache.clear()
            self._date_index = []
            self._job = ForecastJobStatus(status="idle")

    def get_forecast(self, item_id: str, store_id: str, horizon: int) -> ForecastResult | None:
        return self._forecasts.get((item_id, store_id, horizon))

    def list_forecasts(
        self,
        horizon: int | None = None,
        item_id: str | None = None,
        store_id: str | None = None,
    ) -> list[ForecastResult]:
        results = list(self._forecasts.values())
        if horizon is not None:
            results = [r for r in results if r.horizon_days == horizon]
        if item_id:
            results = [r for r in results if r.item_id == item_id]
        if store_id:
            results = [r for r in results if r.store_id == store_id]
        return results

    def ensure_forecasts(
        self,
        snapshot: InventorySnapshot,
        horizons: list[int] | None = None,
        wait: bool = True,
        wait_timeout_seconds: float = 600.0,
    ) -> ForecastJobStatus:
        """Generate forecasts if cache empty; skip if already populated.

        If a background run is in progress and wait=True, block until it finishes
        (or timeout) so API consumers receive complete results.
        """
        with self._lock:
            if self._forecasts and self._job.status == "completed":
                return self._job
            running = self._job.status == "running"

        if running:
            if wait:
                self._wait_until_idle(timeout_seconds=wait_timeout_seconds)
            return self._job

        with self._lock:
            if self._forecasts:
                return self._job
            if self._job.status == "running":
                running = True
            else:
                running = False

        if running:
            if wait:
                self._wait_until_idle(timeout_seconds=wait_timeout_seconds)
            return self._job

        return self.refresh(snapshot, horizons=horizons)

    def _wait_until_idle(self, timeout_seconds: float = 600.0) -> None:
        deadline = datetime.now(timezone.utc).timestamp() + timeout_seconds
        while datetime.now(timezone.utc).timestamp() < deadline:
            with self._lock:
                if self._job.status != "running":
                    return
            threading.Event().wait(0.25)

    def refresh(self, snapshot: InventorySnapshot, horizons: list[int] | None = None) -> ForecastJobStatus:
        """Run the full forecast pipeline. Prevents overlapping runs."""
        with self._lock:
            if self._job.status == "running":
                return self._job
            self._job = ForecastJobStatus(
                status="running",
                started_at=datetime.now(timezone.utc),
                last_run_at=self._job.last_run_at,
            )

        horizons = horizons or [7, 14]
        started = datetime.now(timezone.utc)

        try:
            self._build_series_cache(snapshot)
            new_forecasts: dict[tuple[str, str, int], ForecastResult] = {}
            item_lookup = {i.item_id: i for i in snapshot.items}
            pairs = {(b.item_id, b.store_id) for b in snapshot.balances}

            for item_id, store_id in pairs:
                series = self._series_cache.get((item_id, store_id))
                if series is None:
                    continue
                item = item_lookup.get(item_id)
                for h in horizons:
                    result = self._forecast_one(
                        item_id=item_id,
                        store_id=store_id,
                        series=series,
                        horizon=h,
                        history_end=snapshot.metadata.history_end,
                        item=item,
                    )
                    new_forecasts[(item_id, store_id, h)] = result

            finished = datetime.now(timezone.utc)
            with self._lock:
                self._forecasts = new_forecasts
                self._job = ForecastJobStatus(
                    status="completed",
                    started_at=started,
                    finished_at=finished,
                    duration_seconds=(finished - started).total_seconds(),
                    forecasts_generated=len(new_forecasts),
                    last_run_at=finished,
                )
            return self._job
        except Exception as exc:  # noqa: BLE001 — surface job failure
            finished = datetime.now(timezone.utc)
            with self._lock:
                self._job = ForecastJobStatus(
                    status="failed",
                    started_at=started,
                    finished_at=finished,
                    duration_seconds=(finished - started).total_seconds(),
                    error=str(exc),
                    last_run_at=finished,
                )
            return self._job

    def _build_series_cache(self, snapshot: InventorySnapshot) -> None:
        history_start = snapshot.metadata.history_start
        history_end = snapshot.metadata.history_end
        n_days = (history_end - history_start).days + 1
        self._date_index = [history_start + timedelta(days=i) for i in range(n_days)]
        date_to_idx = {d: i for i, d in enumerate(self._date_index)}

        buckets: dict[tuple[str, str], np.ndarray] = {}
        for rec in snapshot.consumption:
            key = (rec.item_id, rec.store_id)
            if key not in buckets:
                buckets[key] = np.full(n_days, np.nan)
            idx = date_to_idx.get(rec.date)
            if idx is None:
                continue
            if rec.is_missing:
                buckets[key][idx] = np.nan
            else:
                buckets[key][idx] = rec.quantity

        self._series_cache = buckets

    def get_history_series(self, item_id: str, store_id: str) -> tuple[list[date], np.ndarray] | None:
        series = self._series_cache.get((item_id, store_id))
        if series is None or not self._date_index:
            return None
        return self._date_index, series

    def _assess_quality(self, series: np.ndarray) -> tuple[DataQuality, list[str]]:
        limitations: list[str] = []
        observed = series[~np.isnan(series)]
        n = len(observed)
        missing = int(np.isnan(series).sum())
        zero_frac = float(np.mean(observed == 0)) if n else 1.0

        if n < 30:
            limitations.append("Fewer than 30 observed days — forecast uncertainty is elevated.")
            return "insufficient_history", limitations
        if missing > 0:
            limitations.append(f"{missing} missing observation(s) were interpolated or excluded.")
        if zero_frac >= 0.45:
            limitations.append("Demand is intermittent; Croston-style models preferred.")
            return "sparse", limitations
        if missing > 0:
            return "missing_observations", limitations
        return "ok", limitations

    def _forecast_one(
        self,
        item_id: str,
        store_id: str,
        series: np.ndarray,
        horizon: int,
        history_end: date,
        item: InventoryItem | None,
    ) -> ForecastResult:
        generated_at = datetime.now(timezone.utc)
        quality, limitations = self._assess_quality(series)
        candidates = candidate_models_for_series(series)
        model, metrics = select_best_model(series, candidates, horizon=min(horizon, 7))

        # Trim leading nans for fitting
        valid = np.where(~np.isnan(series))[0]
        if len(valid) == 0:
            points = [
                ForecastPoint(date=history_end + timedelta(days=i + 1), predicted=0.0, lower=0.0, upper=0.0)
                for i in range(horizon)
            ]
            limitations.append("No observed demand history available.")
            return ForecastResult(
                item_id=item_id,
                store_id=store_id,
                horizon_days=horizon,
                model_id="moving_average",
                generated_at=generated_at,
                data_through=history_end,
                data_quality="insufficient_history",
                points=points,
                eval_metrics=None,
                limitations=limitations,
            )

        fit_series = series[valid[0] :]
        fc = model.fit_predict(fit_series, horizon)
        # Round consistently to 1 decimal; enforce non-negative
        point = np.round(np.maximum(0.0, fc.point), 1)
        lower = np.round(np.maximum(0.0, fc.lower), 1) if fc.lower is not None else None
        upper = np.round(np.maximum(0.0, fc.upper), 1) if fc.upper is not None else None

        if item and item.supplier_lead_time_days > horizon:
            limitations.append(
                f"Supplier lead time ({item.supplier_lead_time_days}d) exceeds forecast horizon ({horizon}d). "
                "Reorder projections beyond the horizon are limited."
            )

        points = []
        for i in range(horizon):
            points.append(
                ForecastPoint(
                    date=history_end + timedelta(days=i + 1),
                    predicted=float(point[i]),
                    lower=float(lower[i]) if lower is not None else None,
                    upper=float(upper[i]) if upper is not None else None,
                )
            )

        return ForecastResult(
            item_id=item_id,
            store_id=store_id,
            horizon_days=horizon,
            model_id=fc.model_id,
            generated_at=generated_at,
            data_through=history_end,
            data_quality=quality,
            points=points,
            eval_metrics=metrics,
            limitations=limitations,
        )


# Process-wide engine singleton
forecast_engine = ForecastEngine()


def consumption_by_pair(records: list[ConsumptionRecord]) -> dict[tuple[str, str], list[ConsumptionRecord]]:
    out: dict[tuple[str, str], list[ConsumptionRecord]] = {}
    for r in records:
        out.setdefault((r.item_id, r.store_id), []).append(r)
    return out