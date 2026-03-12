import { format } from 'date-fns'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useTrends } from '@/hooks/useAnalytics'
import type { PortfolioMetric } from '@/api/analytics'

function formatMonth(dateStr: string): string {
  return format(new Date(dateStr + '-01T12:00:00'), 'MMM yy')
}

export function TrendCharts() {
  const { data: metrics, isLoading } = useTrends(12)

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading trends…</div>
  }

  if (!metrics?.length) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No trend data available yet. Run the metrics compute job to generate data.
        </CardContent>
      </Card>
    )
  }

  const chartData = metrics
    .map((m: PortfolioMetric) => ({
      month: m.metric_date,
      occupancy: m.occupancy_rate ? parseFloat(m.occupancy_rate) * 100 : null,
      adr: m.adr ? parseFloat(m.adr) : null,
      revpar: m.revpar ? parseFloat(m.revpar) : null,
      revenue: m.revenue ? parseFloat(m.revenue) : null,
    }))
    .sort((a, b) => a.month.localeCompare(b.month))

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Occupancy Rate (%)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="month" tickFormatter={formatMonth} className="text-xs" />
              <YAxis unit="%" domain={[0, 100]} className="text-xs" />
              <Tooltip labelFormatter={formatMonth} formatter={(v: number) => `${v.toFixed(1)}%`} />
              <Line type="monotone" dataKey="occupancy" name="Occupancy" stroke="hsl(var(--chart-1))" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">ADR & RevPAR ($)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="month" tickFormatter={formatMonth} className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip labelFormatter={formatMonth} formatter={(v: number) => `$${v.toFixed(0)}`} />
              <Legend />
              <Line type="monotone" dataKey="adr" name="ADR" stroke="hsl(var(--chart-2))" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="revpar" name="RevPAR" stroke="hsl(var(--chart-3))" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">Monthly Revenue ($)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="month" tickFormatter={formatMonth} className="text-xs" />
              <YAxis className="text-xs" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip labelFormatter={formatMonth} formatter={(v: number) => `$${v.toLocaleString()}`} />
              <Line type="monotone" dataKey="revenue" name="Revenue" stroke="hsl(var(--chart-4))" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
