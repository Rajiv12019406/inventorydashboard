"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from app.forecasting.engine import forecast_engine
from app.main import app


@pytest.fixture(scope="module")
def client():
    # Reset engine so lifespan / first call regenerates cleanly
    forecast_engine.clear()
    with TestClient(app) as c:
        yield c


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "SYNTHETIC" in r.json()["mode"]


def test_health(client):
    r = client.get("/api/v1/system/health")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "Synthetic Data"
    assert body["provider_ready"] is True
    assert body["dataset"]["item_count"] == 150


def test_dashboard_summary(client):
    r = client.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["active_items"] == 150
    assert "risk_distribution" in body
    assert body["provider"] == "Synthetic Data"


def test_trends(client):
    r = client.get("/api/v1/dashboard/trends", params={"horizon": 14})
    assert r.status_code == 200
    body = r.json()
    assert len(body["actual"]) > 0
    assert len(body["forecast"]) == 14


def test_stockout_risks(client):
    r = client.get("/api/v1/inventory/stockout-risks", params={"page_size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["items"]) <= 10


def test_expiry_risks(client):
    r = client.get("/api/v1/inventory/expiry-risks", params={"page_size": 5})
    assert r.status_code == 200
    assert r.json()["total"] > 0


def test_reorder_recommendations(client):
    r = client.get("/api/v1/inventory/reorder-recommendations", params={"page_size": 5})
    assert r.status_code == 200
    body = r.json()
    if body["total"] > 0:
        assert "calculation_steps" in body["items"][0]


def test_forecast_evaluations(client):
    r = client.get("/api/v1/forecast-evaluations")
    assert r.status_code == 200
    assert "status" in r.json()


def test_filters(client):
    r = client.get("/api/v1/filters")
    assert r.status_code == 200
    body = r.json()
    assert len(body["stores"]) == 4
    assert len(body["categories"]) == 5


def test_refresh_forecasts(client):
    r = client.post("/api/v1/forecasts/refresh")
    assert r.status_code == 200
    assert r.json()["status"] in {"completed", "running"}