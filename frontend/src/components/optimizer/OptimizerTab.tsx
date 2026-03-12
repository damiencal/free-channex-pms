import { Sparkles, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ListingScoreCard } from './ListingScoreCard'
import { RecommendationsList } from './RecommendationsList'
import { usePropertyStore } from '@/store/usePropertyStore'
import {
  useListingAnalysis,
  useTriggerListingAnalysis,
} from '@/hooks/useListingOptimizer'

export function OptimizerTab() {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  const { data: analysis, isLoading, error } = useListingAnalysis(propertyId)
  const trigger = useTriggerListingAnalysis(propertyId)

  const is404 = (error as { status?: number } | null)?.status === 404

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Listing Optimizer</h2>
          <p className="text-sm text-muted-foreground">
            AI-powered recommendations to improve title, description, amenities, and pricing.
          </p>
        </div>
        <Button
          onClick={() => trigger.mutate()}
          disabled={!propertyId || trigger.isPending}
        >
          {trigger.isPending ? (
            <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="mr-2 h-4 w-4" />
          )}
          {trigger.isPending ? 'Analyzing…' : 'Run Analysis'}
        </Button>
      </div>

      {!propertyId ? (
        <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground">
          Select a property to run the listing optimizer.
        </div>
      ) : isLoading ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : is404 || !analysis ? (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <Sparkles className="mx-auto mb-3 h-10 w-10 text-muted-foreground opacity-50" />
          <p className="font-medium">No analysis yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Click <strong>Run Analysis</strong> to get AI-powered recommendations.
          </p>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <ListingScoreCard analysis={analysis} />
          <RecommendationsList recommendations={analysis.recommendations} />
        </div>
      )}

      {trigger.isSuccess && (
        <p className="text-sm text-green-600 dark:text-green-400">
          Analysis complete — scores updated.
        </p>
      )}
    </div>
  )
}
