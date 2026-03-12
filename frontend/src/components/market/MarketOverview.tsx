import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useMarketSnapshots } from '@/hooks/useAnalytics'
import type { MarketSnapshot } from '@/api/analytics'

export function MarketOverview() {
  const { data: snapshots, isLoading } = useMarketSnapshots(90)

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading market data…</div>

  if (!snapshots?.length) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-muted-foreground">
          <p>No market snapshot data available.</p>
          <p className="text-sm mt-1">
            Market data is collected nightly from internal booking patterns.
          </p>
        </CardContent>
      </Card>
    )
  }

  const chartData = snapshots
    .map((s: MarketSnapshot) => ({
      date: s.snapshot_date,
      demand: s.demand_index ? parseFloat(s.demand_index) : null,
      occupancy: s.occupancy_rate ? parseFloat(s.occupancy_rate) * 100 : null,
      adr: s.avg_daily_rate ? parseFloat(s.avg_daily_rate) : null,
    }))
    .sort((a, b) => a.date.localeCompare(b.date))

  // Latest snapshot for KPI cards
  const latest = snapshots[snapshots.length - 1]

  return (
    <div className="space-y-4">
      <div className="grid gap-4 grid-cols-3">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">Demand Index</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {latest.demand_index ? parseFloat(latest.demand_index).toFixed(0) : '—'}/100
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">Market Occupancy</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {latest.occupancy_rate
                ? `${(parseFloat(latest.occupancy_rate) * 100).toFixed(1)}%`
                : '—'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">Avg Market Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {latest.avg_daily_rate ? `$${parseFloat(latest.avg_daily_rate).toFixed(0)}` : '—'}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Demand Index — 90 Day Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="demandGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                tickFormatter={(v) => format(new Date(v + 'T12:00:00'), 'MMM d')}
                className="text-xs"
              />
              <YAxis domain={[0, 100]} className="text-xs" />
              <Tooltip
                labelFormatter={(v) => format(new Date(v + 'T12:00:00'), 'MMM d, yyyy')}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="demand"
                name="Demand Index"
                stroke="hsl(var(--chart-1))"
                fill="url(#demandGrad)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
