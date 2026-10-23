import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatNumber } from '@/lib/utils'

export interface DemandChartPoint {
  date: string
  actual?: number | null
  predicted?: number | null
  lower?: number | null
  upper?: number | null
}

export function DemandForecastChart({
  data,
  historyEnd,
  height = 320,
}: {
  data: DemandChartPoint[]
  historyEnd?: string
  height?: number
}) {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickFormatter={(v) =>
              new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            }
            minTickGap={28}
            axisLine={{ stroke: '#cbd5e1' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={48}
            tickFormatter={(v) => formatNumber(Number(v))}
          />
          <Tooltip
            contentStyle={{
              borderRadius: 10,
              border: '1px solid #e2e8f0',
              boxShadow: '0 8px 24px rgba(15,23,42,0.08)',
              fontSize: 12,
            }}
            labelFormatter={(v) =>
              new Date(String(v)).toLocaleDateString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })
            }
            formatter={(value, name) => [formatNumber(Number(value), 1), String(name)]}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          <Area
            type="monotone"
            dataKey="upper"
            stroke="none"
            fill="#99f6e4"
            fillOpacity={0.45}
            name="Upper interval"
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="lower"
            stroke="none"
            fill="#ffffff"
            fillOpacity={1}
            name="Lower interval"
            connectNulls
            legendType="none"
          />
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#1e3a5f"
            strokeWidth={2.25}
            dot={false}
            name="Actual consumption"
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#0d9488"
            strokeWidth={2.25}
            strokeDasharray="5 4"
            dot={false}
            name="Forecast"
            connectNulls
          />
          {historyEnd ? (
            <ReferenceLine
              x={historyEnd}
              stroke="#94a3b8"
              strokeDasharray="4 4"
              label={{ value: 'Forecast start', position: 'insideTopRight', fill: '#64748b', fontSize: 11 }}
            />
          ) : null}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}