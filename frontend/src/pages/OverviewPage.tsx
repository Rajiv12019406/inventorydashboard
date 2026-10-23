import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import {
  AlertTriangle,
  Boxes,
  CalendarClock,
  PackageMinus,
  PackagePlus,
} from 'lucide-react'
import { DemandForecastChart, type DemandChartPoint } from '@/components/charts/DemandForecastChart'
import { HorizontalBarChart } from '@/components/charts/HorizontalBarChart'
import { RiskDistributionChart } from '@/components/charts/RiskDistributionChart'
import { GlobalFiltersBar } from '@/components/filters/GlobalFilters'
import { ItemDetailDrawer } from '@/components/ItemDetailDrawer'
import { DataTable } from '@/components/tables/DataTable'
import { RiskBadge } from '@/components/ui/Badge'
import { KpiCard } from '@/components/ui/KpiCard'
import { ErrorState, PageHeader, Panel, Skeleton } from '@/components/ui/Panel'
import { useFilters } from '@/context/FilterContext'
import { formatDate, formatNumber } from '@/lib/utils'
import { api } from '@/services/api'
import type { PriorityAction } from '@/types/api'

export function OverviewPage() {
  const { filters, apiParams } = useFilters()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [selected, setSelected] = useState<{ itemId: string; storeId: string } | null>(null)

  const summaryQ = useQuery({
    queryKey: ['summary', apiParams],
    queryFn: () => api.summary(apiParams),
  })
  const trendsQ = useQuery({
    queryKey: ['trends', apiParams, filters.lookbackDays, filters.aggregation],
    queryFn: () =>
      api.trends({
        ...apiParams,
        lookback_days: filters.lookbackDays,
        aggregation: filters.aggregation,
      }),
  })
  const rankingQ = useQuery({
    queryKey: ['ranking', apiParams],
    queryFn: () => api.stockoutRanking({ ...apiParams, by: 'category', limit: 8 }),
  })
  const actionsQ = useQuery({
    queryKey: ['priority', apiParams],
    queryFn: () => api.priorityActions({ ...apiParams, page_size: 100 }),
  })

  const refreshMut = useMutation({
    mutationFn: api.refreshForecasts,
    onSuccess: () => {
      qc.invalidateQueries()
    },
  })

  const chartData: DemandChartPoint[] = useMemo(() => {
    if (!trendsQ.data) return []
    const map = new Map<string, DemandChartPoint>()
    trendsQ.data.actual.forEach((a) => map.set(a.date, { date: a.date, actual: a.actual }))
    trendsQ.data.forecast.forEach((f) => {
      const existing = map.get(f.date) ?? { date: f.date }
      map.set(f.date, {
        ...existing,
        predicted: f.predicted,
        lower: f.lower,
        upper: f.upper,
      })
    })
    return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date))
  }, [trendsQ.data])

  const columns = useMemo<ColumnDef<PriorityAction, unknown>[]>(
    () => [
      {
        accessorKey: 'item_name',
        header: 'Item',
        cell: ({ row }) => (
          <div>
            <p className="font-medium text-ink">{row.original.item_name}</p>
            <p className="text-[11px] text-ink-subtle">{row.original.item_code}</p>
          </div>
        ),
      },
      { accessorKey: 'category_name', header: 'Category' },
      { accessorKey: 'store_name', header: 'Store' },
      {
        accessorKey: 'current_stock',
        header: 'Stock',
        cell: ({ getValue }) => formatNumber(getValue<number>(), 1),
      },
      {
        accessorKey: 'days_of_cover',
        header: 'Days cover',
        cell: ({ getValue }) => {
          const v = getValue<number | null>()
          return v == null ? '—' : formatNumber(v, 1)
        },
      },
      {
        accessorKey: 'predicted_stockout_date',
        header: 'Stockout',
        cell: ({ getValue }) => formatDate(getValue<string | null>()),
      },
      {
        accessorKey: 'suggested_reorder_qty',
        header: 'Reorder qty',
        cell: ({ getValue }) => formatNumber(getValue<number>()),
      },
      {
        accessorKey: 'risk_status',
        header: 'Risk',
        cell: ({ getValue }) => <RiskBadge level={String(getValue())} />,
      },
    ],
    [],
  )

  const s = summaryQ.data

  return (
    <div>
      <PageHeader
        title="Inventory Intelligence"
        subtitle="Predicted demand, stockout exposure, and expiry risk across synthetic hospital stores — advisory analytics only."
      />
      <GlobalFiltersBar
        forecastGeneratedAt={s?.forecast_generated_at}
        onRefresh={() => refreshMut.mutate()}
        refreshing={refreshMut.isPending}
      />

      {summaryQ.isError ? (
        <ErrorState message={(summaryQ.error as Error).message} onRetry={() => summaryQ.refetch()} />
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {summaryQ.isLoading || !s ? (
          Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-28" />)
        ) : (
          <>
            <KpiCard label="Active items" value={formatNumber(s.active_items)} icon={Boxes} hint="Distinct SKUs in scope" />
            <KpiCard
              label="Low-stock items"
              value={formatNumber(s.low_stock_items)}
              icon={PackageMinus}
              tone="warning"
              hint="At or below minimum stock"
            />
            <KpiCard
              label="Stockout risk ≤7d"
              value={formatNumber(s.stockout_risk_7d)}
              icon={AlertTriangle}
              tone="critical"
              hint="Critical or high projected stockouts"
            />
            <KpiCard
              label="Approaching expiry"
              value={formatNumber(s.approaching_expiry)}
              icon={CalendarClock}
              tone="warning"
              hint="Batches expiring within 30 days"
            />
            <KpiCard
              label="Reorder required"
              value={formatNumber(s.reorder_required)}
              icon={PackagePlus}
              tone="accent"
              hint="Below target-stock policy"
            />
          </>
        )}
      </div>

      {s ? (
        <div className="mt-3 grid grid-cols-3 gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-ink-subtle">Expired stock</p>
            <p className="mt-0.5 font-semibold text-risk-critical">{formatNumber(s.expired_qty, 1)}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-ink-subtle">14-day stockout risk</p>
            <p className="mt-0.5 font-semibold text-ink">{formatNumber(s.stockout_risk_14d)}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-ink-subtle">
              Forecasted demand ({filters.horizon}d)
            </p>
            <p className="mt-0.5 font-semibold text-ink">{formatNumber(s.forecasted_demand, 1)}</p>
          </div>
        </div>
      ) : null}

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Panel
          className="xl:col-span-2"
          title="Demand forecast"
          subtitle="Solid navy = historical actuals · dashed teal = model forecast · band = prediction interval"
        >
          {trendsQ.isLoading ? <Skeleton className="h-80" /> : null}
          {trendsQ.data ? (
            <DemandForecastChart data={chartData} historyEnd={trendsQ.data.history_end} />
          ) : null}
        </Panel>
        <Panel title="Inventory risk distribution" subtitle="Click a segment to open stockout intelligence">
          {s ? (
            <RiskDistributionChart
              distribution={s.risk_distribution}
              onSelect={(level) => navigate(`/stockouts?risk=${level}`)}
            />
          ) : (
            <Skeleton className="h-48" />
          )}
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Panel title="Stockout risk ranking" subtitle="Category exposure from projected cover shortfalls">
          {rankingQ.isLoading ? <Skeleton className="h-64" /> : null}
          {rankingQ.data ? (
            <HorizontalBarChart
              data={rankingQ.data.map((r) => ({ label: r.label, value: r.exposure }))}
            />
          ) : null}
        </Panel>
        <Panel title="Consumption trend" subtitle={`Recent ${filters.aggregation} actual demand (filters applied)`}>
          {trendsQ.data ? (
            <DemandForecastChart
              data={trendsQ.data.actual.map((a) => ({ date: a.date, actual: a.actual }))}
              height={280}
            />
          ) : (
            <Skeleton className="h-64" />
          )}
        </Panel>
      </div>

      <Panel className="mt-5" title="Requires attention" subtitle="Priority stockout and reorder actions">
        {actionsQ.isLoading ? <Skeleton className="h-64" /> : null}
        {actionsQ.data ? (
          <DataTable
            data={actionsQ.data.items}
            columns={columns}
            searchPlaceholder="Search item, store, category…"
            onRowClick={(row) => setSelected({ itemId: row.item_id, storeId: row.store_id })}
            emptyTitle="Nothing requires attention"
            emptyDescription="No items match the current filters for priority action."
          />
        ) : null}
      </Panel>

      {selected ? (
        <ItemDetailDrawer
          itemId={selected.itemId}
          storeId={selected.storeId}
          onClose={() => setSelected(null)}
        />
      ) : null}
    </div>
  )
}