import { useState } from 'react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { getPlatformColorEntry } from '@/lib/platformColors'
import type { Booking } from '@/hooks/useBookings'

interface BookingPopoverProps {
  booking: Booking
  children: React.ReactNode
}

const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function formatDate(iso: string): string {
  const [, month, day] = iso.split('-').map(Number)
  return `${MONTH_ABBR[month - 1]} ${day}`
}

function nightCount(checkIn: string, checkOut: string): number {
  return Math.round(
    (new Date(checkOut).getTime() - new Date(checkIn).getTime()) / (1000 * 60 * 60 * 24)
  )
}

function formatCurrency(value: string): string {
  const num = parseFloat(value)
  if (isNaN(num)) return '$0'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(num)
}

/**
 * Popover showing booking detail on click.
 * Uses shadcn Popover (not Tooltip) — per RESEARCH.md avoid nesting Tooltip+Popover.
 *
 * Content:
 *  - Guest name (bold)
 *  - Dates with night count
 *  - Platform with color dot
 *  - Currency amount
 *  - Property display name
 */
export function BookingPopover({ booking, children }: BookingPopoverProps) {
  const [open, setOpen] = useState(false)
  const colorEntry = getPlatformColorEntry(booking.platform)
  const nights = nightCount(booking.check_in_date, booking.check_out_date)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild onClick={(e) => { e.stopPropagation(); setOpen(!open) }}>
        {children}
      </PopoverTrigger>

      <PopoverContent className="w-64 p-3" side="top" align="start" onClick={(e) => e.stopPropagation()}>
        <div className="space-y-2">
          {/* Guest name */}
          <p className="text-sm font-semibold leading-tight">{booking.guest_name}</p>

          {/* Dates + nights */}
          <p className="text-xs text-muted-foreground">
            {formatDate(booking.check_in_date)} &ndash; {formatDate(booking.check_out_date)}
            <span className="ml-1 font-medium text-foreground">({nights} night{nights !== 1 ? 's' : ''})</span>
          </p>

          {/* Platform */}
          <div className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
              style={{ backgroundColor: colorEntry.chart }}
            />
            <span className="text-xs capitalize">{booking.platform}</span>
          </div>

          {/* Amount */}
          <p className="text-xs">
            <span className="text-muted-foreground">Payout: </span>
            <span className="font-medium">{formatCurrency(booking.net_amount)}</span>
          </p>

          {/* Property */}
          <p className="text-xs text-muted-foreground">{booking.property_display_name}</p>
        </div>
      </PopoverContent>
    </Popover>
  )
}
