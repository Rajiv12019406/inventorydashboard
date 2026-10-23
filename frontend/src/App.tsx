import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { FilterProvider } from '@/context/FilterContext'
import { AppLayout } from '@/layouts/AppLayout'
import { ExpiryPage } from '@/pages/ExpiryPage'
import { ForecastsPage } from '@/pages/ForecastsPage'
import { HealthPage } from '@/pages/HealthPage'
import { OverviewPage } from '@/pages/OverviewPage'
import { PerformancePage } from '@/pages/PerformancePage'
import { ReordersPage } from '@/pages/ReordersPage'
import { StockoutsPage } from '@/pages/StockoutsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <FilterProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<OverviewPage />} />
              <Route path="forecasts" element={<ForecastsPage />} />
              <Route path="stockouts" element={<StockoutsPage />} />
              <Route path="expiry" element={<ExpiryPage />} />
              <Route path="reorders" element={<ReordersPage />} />
              <Route path="performance" element={<PerformancePage />} />
              <Route path="health" element={<HealthPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </FilterProvider>
    </QueryClientProvider>
  )
}
