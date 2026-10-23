import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import type { ColumnDef } from '@tanstack/react-table'
import { RiskDistributionChart } from '@/components/charts/RiskDistributionChart'
import { GlobalFiltersBar } from '@/components/filters/GlobalFilters'
import { ItemDetailDrawer } from '@/components/ItemDetailDrawer'
import { DataTable } from '@/components/tables/DataTable'
import { RiskBadge } from '@/components/ui/Badge'
import { KpiCard } from '@/components/ui/KpiCard'
import { ErrorState, PageHeader, Panel, Skeleton } from '@/components/ui/Panel'
import { SearchInput, SelectField } from '@/components/ui/Select'
import { useFilters } from '@/context/FilterContext'
import { formatDate, formatNumber } from '@/lib/utils'
import { api } from '@/services/api'
import type { StockoutRisk } from '@/types/api'
import { AlertTriangle, ShieldAlert } from 'lucide-react'

export function StockoutsPage() {
  const { apiParams } = useFilters()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [riskLevel, setRiskLevel] = useState(params.get('risk') ?? '')
  const [selected, setSelected] = useState<{ itemId: string; storeId: string } | null>(null)

  const summaryQ = useQuery({
    queryKey: ['summary', apiParams],
    queryFn: () => api.summary(apiParams),
  })

  const risksQ = useQuery({
    queryKey: ['stockouts', apiParams, riskLevel, search],
    queryFn: () =>
      api.stockoutRisks({
        ...apiParams,
        risk_level: riskLevel || undefined,
        search: search || undefined,
        page_size: 200,
      }),
  })

  const columns = useMemo<ColumnDef<StockoutRisk, unknown>[]>(
    () => [
      {
        accessorKey: 'item_code',
        header: 'Code',
        cell: ({ row }) => (
          <div>
            <p className="font-medium">{row.original.item_code}</p>
            <p className="max-w-[220px] truncate text-[11px] text-ink-subtle">{row.original.item_name}</p>
          </div>
        ),
      },
      { accessorKey: 'store_name', header: 'Store' },
      {
        accessorKey: 'current_usable_stock',
        header: 'Usable stock',
        cell: ({ getValue }) => formatNumber(getValue<number>(), 1),
      },
      {
        accessorKey: 'avg_daily_consumption',
        header: 'Avg daily',
        cell: ({ getValue }) => formatNumber(getValue<number>(), 2),
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
        header: 'Stockout date',
        cell: ({ getValue }) => formatDate(getValue<string | null>()),
      },
      {
        accessorKey: 'expected_incoming_stock',
        header: 'Incoming',
        cell: ({ getValue }) => formatNumber(getValue<number>(), 1),
      },
      { accessorKey: 'supplier_lead_time_days', header: 'Lead time' },
      {
        accessorKey: 'risk_level',
        header: 'Risk',
        cell: ({ getValue }) => <RiskBadge level={String(getValue())} />,
      },
      {
        accessorKey: 'explanation',
        header: 'Explanation',
        cell: ({ getValue }) => (
          <p className="max-w-xs whitespace-normal text-xs text-ink-muted">{String(getValue())}</p>
        ),
      },
    ],
    [],
  )

  const critical = summaryQ.data?.risk_distribution.critical ?? 0
  const high = summaryQ.data?.risk_distribution.high ?? 0

  return (
    <div>
      <PageHeader
        title="Stockout Intelligence"
        subtitle="Items likely to run out based on projected stock = current + incoming − cumulative forecast demand. Thresholds: critical ≤3d, high ≤7d, medium ≤14d."
      />
      <GlobalFiltersBar forecastGeneratedAt={summaryQ.data?.forecast_generated_at} />

      <div className="mb-5 grid gap-3 sm:grid-cols-2">
        <KpiCard label="Critical risk" value={formatNumber(critical)} icon={ShieldAlert} tone="critical" hint="Stockout within 3 days" />
        <KpiCard label="High risk" value={formatNumber(high)} icon={AlertTriangle} tone="warning" hint="Stockout within 7 days" />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <Panel title="Risk distribution" subtitle="Navigate by severity">
          {summaryQ.data ? (
            <RiskDistributionChart
              distribution={summaryQ.data.risk_distribution}
              onSelect={(level) => {
                setRiskLevel(level)
                setParams({ risk: level })
              }}
            />
          ) : (
            <Skeleton className="h-48" />
          )}
        </Panel>
        <Panel className="xl:col-span-2" title="Filters">
          <div className="flex flex-wrap gap-3">
            <SearchInput value={search} onChange={setSearch} placeholder="Search item…" className="max-w-sm" />
            <SelectField
              label="Risk severity"
              value={riskLevel}
              onChange={(v) => {
                setRiskLevel(v)
                if (v) setParams({ risk: v })
                else setParams({})
              }}
              options={[
                { value: '', label: 'All levels' },
                { value: 'critical', label: 'Critical' },
                { value: 'high', label: 'High' },
                { value: 'medium', label: 'Medium' },
                { value: 'low', label: 'Low' },
              ]}
            />
          </div>
          <p className="mt-3 text-xs text-ink-subtle">
            Explanations reflect model uncertainty. Insufficient history reduces confidence — never treat dates as certain.
          </p>
        </Panel>
      </div>

      <Panel className="mt-5" title="Stockout risk table" subtitle="Click a row for item-level forecast detail">
        {risksQ.isError ? (
          <ErrorState message={(risksQ.error as Error).message} onRetry={() => risksQ.refetch()} />
        ) : null}
        {risksQ.isLoading ? <Skeleton className="h-64" /> : null}
        {risksQ.data ? (
          <DataTable
            data={risksQ.data.items}
            columns={columns}
            pageSize={15}
            onRowClick={(row) => setSelected({ itemId: row.item_id, storeId: row.store_id })}
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