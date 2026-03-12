import { format } from 'date-fns'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { usePortfolioKPIs } from '@/hooks/useAnalytics'
import type { PortfolioMetric } from '@/api/analytics'

function pct(v: string | null): string {
  if (!v) return '—'
  return `${(parseFloat(v) * 100).toFixed(1)}%`
}
function usd(v: string | null): string {
  if (!v) return '—'
  return `$${parseFloat(v).toFixed(0)}`
}

export function PerformanceTable() {
  const { data: metrics, isLoading } = usePortfolioKPIs(24)

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading…</div>

  const sorted = [...(metrics ?? [])].sort((a, b) => b.metric_date.localeCompare(a.metric_date))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Monthly Performance — Last 24 Months</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 pr-4">Month</th>
              <th className="py-2 pr-4 text-right">Occupancy</th>
              <th className="py-2 pr-4 text-right">ADR</th>
              <th className="py-2 pr-4 text-right">RevPAR</th>
              <th className="py-2 pr-4 text-right">Revenue</th>
              <th className="py-2 pr-4 text-right">Bookings</th>
              <th className="py-2 text-right">Nights Booked</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((m: PortfolioMetric) => (
              <tr key={`${m.property_id}-${m.metric_date}`} className="border-b last:border-0">
                <td className="py-2 pr-4 font-medium">
                  {format(new Date(m.metric_date + '-01T12:00:00'), 'MMM yyyy')}
                </td>
                <td className="py-2 pr-4 text-right tabular-nums">{pct(m.occupancy_rate)}</td>
                <td className="py-2 pr-4 text-right tabular-nums">{usd(m.adr)}</td>
                <td className="py-2 pr-4 text-right tabular-nums">{usd(m.revpar)}</td>
                <td className="py-2 pr-4 text-right tabular-nums">{usd(m.revenue)}</td>
                <td className="py-2 pr-4 text-right tabular-nums">{m.booking_count ?? '—'}</td>
                <td className="py-2 text-right tabular-nums">{m.booked_nights ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!sorted.length && (
          <p className="py-8 text-center text-muted-foreground">No monthly data yet.</p>
        )}
      </CardContent>
    </Card>
  )
}
