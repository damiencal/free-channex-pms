import { useState } from 'react'
import { format, addDays, startOfWeek, addWeeks } from 'date-fns'
import { Check, X, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { usePropertyStore } from '@/store/usePropertyStore'
import {
  useRecommendations,
  useAcceptRecommendation,
  useRejectRecommendation,
  useBulkAcceptRecommendations,
  useGenerateRecommendations,
} from '@/hooks/usePricing'
import type { PriceRecommendation } from '@/api/pricing'

const DEMAND_COLOR = (score: string | null) => {
  if (!score) return 'bg-muted'
  const n = parseFloat(score)
  if (n >= 0.7) return 'bg-red-100 dark:bg-red-900/30'
  if (n >= 0.4) return 'bg-yellow-100 dark:bg-yellow-900/30'
  return 'bg-green-100 dark:bg-green-900/30'
}

const STATUS_BADGE = (status: PriceRecommendation['status']) => {
  const map: Record<string, string> = {
    pending: 'secondary',
    accepted: 'default',
    rejected: 'destructive',
    expired: 'outline',
  }
  return map[status] ?? 'secondary'
}

export function RecommendationsView() {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  const today = new Date()
  const [weekOffset, setWeekOffset] = useState(0)

  const weekStart = startOfWeek(addWeeks(today, weekOffset), { weekStartsOn: 1 })
  const dateFrom = format(weekStart, 'yyyy-MM-dd')
  const dateTo = format(addDays(weekStart, 29), 'yyyy-MM-dd') // 4-week view

  const { data: recs, isLoading } = useRecommendations({ date_from: dateFrom, date_to: dateTo })
  const accept = useAcceptRecommendation()
  const reject = useRejectRecommendation()
  const bulkAccept = useBulkAcceptRecommendations()
  const generate = useGenerateRecommendations()

  const pendingIds = recs?.filter((r) => r.status === 'pending').map((r) => r.id) ?? []

  const handleGenerate = () => {
    if (!propertyId) return
    generate.mutate({ property_id: propertyId, date_from: dateFrom, date_to: dateTo })
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setWeekOffset((o) => o - 4)}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-sm font-medium min-w-[16ch] text-center">
          {format(weekStart, 'MMM d')} – {format(addDays(weekStart, 27), 'MMM d, yyyy')}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setWeekOffset((o) => o + 4)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>

        <div className="ml-auto flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleGenerate}
            disabled={!propertyId || generate.isPending}
          >
            <RefreshCw className={`mr-1.5 h-4 w-4 ${generate.isPending ? 'animate-spin' : ''}`} />
            Generate
          </Button>
          {pendingIds.length > 0 && (
            <Button
              size="sm"
              onClick={() => bulkAccept.mutate({ ids: pendingIds })}
              disabled={bulkAccept.isPending}
            >
              <Check className="mr-1.5 h-4 w-4" />
              Accept All ({pendingIds.length})
            </Button>
          )}
        </div>
      </div>

      {generate.isSuccess && (
        <p className="text-sm text-muted-foreground">
          Generation queued — prices will appear shortly.
        </p>
      )}

      {/* Grid */}
      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading recommendations…</div>
      ) : !recs?.length ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No price recommendations for this period.</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Click <strong>Generate</strong> to run the HLP algorithm.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
          {recs.map((rec) => (
            <Card
              key={rec.id}
              className={`${DEMAND_COLOR(rec.demand_score)} border transition-colors`}
            >
              <CardHeader className="p-2 pb-0">
                <p className="text-xs font-medium text-muted-foreground">
                  {format(new Date(rec.date + 'T12:00:00'), 'EEE, MMM d')}
                </p>
              </CardHeader>
              <CardContent className="p-2 pt-1 space-y-1">
                <p className="text-lg font-bold tabular-nums">
                  ${parseFloat(rec.recommended_price).toFixed(0)}
                </p>
                <p className="text-xs text-muted-foreground">
                  base ${parseFloat(rec.base_price).toFixed(0)}
                </p>
                <Badge variant={STATUS_BADGE(rec.status) as never} className="text-[10px] h-4">
                  {rec.status}
                </Badge>
                {rec.status === 'pending' && (
                  <div className="flex gap-1 pt-1">
                    <button
                      className="rounded bg-green-600 p-0.5 text-white hover:bg-green-700"
                      onClick={() => accept.mutate({ id: rec.id })}
                      title="Accept"
                    >
                      <Check className="h-3 w-3" />
                    </button>
                    <button
                      className="rounded bg-red-500 p-0.5 text-white hover:bg-red-600"
                      onClick={() => reject.mutate({ id: rec.id })}
                      title="Reject"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                )}
                {rec.accepted_price && rec.status === 'accepted' && (
                  <p className="text-xs text-green-700 dark:text-green-400">
                    ✓ ${parseFloat(rec.accepted_price).toFixed(0)}
                  </p>
                )}
                {rec.confidence && (
                  <p className="text-[10px] text-muted-foreground">
                    {Math.round(parseFloat(rec.confidence) * 100)}% conf.
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="h-3 w-3 rounded bg-red-100 dark:bg-red-900/30 border" /> High demand
        </span>
        <span className="flex items-center gap-1">
          <span className="h-3 w-3 rounded bg-yellow-100 dark:bg-yellow-900/30 border" /> Moderate
        </span>
        <span className="flex items-center gap-1">
          <span className="h-3 w-3 rounded bg-green-100 dark:bg-green-900/30 border" /> Low demand
        </span>
      </div>
    </div>
  )
}
