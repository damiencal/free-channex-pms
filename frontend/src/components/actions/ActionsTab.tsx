import { Skeleton } from '@/components/ui/skeleton'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { EmptyState } from '@/components/shared/EmptyState'
import { ActionsList } from './ActionsList'
import { DataImportSection } from './DataImportSection'
import { useActions } from '@/hooks/useActions'

/**
 * Actions tab: always shows the DataImportSection at the top, then
 * fetches pending action items and renders an expandable sorted list below.
 * Loading: skeleton rows. Error: ErrorAlert with retry. Empty: muted centered message.
 */
export function ActionsTab() {
  const { data, isLoading, isError, error, refetch } = useActions()

  const items = data?.actions ?? []

  return (
    <div className="space-y-6">
      {/* Data import is always visible regardless of actions loading state */}
      <DataImportSection />

      {/* Existing actions section */}
      {isLoading ? (
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
      ) : isError ? (
        <ErrorAlert
          message={error instanceof Error ? error.message : 'Failed to load actions.'}
          onRetry={() => void refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState title="No pending actions" />
      ) : (
        <ActionsList items={items} />
      )}
    </div>
  )
}
