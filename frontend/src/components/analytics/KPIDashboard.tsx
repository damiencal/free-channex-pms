import { TrendingUp, TrendingDown, Bed, DollarSign, BarChart2, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { usePortfolioKPIs, useTriggerMetricsCompute } from '@/hooks/useAnalytics'
import type { PortfolioMetric } from '@/api/analytics'

function pct(v: string | null | undefined): string {
  if (!v) return '—'
  return `${(parseFloat(v) * 100).toFixed(1)}%`
}
function usd(v: string | null | undefined): string {
  if (!v) return '—'
  return `$${parseFloat(v).toFixed(0)}`
}

function changeVsLastMonth(current: PortfolioMetric, previous: PortfolioMetric | undefined, field: keyof PortfolioMetric): string | null {
  if (!previous) return null
  const cur = parseFloat(current[field] as string)
  const prev = parseFloat(previous[field] as string)
  if (isNaN(cur) || isNaN(prev) || prev === 0) return null
  const change = ((cur - prev) / prev) * 100
  return `${change >= 0 ? '+' : ''}${change.toFixed(1)}%`
}

function KPICard({
  title,
  value,
  change,
  icon: Icon,
}: {
  title: string
  value: string
  change: string | null
  icon: React.ElementType
  tooltip?: string
}) {
  const isPositive = change?.startsWith('+')
  const isNegative = change?.startsWith('-')

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold tabular-nums">{value}</p>
        {change && (
          <div
            className={`mt-1 flex items-center gap-1 text-sm ${
              isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-muted-foreground'
            }`}
          >
            {isPositive && <TrendingUp className="h-3.5 w-3.5" />}
            {isNegative && <TrendingDown className="h-3.5 w-3.5" />}
            <span>{change} vs prior month</span>
          </div>
        )}
        {!change && <p className="mt-1 text-sm text-muted-foreground">No prior month</p>}
      </CardContent>
    </Card>
  )
}

export function KPIDashboard() {
  const { data: metrics, isLoading } = usePortfolioKPIs(12)
  const compute = useTriggerMetricsCompute()

  const latest = metrics?.[metrics.length - 1]
  const previous = metrics?.[metrics.length - 2]

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardContent className="py-8">
              <div className="h-8 w-24 animate-pulse rounded bg-muted" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (!latest) {
    return (
      <Card>
        <CardContent className="py-12 text-center space-y-3">
          <p className="text-muted-foreground">No metrics computed yet.</p>
          <Button
            size="sm"
            variant="outline"
            onClick={() => compute.mutate()}
            disabled={compute.isPending}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${compute.isPending ? 'animate-spin' : ''}`} />
            Compute Now
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KPICard
          title="Occupancy Rate"
          value={pct(latest.occupancy_rate)}
          change={changeVsLastMonth(latest, previous, 'occupancy_rate')}
          icon={Bed}
        />
        <KPICard
          title="ADR"
          value={usd(latest.adr)}
          change={changeVsLastMonth(latest, previous, 'adr')}
          icon={DollarSign}
          tooltip="Average Daily Rate"
        />
        <KPICard
          title="RevPAR"
          value={usd(latest.revpar)}
          change={changeVsLastMonth(latest, previous, 'revpar')}
          icon={BarChart2}
          tooltip="Revenue Per Available Room/Night"
        />
        <KPICard
          title="Revenue"
          value={usd(latest.revenue)}
          change={changeVsLastMonth(latest, previous, 'revenue')}
          icon={TrendingUp}
        />
      </div>

      <div className="flex justify-end">
        <Button
          size="sm"
          variant="ghost"
          onClick={() => compute.mutate()}
          disabled={compute.isPending}
        >
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${compute.isPending ? 'animate-spin' : ''}`} />
          Recompute
        </Button>
      </div>
    </div>
  )
}
