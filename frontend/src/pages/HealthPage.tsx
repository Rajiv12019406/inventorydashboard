import { useQuery } from '@tanstack/react-query'
import { DemoBadge, RiskBadge } from '@/components/ui/Badge'
import { ErrorState, PageHeader, Panel, Skeleton } from '@/components/ui/Panel'
import { formatDateTime, formatNumber } from '@/lib/utils'
import { api } from '@/services/api'

export function HealthPage() {
  const healthQ = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 30_000 })

  const h = healthQ.data
  const dataset = (h?.dataset ?? {}) as Record<string, unknown>
  const job = (h?.forecast_job ?? {}) as Record<string, unknown>

  return (
    <div>
      <PageHeader
        title="Data & Model Health"
        subtitle="Operational status for the synthetic provider, forecast jobs, and dataset coverage. No live hospital systems are connected."
      />

      {healthQ.isError ? (
        <ErrorState message={(healthQ.error as Error).message} onRetry={() => healthQ.refetch()} />
      ) : null}
      {healthQ.isLoading ? <Skeleton className="h-40" /> : null}

      {h ? (
        <>
          <div className="mb-5 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3">
            <DemoBadge />
            <StatusPill status={h.status} />
            <span className="text-sm text-ink-muted">
              {h.app} v{h.version}
            </span>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <Panel title="Data provider" subtitle="Replaceable InventoryDataProvider abstraction">
              <dl className="space-y-3 text-sm">
                <Row label="Active provider" value={h.provider} />
                <Row label="Provider ready" value={h.provider_ready ? 'Yes' : 'No'} />
                <Row label="Dataset generated" value={formatDateTime(String(dataset.generated_at ?? ''))} />
                <Row
                  label="Historical coverage"
                  value={`${String(dataset.history_start ?? '—')} → ${String(dataset.history_end ?? '—')}`}
                />
                <Row label="Items" value={formatNumber(Number(dataset.item_count ?? 0))} />
                <Row label="Stores" value={formatNumber(Number(dataset.store_count ?? 0))} />
                <Row label="Categories" value={formatNumber(Number(dataset.category_count ?? 0))} />
                <Row
                  label="Missing observations"
                  value={formatNumber(Number(dataset.missing_observations ?? 0))}
                />
                <Row
                  label="Insufficient-history pairs"
                  value={formatNumber(Number(dataset.insufficient_history_pairs ?? 0))}
                />
                <Row label="Random seed" value={String(dataset.seed ?? '—')} />
              </dl>
            </Panel>

            <Panel title="Forecast job" subtitle="Overlapping runs are blocked">
              <dl className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-ink-subtle">Status</span>
                  <RiskBadge
                    level={
                      job.status === 'completed'
                        ? 'low'
                        : job.status === 'failed'
                          ? 'critical'
                          : 'medium'
                    }
                  />
                </div>
                <Row label="Last run" value={formatDateTime(String(job.last_run_at ?? ''))} />
                <Row
                  label="Duration"
                  value={
                    job.duration_seconds != null
                      ? `${formatNumber(Number(job.duration_seconds), 1)}s`
                      : '—'
                  }
                />
                <Row
                  label="Forecasts generated"
                  value={formatNumber(Number(job.forecasts_generated ?? 0))}
                />
                <Row label="Models used" value="MA · WMA · Seasonal naïve · Croston · ETS" />
                <Row
                  label="Failed jobs"
                  value={job.status === 'failed' ? String(job.error ?? 'Yes') : 'None'}
                />
              </dl>
            </Panel>
          </div>

          <Panel className="mt-5" title="System checks" subtitle="Derived from actual health endpoint responses">
            <ul className="space-y-2">
              {h.checks.map((c) => (
                <li
                  key={c.name}
                  className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm"
                >
                  <span className="font-medium capitalize text-ink">{c.name.replaceAll('_', ' ')}</span>
                  <span className="flex items-center gap-2 text-ink-muted">
                    <RiskBadge level={c.status === 'ok' ? 'low' : 'critical'} />
                    {c.detail}
                  </span>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel className="mt-5" title="Dataset assumptions" subtitle="Documented synthetic generation rules">
            <ul className="list-disc space-y-1.5 pl-5 text-sm text-ink-muted">
              {((dataset.assumptions as string[]) ?? []).map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </Panel>
        </>
      ) : null}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-ink-subtle">{label}</dt>
      <dd className="text-right font-medium text-ink">{value || '—'}</dd>
    </div>
  )
}

function StatusPill({ status }: { status: string }) {
  const color =
    status === 'healthy'
      ? 'bg-risk-low-soft text-risk-low'
      : status === 'degraded'
        ? 'bg-risk-medium-soft text-risk-medium'
        : 'bg-risk-critical-soft text-risk-critical'
  return (
    <span className={`rounded-md px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${color}`}>
      {status}
    </span>
  )
}