# MediStock Intelligence

**Hospital Inventory Forecasting & Risk Analytics**

> **DEMO MODE · SYNTHETIC DATA** — All inventory, consumption, batches, and forecasts are fictional. No Microsoft SQL Server or real hospital database is connected.

MediStock Intelligence is a premium analytics dashboard that:

- Generates a deterministic synthetic hospital inventory dataset (150 items × 4 stores × 365 days)
- Runs genuine demand forecasting (moving average, weighted MA, seasonal naïve, Croston intermittent, exponential smoothing)
- Projects stockout risk, expiry risk, and explainable reorder recommendations
- Exposes results through a FastAPI backend consumed by a React analytics UI

## Architecture

```
frontend/          React + TypeScript + Vite + Tailwind + Recharts
backend/
  app/data/        InventoryDataProvider + SyntheticInventoryDataProvider
  app/forecasting/ Model zoo, chronological backtesting, ForecastEngine
  app/services/    Stockout / expiry / reorder / dashboard aggregation
  app/api/         FastAPI routes under /api/v1
  tests/           Calculation and API tests
```

### Replaceable data provider

`InventoryDataProvider` abstracts data loading. The app currently uses `SyntheticInventoryDataProvider`. A documented `SqlServerInventoryDataProvider` stub exists for a future phase — forecasting and UI schemas stay stable.

**Projected stock formula**

```
projected_stock[t] = current_usable_stock
                   + incoming receipts with expected_date ≤ t
                   − cumulative forecast demand through t
```

**Reorder policy**

```
target_stock = forecast_demand_during_lead_time + safety_stock
suggested_qty = max(0, ceil(target_stock − projected_stock_at_lead))
```

If supplier lead time exceeds the forecast horizon, the UI/API states the limitation and does **not** silently extrapolate.

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 20+

### Backend

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/api/v1/system/health

On startup the API becomes available immediately while forecasts generate in a background thread (typically under a minute with the fast Holt ETS implementation). Check `/api/v1/system/health` → `forecast_job.status` until `completed`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173  
Vite proxies `/api` → `http://127.0.0.1:8000`.

### Tests

```bash
cd backend
.\.venv\Scripts\Activate.ps1   # if needed
$env:PYTHONPATH = (Get-Location).Path   # Windows PowerShell
pytest tests -q
```

## Key API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/dashboard/summary` | KPI + risk distribution |
| GET | `/api/v1/dashboard/trends` | Actual + forecast series |
| GET | `/api/v1/inventory/forecasts/{item_id}` | Item forecast detail |
| GET | `/api/v1/inventory/stockout-risks` | Stockout table |
| GET | `/api/v1/inventory/expiry-risks` | Batch expiry table |
| GET | `/api/v1/inventory/reorder-recommendations` | Reorder advice |
| GET | `/api/v1/forecast-evaluations` | Backtest metrics |
| GET | `/api/v1/system/health` | Provider + job health |
| POST | `/api/v1/forecasts/refresh` | Re-run forecast pipeline |

## Synthetic data assumptions

- Fixed seed `42` (configurable via `SYNTHETIC_SEED`)
- 150 SKUs, 5 categories, 4 stores, 365 daily observations
- Demand patterns: stable, trending, weekly seasonal, spikes, intermittent, zero windows
- Controlled edge cases: ~3% missing observations, 8 insufficient-history pairs
- Fictional item codes, names, batches, and locations only

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Frontend API errors / CORS | Ensure backend is on port 8000; check `CORS_ORIGINS` |
| Forecasts empty / slow first load | Wait for lifespan forecast job; check `/api/v1/system/health` |
| `ModuleNotFoundError: app` | Set `PYTHONPATH` to the `backend` directory |
| Port 5173 in use | `npm run dev -- --port 5174` |
| Want fresh forecasts | Use **Refresh forecasts** on Overview, or `POST /api/v1/forecasts/refresh` |

## What this is not

- Not a full inventory management / CRUD system
- Not connected to SQL Server or any real hospital system
- Not a purchase-order workflow — recommendations are advisory only
