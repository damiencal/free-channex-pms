import { getPlatformColorEntry } from '@/lib/platformColors'
import type { Booking } from '@/hooks/useBookings'

interface BookingBarProps {
  booking: Booking
  /** onClick triggers BookingPopover — handler provided by parent */
  onClick: () => void
  /** 1-based CSS grid column start (1 = Sunday, 7 = Saturday) */
  startCol: number
  /** Number of day-cells this segment spans */
  span: number
  /** True if this is the first segment of the booking (rounded left corners) */
  isStart: boolean
  /** True if this is the last segment of the booking (rounded right corners) */
  isEnd: boolean
  /** Visual row offset for stacking multiple bookings on overlapping days */
  rowOffset: number
}

/**
 * Horizontal bar representing a booking segment within a calendar week row.
 *
 * Rounded corners: only on the chronological start (left) and end (right) of
 * the full booking. Week-boundary splits are flat on the split side.
 *
 * Positioned via CSS grid-column for precise day alignment. rowOffset stacks
 * multiple bookings that overlap within the same week row.
 */
export function BookingBar({
  booking,
  onClick,
  startCol,
  span,
  isStart,
  isEnd,
  rowOffset,
}: BookingBarProps) {
  const colorEntry = getPlatformColorEntry(booking.platform)

  // Build border-radius from individual corner tokens so we can selectively
  // round only the booking's start/end — not the week-split sides.
  const radiusLeft = isStart ? '4px' : '0'
  const radiusRight = isEnd ? '4px' : '0'

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick() }}
      title={`${booking.guest_name} (${booking.platform})`}
      className="absolute flex items-center overflow-hidden cursor-pointer select-none text-xs font-medium leading-none transition-opacity hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      style={{
        // Grid-based horizontal position (CSS custom properties for column math)
        left: `calc((${startCol - 1} / 7) * 100%)`,
        width: `calc((${span} / 7) * 100%)`,
        // Vertical stacking: each bar is 20px tall with 2px gap
        top: `${24 + rowOffset * 22}px`,
        height: '18px',
        backgroundColor: colorEntry.light,
        // Dark mode: switch to dark variant via a CSS data attribute on documentElement
        borderRadius: `${radiusLeft} ${radiusRight} ${radiusRight} ${radiusLeft}`,
        paddingLeft: isStart ? '6px' : '2px',
        paddingRight: isEnd ? '6px' : '2px',
        zIndex: 10 + rowOffset,
      }}
    >
      <span className="truncate" style={{ color: '#1f2937' }}>
        {booking.guest_name}
      </span>
    </div>
  )
}
