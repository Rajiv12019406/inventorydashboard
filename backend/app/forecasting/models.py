"""Forecasting model implementations.

All models produce non-negative demand forecasts. Models that cannot produce
prediction intervals return None for lower/upper bounds.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class ModelForecast:
    point: np.ndarray
    lower: np.ndarray | None
    upper: np.ndarray | None
    model_id: str


class BaseForecaster(ABC):
    model_id: str

    @abstractmethod
    def fit_predict(self, history: np.ndarray, horizon: int) -> ModelForecast:
        """Fit on history and forecast `horizon` steps ahead."""

    def requires_min_obs(self) -> int:
        return 7


class MovingAverageForecaster(BaseForecaster):
    model_id = "moving_average"

    def __init__(self, window: int = 7) -> None:
        self.window = window

    def requires_min_obs(self) -> int:
        return self.window

    def fit_predict(self, history: np.ndarray, horizon: int) -> ModelForecast:
        clean = history[~np.isnan(history)]
        window = min(self.window, len(clean))
        level = float(np.mean(clean[-window:])) if window else 0.0
        resid = clean[-window:] - level if window else np.array([0.0])
        sigma = float(np.std(resid, ddof=1)) if len(resid) > 1 else float(np.std(clean)) if len(clean) else 0.0
        point = np.full(horizon, max(0.0, level))
        lower = np.maximum(0.0, point - 1.96 * sigma)
        upper = point + 1.96 * sigma
        return ModelForecast(point=point, lower=lower, upper=upper, model_id=self.model_id)


class WeightedMovingAverageForecaster(BaseForecaster):
    model_id = "weighted_moving_average"

    def __init__(self, window: int = 14) -> None:
        self.window = window

    def requires_min_obs(self) -> int:
        return self.window

    def fit_predict(self, history: np.ndarray, horizon: int) -> ModelForecast:
        clean = history[~np.isnan(history)]
        window = min(self.window, len(clean))
        if window == 0:
            point = np.zeros(horizon)
            return ModelForecast(point=point, lower=point.copy(), upper=point.copy(), model_id=self.model_id)
        weights = np.arange(1, window + 1, dtype=float)
        weights /= weights.sum()
        level = float(np.dot(clean[-window:], weights))
        resid = clean[-window:] - level
        sigma = float(np.std(resid, ddof=1)) if window > 1 else 0.0
        point = np.full(horizon, max(0.0, level))
        lower = np.maximum(0.0, point - 1.96 * sigma)
        upper = point + 1.96 * sigma
        return ModelForecast(point=point, lower=lower, upper=upper, model_id=self.model_id)


class SeasonalNaiveForecaster(BaseForecaster):
    """Weekly seasonal naive: forecast = value from same weekday last week."""

    model_id = "seasonal_naive"
    season: int = 7

    def requires_min_obs(self) -> int:
        return self.season * 2

    def fit_predict(self, history: np.ndarray, horizon: int) -> ModelForecast:
        clean = history.copy()
        # forward-fill nan for seasonal indexing
        if np.any(np.isnan(clean)):
            idx = np.where(~np.isnan(clean))[0]
            if len(idx) == 0:
                z = np.zeros(horizon)
                return ModelForecast(point=z, lower=z.copy(), upper=z.copy(), model_id=self.model_id)
            clean = clean.copy()
            for i in range(len(clean)):
                if np.isnan(clean[i]):
                    clean[i] = clean[idx[np.searchsorted(idx, i, side="right") - 1]]

        point = np.array([max(0.0, float(clean[-(self.season - (h % self.season))])) for h in range(horizon)])
        # residual from seasonal differences
        if len(clean) >= self.season * 2:
            diffs = clean[self.season :] - clean[: -self.season]
            sigma = float(np.nanstd(diffs))
        else:
            sigma = float(np.nanstd(clean))
        lower = np.maximum(0.0, point - 1.96 * sigma)
        upper = point + 1.96 * sigma
        return ModelForecast(point=point, lower=lower, upper=upper, model_id=self.model_id)


class IntermittentCrostonForecaster(BaseForecaster):
    """Simple Croston-like intermittent demand model."""

    model_id = "intermittent_croston"

    def __init__(self, alpha: float = 0.1) -> None:
        self.alpha = alpha

    def requires_min_obs(self) -> int:
        return 14

    def fit_predict(self, history: np.ndarray, horizon: int) -> ModelForecast:
        clean = history[~np.isnan(history)]
        if len(clean) == 0:
            z = np.zeros(horizon)
            return ModelForecast(point=z, lower=z.copy(), upper=z.copy(), model_id=self.model_id)

        demand_sizes = clean[clean > 0]
        if len(demand_sizes) == 0:
            z = np.zeros(horizon)
            return ModelForecast(point=z, lower=z.copy(), upper=z.copy(), model_id=self.model_id)

        # Inter-demand intervals
        nonzero_idx = np.where(clean > 0)[0]
        if len(nonzero_idx) >= 2:
            intervals = np.diff(nonzero_idx).astype(float)
        else:
            intervals = np.array([max(1.0, len(clean) / max(1, len(demand_sizes)))])

        z = float(np.mean(demand_sizes))
        p = float(np.mean(intervals))
        # Simple SES update over observed non-zero demands / intervals
        for i, d in enumerate(demand_sizes):
            z = self.alpha * float(d) + (1 - self.alpha) * z
            if i < len(intervals):
                p = self.alpha * float(intervals[min(i, len(intervals) - 1)]) + (1 - self.alpha) * p

        rate = max(0.0, z / max(p, 1.0))
        point = np.full(horizon, rate)
        sigma = float(np.std(demand_sizes)) / max(p, 1.0) if len(demand_sizes) > 1 else rate * 0.5
        lower = np.maximum(0.0, point - 1.96 * sigma)
        upper = point + 1.96 * sigma
        return ModelForecast(point=point, lower=lower, upper=upper, model_id=self.model_id)


class ExponentialSmoothingForecaster(BaseForecaster):
    """Holt linear exponential smoothing (fast NumPy implementation).

    Prefer this over statsmodels Holt-Winters for bulk generation speed and
    stability; still a genuine ETS-style model with level + trend.
    """

    model_id = "exponential_smoothing"

    def __init__(self, alpha: float = 0.35, beta: float = 0.15) -> None:
        self.alpha = alpha
        self.beta = beta

    def requires_min_obs(self) -> int:
        return 21

    def fit_predict(self, history: np.ndarray, horizon: int) -> ModelForecast:
        clean = history.copy()
        if np.any(np.isnan(clean)):
            nans = np.isnan(clean)
            if nans.all():
                z = np.zeros(horizon)
                return ModelForecast(point=z, lower=z.copy(), upper=z.copy(), model_id=self.model_id)
            x = np.arange(len(clean))
            clean[nans] = np.interp(x[nans], x[~nans], clean[~nans])

        level = float(clean[0])
        trend = float(clean[1] - clean[0]) if len(clean) > 1 else 0.0
        fitted = np.empty(len(clean), dtype=float)
        fitted[0] = level
        for i in range(1, len(clean)):
            value = float(clean[i])
            prev_level = level
            level = self.alpha * value + (1 - self.alpha) * (level + trend)
            trend = self.beta * (level - prev_level) + (1 - self.beta) * trend
            fitted[i] = level + trend

        point = np.array([max(0.0, level + (h + 1) * trend) for h in range(horizon)], dtype=float)
        resid = clean - fitted
        sigma = float(np.nanstd(resid)) if len(resid) > 1 else 0.0
        lower = np.maximum(0.0, point - 1.96 * sigma)
        upper = point + 1.96 * sigma
        return ModelForecast(point=point, lower=lower, upper=upper, model_id=self.model_id)


def zero_fraction(history: np.ndarray) -> float:
    clean = history[~np.isnan(history)]
    if len(clean) == 0:
        return 1.0
    return float(np.mean(clean == 0))


def candidate_models_for_series(history: np.ndarray) -> list[BaseForecaster]:
    """Select candidate models based on data characteristics."""
    clean = history[~np.isnan(history)]
    n = len(clean)
    models: list[BaseForecaster] = [MovingAverageForecaster(7), WeightedMovingAverageForecaster(14)]

    if n >= 14:
        models.append(IntermittentCrostonForecaster())
    if n >= 14 and zero_fraction(history) < 0.45:
        models.append(SeasonalNaiveForecaster())
    if n >= 21 and zero_fraction(history) < 0.55:
        models.append(ExponentialSmoothingForecaster())

    # Prefer intermittent when sparse
    if zero_fraction(history) >= 0.45:
        models = [m for m in models if m.model_id in {"intermittent_croston", "moving_average", "weighted_moving_average"}]
        if not any(m.model_id == "intermittent_croston" for m in models) and n >= 14:
            models.append(IntermittentCrostonForecaster())

    return models