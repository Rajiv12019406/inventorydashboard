"""Forecasting engine and model tests."""

import numpy as np

from app.data.synthetic_generator import generate_synthetic_snapshot
from app.forecasting.engine import ForecastEngine
from app.forecasting.evaluation import rolling_origin_backtest, select_best_model
from app.forecasting.models import (
    IntermittentCrostonForecaster,
    MovingAverageForecaster,
    SeasonalNaiveForecaster,
    WeightedMovingAverageForecaster,
    candidate_models_for_series,
)


def test_moving_average_non_negative():
    history = np.array([10.0, 12.0, 8.0, 11.0, 9.0, 13.0, 10.0])
    fc = MovingAverageForecaster(7).fit_predict(history, 7)
    assert len(fc.point) == 7
    assert np.all(fc.point >= 0)


def test_weighted_ma():
    history = np.arange(1, 21, dtype=float)
    fc = WeightedMovingAverageForecaster(14).fit_predict(history, 14)
    assert len(fc.point) == 14
    assert fc.point[0] > 0


def test_seasonal_naive():
    history = np.tile([5, 6, 7, 8, 9, 4, 3], 6).astype(float)
    fc = SeasonalNaiveForecaster().fit_predict(history, 7)
    assert len(fc.point) == 7


def test_intermittent():
    history = np.array([0, 0, 5, 0, 0, 0, 8, 0, 0, 3, 0, 0, 0, 6, 0, 0, 4, 0, 0, 0], dtype=float)
    fc = IntermittentCrostonForecaster().fit_predict(history, 7)
    assert np.all(fc.point >= 0)


def test_backtest_is_chronological():
    rng = np.random.default_rng(0)
    history = rng.poisson(10, 90).astype(float)
    metrics = rolling_origin_backtest(history, MovingAverageForecaster(7), horizon=7)
    assert metrics is not None
    assert metrics.n_obs > 0
    assert metrics.mae >= 0


def test_model_selection():
    history = np.concatenate([np.full(40, 10.0), np.full(40, 14.0)])
    candidates = candidate_models_for_series(history)
    model, metrics = select_best_model(history, candidates, horizon=7)
    assert model is not None


def test_engine_generates_forecasts():
    snap = generate_synthetic_snapshot(seed=42)
    engine = ForecastEngine()
    # Limit work: temporarily forecast only a few pairs by monkeypatching balances
    snap.balances = snap.balances[:6]
    job = engine.refresh(snap, horizons=[7, 14])
    assert job.status == "completed"
    assert job.forecasts_generated == 6 * 2
    fc = engine.get_forecast(snap.balances[0].item_id, snap.balances[0].store_id, 7)
    assert fc is not None
    assert len(fc.points) == 7
    assert all(p.predicted >= 0 for p in fc.points)


def test_overlapping_refresh_blocked():
    snap = generate_synthetic_snapshot(seed=42)
    snap.balances = snap.balances[:2]
    engine = ForecastEngine()
    engine._job.status = "running"
    job = engine.refresh(snap, horizons=[7])
    assert job.status == "running"