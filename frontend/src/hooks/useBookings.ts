import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/api/client'
import { usePropertyStore } from '@/store/usePropertyStore'

export interface Booking {
  id: number
  platform: string
  platform_booking_id: string
  guest_name: string
  check_in_date: string
  check_out_date: string
  net_amount: string
  property_slug: string
  property_display_name: string
}

/**
 * TanStack Query hook for fetching bookings within a date range.
 * Automatically refetches when selectedPropertyId changes.
 *
 * @param startDate - ISO date string (YYYY-MM-DD) for range start
 * @param endDate   - ISO date string (YYYY-MM-DD) for range end
 */
export function useBookings(startDate: string, endDate: string) {
  const selectedPropertyId = usePropertyStore((s) => s.selectedPropertyId)

  return useQuery<Booking[]>({
    queryKey: ['dashboard', 'bookings', selectedPropertyId, startDate, endDate],
    queryFn: () => {
      const params = new URLSearchParams({ start_date: startDate, end_date: endDate })
      if (selectedPropertyId !== null) params.set('property_id', String(selectedPropertyId))
      return apiFetch<Booking[]>(`/dashboard/bookings?${params.toString()}`)
    },
    staleTime: 5 * 60 * 1000,
  })
}
