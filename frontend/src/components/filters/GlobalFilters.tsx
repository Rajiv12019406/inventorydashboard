import { useQuery } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useFilters } from '@/context/FilterContext'
import { api } from '@/services/api'
import { Button, SelectField } from '@/components/ui/Select'
import { formatDateTime } from '@/lib/utils'

export function GlobalFiltersBar({
  forecastGeneratedAt,
  onRefresh,
  refreshing,
}: {
  forecastGeneratedAt?: string | null
  onRefresh?: () => void
  refreshing?: boolean
}) {
  const { filters, setStoreId, setCategoryId, setHorizon, setLookbackDays, setAggregation } =
    useFilters()
  const { data } = useQuery({ queryKey: ['filters'], queryFn: api.filters })

  return (
    <div className="mb-6 rounded-xl border border-border bg-surface p-3 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div className="flex flex-wrap gap-3">
          <SelectField
            label="Store"
            value={filters.storeId}
            onChange={setStoreId}
            options={[
              { value: '', label: 'All stores' },
              ...(data?.stores.map((s) => ({ value: s.store_id, label: s.name })) ?? []),
            ]}
          />
          <SelectField
            label="Category"
            value={filters.categoryId}
            onChange={setCategoryId}
            options={[
              { value: '', label: 'All categories' },
              ...(data?.categories.map((c) => ({ value: c.category_id, label: c.name })) ?? []),
            ]}
          />
          <SelectField
            label="Forecast horizon"
            value={String(filters.horizon)}
            onChange={(v) => setHorizon(Number(v))}
            options={[
              { value: '7', label: '7 days' },
              { value: '14', label: '14 days' },
            ]}
          />
          <SelectField
            label="History window"
            value={String(filters.lookbackDays)}
            onChange={(v) => setLookbackDays(Number(v))}
            options={[
              { value: '28', label: '28 days' },
              { value: '56', label: '56 days' },
              { value: '90', label: '90 days' },
            ]}
          />
          <SelectField
            label="Aggregation"
            value={filters.aggregation}
            onChange={(v) => setAggregation(v as 'daily' | 'weekly')}
            options={[
              { value: 'daily', label: 'Daily' },
              { value: 'weekly', label: 'Weekly' },
            ]}
          />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {forecastGeneratedAt ? (
            <p className="text-xs text-ink-subtle">
              Last forecast run · {formatDateTime(forecastGeneratedAt)}
            </p>
          ) : null}
          {onRefresh ? (
            <Button onClick={onRefresh} disabled={refreshing} variant="secondary">
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh forecasts
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}