import { Skeleton } from '@/components/ui/skeleton'

/**
 * Loading skeleton that matches stat card dimensions.
 */
export function SkeletonCard() {
  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <Skeleton className="mb-3 h-4 w-24" />
      <Skeleton className="mb-2 h-8 w-32" />
      <Skeleton className="h-3 w-16" />
    </div>
  )
}
