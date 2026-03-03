import { useState } from 'react'
import { useIncomeStatement } from '@/hooks/useReports'
import { ReportFilters } from './ReportFilters'
import { ReportSection } from './ReportSection'
import { MonthlyTable } from './MonthlyTable'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import type {
  IncomeStatementParams,
  IncomeStatementTotalsResponse,
  IncomeStatementMonthlyResponse,
} from '@/api/reports'

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

function formatDateLabel(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
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
// Sub-view type
// ---------------------------------------------------------------------------

type SubView = 'totals' | 'monthly'

// ---------------------------------------------------------------------------
// IncomeStatementTab
// ---------------------------------------------------------------------------

export function IncomeStatementTab() {
  const { data, isFetching, isError, error, refetch, generate, hasGenerated } =
    useIncomeStatement()
  const [activeView, setActiveView] = useState<SubView>('totals')

  function handleGenerate(params: { start_date: string; end_date: string } | { as_of: string }) {
    if ('start_date' in params) {
      const isParams: IncomeStatementParams = {
        start_date: params.start_date,
        end_date: params.end_date,
        breakdown: activeView,
      }
      generate(isParams)
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
          description="Select a date range and click Generate to view the income statement."
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
          message={(error as Error)?.message ?? 'Failed to load income statement.'}
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
                {formatDateLabel(data.period.start_date)} &mdash;{' '}
                {formatDateLabel(data.period.end_date)}
              </span>
            </p>

            {/* Sub-view toggle */}
            <div className="flex items-center gap-1">
              <Button
                variant={activeView === 'totals' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setActiveView('totals')}
              >
                Totals
              </Button>
              <Button
                variant={activeView === 'monthly' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setActiveView('monthly')}
              >
                Monthly
              </Button>
            </div>
          </div>

          {/* Prompt: sub-view switched but not re-generated */}
          {activeView !== data.breakdown && (
            <p className="text-sm text-muted-foreground">
              Click Generate to load the {activeView} view.
            </p>
          )}

          {/* ----------------------------------------------------------------
              TOTALS sub-view
          ---------------------------------------------------------------- */}
          {data.breakdown === 'totals' && activeView === 'totals' && (() => {
            const totalsData = data as IncomeStatementTotalsResponse
            const { display: revTotal } = formatAmount(totalsData.revenue.total)
            const { display: expTotal } = formatAmount(totalsData.expenses.total)
            const { display: netDisplay, isNegative: netNeg } = formatAmount(totalsData.net_income)

            return (
              <div className="space-y-3">
                {/* Revenue section */}
                <ReportSection title="Revenue" total={revTotal}>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-xs text-muted-foreground">
                        <th className="py-1.5 text-left font-medium">Account</th>
                        <th className="py-1.5 text-right font-medium tabular-nums">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(totalsData.revenue.by_account).map(([account, amount]) => {
                        const { display, isNegative } = formatAmount(amount)
                        return (
                          <tr key={account} className="border-b border-muted/40 last:border-0">
                            <td className="px-0 py-1.5 text-left">{account}</td>
                            <td
                              className={`px-0 py-1.5 text-right tabular-nums ${isNegative ? 'text-red-600 dark:text-red-400' : ''}`}
                            >
                              {display}
                            </td>
                          </tr>
                        )
                      })}
                      {/* Subtotal row */}
                      <tr className="bg-muted/30 font-medium">
                        <td className="px-3 py-1.5 text-left">Total Revenue</td>
                        <AmountCell value={totalsData.revenue.total} className="px-0" />
                      </tr>
                    </tbody>
                  </table>
                </ReportSection>

                {/* Expenses section */}
                <ReportSection title="Expenses" total={expTotal}>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-xs text-muted-foreground">
                        <th className="py-1.5 text-left font-medium">Account</th>
                        <th className="py-1.5 text-right font-medium tabular-nums">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(totalsData.expenses.by_account).map(([account, amount]) => {
                        const { display, isNegative } = formatAmount(amount)
                        return (
                          <tr key={account} className="border-b border-muted/40 last:border-0">
                            <td className="px-0 py-1.5 text-left">{account}</td>
                            <td
                              className={`px-0 py-1.5 text-right tabular-nums ${isNegative ? 'text-red-600 dark:text-red-400' : ''}`}
                            >
                              {display}
                            </td>
                          </tr>
                        )
                      })}
                      {/* Subtotal row */}
                      <tr className="bg-muted/30 font-medium">
                        <td className="px-3 py-1.5 text-left">Total Expenses</td>
                        <AmountCell value={totalsData.expenses.total} className="px-0" />
                      </tr>
                    </tbody>
                  </table>
                </ReportSection>

                {/* Net Income grand total */}
                <div className="flex items-center justify-between rounded-md bg-muted/60 px-4 py-3 font-semibold border-t-2">
                  <span className="text-sm">Net Income</span>
                  <span
                    className={`text-sm tabular-nums ${netNeg ? 'text-red-600 dark:text-red-400' : ''}`}
                  >
                    {netDisplay}
                  </span>
                </div>
              </div>
            )
          })()}

          {/* ----------------------------------------------------------------
              MONTHLY sub-view
          ---------------------------------------------------------------- */}
          {data.breakdown === 'monthly' && activeView === 'monthly' && (() => {
            const monthlyData = data as IncomeStatementMonthlyResponse

            // Collect ordered month keys
            const months = monthlyData.months.map((m) => m.month)

            // Collect all unique revenue account names across all months
            const revenueAccountSet = new Set<string>()
            monthlyData.months.forEach((m) => {
              Object.keys(m.revenue.by_account).forEach((acct) => revenueAccountSet.add(acct))
            })
            const revenueAccounts = Array.from(revenueAccountSet)

            // Collect all unique expense account names across all months
            const expenseAccountSet = new Set<string>()
            monthlyData.months.forEach((m) => {
              Object.keys(m.expenses.by_account).forEach((acct) => expenseAccountSet.add(acct))
            })
            const expenseAccounts = Array.from(expenseAccountSet)

            // Build revenue rows
            const revenueRows: { label: string; values: Record<string, string>; total: string; isSubtotal?: boolean }[] = revenueAccounts.map((account) => {
              const values: Record<string, string> = {}
              monthlyData.months.forEach((m) => {
                const amt = m.revenue.by_account[account]
                if (amt !== undefined) values[m.month] = amt
              })
              const total = monthlyData.totals.revenue.by_account[account] ?? '0.00'
              return { label: account, values, total }
            })

            // Revenue subtotal row (grand total per month)
            const revMonthlyTotals: Record<string, string> = {}
            monthlyData.months.forEach((m) => {
              revMonthlyTotals[m.month] = m.revenue.total
            })
            revenueRows.push({
              label: 'Total Revenue',
              values: revMonthlyTotals,
              total: monthlyData.totals.revenue.total,
              isSubtotal: true,
            })

            // Build expense rows
            const expenseRows: { label: string; values: Record<string, string>; total: string; isSubtotal?: boolean }[] = expenseAccounts.map((account) => {
              const values: Record<string, string> = {}
              monthlyData.months.forEach((m) => {
                const amt = m.expenses.by_account[account]
                if (amt !== undefined) values[m.month] = amt
              })
              const total = monthlyData.totals.expenses.by_account[account] ?? '0.00'
              return { label: account, values, total }
            })

            // Expense subtotal row
            const expMonthlyTotals: Record<string, string> = {}
            monthlyData.months.forEach((m) => {
              expMonthlyTotals[m.month] = m.expenses.total
            })
            expenseRows.push({
              label: 'Total Expenses',
              values: expMonthlyTotals,
              total: monthlyData.totals.expenses.total,
              isSubtotal: true,
            })

            // Net Income row (grand total)
            const netMonthlyValues: Record<string, string> = {}
            monthlyData.months.forEach((m) => {
              netMonthlyValues[m.month] = m.net_income
            })
            const netIncomeRow = {
              label: 'Net Income',
              values: netMonthlyValues,
              total: monthlyData.totals.net_income,
              isGrandTotal: true,
            }

            const { display: revTotal } = formatAmount(monthlyData.totals.revenue.total)
            const { display: expTotal } = formatAmount(monthlyData.totals.expenses.total)

            return (
              <div className="space-y-3">
                {/* Revenue monthly table */}
                <ReportSection title="Revenue" total={revTotal}>
                  <MonthlyTable months={months} rows={revenueRows} />
                </ReportSection>

                {/* Expenses monthly table */}
                <ReportSection title="Expenses" total={expTotal}>
                  <MonthlyTable months={months} rows={expenseRows} />
                </ReportSection>

                {/* Net Income grand total row */}
                <MonthlyTable months={months} rows={[netIncomeRow]} />
              </div>
            )
          })()}
        </div>
      )}
    </div>
  )
}
