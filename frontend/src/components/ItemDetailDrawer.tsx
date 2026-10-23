import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { DemandForecastChart, type DemandChartPoint } from '@/components/charts/DemandForecastChart'
import { RiskBadge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Panel'
import { formatDate, formatNumber } from '@/lib/utils'
import { api } from '@/services/api'
import { useFilters } from '@/context/FilterContext'

export function ItemDetailDrawer({
  itemId,
  storeId,
  onClose,
}: {
  itemId: string
  storeId: string
  onClose: () => void
}) {
  const { filters } = useFilters()
  const { data, isLoading, error } = useQuery({
    queryKey: ['forecast-detail', itemId, storeId, filters.horizon],
    queryFn: () => api.forecastDetail(itemId, { store_id: storeId, horizon: filters.horizon }),
    enabled: Boolean(itemId && storeId),
  })

  const chartData: DemandChartPoint[] = []
  if (data) {
    data.history.forEach((h) => chartData.push({ date: h.date, actual: h.actual }))
    data.points.forEach((p) =>
      chartData.push({
        date: p.date,
        predicted: p.predicted,
        lower: p.lower,
        upper: p.upper,
      }),
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button type="button" className="absolute inset-0 bg-navy-950/40" onClick={onClose} aria-label="Close" />
      <aside className="relative z-10 flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-border bg-surface shadow-xl">
        <div className="sticky top-0 flex items-start justify-between gap-3 border-b border-border bg-surface px-5 py-4">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-ink-subtle">
              Item analytics
            </p>
            <h2 className="mt-1 text-lg font-semibold text-ink">
              {data?.item_name ?? 'Loading…'}
            </h2>
            <p className="text-xs text-ink-muted">
              {data?.item_code} · {data?.store_name}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border p-1.5 text-ink-muted hover:bg-surface-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-5 p-5">
          {isLoading ? <Skeleton className="h-40 w-full" /> : null}
          {error ? (
            <p className="text-sm text-risk-critical">{(error as Error).message}</p>
          ) : null}
          {data ? (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Metric label="Current stock" value={formatNumber(data.current_stock, 1)} />
                <Metric label="Avg daily use" value={formatNumber(data.avg_daily_consumption, 2)} />
                <Metric label="Forecast total" value={formatNumber(data.forecast_total, 1)} />
                <Metric
                  label="Days of cover"
                  value={data.estimated_days_of_cover != null ? formatNumber(data.estimated_days_of_cover, 1) : '—'}
                />
                <Metric label="Trend" value={data.recent_trend} />
                <Metric label="Model" value={data.model_id.replaceAll('_', ' ')} />
              </div>
              <div className="rounded-lg border border-border bg-surface-muted/40 px-3 py-2 text-xs text-ink-muted">
                <div className="flex flex-wrap items-center gap-2">
                  <span>Data quality</span>
                  <RiskBadge level={data.data_quality === 'ok' ? 'low' : 'medium'} />
                  <span>· Through {formatDate(data.data_through)}</span>
                  {data.expected_stockout_date ? (
                    <span>· Stockout {formatDate(data.expected_stockout_date)}</span>
                  ) : null}
                </div>
              </div>
              <DemandForecastChart data={chartData} historyEnd={data.data_through} height={260} />
              {data.limitations.length > 0 ? (
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-subtle">
                    Forecast limitations
                  </p>
                  <ul className="space-y-1.5">
                    {data.limitations.map((l) => (
                      <li key={l} className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
                        {l}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      </aside>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border px-3 py-2.5">
      <p className="text-[11px] uppercase tracking-wide text-ink-subtle">{label}</p>
      <p className="mt-1 text-sm font-semibold capitalize text-ink">{value}</p>
    </div>
  )
}