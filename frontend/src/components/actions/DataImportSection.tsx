import { useState } from 'react'
import { CsvDropZone, type ImportResult } from './CsvDropZone'
import { CsvUploadResult } from './CsvUploadResult'
import { RVshareEntryForm } from './RVshareEntryForm'
import { ImportHistoryAccordion } from './ImportHistoryAccordion'
import { Separator } from '@/components/ui/separator'

/**
 * Top-level import section that composes the four data import sub-components:
 * CsvDropZone / CsvUploadResult (mutually exclusive), RVshareEntryForm,
 * and ImportHistoryAccordion.
 *
 * Owns the upload result / error state so it can swap CsvDropZone for
 * CsvUploadResult after an upload attempt without losing the sibling components.
 */
export function DataImportSection() {
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  function handleResult(res: ImportResult | null, err: string | null) {
    setResult(res)
    setError(err)
  }

  function handleDismiss() {
    setResult(null)
    setError(null)
  }

  const showResult = result !== null || error !== null

  return (
    <div className="rounded-xl border bg-card p-4 md:p-6 shadow-sm space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold">Data Import</h2>
        <p className="text-sm text-muted-foreground">
          Upload CSV files or add bookings manually
        </p>
      </div>

      {/* Upload area: DropZone OR result card */}
      {showResult ? (
        <CsvUploadResult result={result} error={error} onDismiss={handleDismiss} />
      ) : (
        <CsvDropZone onResult={handleResult} />
      )}

      <Separator />

      {/* RVshare manual entry form */}
      <RVshareEntryForm />

      <Separator />

      {/* Collapsible import history */}
      <ImportHistoryAccordion />
    </div>
  )
}
