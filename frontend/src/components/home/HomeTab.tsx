import { useMetrics } from '@/hooks/useFinancials'
import { StatCard } from './StatCard'
import { BookingTrendChart } from './BookingTrendChart'
import { OccupancyChart } from './OccupancyChart'
import { ActionsPreview } from './ActionsPreview'

function formatCurrency(value: string | undefined): string {
  if (!value) return '$0.00'
  const num = parseFloat(value)
  if (isNaN(num)) return '$0.00'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(num)
}

/**
 * Home tab: stat cards, booking trend chart, occupancy chart, and actions preview.
 */
export function HomeTab() {
  const { data: metrics, isLoading, error, refetch } = useMetrics()

  return (
    <div className="space-y-6">
      {/* Top row: 3 stat cards */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <StatCard
          title="YTD Revenue"
          value={formatCurrency(metrics?.ytd_revenue)}
          yoyChange={metrics?.yoy_revenue_change ?? null}
          tooltipText="Total income from all bookings this year"
          isLoading={isLoading}
        />
        <StatCard
          title="YTD Expenses"
          value={formatCurrency(metrics?.ytd_expenses)}
          yoyChange={metrics?.yoy_expense_change ?? null}
          tooltipText="Total costs including rent, utilities, and maintenance this year"
          isLoading={isLoading}
        />
        <StatCard
          title="Current Month Profit"
          value={formatCurrency(metrics?.current_month_profit)}
          yoyChange={null}
          tooltipText="Revenue minus expenses for this month"
          isLoading={isLoading}
        />
      </div>

      {/* Error fallback for metrics */}
      {error && !isLoading && (
        <div className="text-sm text-destructive">
          Failed to load financial metrics.{' '}
          <button className="underline" onClick={() => refetch()}>Retry</button>
        </div>
      )}

      {/* Middle row: charts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <BookingTrendChart />
        </div>
        <div className="lg:col-span-1">
          <OccupancyChart />
        </div>
      </div>

      {/* Bottom: actions preview */}
      <ActionsPreview />
    </div>
  )
}
