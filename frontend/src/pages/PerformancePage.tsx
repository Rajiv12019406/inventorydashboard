import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { PageHeader, Panel, Skeleton, ErrorState, EmptyState } from '@/components/ui/Panel'
import { formatNumber } from '@/lib/utils'
import { api } from '@/services/api'

export function PerformancePage() {
  const evalQ = useQuery({ queryKey: ['evaluations'], queryFn: api.evaluations })

  const data = evalQ.data
  const insufficient = data?.status === 'insufficient_evaluation_history'

  return (
    <div>
      <PageHeader
        title="Forecast Performance"
        subtitle="Chronological rolling-origin backtests on historical demand. These scores measure past accuracy — not future forecast confidence. MAPE is avoided as a sole metric when demand contains zeros; WAPE/MAE preferred."
      />

      {evalQ.isError ? (
        <ErrorState message={(evalQ.error as Error).message} onRetry={() => evalQ.refetch()} />
      ) : null}
      {evalQ.isLoading ? <Skeleton className="mb-5 h-40" /> : null}

      {insufficient ? (
        <Panel title="Evaluation status">
          <EmptyState
            title="Insufficient evaluation history"
            description={data?.message ?? 'The dataset cannot support a reliable score.'}
          />
        </Panel>
      ) : null}

      {data && !insufficient ? (
        <>
          <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Overall MAE" value={formatNumber(data.overall?.mae, 3)} hint="Mean absolute error" />
            <MetricCard
              label="Overall WAPE"
              value={data.overall?.wape != null ? formatNumber(data.overall.wape * 100, 1) + '%' : '—'}
              hint="Weighted absolute percentage error"
            />
            <MetricCard label="Forecast bias" value={formatNumber(data.overall?.bias, 3)} hint="Predicted − actual (mean)" />
            <MetricCard
              label="Observations"
              value={formatNumber(data.overall?.n_obs)}
              hint={`${data.overall?.series_evaluated ?? 0} series · ${data.evaluation_period?.start} → ${data.evaluation_period?.end}`}
            />
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <Panel title="Model comparison" subtitle="Lower MAE is better">
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.models}>
                    <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="model_id"
                      tick={{ fontSize: 10, fill: '#64748b' }}
                      tickFormatter={(v) => String(v).replaceAll('_', ' ')}
                    />
                    <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                    <Tooltip />
                    <Bar dataKey="mae" fill="#4338ca" name="MAE" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="Model summary table" subtitle={data.message}>
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="text-[11px] uppercase tracking-wide text-ink-subtle">
                    <tr>
                      <th className="pb-2 pr-3">Model</th>
                      <th className="pb-2 pr-3">Series</th>
                      <th className="pb-2 pr-3">MAE</th>
                      <th className="pb-2 pr-3">WAPE</th>
                      <th className="pb-2">Bias</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.models.map((m) => (
                      <tr key={m.model_id} className="border-t border-border">
                        <td className="py-2 pr-3 capitalize">{m.model_id.replaceAll('_', ' ')}</td>
                        <td className="py-2 pr-3">{m.series_count}</td>
                        <td className="py-2 pr-3">{formatNumber(m.mae, 3)}</td>
                        <td className="py-2 pr-3">
                          {m.wape != null ? formatNumber(m.wape * 100, 1) + '%' : '—'}
                        </td>
                        <td className="py-2">{formatNumber(m.bias, 3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </div>

          <Panel className="mt-5" title="Per-series error sample" subtitle="Illustrative MAE by item-store series">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={(data.series ?? []).slice(0, 20)}>
                  <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="item_id" hide />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    labelFormatter={(_, payload) => {
                      const p = payload?.[0]?.payload as { item_id?: string; store_id?: string }
                      return `${p?.item_id ?? ''} @ ${p?.store_id ?? ''}`
                    }}
                  />
                  <Bar dataKey="mae" fill="#0f766e" name="MAE" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </>
      ) : null}
    </div>
  )
}

function MetricCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <p className="text-[11px] font-medium uppercase tracking-wide text-ink-subtle">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-ink">{value}</p>
      <p className="mt-1 text-xs text-ink-muted">{hint}</p>
    </div>
  )
}