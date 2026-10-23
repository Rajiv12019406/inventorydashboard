import { cn } from '@/lib/utils'
import type { ExpiryRisk, RiskLevel } from '@/types/api'

const riskStyles: Record<string, string> = {
  critical: 'bg-risk-critical-soft text-risk-critical',
  high: 'bg-risk-high-soft text-risk-high',
  medium: 'bg-risk-medium-soft text-risk-medium',
  low: 'bg-risk-low-soft text-risk-low',
  expired: 'bg-risk-critical-soft text-risk-critical',
}

export function RiskBadge({ level }: { level: RiskLevel | ExpiryRisk | string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium capitalize tracking-wide',
        riskStyles[level] ?? 'bg-surface-muted text-ink-muted',
      )}
    >
      {level}
    </span>
  )
}

export function DemoBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-amber-300/60 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-amber-800">
      <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
      Demo Mode · Synthetic Data
    </span>
  )
}