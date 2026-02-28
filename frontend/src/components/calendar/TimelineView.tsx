import { getPlatformColorEntry } from '@/lib/platformColors'
import { BookingPopover } from './BookingPopover'
import type { Booking } from '@/hooks/useBookings'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TimelineViewProps {
  currentMonth: Date
  bookings: Booking[]
}

// ---------------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------------

/** Days in a given month (0-based month). */
function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

/** Parse YYYY-MM-DD safely (midnight local time, no UTC shift). */
function parseDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** Day-of-week of a given date (0=Sun). */
function dayOfWeek(date: Date): number {
  return date.getDay()
}

// ---------------------------------------------------------------------------
// Property grouping
// ---------------------------------------------------------------------------

/** Extract unique properties from bookings list, preserving insertion order. */
function extractProperties(bookings: Booking[]): Array<{ slug: string; displayName: string }> {
  const seen = new Set<string>()
  const result: Array<{ slug: string; displayName: string }> = []
  for (const b of bookings) {
    if (!seen.has(b.property_slug)) {
      seen.add(b.property_slug)
      result.push({ slug: b.property_slug, displayName: b.property_display_name })
    }
  }
  return result
}

// ---------------------------------------------------------------------------
// TimelineView
// ---------------------------------------------------------------------------

/**
 * Gantt-style timeline view: properties as rows, days of current month as columns.
 *
 * Layout: CSS Grid with `grid-template-columns: 140px repeat(N, 1fr)`.
 * - Column 1 (140px): property display name
 * - Columns 2..N+1: one per day in the month
 *
 * Booking bars span `grid-column: (check_in_day + 1) / (check_out_day + 2)`.
 * Day column = 2 + (day_of_month - 1) — offset by 2 to account for property label col.
 *
 * Weekend columns (Sat/Sun) are lightly shaded.
 * Container has overflow-x: auto for horizontal scroll on mobile.
 */
export function TimelineView({ currentMonth, bookings }: TimelineViewProps) {
  const year = currentMonth.getFullYear()
  const month = currentMonth.getMonth()
  const numDays = daysInMonth(year, month)

  // Properties to display as rows
  const properties = extractProperties(bookings)

  // Group bookings by property slug
  const bookingsByProperty = new Map<string, Booking[]>()
  for (const b of bookings) {
    if (!bookingsByProperty.has(b.property_slug)) bookingsByProperty.set(b.property_slug, [])
    bookingsByProperty.get(b.property_slug)!.push(b)
  }

  // Build weekend day set (0-based day indices within the month)
  const weekendDayIndices = new Set<number>()
  for (let d = 0; d < numDays; d++) {
    const date = new Date(year, month, d + 1)
    const dow = dayOfWeek(date)
    if (dow === 0 || dow === 6) weekendDayIndices.add(d)
  }

  // If no properties found, show empty state
  if (properties.length === 0) {
    return (
      <div className="rounded-xl border bg-card shadow-sm p-8 text-center text-sm text-muted-foreground">
        No bookings this month.
      </div>
    )
  }

  // Minimum column width per day in pixels — ensures bars are visible on mobile
  const DAY_MIN_WIDTH = 28

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Horizontally scrollable container */}
      <div className="overflow-x-auto">
        {/* Min width: property label (140px) + each day cell */}
        <div style={{ minWidth: `${140 + numDays * DAY_MIN_WIDTH}px` }}>
          {/*
            CSS Grid:
              Column 1: 140px fixed — property label
              Columns 2..N+1: equal-width day cells
          */}
          <div
            className="grid"
            style={{
              gridTemplateColumns: `140px repeat(${numDays}, minmax(${DAY_MIN_WIDTH}px, 1fr))`,
            }}
          >
            {/* ---- Header row ---- */}
            {/* Empty corner cell */}
            <div className="border-b border-r bg-muted/30 px-2 py-2 text-xs font-medium text-muted-foreground sticky left-0 z-20">
              Property
            </div>

            {/* Day number headers */}
            {Array.from({ length: numDays }, (_, d) => {
              const date = new Date(year, month, d + 1)
              const dow = dayOfWeek(date)
              const isWeekend = dow === 0 || dow === 6

              return (
                <div
                  key={d}
                  className={[
                    'border-b border-r last:border-r-0 py-2 text-center text-xs font-medium',
                    isWeekend ? 'bg-muted/40 text-muted-foreground' : 'text-muted-foreground',
                  ].join(' ')}
                >
                  {d + 1}
                </div>
              )
            })}

            {/* ---- Property rows ---- */}
            {properties.map(({ slug, displayName }) => {
              const propBookings = bookingsByProperty.get(slug) ?? []

              return (
                <PropertyRow
                  key={slug}
                  displayName={displayName}
                  bookings={propBookings}
                  year={year}
                  month={month}
                  numDays={numDays}
                  weekendDayIndices={weekendDayIndices}
                />
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// PropertyRow sub-component
// ---------------------------------------------------------------------------

interface PropertyRowProps {
  displayName: string
  bookings: Booking[]
  year: number
  month: number
  numDays: number
  weekendDayIndices: Set<number>
}

function PropertyRow({
  displayName,
  bookings,
  year,
  month,
  numDays,
  weekendDayIndices,
}: PropertyRowProps) {
  const monthStartDate = new Date(year, month, 1)
  const monthEndDate = new Date(year, month, numDays)

  // Compute visible booking segments for this property
  const segments = computeSegments(bookings, monthStartDate, monthEndDate)

  return (
    <>
      {/* Property label — sticky on horizontal scroll */}
      <div
        className="border-b border-r bg-card sticky left-0 z-10 flex items-center px-2 py-3"
        style={{ minHeight: '52px' }}
      >
        <span className="text-xs font-medium leading-tight line-clamp-2">{displayName}</span>
      </div>

      {/* Day cells for this property row */}
      {Array.from({ length: numDays }, (_, d) => {
        const isWeekend = weekendDayIndices.has(d)
        return (
          <div
            key={d}
            className={[
              'border-b border-r last:border-r-0 relative',
              isWeekend ? 'bg-muted/20' : '',
            ].join(' ')}
            style={{ minHeight: '52px' }}
          />
        )
      })}

      {/* Booking bars overlaid as grid items spanning their day columns.
          Each bar is positioned using overflow:visible so the 0-height grid
          cell doesn't affect row sizing. */}
      {segments.map(({ booking, colStart, colEnd, stackRow }) => (
        <BookingBarCell
          key={booking.id}
          booking={booking}
          colStart={colStart}
          colEnd={colEnd}
          stackRow={stackRow}
          numDays={numDays}
        />
      ))}
    </>
  )
}

// ---------------------------------------------------------------------------
// Segment computation
// ---------------------------------------------------------------------------

interface Segment {
  booking: Booking
  colStart: number  // 1-based day of month
  colEnd: number    // exclusive (1-based day + 1)
  stackRow: number  // vertical stacking offset for overlaps
}

function computeSegments(
  bookings: Booking[],
  monthStartDate: Date,
  monthEndDate: Date,
): Segment[] {
  const segments: Segment[] = []

  for (const booking of bookings) {
    const checkIn = parseDate(booking.check_in_date)
    const checkOut = parseDate(booking.check_out_date)

    // Booking occupies nights [checkIn, checkOut-1]
    const lastNight = new Date(checkOut)
    lastNight.setDate(lastNight.getDate() - 1)

    const visStart = checkIn > monthStartDate ? checkIn : monthStartDate
    const visEnd = lastNight < monthEndDate ? lastNight : monthEndDate

    if (visStart > visEnd) continue

    segments.push({
      booking,
      colStart: visStart.getDate(),
      colEnd: visEnd.getDate() + 1, // exclusive
      stackRow: 0,
    })
  }

  // Assign stack rows to prevent visual overlap
  for (let i = 0; i < segments.length; i++) {
    const usedRows = new Set<number>()
    for (let j = 0; j < i; j++) {
      const a = segments[i]
      const b = segments[j]
      if (a.colStart < b.colEnd && a.colEnd > b.colStart) {
        usedRows.add(b.stackRow)
      }
    }
    let row = 0
    while (usedRows.has(row)) row++
    segments[i].stackRow = row
  }

  return segments
}

// ---------------------------------------------------------------------------
// BookingBarCell
// ---------------------------------------------------------------------------

interface BookingBarCellProps {
  booking: Booking
  colStart: number
  colEnd: number
  stackRow: number
  numDays: number
}

/**
 * A single booking bar positioned as a grid item spanning the correct day columns.
 *
 * Grid column math (relative to the full grid including the 140px property label col):
 *   gridColStart = colStart + 1  (day 1 = column 2, accounting for label col)
 *   gridColEnd   = colEnd + 1    (exclusive upper bound)
 *
 * The element has height:0 and overflow:visible so it overlays the underlying
 * day cells without affecting the row height. The actual bar is absolute-positioned
 * using top offset to clear the row's top border/padding.
 */
function BookingBarCell({ booking, colStart, colEnd, stackRow }: BookingBarCellProps) {
  const colorEntry = getPlatformColorEntry(booking.platform)

  return (
    <div
      style={{
        gridColumn: `${colStart + 1} / ${colEnd + 1}`,
        position: 'relative',
        height: 0,
        overflow: 'visible',
        zIndex: 10 + stackRow,
      }}
    >
      <BookingPopover booking={booking}>
        <button
          type="button"
          className="absolute inset-x-0 cursor-pointer select-none overflow-hidden rounded text-xs font-medium leading-none transition-opacity hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          style={{
            top: `${4 + stackRow * 22}px`,
            height: '18px',
            backgroundColor: colorEntry.light,
            color: '#1f2937',
            paddingLeft: '4px',
            paddingRight: '4px',
            textAlign: 'left',
            whiteSpace: 'nowrap',
          }}
          title={`${booking.guest_name} (${booking.platform})`}
        >
          <span className="block truncate">{booking.guest_name}</span>
        </button>
      </BookingPopover>
    </div>
  )
}
