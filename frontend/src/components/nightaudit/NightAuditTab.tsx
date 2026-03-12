/**
 * Night Audit Tab — advance the selling date and view audit history.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Moon, Play, History, CheckCircle, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from '@/components/ui/dialog'
import { getCurrentAuditState, runNightAudit, fetchAuditHistory } from '@/api/nightAudit'
import { usePropertyStore } from '@/store/usePropertyStore'

// -------------------------------------------------------------------------
function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit',
  })
}

// -------------------------------------------------------------------------
// Confirm Audit Dialog
// -------------------------------------------------------------------------
function RunAuditDialog({
  open, onClose, sellingDate, onRun, isPending, errorMsg,
}: {
  open: boolean
  onClose: () => void
  sellingDate: string
  onRun: (notes: string) => void
  isPending?: boolean
  errorMsg?: string | null
}) {
  const [notes, setNotes] = useState('')
  const nextDate = (() => {
    const d = new Date(sellingDate + 'T12:00:00')
    d.setDate(d.getDate() + 1)
    return d.toISOString().slice(0, 10)
  })()

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Moon className="h-5 w-5 text-indigo-500" />
            Run Night Audit
          </DialogTitle>
        </DialogHeader>
        <DialogBody className="space-y-4 pt-4">
          <div className="rounded-lg bg-amber-50 border border-amber-200 dark:bg-amber-950/20 p-3 space-y-1">
            <div className="flex items-center gap-2 text-amber-700 text-sm font-medium">
              <AlertTriangle className="h-4 w-4" />
              Confirm Audit
            </div>
            <p className="text-sm text-muted-foreground">
              This will advance the selling date from{' '}
              <strong className="text-foreground">{sellingDate}</strong> to{' '}
              <strong className="text-foreground">{nextDate}</strong>.
            </p>
            <p className="text-xs text-muted-foreground">
              This action cannot be undone. All applicable charges will be posted.
            </p>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Notes (optional)</label>
            <textarea
              className="w-full min-h-16 rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Shift handover notes, special situations..."
              value={notes}
              onChange={e => setNotes(e.target.value)}
            />
          </div>
        </DialogBody>
        <DialogFooter>
          {errorMsg && (
            <p className="text-sm text-destructive mr-auto">{errorMsg}</p>
          )}
          <Button variant="outline" onClick={onClose} disabled={isPending}>Cancel</Button>
          <Button className="bg-indigo-600 hover:bg-indigo-700" onClick={() => onRun(notes)} disabled={isPending}>
            <Moon className="h-4 w-4 mr-1.5" />{isPending ? 'Running…' : 'Run Night Audit'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// -------------------------------------------------------------------------
// Main Tab
// -------------------------------------------------------------------------
export function NightAuditTab() {
  const { selectedPropertyId } = usePropertyStore()
  const qc = useQueryClient()
  const [showConfirm, setShowConfirm] = useState(false)
  const [lastResult, setLastResult] = useState<string | null>(null)
  const [auditError, setAuditError] = useState<string | null>(null)

  const { data: auditState, isLoading: loadingState } = useQuery({
    queryKey: ['audit-state', selectedPropertyId],
    queryFn: () => getCurrentAuditState(selectedPropertyId!),
    enabled: !!selectedPropertyId,
    staleTime: 30_000,
  })

  const { data: historyData, isLoading: loadingHistory } = useQuery({
    queryKey: ['audit-history', selectedPropertyId],
    queryFn: () => fetchAuditHistory(selectedPropertyId!, 20),
    enabled: !!selectedPropertyId,
    staleTime: 30_000,
  })
  const history = historyData?.results ?? []

  const runAudit = useMutation({
    mutationFn: (notes: string) => runNightAudit(selectedPropertyId!, notes || undefined),
    onSuccess: (result) => {
      void qc.invalidateQueries({ queryKey: ['audit-state'] })
      void qc.invalidateQueries({ queryKey: ['audit-history'] })
      setLastResult(result.selling_date ?? null)
      setAuditError(null)
      setShowConfirm(false)
    },
    onError: (err: Error) => {
      setAuditError(err.message ?? 'Night audit failed.')
    },
  })

  if (!selectedPropertyId) {
    return (
      <div className="rounded-xl border border-dashed p-12 text-center">
        <Moon className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-sm font-medium">Select a property to run night audit</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Night Audit</h2>
        <p className="text-muted-foreground text-sm">Advance the selling date and post nightly charges</p>
      </div>

      {/* Current state card */}
      <div className="rounded-xl border bg-card p-6 space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-100 dark:bg-indigo-950/30">
            <Moon className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Current Selling Date</p>
            {loadingState ? (
              <Skeleton className="h-7 w-36 mt-1" />
            ) : (
              <p className="text-2xl font-bold">{auditState?.current_selling_date ?? '—'}</p>
            )}
          </div>
        </div>

        {auditState && (
          <div className="grid grid-cols-2 gap-3 text-sm">
            {auditState.last_audit?.created_at && (
              <div className="rounded-lg bg-muted/40 px-3 py-2">
                <p className="text-xs text-muted-foreground">Last Audit</p>
                <p className="font-medium">{formatDateTime(auditState.last_audit.created_at)}</p>
              </div>
            )}
            {auditState.last_audit?.performed_by && (
              <div className="rounded-lg bg-muted/40 px-3 py-2">
                <p className="text-xs text-muted-foreground">Performed By</p>
                <p className="font-medium">User #{auditState.last_audit.performed_by}</p>
              </div>
            )}
          </div>
        )}

        {lastResult && (
          <div className="flex items-center gap-2 rounded-lg bg-emerald-50 border border-emerald-200 dark:bg-emerald-950/20 px-3 py-2 text-sm text-emerald-700">
            <CheckCircle className="h-4 w-4 shrink-0" />
            Night audit completed. New selling date: <strong>{lastResult}</strong>
          </div>
        )}

        <Button
          className="bg-indigo-600 hover:bg-indigo-700 text-white"
          onClick={() => setShowConfirm(true)}
          disabled={!auditState || runAudit.isPending}
        >
          <Play className="h-4 w-4 mr-1.5" />
          {runAudit.isPending ? 'Running Audit…' : 'Run Night Audit'}
        </Button>
      </div>

      {/* History */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">Audit History</h3>
        </div>

        {loadingHistory ? (
          <div className="space-y-2">
            {[0,1,2,3].map(i => <Skeleton key={i} className="h-12 rounded-lg" />)}
          </div>
        ) : history.length === 0 ? (
          <p className="text-sm text-muted-foreground">No audit history yet</p>
        ) : (
          <div className="rounded-xl border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="text-left px-4 py-2.5">Selling Date</th>
                  <th className="text-left px-4 py-2.5">Run At</th>
                  <th className="text-left px-4 py-2.5 hidden sm:table-cell">Performed By</th>
                  <th className="text-left px-4 py-2.5 hidden md:table-cell">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {history.map((entry, i) => (
                  <tr key={i} className="hover:bg-muted/20">
                    <td className="px-4 py-3 font-medium">{entry.selling_date}</td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDateTime(entry.created_at)}</td>
                    <td className="px-4 py-3 text-muted-foreground hidden sm:table-cell">
                      {entry.performed_by ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-xs hidden md:table-cell max-w-xs truncate">
                      {entry.notes ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showConfirm && auditState && (
        <RunAuditDialog
          open
          onClose={() => { setShowConfirm(false); setAuditError(null) }}
          sellingDate={auditState.current_selling_date}
          onRun={notes => runAudit.mutate(notes)}
          isPending={runAudit.isPending}
          errorMsg={auditError}
        />
      )}
    </div>
  )
}
