import { apiFetch } from './client'

export interface Guest {
  id: number
  first_name: string
  last_name: string
  email: string | null
  phone: string | null
  address: string | null
  city: string | null
  state: string | null
  country: string | null
  postal_code: string | null
  guest_type: 'individual' | 'corporate' | 'vip' | 'group'
  notes: string | null
  balance: string
  is_active: boolean
  full_name: string
  created_at: string
  updated_at: string
}

export interface GuestPayload {
  first_name: string
  last_name: string
  email?: string | null
  phone?: string | null
  address?: string | null
  city?: string | null
  state?: string | null
  country?: string | null
  postal_code?: string | null
  guest_type?: Guest['guest_type']
  notes?: string | null
}

export const fetchGuests = (search?: string): Promise<Guest[]> => {
  const qs = search ? `?search=${encodeURIComponent(search)}` : ''
  return apiFetch<{ items: Guest[] }>(`/guests${qs}`).then(r => r.items)
}
export const getGuest = (id: number): Promise<Guest & { booking_count: number }> =>
  apiFetch<Guest & { booking_count: number }>(`/guests/${id}`)
export const createGuest = (payload: GuestPayload): Promise<Guest> =>
  apiFetch<Guest>('/guests', { method: 'POST', body: JSON.stringify(payload) })
export const updateGuest = (id: number, payload: Partial<GuestPayload>): Promise<Guest> =>
  apiFetch<Guest>(`/guests/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deactivateGuest = (id: number): Promise<void> =>
  apiFetch<void>(`/guests/${id}`, { method: 'DELETE' })
export const fetchGuestBookings = (id: number): Promise<unknown[]> =>
  apiFetch<unknown[]>(`/guests/${id}/bookings`)
