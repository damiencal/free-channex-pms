import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useImportHistory } from '@/hooks/useImportHistory'

/**
 * Format record count as "N new, M updated" when both > 0, else a single total.
 */
function formatRecordCount(inserted: number, updated: number): string {
  if (inserted > 0 && updated > 0) {
    return `${inserted} new, ${updated} updated`
  }
  return `${inserted + updated} records`
}

/**
 * Capitalize first letter of a string (e.g. "airbnb" -> "Airbnb").
 */
function capitalize(s: string): string {
  if (!s) return s
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/**
 * Collapsible import history section showing past CSV upload runs.
 * Collapsed by default. Shows last 10 entries with a "Show more" link to load 50.
 * Each row: timestamp, platform, filename, record count, success badge, property (—).
 */
export function ImportHistoryAccordion() {
  const [open, setOpen] = useState(false)
  const [limit, setLimit] = useState(10)

  const { data, isLoading, isError, error } = useImportHistory(limit)

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5 px-2">
          <ChevronDown
            className="size-4 transition-transform duration-200"
            style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
          />
          Import History
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="mt-2 rounded-lg border bg-card overflow-hidden">
          {isLoading && (
            <div className="divide-y">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3">
                  <Skeleton className="h-3 w-32" />
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-3 w-40" />
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-5 w-16 rounded-full" />
                </div>
              ))}
            </div>
          )}

          {isError && (
            <p className="px-4 py-3 text-sm text-destructive">
              {error instanceof Error ? error.message : 'Failed to load import history'}
            </p>
          )}

          {!isLoading && !isError && data && data.length === 0 && (
            <p className="px-4 py-3 text-sm text-muted-foreground">No imports yet</p>
          )}

          {!isLoading && !isError && data && data.length > 0 && (
            <>
              {/* Desktop: horizontal table layout */}
              <div className="hidden md:block">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/40 text-muted-foreground text-xs">
                      <th className="px-4 py-2 text-left font-medium">Date</th>
                      <th className="px-4 py-2 text-left font-medium">Platform</th>
                      <th className="px-4 py-2 text-left font-medium">File</th>
                      <th className="px-4 py-2 text-left font-medium">Records</th>
                      <th className="px-4 py-2 text-left font-medium">Status</th>
                      <th className="px-4 py-2 text-left font-medium">Property</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.map((run, idx) => (
                      <tr
                        key={run.id}
                        className={idx % 2 === 0 ? 'bg-background' : 'bg-muted/20'}
                      >
                        <td className="px-4 py-2.5 text-xs text-muted-foreground whitespace-nowrap">
                          {new Date(run.imported_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-2.5 font-medium">
                          {capitalize(run.platform)}
                        </td>
                        <td className="px-4 py-2.5 max-w-[200px]">
                          <span className="truncate block text-xs text-muted-foreground" title={run.filename}>
                            {run.filename}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-xs whitespace-nowrap">
                          {formatRecordCount(run.inserted_count, run.updated_count)}
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="text-xs bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 px-2 py-0.5 rounded-full">
                            Success
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-muted-foreground">—</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile: stacked card layout */}
              <div className="md:hidden divide-y">
                {data.map((run) => (
                  <div key={run.id} className="px-4 py-3 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-sm">{capitalize(run.platform)}</span>
                      <span className="text-xs bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 px-2 py-0.5 rounded-full">
                        Success
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground truncate max-w-[200px]" title={run.filename}>
                      {run.filename}
                    </p>
                    <div className="flex gap-4 text-xs text-muted-foreground">
                      <span>{new Date(run.imported_at).toLocaleString()}</span>
                      <span>{formatRecordCount(run.inserted_count, run.updated_count)}</span>
                      <span>Property: —</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Show more link */}
              {data.length === limit && limit < 50 && (
                <div className="border-t px-4 py-2.5 text-center">
                  <button
                    onClick={() => setLimit(50)}
                    className="text-xs text-primary hover:underline underline-offset-2"
                  >
                    Show more
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
