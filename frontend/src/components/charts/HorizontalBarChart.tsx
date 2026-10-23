import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatNumber } from '@/lib/utils'

export function HorizontalBarChart({
  data,
  height = 280,
}: {
  data: { label: string; value: number }[]
  height?: number
}) {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            type="category"
            dataKey="label"
            width={120}
            tick={{ fill: '#475569', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip formatter={(v) => formatNumber(Number(v), 2)} />
          <Bar dataKey="value" fill="#4338ca" radius={[0, 4, 4, 0]} name="Exposure" barSize={16} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}