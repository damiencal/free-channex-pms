import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { BookingBar } from './BookingBar'
import { BookingPopover } from './BookingPopover'
import type { Booking } from '@/hooks/useBookings'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BookingSegment {
  booking: Booking
  /** Week row index (0-based) */
  weekRow: number
  /** 1-based CSS grid column start (1=Sun, 7=Sat) */
  startCol: number
  /** Number of columns spanned in this week row */
  span: number
  /** Whether this segment starts at the booking's check-in date */
  isStart: boolean
  /** Whether this segment ends at the booking's check-out date */
  isEnd: boolean
  /** Vertical row offset for stacking overlapping bookings */
  rowOffset: number
}

interface MonthCalendarProps {
  currentMonth: Date
  onMonthChange: (direction: 'prev' | 'next') => void
  bookings: Booking[]
}

// ---------------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------------

const DAY_HEADERS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

/** Return local calendar date as YYYY-MM-DD string (no timezone shift). */
function toISOLocal(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** Parse YYYY-MM-DD safely (midnight local, no UTC shift). */
function parseDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

// ---------------------------------------------------------------------------
// Segment calculation
// ---------------------------------------------------------------------------

/**
 * Determine which day-cells within the visible month a booking occupies.
 * A booking occupies days [check_in, check_out). The last night is check_out - 1.
 *
 * Returns an array of {dayIndex} where dayIndex is 0-based from monthStart.
 */
function bookingOccupiedDays(
  booking: Booking,
  monthStart: Date,
  monthEnd: Date,
): { start: Date; end: Date } | null {
  const checkIn = parseDate(booking.check_in_date)
  const checkOut = parseDate(booking.check_out_date)

  // Booking occupies [checkIn, checkOut-1] (last night before checkout day)
  const lastNight = new Date(checkOut)
  lastNight.setDate(lastNight.getDate() - 1)

  const visStart = checkIn > monthStart ? checkIn : monthStart
  const visEnd = lastNight < monthEnd ? lastNight : monthEnd

  if (visStart > visEnd) return null

  return { start: visStart, end: visEnd }
}

/**
 * Split a booking into per-week-row segments.
 * Splits happen at Saturday→Sunday boundaries.
 *
 * @param booking       - The booking to split
 * @param monthStart    - First day of the displayed month
 * @param monthEnd      - Last day of the displayed month
 * @param firstDayCol   - Day-of-week (0=Sun) of the 1st of the month
 * @returns Array of BookingSegment (without rowOffset set yet)
 */
function splitIntoWeekSegments(
  booking: Booking,
  monthStart: Date,
  monthEnd: Date,
  firstDayCol: number,
): Omit<BookingSegment, 'rowOffset'>[] {
  const range = bookingOccupiedDays(booking, monthStart, monthEnd)
  if (!range) return []

  const segments: Omit<BookingSegment, 'rowOffset'>[] = []

  const checkIn = parseDate(booking.check_in_date)
  const checkOut = parseDate(booking.check_out_date)
  const lastNight = new Date(checkOut)
  lastNight.setDate(lastNight.getDate() - 1)

  let cursor = new Date(range.start)

  while (cursor <= range.end) {
    // Determine how many days until end-of-week (Saturday) or end of range
    const dayOfWeek = cursor.getDay() // 0=Sun
    const daysToEndOfWeek = 6 - dayOfWeek // days until Saturday inclusive

    const weekEnd = new Date(cursor)
    weekEnd.setDate(weekEnd.getDate() + daysToEndOfWeek)

    const segEnd = weekEnd < range.end ? weekEnd : range.end

    // Grid column (1-based): cursor's day offset from month start + firstDayCol offset + 1
    const dayIndex = Math.round((cursor.getTime() - monthStart.getTime()) / 86400000)
    const gridCol = (firstDayCol + dayIndex) % 7 + 1

    const span = Math.round((segEnd.getTime() - cursor.getTime()) / 86400000) + 1

    // Week row = which row of the 7-column grid
    const weekRow = Math.floor((firstDayCol + dayIndex) / 7)

    const isStart = cursor.getTime() === range.start.getTime() && checkIn >= monthStart
    const isEnd = segEnd.getTime() === range.end.getTime() && lastNight <= monthEnd

    segments.push({
      booking,
      weekRow,
      startCol: gridCol,
      span,
      isStart,
      isEnd,
    })

    // Advance cursor to next Sunday
    cursor = new Date(segEnd)
    cursor.setDate(cursor.getDate() + 1)
  }

  return segments
}

/**
 * Assign rowOffset to segments so overlapping bars stack vertically.
 * Two segments overlap if they share a week row and any column.
 */
function assignRowOffsets(segments: Omit<BookingSegment, 'rowOffset'>[]): BookingSegment[] {
  // Group by weekRow
  const byWeekRow = new Map<number, Omit<BookingSegment, 'rowOffset'>[]>()
  for (const seg of segments) {
    if (!byWeekRow.has(seg.weekRow)) byWeekRow.set(seg.weekRow, [])
    byWeekRow.get(seg.weekRow)!.push(seg)
  }

  const result: BookingSegment[] = []

  for (const [, weekSegs] of byWeekRow) {
    // For each segment, find the lowest rowOffset not occupied by an overlapping prior segment
    const rowAssignments: Map<string, number> = new Map() // key = segId

    for (let i = 0; i < weekSegs.length; i++) {
      const seg = weekSegs[i]
      const segKey = `${seg.booking.id}-${seg.startCol}`
      const usedRows: Set<number> = new Set()

      // Check all earlier segments in the same week row for column overlap
      for (let j = 0; j < i; j++) {
        const other = weekSegs[j]
        const segStart = seg.startCol
        const segEndCol = seg.startCol + seg.span - 1
        const otherStart = other.startCol
        const otherEndCol = other.startCol + other.span - 1

        // Overlap if ranges intersect
        if (segStart <= otherEndCol && segEndCol >= otherStart) {
          const otherKey = `${other.booking.id}-${other.startCol}`
          const otherRow = rowAssignments.get(otherKey)
          if (otherRow !== undefined) usedRows.add(otherRow)
        }
      }

      // Assign lowest available row
      let row = 0
      while (usedRows.has(row)) row++
      rowAssignments.set(segKey, row)
      result.push({ ...seg, rowOffset: row })
    }
  }

  return result
}

// ---------------------------------------------------------------------------
// MonthCalendar component
// ---------------------------------------------------------------------------

/**
 * 7-column CSS Grid monthly calendar with booking bars.
 *
 * - Header row: Sun – Sat
 * - Day cells numbered 1–N with leading/trailing empty cells
 * - Booking bars positioned via absolute positioning within week rows
 * - Bars split at week boundaries (Sat→Sun)
 * - Overlapping bookings stacked vertically within a row
 * - Current day highlighted
 * - Prev/next month navigation arrows
 */
export function MonthCalendar({ currentMonth, onMonthChange, bookings }: MonthCalendarProps) {
  const year = currentMonth.getFullYear()
  const month = currentMonth.getMonth() // 0-based

  const firstDayOfMonth = new Date(year, month, 1)
  const firstDayCol = firstDayOfMonth.getDay() // 0=Sun
  const totalDays = daysInMonth(year, month)

  const monthStart = new Date(year, month, 1)
  const monthEnd = new Date(year, month, totalDays)

  const todayStr = toISOLocal(new Date())

  // Total grid cells including leading/trailing empty cells
  const totalCells = firstDayCol + totalDays
  const totalWeekRows = Math.ceil(totalCells / 7)

  // Build all booking segments
  const allSegmentsRaw: Omit<BookingSegment, 'rowOffset'>[] = []
  for (const booking of bookings) {
    allSegmentsRaw.push(...splitIntoWeekSegments(booking, monthStart, monthEnd, firstDayCol))
  }
  const allSegments = assignRowOffsets(allSegmentsRaw)

  // Max stacking rows per week row (for min-height calculation)
  const maxOffsetByWeekRow: number[] = Array(totalWeekRows).fill(0)
  for (const seg of allSegments) {
    if (seg.rowOffset > maxOffsetByWeekRow[seg.weekRow]) {
      maxOffsetByWeekRow[seg.weekRow] = seg.rowOffset
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Month navigation header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onMonthChange('prev')}
          aria-label="Previous month"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        <h2 className="text-sm font-semibold">
          {MONTH_NAMES[month]} {year}
        </h2>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => onMonthChange('next')}
          aria-label="Next month"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Calendar grid */}
      <div
        className="grid"
        style={{ gridTemplateColumns: 'repeat(7, 1fr)' }}
      >
        {/* Day-of-week headers */}
        {DAY_HEADERS.map((label) => (
          <div
            key={label}
            className="py-2 text-center text-xs font-medium text-muted-foreground border-b"
          >
            {label}
          </div>
        ))}

        {/* Week rows — each row contains day cells and booking bars */}
        {Array.from({ length: totalWeekRows }, (_, weekIdx) => {
          const weekSegments = allSegments.filter((s) => s.weekRow === weekIdx)
          const maxOffset = maxOffsetByWeekRow[weekIdx]
          // Min row height: 24px day-number area + bookings (22px each) + 8px bottom pad
          const rowMinHeight = 24 + (maxOffset + 1) * 22 + 8

          return (
            // Week row: a full-width relative container spanning all 7 columns
            <div
              key={weekIdx}
              className="relative col-span-7"
              style={{ minHeight: `${rowMinHeight}px` }}
            >
              {/* Day number cells */}
              <div
                className="grid absolute inset-0"
                style={{ gridTemplateColumns: 'repeat(7, 1fr)' }}
              >
                {Array.from({ length: 7 }, (_, colIdx) => {
                  const dayIndex = weekIdx * 7 + colIdx - firstDayCol
                  const dayNum = dayIndex + 1
                  const isValid = dayNum >= 1 && dayNum <= totalDays
                  const dayStr = isValid
                    ? `${year}-${String(month + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`
                    : ''
                  const isToday = dayStr === todayStr
                  const isWeekend = colIdx === 0 || colIdx === 6

                  return (
                    <div
                      key={colIdx}
                      className={[
                        'border-r border-b last:border-r-0 p-1',
                        isWeekend && isValid ? 'bg-muted/30' : '',
                        !isValid ? 'bg-muted/10' : '',
                      ].join(' ')}
                    >
                      {isValid && (
                        <span
                          className={[
                            'flex h-6 w-6 items-center justify-center rounded-full text-xs',
                            isToday
                              ? 'bg-primary text-primary-foreground font-bold'
                              : 'text-foreground',
                          ].join(' ')}
                        >
                          {dayNum}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>

              {/* Booking bars overlaid on the week row */}
              {weekSegments.map((seg) => (
                <BookingPopover key={`${seg.booking.id}-${seg.startCol}`} booking={seg.booking}>
                  <BookingBar
                    booking={seg.booking}
                    onClick={() => {/* popover handles open/close */}}
                    startCol={seg.startCol}
                    span={seg.span}
                    isStart={seg.isStart}
                    isEnd={seg.isEnd}
                    rowOffset={seg.rowOffset}
                  />
                </BookingPopover>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
