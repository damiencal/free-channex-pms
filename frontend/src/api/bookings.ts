import { apiFetch } from './client'

export interface Booking {
  id: number
  platform: string
  platform_booking_id: string
  property_id: number
  guest_name: string
  guest_email: string | null
  guest_phone: string | null
  check_in_date: string
  check_out_date: string
  net_amount: string
  reconciliation_status: string
  // PMS fields
  booking_state: 'reservation' | 'checked_in' | 'checked_out' | 'no_show' | 'cancelled'
  adults: number
  children: number
  notes: string | null
  guest_id: number | null
  room_id: number | null
  group_id: number | null
  created_at: string
  updated_at: string
}

export interface ManualBookingPayload {
  property_id: number
  guest_name: string
  guest_email?: string | null
  check_in_date: string
  check_out_date: string
  net_amount: number
  notes?: string | null
}

export function fetchBookings(params?: {
  property_id?: number | null
  platform?: string
}): Promise<Booking[]> {
  const qs = new URLSearchParams()
  if (params?.property_id != null) qs.set('property_id', String(params.property_id))
  if (params?.platform) qs.set('platform', params.platform)
  const q = qs.toString()
  return apiFetch<Booking[]>(`/bookings${q ? `?${q}` : ''}`)
}

export function createManualBooking(payload: ManualBookingPayload): Promise<Booking> {
  return apiFetch<Booking>('/bookings/manual', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateBooking(id: number, payload: Partial<ManualBookingPayload>): Promise<Booking> {
  return apiFetch<Booking>(`/bookings/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function deleteBooking(id: number): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(`/bookings/${id}`, { method: 'DELETE' })
}

// State transitions
export const checkInBooking = (id: number) =>
  apiFetch<Booking>(`/bookings/${id}/check-in`, { method: 'POST' })

export const checkOutBooking = (id: number) =>
  apiFetch<Booking>(`/bookings/${id}/check-out`, { method: 'POST' })

export const noShowBooking = (id: number) =>
  apiFetch<Booking>(`/bookings/${id}/no-show`, { method: 'POST' })

export const cancelBooking = (id: number) =>
  apiFetch<Booking>(`/bookings/${id}/cancel`, { method: 'POST' })

export const fetchBookingAuditLog = (id: number) =>
  apiFetch<Array<{ id: number; action: string; performed_by: string | null; notes: string | null; created_at: string }>>(`/bookings/${id}/audit-log`)
