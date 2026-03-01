import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import type { QueryResult } from '@/store/useChatStore'

const MONEY_COLUMN_PATTERN =
  /amount|revenue|expense|total|net|gross|balance|profit|cost|fee|income/i

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
})

function formatCell(column: string, value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number' && MONEY_COLUMN_PATTERN.test(column)) {
    return currencyFormatter.format(value)
  }
  return String(value)
}

interface ResultTableProps {
  results: QueryResult
}

export function ResultTable({ results }: ResultTableProps) {
  const [open, setOpen] = useState(false)

  const { columns, rows } = results
  const displayRows = rows.slice(0, 100)
  const truncated = rows.length > 100

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mt-2">
        {open ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        View data ({rows.length} {rows.length === 1 ? 'row' : 'rows'})
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-2 overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                {columns.map((col) => (
                  <th
                    key={col}
                    className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayRows.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className={rowIdx % 2 === 1 ? 'bg-muted/50' : ''}
                >
                  {columns.map((col) => (
                    <td key={col} className="px-3 py-2 whitespace-nowrap">
                      {formatCell(col, row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {truncated && (
            <p className="border-t px-3 py-2 text-xs text-muted-foreground">
              Showing first 100 of {rows.length} rows
            </p>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
