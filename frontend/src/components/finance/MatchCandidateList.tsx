import { type UnreconciledDeposit, type UnreconciledPayout } from '@/api/finance'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface MatchCandidateListProps {
  deposit: UnreconciledDeposit
  unmatchedPayouts: UnreconciledPayout[]
  onConfirm: (bookingId: number, bankTransactionId: number) => void
}

const PLATFORM_COLORS: Record<string, string> = {
  airbnb: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200',
  vrbo: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
  rvshare: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
}

function getPlatformClass(platform: string): string {
  return PLATFORM_COLORS[platform.toLowerCase()] ?? 'bg-secondary text-secondary-foreground'
}

function getCandidates(
  deposit: UnreconciledDeposit,
  payouts: UnreconciledPayout[],
): UnreconciledPayout[] {
  const depositAmount = parseFloat(deposit.amount)
  const depositDate = deposit.date ? new Date(deposit.date + 'T00:00:00') : null
  return payouts.filter((payout) => {
    const payoutAmount = parseFloat(payout.net_amount)
    if (payoutAmount !== depositAmount) return false
    if (!depositDate || !payout.check_in_date) return true
    const payoutDate = new Date(payout.check_in_date + 'T00:00:00')
    const daysDiff =
      Math.abs((depositDate.getTime() - payoutDate.getTime()) / (1000 * 60 * 60 * 24))
    return daysDiff <= 7
  })
}

export function MatchCandidateList({
  deposit,
  unmatchedPayouts,
  onConfirm,
}: MatchCandidateListProps) {
  const candidates = getCandidates(deposit, unmatchedPayouts)

  if (candidates.length === 0) {
    return (
      <p className="text-xs text-muted-foreground py-2 px-3">
        No matching bookings found for this deposit.
      </p>
    )
  }

  return (
    <div className="divide-y divide-border rounded-md border bg-background">
      {candidates.map((candidate) => (
        <div
          key={candidate.id}
          className="flex items-center justify-between gap-3 px-3 py-2 hover:bg-accent/40 transition-colors"
        >
          <div className="flex items-center gap-2 min-w-0">
            <Badge className={getPlatformClass(candidate.platform)} variant="outline">
              {candidate.platform}
            </Badge>
            <span className="text-sm truncate">{candidate.guest_name}</span>
            {candidate.check_in_date && (
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {candidate.check_in_date}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-sm font-medium tabular-nums">
              ${parseFloat(candidate.net_amount).toFixed(2)}
            </span>
            <Button
              size="xs"
              variant="outline"
              onClick={() => onConfirm(candidate.id, deposit.id)}
            >
              Select
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}
