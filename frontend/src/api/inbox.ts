import { apiFetch } from './client'

export interface InboxThread {
  channex_booking_id: string
  booking_id: number | null
  property_id: number | null
  guest_name: string
  last_message_body: string
  last_message_at: string | null
  unread_count: number
  message_count: number
}

export interface InboxMessage {
  id: number
  channex_message_id: string
  channex_booking_id: string
  booking_id: number | null
  property_id: number | null
  guest_name: string
  direction: 'inbound' | 'outbound'
  body: string
  sent_at: string | null
  created_at: string
}

export function fetchInboxThreads(propertyId?: number | null): Promise<InboxThread[]> {
  const qs = propertyId != null ? `?property_id=${propertyId}` : ''
  return apiFetch<InboxThread[]>(`/inbox/threads${qs}`)
}

export function fetchThreadMessages(channexBookingId: string): Promise<InboxMessage[]> {
  return apiFetch<InboxMessage[]>(`/inbox/threads/${channexBookingId}/messages`)
}

export function fetchAiSuggestion(channexBookingId: string): Promise<{ suggestion: string }> {
  return apiFetch<{ suggestion: string }>(
    `/inbox/threads/${channexBookingId}/ai-suggest`,
    { method: 'POST' },
  )
}

export function sendInboxMessage(
  channexBookingId: string,
  body: string,
): Promise<{ sent: boolean }> {
  return apiFetch<{ sent: boolean }>(
    `/inbox/threads/${channexBookingId}/send`,
    { method: 'POST', body: JSON.stringify({ body }) },
  )
}
