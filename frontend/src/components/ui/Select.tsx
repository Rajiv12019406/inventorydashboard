import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function SelectField({
  label,
  value,
  onChange,
  options,
  className,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
  className?: string
}) {
  return (
    <label className={cn('flex min-w-[140px] flex-col gap-1', className)}>
      <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-ink-subtle">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-lg border border-border bg-surface px-2.5 text-sm text-ink outline-none ring-accent/30 focus:ring-2"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  )
}

export function SearchInput({
  value,
  onChange,
  placeholder = 'Search…',
  className,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  className?: string
}) {
  return (
    <input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={cn(
        'h-9 w-full min-w-[180px] rounded-lg border border-border bg-surface px-3 text-sm text-ink outline-none ring-accent/30 placeholder:text-ink-subtle focus:ring-2',
        className,
      )}
    />
  )
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  disabled,
  type = 'button',
  className,
}: {
  children: ReactNode
  onClick?: () => void
  variant?: 'primary' | 'secondary' | 'ghost'
  disabled?: boolean
  type?: 'button' | 'submit'
  className?: string
}) {
  const styles = {
    primary: 'bg-navy-900 text-white hover:bg-navy-800',
    secondary: 'border border-border bg-surface text-ink hover:bg-surface-muted',
    ghost: 'text-ink-muted hover:bg-surface-muted hover:text-ink',
  }
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'inline-flex h-9 items-center justify-center gap-2 rounded-lg px-3 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50',
        styles[variant],
        className,
      )}
    >
      {children}
    </button>
  )
}