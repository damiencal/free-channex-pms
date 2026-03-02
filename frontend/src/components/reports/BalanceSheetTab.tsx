import { useBalanceSheet } from '@/hooks/useReports'
import { ReportFilters } from './ReportFilters'
import { ReportSection } from './ReportSection'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { Skeleton } from '@/components/ui/skeleton'

// ---------------------------------------------------------------------------
// Number formatting helpers
// ---------------------------------------------------------------------------

function formatAmount(value: string): { display: string; isNegative: boolean; isZero: boolean } {
  const num = parseFloat(value)
  if (isNaN(num) || num === 0) return { display: '\u2014', isNegative: false, isZero: true }
  const formatted = Math.abs(num).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
  return {
    display: num < 0 ? `(${formatted})` : formatted,
    isNegative: num < 0,
    isZero: false,
  }
}

function formatAsOfDate(isoDate: string): string {
  // Parse as local date to avoid UTC midnight shift
  const [year, month, day] = isoDate.split('-').map(Number)
  const date = new Date(year, month - 1, day)
  return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
}

// ---------------------------------------------------------------------------
// Local components
// ---------------------------------------------------------------------------

function AmountCell({ value, className = '' }: { value: string; className?: string }) {
  const { display, isNegative } = formatAmount(value)
  return (
    <span className={`tabular-nums ${isNegative ? 'text-red-600 dark:text-red-400' : ''} ${className}`}>
      {display}
    </span>
  )
}

interface SectionAccount {
  name: string
  balance: string
  number?: string
}

interface AccountTableProps {
  accounts: SectionAccount[]
  subtotalLabel: string
  subtotalValue: string
}

function AccountTable({ accounts, subtotalLabel, subtotalValue }: AccountTableProps) {
  return (
    <table className="w-full text-sm">
      <tbody>
        {accounts.map((account, i) => (
          <tr key={i} className="border-b border-border/40 last:border-0">
            <td className="px-3 py-1.5 text-left text-muted-foreground">{account.name}</td>
            <td className="px-3 py-1.5 text-right">
              <AmountCell value={account.balance} />
            </td>
          </tr>
        ))}
        <tr className="bg-muted/30">
          <td className="px-3 py-1.5 text-left font-medium">{subtotalLabel}</td>
          <td className="px-3 py-1.5 text-right font-medium">
            <AmountCell value={subtotalValue} />
          </td>
        </tr>
      </tbody>
    </table>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function BalanceSheetTab() {
  const { data, isFetching, isError, error, refetch, generate, hasGenerated } = useBalanceSheet()

  function handleGenerate(params: { as_of: string } | { start_date: string; end_date: string }) {
    if ('as_of' in params) {
      generate({ as_of: params.as_of })
    }
  }

  // ---------------------------------------------------------------------------
  // Determine if data has meaningful content
  // ---------------------------------------------------------------------------
  const hasContent = data
    ? data.assets.accounts.length > 0 ||
      data.liabilities.accounts.length > 0 ||
      data.equity.accounts.length > 0
    : false

  // Balance check warning
  const doesNotBalance =
    data && hasContent && data.assets.total !== data.total_liabilities_and_equity

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-4">
      <ReportFilters mode="snapshot" onGenerate={handleGenerate} isFetching={isFetching} />

      {/* Pre-generate prompt */}
      {!hasGenerated && (
        <div className="flex flex-col items-center justify-center py-16 gap-1">
          <p className="text-sm text-muted-foreground">
            Select a date and click Generate to view the balance sheet.
          </p>
        </div>
      )}

      {/* Loading skeletons */}
      {hasGenerated && isFetching && !data && (
        <div className="space-y-3">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {/* Error state */}
      {hasGenerated && isError && (
        <ErrorAlert
          message={error instanceof Error ? error.message : 'Failed to load balance sheet.'}
          onRetry={refetch}
        />
      )}

      {/* Empty state */}
      {hasGenerated && !isFetching && !isError && data && !hasContent && (
        <EmptyState
          title="No balance sheet data"
          description="No account activity found for this date."
        />
      )}

      {/* Report content */}
      {hasGenerated && !isError && data && hasContent && (
        <div className="space-y-3">
          {/* Report header */}
          <p className="text-xs text-muted-foreground">As of {formatAsOfDate(data.as_of)}</p>

          {/* Assets section */}
          <ReportSection
            title="Assets"
            total={formatAmount(data.assets.total).display}
          >
            <AccountTable
              accounts={data.assets.accounts}
              subtotalLabel="Total Assets"
              subtotalValue={data.assets.total}
            />
          </ReportSection>

          {/* Liabilities section */}
          <ReportSection
            title="Liabilities"
            total={formatAmount(data.liabilities.total).display}
          >
            <AccountTable
              accounts={data.liabilities.accounts}
              subtotalLabel="Total Liabilities"
              subtotalValue={data.liabilities.total}
            />
          </ReportSection>

          {/* Equity section */}
          <ReportSection
            title="Equity"
            total={formatAmount(data.equity.total).display}
          >
            <AccountTable
              accounts={data.equity.accounts}
              subtotalLabel="Total Equity"
              subtotalValue={data.equity.total}
            />
          </ReportSection>

          {/* Grand total row */}
          <div className="rounded-md bg-muted/60 border-t-2 border-border px-3 py-2.5 flex items-center justify-between font-semibold text-sm">
            <span>Total Liabilities &amp; Equity</span>
            <AmountCell value={data.total_liabilities_and_equity} />
          </div>

          {/* Balance check warning */}
          {doesNotBalance && (
            <p className="text-xs text-amber-600 dark:text-amber-400 text-center">
              Balance sheet does not balance
            </p>
          )}
        </div>
      )}
    </div>
  )
}
