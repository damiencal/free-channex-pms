import { format } from 'date-fns'
import { addMonths, startOfMonth } from 'date-fns'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { RevenueEstimate } from '@/api/estimator'

const CONFIDENCE_BADGE: Record<string, string> = {
  very_low: 'secondary',
  low: 'secondary',
  medium: 'default',
  high: 'default',
  very_high: 'default',
}

interface Props {
  data: RevenueEstimate
  onReset: () => void
}

export function EstimatorResults({ data, onReset }: Props) {
  const today = startOfMonth(new Date())
  const chartData = data.monthly_estimates.map((m, i) => ({
    month: format(addMonths(today, i), 'MMM yy'),
    revenue: Math.round(m.estimated_revenue),
    adr: Math.round(m.estimated_adr),
  }))

  return (
    <div className="space-y-4">
      {/* Summary row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">Annual Estimate</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              ${data.annual_estimate.toLocaleString('en-US', { maximumFractionDigits: 0 })}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">Est. ADR</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              ${Math.round(data.adr_estimate).toLocaleString()}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">Est. Occupancy</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {(data.occupancy_estimate * 100).toFixed(0)}%
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">Confidence</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant={CONFIDENCE_BADGE[data.confidence] as never}>
              {data.confidence.replace('_', ' ')}
            </Badge>
            <p className="mt-1 text-xs text-muted-foreground">
              {data.data_points} comparable data points
            </p>
          </CardContent>
        </Card>
      </div>

      {data.note && (
        <p className="text-sm text-muted-foreground italic">{data.note}</p>
      )}

      {/* Monthly bar chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Monthly Revenue Projection</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="month" className="text-xs" />
              <YAxis
                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                className="text-xs"
              />
              <Tooltip formatter={(v: number) => `$${v.toLocaleString()}`} />
              <Bar dataKey="revenue" name="Estimated Revenue" fill="hsl(var(--chart-1))" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Button variant="outline" size="sm" onClick={onReset}>
        <RotateCcw className="mr-1.5 h-4 w-4" />
        New Estimate
      </Button>
    </div>
  )
}
