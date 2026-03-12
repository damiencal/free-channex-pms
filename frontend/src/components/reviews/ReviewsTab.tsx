import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Star, MessageSquare, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { EmptyState } from '@/components/shared/EmptyState'
import {
  fetchChannexReviews,
  respondToChannexReview,
  syncChannexReviews,
  type ChannexReview,
} from '@/api/channex'

function StarRating({ rating }: { rating: number | null }) {
  if (rating === null) return <span className="text-muted-foreground text-xs">No rating</span>
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <Star
          key={i}
          className={`w-4 h-4 ${i < rating ? 'fill-amber-400 text-amber-400' : 'text-muted-foreground'}`}
        />
      ))}
    </div>
  )
}

function ReviewCard({ review }: { review: ChannexReview }) {
  const queryClient = useQueryClient()
  const [showReply, setShowReply] = useState(false)
  const [responseText, setResponseText] = useState(review.response_text ?? '')

  const respondMutation = useMutation({
    mutationFn: (text: string) => respondToChannexReview(review.channex_review_id, text),
    onSuccess: () => {
      setShowReply(false)
      void queryClient.invalidateQueries({ queryKey: ['channex', 'reviews'] })
    },
  })

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <p className="font-medium text-sm truncate">{review.guest_name}</p>
          {review.reviewed_at && (
            <p className="text-xs text-muted-foreground">
              {new Date(review.reviewed_at).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StarRating rating={review.rating} />
          <Badge variant={review.status === 'responded' ? 'secondary' : 'destructive'} className="text-xs">
            {review.status === 'responded' ? 'Responded' : 'New'}
          </Badge>
        </div>
      </div>

      {review.review_text && (
        <p className="text-sm text-muted-foreground leading-relaxed">{review.review_text}</p>
      )}

      {review.response_text && (
        <div className="rounded bg-muted px-3 py-2 text-sm">
          <p className="text-xs font-medium text-muted-foreground mb-1">Your response</p>
          <p>{review.response_text}</p>
        </div>
      )}

      {review.status === 'new' && (
        <div className="space-y-2">
          {showReply ? (
            <>
              <Textarea
                rows={3}
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                placeholder="Write your response..."
                className="text-sm"
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => respondMutation.mutate(responseText)}
                  disabled={respondMutation.isPending || !responseText.trim()}
                >
                  {respondMutation.isPending ? 'Sending…' : 'Send Response'}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setShowReply(false)}>
                  Cancel
                </Button>
              </div>
              {respondMutation.isError && (
                <p className="text-xs text-destructive">Failed to send response. Please try again.</p>
              )}
            </>
          ) : (
            <Button
              size="sm"
              variant="outline"
              className="gap-2"
              onClick={() => setShowReply(true)}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Reply
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

function ReviewsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-24" />
            </div>
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-3/4" />
        </div>
      ))}
    </div>
  )
}

export function ReviewsTab() {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<'all' | 'new' | 'responded'>('all')

  const { data: reviews, isLoading, error } = useQuery({
    queryKey: ['channex', 'reviews', filter],
    queryFn: () =>
      fetchChannexReviews(filter === 'all' ? undefined : { status: filter }),
    staleTime: 5 * 60 * 1000,
  })

  const syncMutation = useMutation({
    mutationFn: () => syncChannexReviews(),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['channex', 'reviews'] }),
  })

  const newCount = (reviews ?? []).filter((r) => r.status === 'new').length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Guest Reviews</h2>
          {newCount > 0 && (
            <Badge variant="destructive" className="text-xs">
              {newCount} new
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border overflow-hidden text-sm">
            {(['all', 'new', 'responded'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 capitalize transition-colors ${
                  filter === f
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-background hover:bg-muted text-muted-foreground'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <Button
            size="sm"
            variant="outline"
            className="gap-2"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
            Sync
          </Button>
        </div>
      </div>

      {error && <ErrorAlert message="Failed to load reviews." />}

      {isLoading && <ReviewsSkeleton />}

      {!isLoading && !error && reviews?.length === 0 && (
        <EmptyState title="No reviews found." />
      )}

      {!isLoading && !error && (reviews ?? []).length > 0 && (
        <div className="space-y-3">
          {reviews!.map((review) => (
            <ReviewCard key={review.id} review={review} />
          ))}
        </div>
      )}
    </div>
  )
}
