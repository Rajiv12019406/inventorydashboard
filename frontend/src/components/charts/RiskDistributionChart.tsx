import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { formatNumber } from '@/lib/utils'
import type { RiskLevel } from '@/types/api'

const COLORS: Record<RiskLevel, string> = {
  critical: '#b91c1c',
  high: '#c2410c',
  medium: '#a16207',
  low: '#047857',
}

export function RiskDistributionChart({
  distribution,
  onSelect,
}: {
  distribution: Record<string, number>
  onSelect?: (level: string) => void
}) {
  const data = (['critical', 'high', 'medium', 'low'] as RiskLevel[]).map((k) => ({
    name: k,
    value: distribution[k] ?? 0,
  }))
  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center">
      <div className="relative h-48 w-48 shrink-0">
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={52}
              outerRadius={78}
              paddingAngle={2}
              onClick={(entry) => onSelect?.(String(entry.name))}
              cursor={onSelect ? 'pointer' : undefined}
            >
              {data.map((d) => (
                <Cell key={d.name} fill={COLORS[d.name]} />
              ))}
            </Pie>
            <Tooltip formatter={(v) => formatNumber(Number(v))} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-semibold text-ink">{formatNumber(total)}</span>
          <span className="text-[10px] uppercase tracking-wider text-ink-subtle">Items</span>
        </div>
      </div>
      <ul className="w-full space-y-2">
        {data.map((d) => (
          <li key={d.name}>
            <button
              type="button"
              onClick={() => onSelect?.(d.name)}
              className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-sm hover:bg-surface-muted"
            >
              <span className="flex items-center gap-2 capitalize text-ink-muted">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: COLORS[d.name] }} />
                {d.name}
              </span>
              <span className="font-medium text-ink">{formatNumber(d.value)}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}