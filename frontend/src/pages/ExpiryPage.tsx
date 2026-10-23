import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { ColumnDef } from '@tanstack/react-table'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { CalendarClock, Clock3, OctagonAlert, Timer } from 'lucide-react'
import { GlobalFiltersBar } from '@/components/filters/GlobalFilters'
import { DataTable } from '@/components/tables/DataTable'
import { RiskBadge } from '@/components/ui/Badge'
import { KpiCard } from '@/components/ui/KpiCard'
import { ErrorState, PageHeader, Panel, Skeleton } from '@/components/ui/Panel'
import { SearchInput } from '@/components/ui/Select'
import { useFilters } from '@/context/FilterContext'
import { formatDate, formatNumber } from '@/lib/utils'
import { api } from '@/services/api'
import type { ExpiryRiskRow } from '@/types/api'

export function ExpiryPage() {
  const { apiParams } = useFilters()
  const [search, setSearch] = useState('')

  const summaryQ = useQuery({
    queryKey: ['expiry-summary', apiParams.store_id, apiParams.category_id],
    queryFn: () =>
      api.expirySummary({ store_id: apiParams.store_id, category_id: apiParams.category_id }),
  })
  const risksQ = useQuery({
    queryKey: ['expiry-risks', apiParams.store_id, apiParams.category_id, search],
    queryFn: () =>
      api.expiryRisks({
        store_id: apiParams.store_id,
        category_id: apiParams.category_id,
        search: search || undefined,
        page_size: 200,
      }),
  })

  const columns = useMemo<ColumnDef<ExpiryRiskRow, unknown>[]>(
    () => [
      {
        accessorKey: 'item_name',
        header: 'Item',
        cell: ({ row }) => (
          <div>
            <p className="font-medium">{row.original.item_name}</p>
            <p className="text-[11px] text-ink-subtle">{row.original.item_code}</p>
          </div>
        ),
      },
      { accessorKey: 'batch_id', header: 'Batch' },
      { accessorKey: 'store_name', header: 'Store' },
      {
        accessorKey: 'available_qty',
        header: 'Available qty',
        cell: ({ getValue }) => formatNumber(getValue<number>(), 1),
      },
      {
        accessorKey: 'expiry_date',
        header: 'Expiry date',
        cell: ({ getValue }) => formatDate(getValue<string>()),
      },
      {
        accessorKey: 'days_until_expiry',
        header: 'Days until expiry',
        cell: ({ getValue }) => {
          const v = getValue<number>()
          return v < 0 ? `${v} (expired)` : formatNumber(v)
        },
      },
      {
        accessorKey: 'risk_status',
        header: 'Risk',
        cell: ({ getValue }) => <RiskBadge level={String(getValue())} />,
      },
      {
        accessorKey: 'fefo_note',
        header: 'FEFO guidance',
        cell: ({ getValue }) => (
          <p className="max-w-sm whitespace-normal text-xs text-ink-muted">{String(getValue())}</p>
        ),
      },
    ],
    [],
  )

  const s = summaryQ.data

  return (
    <div>
      <PageHeader
        title="Expiry Intelligence"
        subtitle="Batch-level dating risk from synthetic lots. Expired quantities are never recommended for issue — quarantine per policy."
      />
      <GlobalFiltersBar />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {s ? (
          <>
            <KpiCard label="Expired stock" value={formatNumber(s.expired_qty, 1)} icon={OctagonAlert} tone="critical" hint={`${s.expired_batches} batches`} />
            <KpiCard label="Expiring ≤7 days" value={formatNumber(s.within_7_days_qty, 1)} icon={Timer} tone="warning" hint={`${s.within_7_days_batches} batches`} />
            <KpiCard label="Expiring ≤30 days" value={formatNumber(s.within_30_days_qty, 1)} icon={Clock3} tone="warning" hint={`${s.within_30_days_batches} batches`} />
            <KpiCard label="Expiring ≤90 days" value={formatNumber(s.within_90_days_qty, 1)} icon={CalendarClock} hint={`${s.within_90_days_batches} batches`} />
          </>
        ) : (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)
        )}
      </div>

      <Panel className="mt-5" title="Expiry risk by category" subtitle="Quantity at risk within 90 days (including expired)">
        {s ? (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={s.by_category}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="category" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip formatter={(v) => formatNumber(Number(v), 1)} />
                <Bar dataKey="qty" fill="#0f766e" radius={[4, 4, 0, 0]} name="Qty at risk" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <Skeleton className="h-72" />
        )}
      </Panel>

      <Panel className="mt-5" title="Batch-level expiry table" subtitle="Sorted by days until expiry">
        <div className="mb-3">
          <SearchInput value={search} onChange={setSearch} placeholder="Search item or batch…" className="max-w-sm" />
        </div>
        {risksQ.isError ? (
          <ErrorState message={(risksQ.error as Error).message} onRetry={() => risksQ.refetch()} />
        ) : null}
        {risksQ.isLoading ? <Skeleton className="h-64" /> : null}
        {risksQ.data ? (
          <DataTable data={risksQ.data.items} columns={columns} pageSize={15} />
        ) : null}
      </Panel>
    </div>
  )
}