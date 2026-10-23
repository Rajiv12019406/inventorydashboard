"""Chronological backtesting utilities for forecast model selection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.forecasting.models import BaseForecaster


@dataclass
class EvalMetrics:
    mae: float
    wape: float | None
    bias: float
    n_obs: int


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def wape(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    denom = float(np.sum(np.abs(actual)))
    if denom <= 0:
        return None
    return float(np.sum(np.abs(actual - predicted)) / denom)


def bias(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean forecast error (predicted - actual). Positive => over-forecast."""
    return float(np.mean(predicted - actual))


def rolling_origin_backtest(
    history: np.ndarray,
    model: BaseForecaster,
    horizon: int = 7,
    min_train: int | None = None,
    max_origins: int = 4,
) -> EvalMetrics | None:
    """Rolling-origin evaluation preserving chronological order.

    Does not shuffle time series. Returns None when insufficient history.
    """
    clean = history.copy()
    # Drop leading nans
    valid_idx = np.where(~np.isnan(clean))[0]
    if len(valid_idx) == 0:
        return None
    series = clean[valid_idx[0] :]
    # Remaining internal nans -> interpolate for evaluation stability
    if np.any(np.isnan(series)):
        nans = np.isnan(series)
        x = np.arange(len(series))
        if (~nans).sum() < 2:
            return None
        series = series.copy()
        series[nans] = np.interp(x[nans], x[~nans], series[~nans])

    min_train = min_train or max(model.requires_min_obs(), horizon + 7)
    if len(series) < min_train + horizon:
        return None

    origins = list(range(min_train, len(series) - horizon + 1))
    if len(origins) > max_origins:
        # Evenly spaced origins toward the end of history
        step = max(1, len(origins) // max_origins)
        origins = origins[::step][-max_origins:]

    errors: list[float] = []
    actuals: list[float] = []
    preds: list[float] = []

    for origin in origins:
        train = series[:origin]
        actual = series[origin : origin + horizon]
        try:
            fc = model.fit_predict(train, horizon)
        except Exception:
            continue
        pred = fc.point
        errors.extend(np.abs(actual - pred).tolist())
        actuals.extend(actual.tolist())
        preds.extend(pred.tolist())

    if not actuals:
        return None

    a = np.asarray(actuals, dtype=float)
    p = np.asarray(preds, dtype=float)
    return EvalMetrics(mae=mae(a, p), wape=wape(a, p), bias=bias(a, p), n_obs=len(a))


def select_best_model(
    history: np.ndarray,
    candidates: list[BaseForecaster],
    horizon: int = 7,
) -> tuple[BaseForecaster, EvalMetrics | None]:
    """Pick the model with lowest MAE; fall back to first candidate."""
    if not candidates:
        from app.forecasting.models import MovingAverageForecaster

        return MovingAverageForecaster(), None

    best = candidates[0]
    best_metrics: EvalMetrics | None = None
    best_score = float("inf")

    for model in candidates:
        metrics = rolling_origin_backtest(history, model, horizon=horizon)
        if metrics is None:
            continue
        score = metrics.mae
        if score < best_score:
            best_score = score
            best = model
            best_metrics = metrics

    return best, best_metrics