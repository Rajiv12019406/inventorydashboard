import type {
  DashboardSummary,
  ExpiryRiskRow,
  ExpirySummary,
  FilterOptions,
  ForecastDetail,
  ForecastEvaluationResponse,
  HealthResponse,
  InventoryItem,
  Paginated,
  PriorityAction,
  RankingRow,
  ReorderRecommendation,
  StockoutRisk,
  TrendsResponse,
} from '@/types/api'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.set(k, String(v))
  })
  const s = q.toString()
  return s ? `?${s}` : ''
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  filters: () => request<FilterOptions>('/filters'),

  summary: (params: { store_id?: string; category_id?: string; horizon?: number }) =>
    request<DashboardSummary>(`/dashboard/summary${buildQuery(params)}`),

  trends: (params: {
    store_id?: string
    category_id?: string
    item_id?: string
    aggregation?: string
    lookback_days?: number
    horizon?: number
  }) => request<TrendsResponse>(`/dashboard/trends${buildQuery(params)}`),

  stockoutRanking: (params: {
    store_id?: string
    category_id?: string
    by?: string
    horizon?: number
    limit?: number
  }) => request<RankingRow[]>(`/dashboard/stockout-ranking${buildQuery(params)}`),

  priorityActions: (params: {
    store_id?: string
    category_id?: string
    search?: string
    horizon?: number
    page?: number
    page_size?: number
  }) => request<Paginated<PriorityAction>>(`/dashboard/priority-actions${buildQuery(params)}`),

  items: (params: {
    store_id?: string
    category_id?: string
    search?: string
    page?: number
    page_size?: number
  }) => request<Paginated<InventoryItem>>(`/inventory/items${buildQuery(params)}`),

  forecastDetail: (itemId: string, params: { store_id: string; horizon?: number }) =>
    request<ForecastDetail>(`/inventory/forecasts/${itemId}${buildQuery(params)}`),

  stockoutRisks: (params: {
    store_id?: string
    category_id?: string
    risk_level?: string
    search?: string
    horizon?: number
    page?: number
    page_size?: number
  }) => request<Paginated<StockoutRisk>>(`/inventory/stockout-risks${buildQuery(params)}`),

  expiryRisks: (params: {
    store_id?: string
    category_id?: string
    search?: string
    page?: number
    page_size?: number
  }) => request<Paginated<ExpiryRiskRow>>(`/inventory/expiry-risks${buildQuery(params)}`),

  expirySummary: (params: { store_id?: string; category_id?: string }) =>
    request<ExpirySummary>(`/inventory/expiry-summary${buildQuery(params)}`),

  reorderRecommendations: (params: {
    store_id?: string
    category_id?: string
    search?: string
    horizon?: number
    page?: number
    page_size?: number
  }) =>
    request<Paginated<ReorderRecommendation>>(
      `/inventory/reorder-recommendations${buildQuery(params)}`,
    ),

  evaluations: () => request<ForecastEvaluationResponse>('/forecast-evaluations'),

  health: () => request<HealthResponse>('/system/health'),

  refreshForecasts: () =>
    request<{
      status: string
      duration_seconds: number | null
      forecasts_generated: number
      last_run_at: string | null
      error: string | null
    }>('/forecasts/refresh', { method: 'POST' }),
}