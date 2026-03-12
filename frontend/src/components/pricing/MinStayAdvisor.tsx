import { Moon } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRecommendations } from '@/hooks/usePricing'
import { format, addDays } from 'date-fns'

/** Shows upcoming min-stay recommendations from the pending price recommendations. */
export function MinStayAdvisor() {
  const today = new Date()
  const dateFrom = format(today, 'yyyy-MM-dd')
  const dateTo = format(addDays(today, 60), 'yyyy-MM-dd')

  const { data: recs, isLoading } = useRecommendations({
    date_from: dateFrom,
    date_to: dateTo,
    status: 'pending',
  })

  // Group by min-stay value
  const grouped: Record<number, typeof recs> = {}
  recs?.forEach((r) => {
    const ms = r.min_stay
    if (!grouped[ms]) grouped[ms] = []
    grouped[ms]!.push(r)
  })

  const entries = Object.entries(grouped)
    .map(([k, v]) => ({ minStay: parseInt(k), dates: v! }))
    .sort((a, b) => a.minStay - b.minStay)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Moon className="h-5 w-5 text-muted-foreground" />
            Min Stay Intelligence
          </CardTitle>
          <CardDescription>
            AI-recommended minimum stay lengths for the next 60 days based on demand signals,
            gap detection, and booking patterns. Accept price recommendations to apply these.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : !entries.length ? (
            <p className="text-sm text-muted-foreground">
              No pending recommendations. Generate prices first.
            </p>
          ) : (
            <div className="space-y-4">
              {entries.map(({ minStay, dates }) => (
                <div key={minStay}>
                  <h4 className="mb-2 text-sm font-semibold">
                    {minStay}-night minimum
                    <span className="ml-1.5 text-xs text-muted-foreground">({dates.length} days)</span>
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {dates.map((r) => (
                      <span
                        key={r.id}
                        className="rounded bg-muted px-2 py-0.5 text-xs tabular-nums"
                      >
                        {format(new Date(r.date + 'T12:00:00'), 'MMM d')}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              <p className="mt-2 text-xs text-muted-foreground">
                Orphan-day gaps trigger 1-night min; high-demand weekends trigger 2-night min.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
