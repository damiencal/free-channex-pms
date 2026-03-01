import { useState } from 'react'
import { type UnreconciledDeposit, type UnreconciledPayout } from '@/api/finance'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { MatchCandidateList } from './MatchCandidateList'

// ---------------------------------------------------------------------------
// Platform colors
// ---------------------------------------------------------------------------

const PLATFORM_COLORS: Record<string, string> = {
  airbnb: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200',
  vrbo: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
  rvshare: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
}

function getPlatformClass(platform: string): string {
  return PLATFORM_COLORS[platform.toLowerCase()] ?? 'bg-secondary text-secondary-foreground'
}

// ---------------------------------------------------------------------------
// Internal payout item types (includes pending-confirmation enrichment)
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
// Payout item row
// ---------------------------------------------------------------------------

interface PayoutItemRowProps {
  item: PayoutPanelItem
  isHovered: boolean
  onMouseEnter: () => void
  onMouseLeave: () => void
}

function PayoutItemRow({ item, isHovered, onMouseEnter, onMouseLeave }: PayoutItemRowProps) {
  const isPending = item._isPending

  return (
    <div
      className={[
        'flex items-center justify-between gap-3 px-3 py-2.5 transition-colors',
        isPending
          ? 'bg-amber-50 dark:bg-amber-950/30 border-l-4 border-amber-500'
          : 'border-l-4 border-transparent',
        isPending && isHovered ? 'ring-2 ring-inset ring-amber-400' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="flex items-center gap-2 min-w-0">
        <Badge className={getPlatformClass(item.platform)} variant="outline">
          {item.platform}
        </Badge>
        <span className="text-sm truncate">{item.guest_name}</span>
        {item.check_in_date && (
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {item.check_in_date}
          </span>
        )}
      </div>
      <span className="text-sm font-medium tabular-nums shrink-0">
        ${parseFloat(item.net_amount).toFixed(2)}
      </span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Deposit item row
// ---------------------------------------------------------------------------

interface DepositItemRowProps {
  item: DepositPanelItem
  isHovered: boolean
  onMouseEnter: () => void
  onMouseLeave: () => void
  onConfirm?: (matchId: number) => void
  onReject?: (matchId: number) => void
  unmatchedPayouts?: UnreconciledPayout[]
  onReviewConfirm?: (bookingId: number, bankTransactionId: number) => void
}

function DepositItemRow({
  item,
  isHovered,
  onMouseEnter,
  onMouseLeave,
  onConfirm,
  onReject,
  unmatchedPayouts,
  onReviewConfirm,
}: DepositItemRowProps) {
  const [isOpen, setIsOpen] = useState(false)

  const isPending = item._isPending
  const isNeedsReview = item._isNeedsReview

  const rowBg = isPending
    ? 'bg-amber-50 dark:bg-amber-950/30 border-l-4 border-amber-500'
    : isNeedsReview
      ? 'bg-orange-50 dark:bg-orange-950/30 border-l-4 border-orange-500'
      : 'border-l-4 border-transparent'

  const hoverRing = isPending && isHovered ? 'ring-2 ring-inset ring-amber-400' : ''

  if (isNeedsReview) {
    return (
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger
          className={[
            'w-full flex items-center justify-between gap-3 px-3 py-2.5 transition-colors text-left',
            rowBg,
            'hover:brightness-95',
          ]
            .filter(Boolean)
            .join(' ')}
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xs text-orange-600 dark:text-orange-400 font-medium whitespace-nowrap">
              Needs Review
            </span>
            {item.date && (
              <span className="text-xs text-muted-foreground whitespace-nowrap">{item.date}</span>
            )}
            {item.description && (
              <span className="text-sm truncate max-w-[180px]">{item.description}</span>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-sm font-medium tabular-nums">
              ${parseFloat(item.amount).toFixed(2)}
            </span>
            <span className="text-xs text-muted-foreground">{isOpen ? '▲' : '▼'}</span>
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="px-3 py-2 bg-orange-50/60 dark:bg-orange-950/20">
            <p className="text-xs text-muted-foreground mb-2">
              Multiple bookings match this deposit — select the correct one:
            </p>
            <MatchCandidateList
              deposit={item}
              unmatchedPayouts={unmatchedPayouts ?? []}
              onConfirm={onReviewConfirm ?? (() => {})}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>
    )
  }

  return (
    <div
      className={[
        'flex items-center justify-between gap-3 px-3 py-2.5 transition-colors',
        rowBg,
        hoverRing,
      ]
        .filter(Boolean)
        .join(' ')}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="flex items-center gap-2 min-w-0">
        {item.date && (
          <span className="text-xs text-muted-foreground whitespace-nowrap">{item.date}</span>
        )}
        {item.description && (
          <span className="text-sm truncate max-w-[220px]">{item.description}</span>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-sm font-medium tabular-nums">
          ${parseFloat(item.amount).toFixed(2)}
        </span>
        {isPending && item._matchId != null && (
          <>
            <Button
              size="xs"
              className="bg-green-600 hover:bg-green-700 text-white"
              onClick={() => onConfirm?.(item._matchId!)}
            >
              Confirm
            </Button>
            <Button
              size="xs"
              variant="outline"
              className="border-destructive text-destructive hover:bg-destructive/10"
              onClick={() => onReject?.(item._matchId!)}
            >
              Reject
            </Button>
          </>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ReconciliationPanel
// ---------------------------------------------------------------------------

interface ReconciliationPanelProps {
  title: string
  type: 'payouts' | 'deposits'
  emptyMessage: string
  payoutItems?: PayoutPanelItem[]
  depositItems?: DepositPanelItem[]
  hoveredMatchId: number | null
  onHoverMatch: (matchId: number | null) => void
  onConfirm?: (matchId: number) => void
  onReject?: (matchId: number) => void
  needsReviewItems?: UnreconciledDeposit[]
  unmatchedPayouts?: UnreconciledPayout[]
  onReviewConfirm?: (bookingId: number, bankTransactionId: number) => void
}

export function ReconciliationPanel({
  title,
  type,
  emptyMessage,
  payoutItems = [],
  depositItems = [],
  hoveredMatchId,
  onHoverMatch,
  onConfirm,
  onReject,
  unmatchedPayouts,
  onReviewConfirm,
}: ReconciliationPanelProps) {
  const isEmpty = type === 'payouts' ? payoutItems.length === 0 : depositItems.length === 0

  return (
    <div className="flex flex-col rounded-xl border bg-card shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b">
        <h3 className="text-sm font-semibold">{title}</h3>
      </div>
      <ScrollArea className="h-[480px]">
        {isEmpty ? (
          <div className="flex items-center justify-center py-16">
            <p className="text-sm text-muted-foreground">{emptyMessage}</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {type === 'payouts' &&
              payoutItems.map((item) => (
                <PayoutItemRow
                  key={`${item._isPending ? 'pending' : 'unmatched'}-${item.id}`}
                  item={item}
                  isHovered={item._matchId != null && item._matchId === hoveredMatchId}
                  onMouseEnter={() => item._matchId != null && onHoverMatch(item._matchId)}
                  onMouseLeave={() => onHoverMatch(null)}
                />
              ))}

            {type === 'deposits' &&
              depositItems.map((item) => (
                <DepositItemRow
                  key={`${item._isPending ? 'pending' : item._isNeedsReview ? 'review' : 'unmatched'}-${item.id}`}
                  item={item}
                  isHovered={item._matchId != null && item._matchId === hoveredMatchId}
                  onMouseEnter={() => item._matchId != null && onHoverMatch(item._matchId)}
                  onMouseLeave={() => onHoverMatch(null)}
                  onConfirm={onConfirm}
                  onReject={onReject}
                  unmatchedPayouts={unmatchedPayouts}
                  onReviewConfirm={onReviewConfirm}
                />
              ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
