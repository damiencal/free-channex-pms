import { useState } from 'react'
import {
  useReconciliation,
  useRunReconciliation,
  useConfirmMatch,
  useRejectMatch,
} from '@/hooks/useReconciliation'
import { type UnreconciledPayout, type UnreconciledDeposit } from '@/api/finance'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { ReconciliationPanel } from './ReconciliationPanel'

// ---------------------------------------------------------------------------
// Extended payout/deposit item types with panel-enrichment fields
// ---------------------------------------------------------------------------

interface PayoutPanelItem extends UnreconciledPayout {
  _matchId?: number
  _isPending?: boolean
}

interface DepositPanelItem extends UnreconciledDeposit {
  _matchId?: number
  _isPending?: boolean
  _isNeedsReview?: boolean
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

interface StatCardProps {
  label: string
  value: number | string
  colorClass?: string
}

function StatCard({ label, value, colorClass = 'text-foreground' }: StatCardProps) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border bg-card px-4 py-3 shadow-sm">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={`text-2xl font-semibold tabular-nums ${colorClass}`}>{value}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Skeleton loading layout
// ---------------------------------------------------------------------------

function ReconciliationSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 rounded-lg bg-muted" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="h-72 rounded-xl bg-muted" />
        <div className="h-72 rounded-xl bg-muted" />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ReconciliationTab
// ---------------------------------------------------------------------------

export function ReconciliationTab() {
  const [hoveredMatchId, setHoveredMatchId] = useState<number | null>(null)

  const { data, isLoading, isError, refetch } = useReconciliation()
  const runMutation = useRunReconciliation()
  const confirmMutation = useConfirmMatch()
  const rejectMutation = useRejectMatch()

  // ------------------------------------------------------------------
  // Loading / error states
  // ------------------------------------------------------------------

  if (isLoading) {
    return <ReconciliationSkeleton />
  }

  if (isError || !data) {
    return (
      <ErrorAlert
        message="Failed to load reconciliation data."
        onRetry={() => void refetch()}
      />
    )
  }

  // ------------------------------------------------------------------
  // Derived data
  // ------------------------------------------------------------------

  const { unmatched_payouts, unmatched_deposits, needs_review, pending_confirmation } = data

  // Build left panel (payouts): pending first, then unmatched
  const leftItems: PayoutPanelItem[] = [
    ...pending_confirmation.map((pc) => ({
      ...pc.booking,
      _matchId: pc.match_id,
      _isPending: true as const,
    })),
    ...unmatched_payouts,
  ]

  // Build right panel (deposits): pending first, then needs_review, then unmatched
  const rightItems: DepositPanelItem[] = [
    ...pending_confirmation.map((pc) => ({
      ...pc.deposit,
      _matchId: pc.match_id,
      _isPending: true as const,
    })),
    ...needs_review.map((nr) => ({
      ...nr,
      _isNeedsReview: true as const,
    })),
    ...unmatched_deposits,
  ]

  // Summary statistics
  const totalUnreconciled =
    unmatched_deposits.reduce((sum, d) => sum + parseFloat(d.amount), 0) +
    needs_review.reduce((sum, d) => sum + parseFloat(d.amount), 0) +
    pending_confirmation.reduce((sum, pc) => sum + parseFloat(pc.deposit.amount), 0)

  const isAllReconciled =
    pending_confirmation.length === 0 &&
    needs_review.length === 0 &&
    unmatched_payouts.length === 0 &&
    unmatched_deposits.length === 0

  // ------------------------------------------------------------------
  // Action handlers
  // ------------------------------------------------------------------

  function handleRun() {
    runMutation.mutate()
  }

  function handleConfirmPending(matchId: number) {
    const match = pending_confirmation.find((pc) => pc.match_id === matchId)
    if (!match) return
    confirmMutation.mutate({
      booking_id: match.booking.id,
      bank_transaction_id: match.deposit.id,
      confirmed_by: 'user',
    })
  }

  function handleReject(matchId: number) {
    rejectMutation.mutate(matchId)
  }

  function handleReviewConfirm(bookingId: number, bankTransactionId: number) {
    confirmMutation.mutate({
      booking_id: bookingId,
      bank_transaction_id: bankTransactionId,
      confirmed_by: 'user',
    })
  }

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <div className="space-y-4">
      {/* Summary stats + Run button */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 flex-1">
          <StatCard
            label="Pending Confirmation"
            value={pending_confirmation.length}
            colorClass={pending_confirmation.length > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-foreground'}
          />
          <StatCard
            label="Needs Review"
            value={needs_review.length}
            colorClass={needs_review.length > 0 ? 'text-orange-600 dark:text-orange-400' : 'text-foreground'}
          />
          <StatCard
            label="Unmatched Payouts"
            value={unmatched_payouts.length}
            colorClass="text-muted-foreground"
          />
          <StatCard
            label="Unmatched Deposits"
            value={unmatched_deposits.length}
            colorClass="text-muted-foreground"
          />
        </div>

        <div className="flex flex-col items-end gap-2 shrink-0">
          <Button onClick={handleRun} disabled={runMutation.isPending}>
            {runMutation.isPending ? 'Running...' : 'Run Reconciliation'}
          </Button>
          {totalUnreconciled > 0 && (
            <span className="text-xs text-muted-foreground tabular-nums">
              ${totalUnreconciled.toFixed(2)} unreconciled
            </span>
          )}
        </div>
      </div>

      {/* Empty state */}
      {isAllReconciled ? (
        <EmptyState
          title="All reconciled"
          description="No unreconciled items. Run reconciliation after importing new data."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ReconciliationPanel
            title="Platform Payouts"
            type="payouts"
            emptyMessage="No unmatched payouts"
            payoutItems={leftItems}
            hoveredMatchId={hoveredMatchId}
            onHoverMatch={setHoveredMatchId}
          />
          <ReconciliationPanel
            title="Bank Deposits"
            type="deposits"
            emptyMessage="No unmatched deposits"
            depositItems={rightItems}
            hoveredMatchId={hoveredMatchId}
            onHoverMatch={setHoveredMatchId}
            onConfirm={handleConfirmPending}
            onReject={handleReject}
            unmatchedPayouts={unmatched_payouts}
            onReviewConfirm={handleReviewConfirm}
          />
        </div>
      )}
    </div>
  )
}
