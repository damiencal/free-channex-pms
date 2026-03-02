// ---------------------------------------------------------------------------
// MonthlyTable — reusable horizontal-scroll monthly breakdown table
// Used by PLTab (P&L monthly sub-view) and IncomeStatementTab (Plan 04)
// ---------------------------------------------------------------------------

interface MonthlyTableRow {
  label: string
  values: Record<string, string> // month key -> amount string
  total: string
  isSubtotal?: boolean
  isGrandTotal?: boolean
}

interface MonthlyTableProps {
  months: string[] // ordered month keys e.g. ["2026-01", "2026-02", ...]
  rows: MonthlyTableRow[]
  showPercentage?: boolean
  percentageBase?: string // total to compute % against (e.g. revenue total)
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMonthLabel(monthKey: string): string {
  const [year, monthStr] = monthKey.split('-')
  const monthIndex = parseInt(monthStr, 10) - 1
  return new Date(parseInt(year, 10), monthIndex, 1).toLocaleDateString('en-US', {
    month: 'short',
    year: 'numeric',
  })
}

function formatAmount(value: string): { display: string; isNegative: boolean; isZero: boolean } {
  const num = parseFloat(value)
  if (isNaN(num) || num === 0) {
    return { display: '\u2014', isNegative: false, isZero: true }
  }
  const abs = Math.abs(num).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (num < 0) {
    return { display: `(${abs})`, isNegative: true, isZero: false }
  }
  return { display: abs, isNegative: false, isZero: false }
}

function computePercent(amount: string, base: string): string {
  const num = parseFloat(amount)
  const baseNum = parseFloat(base)
  if (isNaN(num) || isNaN(baseNum) || baseNum === 0 || num === 0) return '\u2014'
  return (Math.abs(num) / Math.abs(baseNum) * 100).toFixed(1) + '%'
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MonthlyTable({ months, rows, showPercentage, percentageBase }: MonthlyTableProps) {
  return (
    <div className="overflow-x-auto print:overflow-visible">
      <table className="w-full min-w-max text-sm">
        <thead>
          <tr className="border-b">
            <th className="sticky left-0 z-10 bg-card px-3 py-2 text-left font-medium min-w-[180px]" />
            {months.map((m) => (
              <th key={m} className="px-3 py-2 text-right font-medium whitespace-nowrap">
                {formatMonthLabel(m)}
              </th>
            ))}
            <th className="px-3 py-2 text-right font-medium whitespace-nowrap">Total</th>
            {showPercentage && (
              <th className="px-3 py-2 text-right font-medium whitespace-nowrap">%</th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const rowBg = row.isGrandTotal
              ? 'bg-muted/60'
              : row.isSubtotal
                ? 'bg-muted/30'
                : ''
            const rowFont = row.isGrandTotal
              ? 'font-semibold'
              : row.isSubtotal
                ? 'font-medium'
                : ''
            const rowBorder = row.isGrandTotal ? 'border-t-2' : ''

            const { display: totalDisplay, isNegative: totalNeg } = formatAmount(row.total)

            return (
              <tr key={i} className={`${rowBg} ${rowBorder}`}>
                {/* Sticky label cell */}
                <td
                  className={`sticky left-0 z-10 px-3 py-1.5 text-left ${rowFont} ${rowBg} ${rowBorder}`}
                >
                  {row.label}
                </td>

                {/* Monthly value cells */}
                {months.map((m) => {
                  const raw = row.values[m]
                  if (raw === undefined) {
                    return (
                      <td key={m} className="px-3 py-1.5 text-right tabular-nums text-muted-foreground">
                        &mdash;
                      </td>
                    )
                  }
                  const { display, isNegative } = formatAmount(raw)
                  return (
                    <td
                      key={m}
                      className={`px-3 py-1.5 text-right tabular-nums ${isNegative ? 'text-red-600 dark:text-red-400' : ''}`}
                    >
                      {display}
                    </td>
                  )
                })}

                {/* Total column */}
                <td
                  className={`px-3 py-1.5 text-right tabular-nums ${rowFont} ${totalNeg ? 'text-red-600 dark:text-red-400' : ''}`}
                >
                  {totalDisplay}
                </td>

                {/* Optional percentage column */}
                {showPercentage && (
                  <td className={`px-3 py-1.5 text-right tabular-nums text-muted-foreground ${rowFont}`}>
                    {percentageBase != null ? computePercent(row.total, percentageBase) : '\u2014'}
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
