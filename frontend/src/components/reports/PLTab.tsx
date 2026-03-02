import { useState } from 'react'
import { usePL } from '@/hooks/useReports'
import { ReportFilters } from './ReportFilters'
import { ReportSection } from './ReportSection'
import { MonthlyTable } from './MonthlyTable'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import type { PLParams } from '@/api/reports'

// ---------------------------------------------------------------------------
// Number formatting helpers
// ---------------------------------------------------------------------------

function formatAmount(value: string): { display: string; isNegative: boolean; isZero: boolean } {
  const num = parseFloat(value)
  if (isNaN(num) || num === 0) {
    return { display: '\u2014', isNegative: false, isZero: true }
  }
  const abs = Math.abs(num).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  if (num < 0) {
    return { display: `(${abs})`, isNegative: true, isZero: false }
  }
  return { display: abs, isNegative: false, isZero: false }
}

function formatPercent(amount: string, base: string): string {
  const num = parseFloat(amount)
  const baseNum = parseFloat(base)
  if (isNaN(num) || isNaN(baseNum) || baseNum === 0 || num === 0) return '\u2014'
  return (Math.abs(num) / Math.abs(baseNum) * 100).toFixed(1) + '%'
}

function formatDateLabel(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function titleCase(str: string): string {
  return str
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// ---------------------------------------------------------------------------
// Local AmountCell component
// ---------------------------------------------------------------------------

function AmountCell({ value, className = '' }: { value: string; className?: string }) {
  const { display, isNegative } = formatAmount(value)
  return (
    <td
      className={`px-3 py-1.5 text-right tabular-nums ${isNegative ? 'text-red-600 dark:text-red-400' : ''} ${className}`}
    >
      {display}
    </td>
  )
}

// ---------------------------------------------------------------------------
// PLTab
// ---------------------------------------------------------------------------

type SubView = 'totals' | 'monthly'

export function PLTab() {
  const { data, isFetching, isError, error, refetch, generate, hasGenerated } = usePL()
  const [subView, setSubView] = useState<SubView>('totals')

  function handleGenerate(params: { start_date: string; end_date: string } | { as_of: string }) {
    if ('start_date' in params) {
      const plParams: PLParams = {
        start_date: params.start_date,
        end_date: params.end_date,
        breakdown: 'combined',
      }
      generate(plParams)
    }
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-4">
      {/* Date filters */}
      <ReportFilters mode="range" onGenerate={handleGenerate} isFetching={isFetching} />

      {/* State: never generated */}
      {!hasGenerated && (
        <EmptyState
          title="No report generated"
          description="Select a date range and click Generate to view the P&L statement."
        />
      )}

      {/* State: fetching without data */}
      {isFetching && !data && (
        <div className="space-y-3">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      )}

      {/* State: error */}
      {isError && !isFetching && (
        <ErrorAlert
          message={(error as Error)?.message ?? 'Failed to load P&L report.'}
          onRetry={refetch}
        />
      )}

      {/* State: data available */}
      {data && !isError && (
        <div className="space-y-4">
          {/* Report header */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              Period:{' '}
              <span className="font-medium text-foreground">
                {formatDateLabel(data.period.start_date)} &mdash; {formatDateLabel(data.period.end_date)}
              </span>
            </p>

            {/* Sub-view toggle */}
            <div className="flex items-center gap-1">
              <Button
                variant={subView === 'totals' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setSubView('totals')}
              >
                Totals
              </Button>
              <Button
                variant={subView === 'monthly' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setSubView('monthly')}
              >
                Monthly
              </Button>
            </div>
          </div>

          {/* ----------------------------------------------------------------
              TOTALS sub-view
          ---------------------------------------------------------------- */}
          {subView === 'totals' && (
            <div className="space-y-3">
              {/* Revenue section */}
              <ReportSection
                title="Revenue"
                total={(() => {
                  const { display } = formatAmount(data.revenue.total)
                  return display
                })()}
              >
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-xs text-muted-foreground">
                      <th className="py-1.5 text-left font-medium">Source</th>
                      <th className="py-1.5 text-right font-medium tabular-nums">Amount</th>
                      <th className="py-1.5 text-right font-medium">% of Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.revenue.by_platform).map(([platform, info]) => {
                      const { display, isNegative } = formatAmount(info.subtotal)
                      return (
                        <tr key={platform} className="border-b border-muted/40 last:border-0">
                          <td className="px-0 py-1.5 text-left capitalize">{platform}</td>
                          <td
                            className={`px-0 py-1.5 text-right tabular-nums ${isNegative ? 'text-red-600 dark:text-red-400' : ''}`}
                          >
                            {display}
                          </td>
                          <td className="px-0 py-1.5 text-right text-muted-foreground">
                            {formatPercent(info.subtotal, data.revenue.total)}
                          </td>
                        </tr>
                      )
                    })}
                    {/* Subtotal row */}
                    <tr className="bg-muted/30 font-medium">
                      <td className="px-3 py-1.5 text-left">Total Revenue</td>
                      <AmountCell value={data.revenue.total} className="px-0" />
                      <td className="px-3 py-1.5 text-right text-muted-foreground">100%</td>
                    </tr>
                  </tbody>
                </table>
              </ReportSection>

              {/* Expenses section */}
              <ReportSection
                title="Expenses"
                total={(() => {
                  const { display } = formatAmount(data.expenses.total)
                  return display
                })()}
              >
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-xs text-muted-foreground">
                      <th className="py-1.5 text-left font-medium">Category</th>
                      <th className="py-1.5 text-right font-medium tabular-nums">Amount</th>
                      <th className="py-1.5 text-right font-medium">% of Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.expenses.by_category).map(([category, amount]) => {
                      const { display, isNegative } = formatAmount(amount)
                      return (
                        <tr key={category} className="border-b border-muted/40 last:border-0">
                          <td className="px-0 py-1.5 text-left">{titleCase(category)}</td>
                          <td
                            className={`px-0 py-1.5 text-right tabular-nums ${isNegative ? 'text-red-600 dark:text-red-400' : ''}`}
                          >
                            {display}
                          </td>
                          <td className="px-0 py-1.5 text-right text-muted-foreground">
                            {formatPercent(amount, data.revenue.total)}
                          </td>
                        </tr>
                      )
                    })}
                    {/* Subtotal row */}
                    <tr className="bg-muted/30 font-medium">
                      <td className="px-3 py-1.5 text-left">Total Expenses</td>
                      <AmountCell value={data.expenses.total} className="px-0" />
                      <td className="px-3 py-1.5 text-right text-muted-foreground">
                        {formatPercent(data.expenses.total, data.revenue.total)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </ReportSection>

              {/* Net Income grand total */}
              {(() => {
                const { display, isNegative } = formatAmount(data.net_income)
                return (
                  <div className="flex items-center justify-between rounded-md bg-muted/60 px-4 py-3 font-semibold border-t-2">
                    <span className="text-sm">Net Income</span>
                    <div className="flex items-center gap-6 text-sm tabular-nums">
                      <span className={isNegative ? 'text-red-600 dark:text-red-400' : ''}>
                        {display}
                      </span>
                      <span className="text-muted-foreground">
                        {formatPercent(data.net_income, data.revenue.total)}
                      </span>
                    </div>
                  </div>
                )
              })()}
            </div>
          )}

          {/* ----------------------------------------------------------------
              MONTHLY sub-view
          ---------------------------------------------------------------- */}
          {subView === 'monthly' && (
            <div className="space-y-3">
              {/* Revenue monthly table */}
              {(() => {
                // Collect all unique months across all platforms, sorted
                const monthSet = new Set<string>()
                Object.values(data.revenue.by_platform).forEach((info) => {
                  info.months.forEach((m) => monthSet.add(m.month))
                })
                const months = Array.from(monthSet).sort()

                // Build per-platform rows
                const platformRows = Object.entries(data.revenue.by_platform).map(
                  ([platform, info]) => {
                    const values: Record<string, string> = {}
                    info.months.forEach((m) => {
                      values[m.month] = m.amount
                    })
                    return {
                      label: platform.charAt(0).toUpperCase() + platform.slice(1),
                      values,
                      total: info.subtotal,
                    }
                  },
                )

                // Compute grand-total values per month (sum across all platforms)
                const grandTotalValues: Record<string, string> = {}
                months.forEach((m) => {
                  const sum = Object.values(data.revenue.by_platform).reduce((acc, info) => {
                    const entry = info.months.find((x) => x.month === m)
                    return acc + (entry ? parseFloat(entry.amount) : 0)
                  }, 0)
                  grandTotalValues[m] = sum.toFixed(2)
                })

                const rows = [
                  ...platformRows,
                  {
                    label: 'Total Revenue',
                    values: grandTotalValues,
                    total: data.revenue.total,
                    isGrandTotal: true,
                  },
                ]

                const { display: revTotal } = formatAmount(data.revenue.total)

                return (
                  <ReportSection title="Revenue" total={revTotal}>
                    <MonthlyTable
                      months={months}
                      rows={rows}
                      showPercentage={true}
                      percentageBase={data.revenue.total}
                    />
                  </ReportSection>
                )
              })()}

              {/* Expenses in monthly view — shown as totals (no monthly breakdown from API) */}
              <ReportSection
                title="Expenses"
                total={(() => {
                  const { display } = formatAmount(data.expenses.total)
                  return display
                })()}
              >
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-xs text-muted-foreground">
                      <th className="py-1.5 text-left font-medium">Category</th>
                      <th className="py-1.5 text-right font-medium tabular-nums">Total</th>
                      <th className="py-1.5 text-right font-medium">% of Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.expenses.by_category).map(([category, amount]) => {
                      const { display, isNegative } = formatAmount(amount)
                      return (
                        <tr key={category} className="border-b border-muted/40 last:border-0">
                          <td className="px-0 py-1.5 text-left">{titleCase(category)}</td>
                          <td
                            className={`px-0 py-1.5 text-right tabular-nums ${isNegative ? 'text-red-600 dark:text-red-400' : ''}`}
                          >
                            {display}
                          </td>
                          <td className="px-0 py-1.5 text-right text-muted-foreground">
                            {formatPercent(amount, data.revenue.total)}
                          </td>
                        </tr>
                      )
                    })}
                    <tr className="bg-muted/30 font-medium">
                      <td className="px-3 py-1.5 text-left">Total Expenses</td>
                      <AmountCell value={data.expenses.total} className="px-0" />
                      <td className="px-3 py-1.5 text-right text-muted-foreground">
                        {formatPercent(data.expenses.total, data.revenue.total)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </ReportSection>

              {/* Net Income grand total */}
              {(() => {
                const { display, isNegative } = formatAmount(data.net_income)
                return (
                  <div className="flex items-center justify-between rounded-md bg-muted/60 px-4 py-3 font-semibold border-t-2">
                    <span className="text-sm">Net Income</span>
                    <div className="flex items-center gap-6 text-sm tabular-nums">
                      <span className={isNegative ? 'text-red-600 dark:text-red-400' : ''}>
                        {display}
                      </span>
                      <span className="text-muted-foreground">
                        {formatPercent(data.net_income, data.revenue.total)}
                      </span>
                    </div>
                  </div>
                )
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
