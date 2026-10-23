export type RiskLevel = 'critical' | 'high' | 'medium' | 'low'
export type ExpiryRisk = 'expired' | 'critical' | 'high' | 'medium' | 'low'

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface FilterOptions {
  stores: { store_id: string; name: string }[]
  categories: { category_id: string; name: string }[]
  horizons: number[]
}

export interface DashboardSummary {
  active_items: number
  low_stock_items: number
  low_stock_delta_pct: number | null
  stockout_risk_7d: number
  stockout_risk_14d: number
  approaching_expiry: number
  expired_qty: number
  reorder_required: number
  forecasted_demand: number
  risk_distribution: Record<RiskLevel, number>
  as_of_date: string
  forecast_generated_at: string | null
  provider: string
}

export interface TrendsResponse {
  aggregation: string
  history_end: string
  actual: { date: string; actual: number }[]
  forecast: { date: string; predicted: number; lower: number | null; upper: number | null }[]
}

export interface PriorityAction {
  item_id: string
  item_code: string
  item_name: string
  category_id: string
  category_name: string
  store_id: string
  store_name: string
  current_stock: number
  days_of_cover: number | null
  predicted_stockout_date: string | null
  suggested_reorder_qty: number
  risk_status: string
}

export interface StockoutRisk {
  item_id: string
  item_code: string
  item_name: string
  store_id: string
  store_name: string
  category_name: string
  current_usable_stock: number
  avg_daily_consumption: number
  days_of_cover: number | null
  predicted_stockout_date: string | null
  expected_incoming_stock: number
  supplier_lead_time_days: number
  risk_level: RiskLevel
  explanation: string
  data_quality: string
}

export interface ExpiryRiskRow {
  batch_id: string
  item_id: string
  item_code: string
  item_name: string
  store_id: string
  store_name: string
  category_name: string
  available_qty: number
  expiry_date: string
  days_until_expiry: number
  risk_status: ExpiryRisk
  fefo_note: string
}

export interface ExpirySummary {
  expired_qty: number
  expired_batches: number
  within_7_days_qty: number
  within_7_days_batches: number
  within_30_days_qty: number
  within_30_days_batches: number
  within_90_days_qty: number
  within_90_days_batches: number
  by_category: { category: string; qty: number }[]
}

export interface ReorderRecommendation {
  item_id: string
  item_code: string
  item_name: string
  store_id: string
  store_name: string
  category_name: string
  current_usable_stock: number
  forecast_demand_lead_time: number
  incoming_qty: number
  safety_stock: number
  projected_stock_at_lead: number | null
  suggested_reorder_qty: number
  estimated_days_of_cover: number | null
  reason: string
  data_quality: string
  calculation_steps: string[]
  lead_time_days: number
  horizon_limitation: boolean
}

export interface ForecastDetail {
  item_id: string
  store_id: string
  horizon_days: number
  model_id: string
  generated_at: string
  data_through: string
  data_quality: string
  points: { date: string; predicted: number; lower: number | null; upper: number | null }[]
  limitations: string[]
  mae: number | null
  wape: number | null
  bias: number | null
  item_code: string
  item_name: string
  store_name: string
  category_name: string
  current_stock: number
  avg_daily_consumption: number
  recent_trend: string
  forecast_total: number
  estimated_days_of_cover: number | null
  expected_stockout_date: string | null
  history: { date: string; actual: number | null }[]
}

export interface InventoryItem {
  item_id: string
  item_code: string
  name: string
  category_id: string
  category_name: string
  unit: string
  min_stock: number
  safety_stock: number
  supplier_lead_time_days: number
  demand_pattern: string
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  app: string
  version: string
  provider: string
  provider_ready: boolean
  forecast_job: Record<string, unknown>
  dataset: Record<string, unknown>
  checks: { name: string; status: string; detail: string }[]
}

export interface ForecastEvaluationResponse {
  status: string
  message: string
  evaluation_period?: { start: string; end: string }
  models: {
    model_id: string
    series_count: number
    mae: number | null
    wape: number | null
    bias: number | null
    n_obs: number
  }[]
  overall: {
    mae: number | null
    wape: number | null
    bias: number | null
    n_obs: number
    series_evaluated: number
  } | null
  series?: {
    item_id: string
    store_id: string
    model_id: string
    mae: number | null
    wape: number | null
    bias: number | null
    n_obs: number
  }[]
}

export interface RankingRow {
  id: string
  label: string
  exposure: number
}

export interface GlobalFilters {
  storeId: string
  categoryId: string
  horizon: number
  lookbackDays: number
  aggregation: 'daily' | 'weekly'
  search: string
}