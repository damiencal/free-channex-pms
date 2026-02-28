import { useState } from 'react'
import { CalendarDays, GanttChart } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { EmptyState } from '@/components/shared/EmptyState'
import { MonthCalendar } from './MonthCalendar'
import { TimelineView } from './TimelineView'
import { useBookings } from '@/hooks/useBookings'

type ViewMode = 'month' | 'timeline'

/** Build YYYY-MM-DD string for the first day of a given month. */
function monthStartISO(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}-01`
}

/** Build YYYY-MM-DD string for the last day of a given month. */
function monthEndISO(date: Date): string {
  const y = date.getFullYear()
  const m = date.getMonth() + 1
  const lastDay = new Date(y, m, 0).getDate()
  return `${y}-${String(m).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
}

/**
 * Loading skeleton matching approximate calendar dimensions.
 */
function CalendarSkeleton() {
  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <Skeleton className="h-7 w-7 rounded" />
        <Skeleton className="h-4 w-36" />
        <Skeleton className="h-7 w-7 rounded" />
      </div>
      {/* Day headers */}
      <div className="grid border-b" style={{ gridTemplateColumns: 'repeat(7, 1fr)' }}>
        {Array.from({ length: 7 }, (_, i) => (
          <Skeleton key={i} className="h-8 m-1 rounded" />
        ))}
      </div>
      {/* Week rows */}
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="grid" style={{ gridTemplateColumns: 'repeat(7, 1fr)', minHeight: '80px' }}>
          {Array.from({ length: 7 }, (_, j) => (
            <div key={j} className="border-r border-b last:border-r-0 p-1">
              <Skeleton className="h-5 w-5 rounded-full" />
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

/**
 * Calendar tab: month grid (default) and timeline/Gantt view.
 *
 * State:
 *   - currentMonth: which month is displayed
 *   - viewMode: 'month' | 'timeline'
 *
 * Fetches bookings via useBookings() covering the displayed month with a
 * 1-day buffer on each side to catch bookings that start just before or
 * end just after the month boundary.
 */
export function CalendarTab() {
  const [currentMonth, setCurrentMonth] = useState<Date>(() => {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), 1)
  })
  const [viewMode, setViewMode] = useState<ViewMode>('month')

  // Date range for the API: full displayed month
  const startDate = monthStartISO(currentMonth)
  const endDate = monthEndISO(currentMonth)

  const { data: bookings, isLoading, error, refetch } = useBookings(startDate, endDate)

  function handleMonthChange(direction: 'prev' | 'next') {
    setCurrentMonth((prev) => {
      const d = new Date(prev)
      d.setMonth(d.getMonth() + (direction === 'next' ? 1 : -1))
      return d
    })
  }

  return (
    <div className="space-y-4">
      {/* View toggle */}
      <div className="flex items-center gap-2">
        <Button
          variant={viewMode === 'month' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setViewMode('month')}
          className="gap-2"
        >
          <CalendarDays className="h-4 w-4" />
          Month
        </Button>
        <Button
          variant={viewMode === 'timeline' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setViewMode('timeline')}
          className="gap-2"
        >
          <GanttChart className="h-4 w-4" />
          Timeline
        </Button>
      </div>

      {/* Error state */}
      {error && !isLoading && (
        <ErrorAlert message="Failed to load bookings." onRetry={() => refetch()} />
      )}

      {/* Loading skeleton */}
      {isLoading && <CalendarSkeleton />}

      {/* Month view */}
      {!isLoading && !error && viewMode === 'month' && (
        <>
          <MonthCalendar
            currentMonth={currentMonth}
            onMonthChange={handleMonthChange}
            bookings={bookings ?? []}
          />
          {(bookings ?? []).length === 0 && (
            <EmptyState title="No bookings for this month" />
          )}
        </>
      )}

      {/* Timeline view */}
      {!isLoading && !error && viewMode === 'timeline' && (
        <>
          <TimelineView
            currentMonth={currentMonth}
            bookings={bookings ?? []}
          />
          {(bookings ?? []).length === 0 && (
            <EmptyState title="No bookings for this month" />
          )}
        </>
      )}
    </div>
  )
}
