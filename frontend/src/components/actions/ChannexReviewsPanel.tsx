import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { fetchChannexReviews, respondToChannexReview, type ChannexReview } from '@/api/channex'
import { apiFetch } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorAlert } from '@/components/shared/ErrorAlert'

function StarRating({ rating }: { rating: number | null }) {
  if (!rating) return null
  return (
    <span className="text-amber-500 text-sm" aria-label={`Rating: ${rating} out of 5`}>
      {'★'.repeat(rating)}{'☆'.repeat(Math.max(0, 5 - rating))}
    </span>
  )
}

interface ReviewCardProps {
  review: ChannexReview
  onResponded: () => void
}

function ReviewCard({ review, onResponded }: ReviewCardProps) {
  const [responseText, setResponseText] = useState('')
  const [showForm, setShowForm] = useState(false)
  const queryClient = useQueryClient()

  const respondMutation = useMutation({
    mutationFn: () => respondToChannexReview(review.channex_review_id, responseText),
    onSuccess: () => {
      setResponseText('')
      setShowForm(false)
      void queryClient.invalidateQueries({ queryKey: ['channex', 'reviews'] })
      onResponded()
    },
  })

  const aiMutation = useMutation({
    mutationFn: () =>
      apiFetch<{ suggestion: string }>(`/channex/reviews/${review.channex_review_id}/ai-suggest`, {
        method: 'POST',
      }),
    onSuccess: (data) => {
      setResponseText(data.suggestion)
      setShowForm(true)
    },
  })

  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium">{review.guest_name || 'Guest'}</div>
          {review.reviewed_at && (
            <div className="text-xs text-muted-foreground">
              {new Date(review.reviewed_at).toLocaleDateString()}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StarRating rating={review.rating} />
          <Badge variant={review.status === 'new' ? 'destructive' : 'secondary'} className="text-xs">
            {review.status === 'new' ? 'Needs response' : 'Responded'}
          </Badge>
        </div>
      </div>

      {review.review_text && (
        <blockquote className="text-sm text-muted-foreground border-l-2 border-muted pl-3 italic">
          "{review.review_text}"
        </blockquote>
      )}

      {review.status === 'responded' && review.response_text && (
        <div className="text-sm bg-muted rounded p-2">
          <span className="font-medium">Your response: </span>
          {review.response_text}
        </div>
      )}

      {review.status === 'new' && (
        <div className="pt-1">
          {!showForm ? (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowForm(true)}
              >
                Write response
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => aiMutation.mutate()}
                disabled={aiMutation.isPending}
                className="gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {aiMutation.isPending ? 'Thinking…' : 'AI Draft'}
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <Textarea
                placeholder="Write a thoughtful response to this review…"
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                className="text-sm resize-none min-h-[80px]"
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  disabled={!responseText.trim() || respondMutation.isPending}
                  onClick={() => respondMutation.mutate()}
                >
                  {respondMutation.isPending ? 'Submitting…' : 'Submit response'}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setShowForm(false)
                    setResponseText('')
                  }}
                >
                  Cancel
                </Button>
              </div>
              {respondMutation.isError && (
                <p className="text-xs text-destructive">
                  {respondMutation.error instanceof Error
                    ? respondMutation.error.message
                    : 'Failed to submit response'}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Channex Reviews Panel — shows guest reviews with status 'new' (awaiting response)
 * with inline response submission.
 */
export function ChannexReviewsPanel() {
  const queryClient = useQueryClient()

  const { data, isLoading, isError, error, refetch } = useQuery<ChannexReview[]>({
    queryKey: ['channex', 'reviews'],
    queryFn: () => fetchChannexReviews({ status: 'new', limit: 50 }),
    staleTime: 5 * 60 * 1000,
  })

  function handleResponded() {
    void queryClient.invalidateQueries({ queryKey: ['channex', 'reviews'] })
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1].map((i) => (
          <div key={i} className="rounded-xl border bg-card p-4 shadow-sm">
            <Skeleton className="h-4 w-40 mb-2" />
            <Skeleton className="h-16 w-full" />
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <ErrorAlert
        message={error instanceof Error ? error.message : 'Failed to load reviews.'}
        onRetry={() => void refetch()}
      />
    )
  }

  const reviews = data ?? []

  if (reviews.length === 0) {
    return <EmptyState title="No reviews awaiting response" />
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        Guest Reviews
        <Badge variant="secondary" className="ml-2">
          {reviews.length}
        </Badge>
      </h3>
      {reviews.map((review) => (
        <ReviewCard
          key={review.id}
          review={review}
          onResponded={handleResponded}
        />
      ))}
    </div>
  )
}
