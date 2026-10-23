import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DemandForecastChart, type DemandChartPoint } from '@/components/charts/DemandForecastChart'
import { GlobalFiltersBar } from '@/components/filters/GlobalFilters'
import { RiskBadge } from '@/components/ui/Badge'
import { ErrorState, PageHeader, Panel, Skeleton } from '@/components/ui/Panel'
import { SearchInput, SelectField } from '@/components/ui/Select'
import { useFilters } from '@/context/FilterContext'
import { formatDate, formatDateTime, formatNumber } from '@/lib/utils'
import { api } from '@/services/api'

export function ForecastsPage() {
  const { filters, apiParams, setHorizon, setStoreId } = useFilters()
  const [search, setSearch] = useState('')
  const [itemId, setItemId] = useState('')

  const itemsQ = useQuery({
    queryKey: ['items', apiParams.category_id, search],
    queryFn: () =>
      api.items({
        category_id: apiParams.category_id,
        search: search || undefined,
        page_size: 100,
      }),
  })

  const selectedItem = itemsQ.data?.items.find((i) => i.item_id === itemId) ?? itemsQ.data?.items[0]
  const effectiveItemId = selectedItem?.item_id ?? ''
  const storeId = filters.storeId || 'ST-MAIN'

  const detailQ = useQuery({
    queryKey: ['forecast-detail', effectiveItemId, storeId, filters.horizon],
    queryFn: () =>
      api.forecastDetail(effectiveItemId, { store_id: storeId, horizon: filters.horizon }),
    enabled: Boolean(effectiveItemId),
  })

  const chartData: DemandChartPoint[] = useMemo(() => {
    if (!detailQ.data) return []
    const rows: DemandChartPoint[] = detailQ.data.history.map((h) => ({
      date: h.date,
      actual: h.actual,
    }))
    detailQ.data.points.forEach((p) =>
      rows.push({ date: p.date, predicted: p.predicted, lower: p.lower, upper: p.upper }),
    )
    return rows
  }, [detailQ.data])

  return (
    <div>
      <PageHeader
        title="Demand Forecasts"
        subtitle="Explore model-generated demand forecasts by item and store. Predictions come from the forecasting engine — not hardcoded chart values."
      />
      <GlobalFiltersBar forecastGeneratedAt={detailQ.data?.generated_at} />

      <div className="mb-5 grid gap-3 rounded-xl border border-border bg-surface p-3 md:grid-cols-3">
        <label className="flex flex-col gap-1 md:col-span-1">
          <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-ink-subtle">
            Search items
          </span>
          <SearchInput value={search} onChange={setSearch} placeholder="Name or code…" />
        </label>
        <SelectField
          label="Item"
          value={effectiveItemId}
          onChange={setItemId}
          options={
            itemsQ.data?.items.map((i) => ({
              value: i.item_id,
              label: `${i.item_code} — ${i.name}`,
            })) ?? []
          }
          className="md:col-span-1"
        />
        <SelectField
          label="Store"
          value={storeId}
          onChange={setStoreId}
          options={[
            { value: 'ST-MAIN', label: 'Main Campus Pharmacy' },
            { value: 'ST-ER', label: 'Emergency Department Store' },
            { value: 'ST-OR', label: 'Surgical Suite Inventory' },
            { value: 'ST-ICU', label: 'ICU Satellite Pharmacy' },
          ]}
        />
      </div>

      {detailQ.isError ? (
        <ErrorState message={(detailQ.error as Error).message} onRetry={() => detailQ.refetch()} />
      ) : null}

      <div className="grid gap-5 xl:grid-cols-3">
        <Panel className="xl:col-span-2" title="Historical consumption & forecast" subtitle="Interval shown when the selected model supports it">
          {detailQ.isLoading ? <Skeleton className="h-80" /> : null}
          {detailQ.data ? (
            <DemandForecastChart data={chartData} historyEnd={detailQ.data.data_through} />
          ) : null}
        </Panel>

        <Panel title="Item detail" subtitle="Forecast metadata and coverage">
          {detailQ.isLoading ? <Skeleton className="h-64" /> : null}
          {detailQ.data ? (
            <div className="space-y-3 text-sm">
              <Row label="Item" value={detailQ.data.item_name} />
              <Row label="Category" value={detailQ.data.category_name} />
              <Row label="Current stock" value={formatNumber(detailQ.data.current_stock, 1)} />
              <Row label="Avg daily" value={formatNumber(detailQ.data.avg_daily_consumption, 2)} />
              <Row label="Recent trend" value={detailQ.data.recent_trend} />
              <Row label="Forecast total" value={formatNumber(detailQ.data.forecast_total, 1)} />
              <Row
                label="Days of cover"
                value={
                  detailQ.data.estimated_days_of_cover != null
                    ? formatNumber(detailQ.data.estimated_days_of_cover, 1)
                    : '—'
                }
              />
              <Row
                label="Expected stockout"
                value={formatDate(detailQ.data.expected_stockout_date)}
              />
              <Row label="Model" value={detailQ.data.model_id.replaceAll('_', ' ')} />
              <Row label="Generated" value={formatDateTime(detailQ.data.generated_at)} />
              <Row label="Data through" value={formatDate(detailQ.data.data_through)} />
              <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
                <span className="text-ink-subtle">Data sufficiency</span>
                <RiskBadge level={detailQ.data.data_quality === 'ok' ? 'low' : 'medium'} />
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setHorizon(7)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium ${filters.horizon === 7 ? 'bg-navy-900 text-white' : 'border border-border'}`}
                >
                  7-day
                </button>
                <button
                  type="button"
                  onClick={() => setHorizon(14)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium ${filters.horizon === 14 ? 'bg-navy-900 text-white' : 'border border-border'}`}
                >
                  14-day
                </button>
              </div>
              {detailQ.data.limitations.length > 0 ? (
                <ul className="space-y-1.5 pt-2">
                  {detailQ.data.limitations.map((l) => (
                    <li key={l} className="rounded-lg bg-amber-50 px-2.5 py-2 text-xs text-amber-900">
                      {l}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </Panel>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-ink-subtle">{label}</span>
      <span className="text-right font-medium capitalize text-ink">{value}</span>
    </div>
  )
}