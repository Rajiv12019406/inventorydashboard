"""Stockout and reorder calculation tests."""

from datetime import date, datetime, timezone, timedelta

from app.data.models import IncomingReceipt, InventoryItem, StockBalance
from app.forecasting.engine import ForecastPoint, ForecastResult
from app.services.risk import assess_expiry, assess_stockout, project_stock, recommend_reorder
from app.data.models import BatchLot


def _item(**kwargs):
    defaults = dict(
        item_id="ITM-001",
        item_code="MS-MED-0001",
        name="Test Item",
        category_id="CAT-MED",
        unit="tabs",
        min_stock=20,
        safety_stock=15,
        supplier_lead_time_days=5,
        demand_pattern="stable",
    )
    defaults.update(kwargs)
    return InventoryItem(**defaults)


def _forecast(daily: float, horizon: int = 14, start: date | None = None) -> ForecastResult:
    start = start or date(2026, 10, 23)
    points = [
        ForecastPoint(date=start + timedelta(days=i), predicted=daily, lower=daily * 0.8, upper=daily * 1.2)
        for i in range(horizon)
    ]
    return ForecastResult(
        item_id="ITM-001",
        store_id="ST-MAIN",
        horizon_days=horizon,
        model_id="moving_average",
        generated_at=datetime.now(timezone.utc),
        data_through=start - timedelta(days=1),
        data_quality="ok",
        points=points,
    )


def test_projected_stock_formula():
    fc = _forecast(10, horizon=5)  # points start 2026-10-23
    bal_stock = 40
    incoming = [
        IncomingReceipt("R1", "ITM-001", "ST-MAIN", 20, date(2026, 10, 24)),
    ]
    projection = project_stock(bal_stock, fc, incoming, as_of=date(2026, 10, 22))
    # Day1 (10-23): 40-10=30; Day2 (10-24): 30+20-10=40
    assert projection[0].closing == 30
    assert projection[1].incoming == 20
    assert projection[1].closing == 40


def test_stockout_critical_within_3_days():
    item = _item()
    bal = StockBalance("ITM-001", "ST-MAIN", 15, date(2026, 10, 22))
    fc = _forecast(10, horizon=14)
    assessment = assess_stockout(item, bal, fc, [], avg_daily=10)
    assert assessment.risk_level == "critical"
    assert assessment.predicted_stockout_date is not None


def test_reorder_suggestion_explainable():
    item = _item(safety_stock=20, supplier_lead_time_days=5)
    bal = StockBalance("ITM-001", "ST-MAIN", 10, date(2026, 10, 22))
    fc = _forecast(8, horizon=14)
    rec = recommend_reorder(item, bal, fc, [], avg_daily=8)
    assert rec is not None
    assert rec.suggested_reorder_qty > 0
    assert len(rec.calculation_steps) >= 5
    assert "Target stock" in rec.calculation_steps[3]


def test_no_silent_lead_time_extrapolation():
    item = _item(supplier_lead_time_days=30, safety_stock=10)
    bal = StockBalance("ITM-001", "ST-MAIN", 5, date(2026, 10, 22))
    fc = _forecast(5, horizon=14)
    rec = recommend_reorder(item, bal, fc, [], avg_daily=5)
    assert rec is not None
    assert rec.horizon_limitation is True
    assert "exceeds" in rec.reason.lower() or "limitation" in rec.reason.lower()


def test_expiry_never_recommends_issuing_expired():
    batch = BatchLot(
        batch_id="BAT-1",
        item_id="ITM-001",
        store_id="ST-MAIN",
        available_qty=50,
        expiry_date=date(2026, 10, 1),
        received_date=date(2026, 1, 1),
    )
    assessment = assess_expiry(batch, as_of=date(2026, 10, 22))
    assert assessment.risk_status == "expired"
    assert "do not issue" in assessment.fefo_note.lower()