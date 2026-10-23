import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { ColumnDef } from '@tanstack/react-table'
import { GlobalFiltersBar } from '@/components/filters/GlobalFilters'
import { DataTable } from '@/components/tables/DataTable'
import { RiskBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Select'
import { ErrorState, PageHeader, Panel, Skeleton } from '@/components/ui/Panel'
import { SearchInput } from '@/components/ui/Select'
import { useFilters } from '@/context/FilterContext'
import { formatNumber } from '@/lib/utils'
import { api } from '@/services/api'
import type { ReorderRecommendation } from '@/types/api'
import { X } from 'lucide-react'

export function ReordersPage() {
  const { apiParams } = useFilters()
  const [search, setSearch] = useState('')
  const [detail, setDetail] = useState<ReorderRecommendation | null>(null)

  const recsQ = useQuery({
    queryKey: ['reorders', apiParams, search],
    queryFn: () =>
      api.reorderRecommendations({
        ...apiParams,
        search: search || undefined,
        page_size: 200,
      }),
  })

  const columns = useMemo<ColumnDef<ReorderRecommendation, unknown>[]>(
    () => [
      {
        accessorKey: 'item_name',
        header: 'Item',
        cell: ({ row }) => (
          <div>
            <p className="font-medium">{row.original.item_name}</p>
            <p className="text-[11px] text-ink-subtle">
              {row.original.item_code} · {row.original.store_name}
            </p>
          </div>
        ),
      },
      {
        accessorKey: 'current_usable_stock',
        header: 'Current stock',
        cell: ({ getValue }) => formatNumber(getValue<number>(), 1),
      },
      {
        accessorKey: 'forecast_demand_lead_time',
        header: 'Demand in lead time',
        cell: ({ getValue }) => formatNumber(getValue<number>(), 1),
      },
      {
        accessorKey: 'incoming_qty',
        header: 'Incoming',
        cell: ({ getValue }) => formatNumber(getValue<number>(), 1),
      },
      {
        accessorKey: 'safety_stock',
        header: 'Safety stock',
        cell: ({ getValue }) => formatNumber(getValue<number>(), 1),
      },
      {
        accessorKey: 'projected_stock_at_lead',
        header: 'Projected @ lead',
        cell: ({ getValue }) => {
          const v = getValue<number | null>()
          return v == null ? '—' : formatNumber(v, 1)
        },
      },
      {
        accessorKey: 'suggested_reorder_qty',
        header: 'Suggested qty',
        cell: ({ getValue }) => (
          <span className="font-semibold text-accent">{formatNumber(getValue<number>())}</span>
        ),
      },
      {
        accessorKey: 'data_quality',
        header: 'Data quality',
        cell: ({ getValue }) => (
          <RiskBadge level={String(getValue()) === 'ok' ? 'low' : 'medium'} />
        ),
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <Button variant="ghost" onClick={() => setDetail(row.original)}>
            Explain
          </Button>
        ),
      },
    ],
    [],
  )

  return (
    <div>
      <PageHeader
        title="Reorder Recommendations"
        subtitle="Advisory replenishment suggestions using target stock = forecast demand during lead time + safety stock. No purchase orders are created."
      />
      <GlobalFiltersBar />

      <Panel title="AI-assisted reorder list" subtitle="Click Explain for step-by-step calculation">
        <div className="mb-3">
          <SearchInput value={search} onChange={setSearch} placeholder="Search item…" className="max-w-sm" />
        </div>
        {recsQ.isError ? (
          <ErrorState message={(recsQ.error as Error).message} onRetry={() => recsQ.refetch()} />
        ) : null}
        {recsQ.isLoading ? <Skeleton className="h-64" /> : null}
        {recsQ.data ? (
          <DataTable
            data={recsQ.data.items}
            columns={columns}
            pageSize={15}
            onRowClick={(row) => setDetail(row)}
            emptyTitle="No reorder actions"
            emptyDescription="Projected positions meet the target-stock policy for the current filters."
          />
        ) : null}
      </Panel>

      {detail ? (
        <div className="fixed inset-0 z-50 flex justify-end">
          <button type="button" className="absolute inset-0 bg-navy-950/40" onClick={() => setDetail(null)} aria-label="Close" />
          <aside className="relative z-10 h-full w-full max-w-lg overflow-y-auto border-l border-border bg-surface p-5 shadow-xl">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-wide text-ink-subtle">Calculation detail</p>
                <h2 className="mt-1 text-lg font-semibold text-ink">{detail.item_name}</h2>
                <p className="text-xs text-ink-muted">
                  {detail.store_name} · lead time {detail.lead_time_days}d
                </p>
              </div>
              <button type="button" className="rounded-lg border border-border p-1.5" onClick={() => setDetail(null)}>
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mb-4 text-sm text-ink-muted">{detail.reason}</p>
            {detail.horizon_limitation ? (
              <p className="mb-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
                Lead time exceeds the forecast horizon. Suggestion uses available horizon only — no silent extrapolation.
              </p>
            ) : null}
            <ol className="space-y-2">
              {detail.calculation_steps.map((step) => (
                <li key={step} className="rounded-lg border border-border bg-surface-muted/40 px-3 py-2 text-sm text-ink">
                  {step}
                </li>
              ))}
            </ol>
            <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
              <Stat label="Suggested qty" value={formatNumber(detail.suggested_reorder_qty)} />
              <Stat
                label="Est. days of cover"
                value={
                  detail.estimated_days_of_cover != null
                    ? formatNumber(detail.estimated_days_of_cover, 1)
                    : '—'
                }
              />
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-ink-subtle">{label}</p>
      <p className="mt-1 font-semibold text-ink">{value}</p>
    </div>
  )
}