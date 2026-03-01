import { Check, AlertCircle, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ImportResult } from './CsvDropZone'

interface CsvUploadResultProps {
  result: ImportResult | null    // non-null on success
  error: string | null           // non-null on error
  onDismiss: () => void          // resets parent to idle state
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function recordLabel(platform: string): string {
  return platform === 'mercury' ? 'bank transactions' : 'bookings'
}

export function CsvUploadResult({ result, error, onDismiss }: CsvUploadResultProps) {
  // Success display
  if (result !== null) {
    const hasInserted = result.inserted_ids.length > 0
    const hasUpdated = result.updated_ids.length > 0
    const hasIds = hasInserted || hasUpdated
    const label = recordLabel(result.platform)

    return (
      <div className="rounded-xl border bg-card p-4 shadow-sm space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
            <Check className="h-5 w-5 shrink-0" />
            <span className="font-semibold text-sm">Import Successful</span>
          </div>
          <button
            className="text-muted-foreground hover:text-foreground transition-colors"
            onClick={onDismiss}
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Summary grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm rounded-lg bg-muted/40 p-3">
          <div>
            <span className="text-muted-foreground text-xs">Platform</span>
            <p className="font-medium">{capitalize(result.platform)}</p>
          </div>
          <div>
            <span className="text-muted-foreground text-xs">File</span>
            <p className="font-medium truncate">{result.filename}</p>
          </div>
          <div>
            <span className="text-muted-foreground text-xs capitalize">{label} inserted</span>
            <p className="font-medium">{result.inserted}</p>
          </div>
          <div>
            <span className="text-muted-foreground text-xs capitalize">{label} updated</span>
            <p className="font-medium">{result.updated}</p>
          </div>
          {result.skipped > 0 && (
            <div>
              <span className="text-muted-foreground text-xs capitalize">{label} skipped</span>
              <p className="font-medium">{result.skipped}</p>
            </div>
          )}
        </div>

        {/* Scrollable ID list */}
        {hasIds && (
          <div className="space-y-2">
            {hasInserted && (
              <div>
                {hasUpdated && (
                  <p className="text-xs text-muted-foreground font-medium mb-1">New</p>
                )}
                <div className="max-h-40 overflow-y-auto rounded-md border bg-muted/20 p-2 space-y-0.5">
                  {result.inserted_ids.map((id) => (
                    <p key={id} className="text-xs font-mono text-foreground/80">
                      {id}
                    </p>
                  ))}
                </div>
              </div>
            )}
            {hasUpdated && (
              <div>
                {hasInserted && (
                  <p className="text-xs text-muted-foreground font-medium mb-1">Updated</p>
                )}
                <div className="max-h-40 overflow-y-auto rounded-md border bg-muted/20 p-2 space-y-0.5">
                  {result.updated_ids.map((id) => (
                    <p key={id} className="text-xs font-mono text-foreground/80">
                      {id}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Dismiss button */}
        <Button size="sm" variant="outline" onClick={onDismiss} className="w-full">
          Upload Another
        </Button>
      </div>
    )
  }

  // Error display
  if (error !== null) {
    const lines = error.split('\n').filter(Boolean)
    const isMultiLine = lines.length > 1

    return (
      <div className="rounded-xl border bg-card p-4 shadow-sm space-y-4">
        {/* Header */}
        <div className="flex items-center gap-2 text-destructive">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span className="font-semibold text-sm">Import Failed</span>
        </div>

        {/* Error body */}
        <div className="rounded-lg bg-destructive/5 border border-destructive/20 p-3">
          {isMultiLine ? (
            <ul className="max-h-40 overflow-y-auto space-y-1 list-disc list-inside">
              {lines.map((line, i) => (
                <li key={i} className="text-sm text-destructive/90">
                  {line}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-destructive/90">{lines[0] ?? error}</p>
          )}
        </div>

        {/* Retry button */}
        <Button size="sm" variant="outline" onClick={onDismiss} className="w-full">
          Try Again
        </Button>
      </div>
    )
  }

  return null
}
