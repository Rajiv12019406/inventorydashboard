import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  CalendarClock,
  ClipboardList,
  Database,
  LayoutDashboard,
  Menu,
  PackagePlus,
  TrendingUp,
  X,
} from 'lucide-react'
import { DemoBadge } from '@/components/ui/Badge'
import { cn } from '@/lib/utils'

const nav = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/forecasts', label: 'Demand Forecasts', icon: TrendingUp },
  { to: '/stockouts', label: 'Stockout Intelligence', icon: AlertTriangle },
  { to: '/expiry', label: 'Expiry Intelligence', icon: CalendarClock },
  { to: '/reorders', label: 'Reorder Recommendations', icon: PackagePlus },
  { to: '/performance', label: 'Forecast Performance', icon: BarChart3 },
  { to: '/health', label: 'Data & Model Health', icon: Database },
]

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-white/10 px-5 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-500/20 text-teal-300">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">MediStock Intelligence</p>
            <p className="text-[11px] leading-tight text-slate-400">
              Hospital Inventory Forecasting & Risk Analytics
            </p>
          </div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition',
                isActive
                  ? 'bg-white/10 font-medium text-white'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white',
              )
            }
          >
            <item.icon className="h-4 w-4 shrink-0 opacity-80" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/10 px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500/30 text-xs font-semibold text-indigo-100">
            AR
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-white">Dr. Aisha Rahman</p>
            <p className="truncate text-[11px] text-slate-400">Supply Chain Analyst · Demo</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  return (
    <div className="min-h-screen bg-canvas">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 bg-navy-950 lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen ? (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-navy-950/50 lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              className="fixed inset-y-0 left-0 z-50 w-72 bg-navy-950 lg:hidden"
              initial={{ x: -288 }}
              animate={{ x: 0 }}
              exit={{ x: -288 }}
              transition={{ type: 'spring', stiffness: 380, damping: 36 }}
            >
              <button
                type="button"
                className="absolute right-3 top-3 rounded-md p-1 text-slate-300 hover:bg-white/10"
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation"
              >
                <X className="h-5 w-5" />
              </button>
              <SidebarContent onNavigate={() => setMobileOpen(false)} />
            </motion.aside>
          </>
        ) : null}
      </AnimatePresence>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-border bg-surface/90 backdrop-blur">
          <div className="flex h-14 items-center justify-between gap-3 px-4 md:px-6">
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="rounded-lg border border-border p-1.5 text-ink-muted lg:hidden"
                onClick={() => setMobileOpen(true)}
                aria-label="Open navigation"
              >
                <Menu className="h-4 w-4" />
              </button>
              <DemoBadge />
            </div>
            <div className="flex items-center gap-2">
              <NavLink
                to="/stockouts"
                className="relative rounded-lg border border-border p-2 text-ink-muted hover:bg-surface-muted hover:text-ink"
                aria-label="Alert center"
              >
                <Bell className="h-4 w-4" />
                <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-risk-critical" />
              </NavLink>
              <div className="hidden items-center gap-2 rounded-lg border border-border px-2.5 py-1.5 sm:flex">
                <ClipboardList className="h-3.5 w-3.5 text-ink-subtle" />
                <span className="text-xs text-ink-muted">Analytics views only</span>
              </div>
            </div>
          </div>
        </header>

        <main className="px-4 py-6 md:px-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}