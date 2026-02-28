import { Skeleton } from '@/components/ui/skeleton'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { ActionsList } from './ActionsList'
import { useActions } from '@/hooks/useActions'

/**
 * Actions tab: fetches pending action items and renders an expandable sorted list.
 * Loading: skeleton rows. Error: ErrorAlert with retry. Empty: muted centered message.
 */
export function ActionsTab() {
  const { data, isLoading, isError, error, refetch } = useActions()

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border bg-card p-4 shadow-sm flex items-center gap-3">
            <Skeleton className="h-4 w-4 rounded-full shrink-0" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-56" />
            </div>
            <Skeleton className="h-5 w-16 rounded-full shrink-0" />
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <ErrorAlert
        message={error instanceof Error ? error.message : 'Failed to load actions.'}
        onRetry={() => void refetch()}
      />
    )
  }

  const items = data?.actions ?? []

  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground text-sm">No pending actions</p>
      </div>
    )
  }

  return <ActionsList items={items} />
}
