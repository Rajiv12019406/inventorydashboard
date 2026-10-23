import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { GlobalFilters } from '@/types/api'

interface FilterContextValue {
  filters: GlobalFilters
  setStoreId: (v: string) => void
  setCategoryId: (v: string) => void
  setHorizon: (v: number) => void
  setLookbackDays: (v: number) => void
  setAggregation: (v: 'daily' | 'weekly') => void
  setSearch: (v: string) => void
  resetFilters: () => void
  apiParams: { store_id?: string; category_id?: string; horizon: number }
}

const defaults: GlobalFilters = {
  storeId: '',
  categoryId: '',
  horizon: 14,
  lookbackDays: 56,
  aggregation: 'daily',
  search: '',
}

const FilterContext = createContext<FilterContextValue | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<GlobalFilters>(defaults)

  const value = useMemo<FilterContextValue>(
    () => ({
      filters,
      setStoreId: (storeId) => setFilters((f) => ({ ...f, storeId })),
      setCategoryId: (categoryId) => setFilters((f) => ({ ...f, categoryId })),
      setHorizon: (horizon) => setFilters((f) => ({ ...f, horizon })),
      setLookbackDays: (lookbackDays) => setFilters((f) => ({ ...f, lookbackDays })),
      setAggregation: (aggregation) => setFilters((f) => ({ ...f, aggregation })),
      setSearch: (search) => setFilters((f) => ({ ...f, search })),
      resetFilters: () => setFilters(defaults),
      apiParams: {
        store_id: filters.storeId || undefined,
        category_id: filters.categoryId || undefined,
        horizon: filters.horizon,
      },
    }),
    [filters],
  )

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>
}

export function useFilters() {
  const ctx = useContext(FilterContext)
  if (!ctx) throw new Error('useFilters must be used within FilterProvider')
  return ctx
}