import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface KpiCardProps {
  label: string
  value: string
  icon: LucideIcon
  hint?: string
  delta?: string | null
  tone?: 'default' | 'critical' | 'warning' | 'accent'
}

const toneMap = {
  default: 'text-indigo bg-indigo-soft',
  critical: 'text-risk-critical bg-risk-critical-soft',
  warning: 'text-risk-high bg-risk-high-soft',
  accent: 'text-accent bg-accent-soft',
}

export function KpiCard({ label, value, icon: Icon, hint, delta, tone = 'default' }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.06em] text-ink-subtle">{label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-ink">{value}</p>
          {delta ? <p className="mt-1 text-xs text-ink-muted">{delta}</p> : null}
          {hint ? <p className="mt-2 text-xs leading-relaxed text-ink-subtle">{hint}</p> : null}
        </div>
        <div className={cn('rounded-lg p-2', toneMap[tone])}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  )
}