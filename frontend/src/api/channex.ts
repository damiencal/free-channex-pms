/**
 * Channex.io API client functions.
 *
 * All functions call the backend /api/channex/* endpoints which proxy
 * to the Channex.io API with authentication, rate limiting, and retry.
 */
import { apiFetch } from './client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChannexProperty {
  id: string
  title?: string
  name?: string
  currency?: string
  [key: string]: unknown
}

export interface ChannexMessage {
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

export interface ChannexReview {
  id: number
  channex_review_id: string
  channex_booking_id: string | null
  booking_id: number | null
  property_id: number | null
  guest_name: string
  rating: number | null
  review_text: string | null
  status: 'new' | 'responded'
  response_text: string | null
  reviewed_at: string | null
  responded_at: string | null
  created_at: string
}

export interface ChannexWebhookEvent {
  id: number
  channex_event_id: string | null
  event_type: string
  status: 'received' | 'processed' | 'failed'
  error_message: string | null
  received_at: string
  processed_at: string | null
}

export interface SyncResult {
  upserted: number
  skipped: number
  failed?: number
  linked?: number
  unlinked?: number
}

export interface CalendarData {
  channex_property_id: string
  date_from: string
  date_to: string
  availability: Record<string, unknown>
  rate_plans: unknown[]
  room_types: unknown[]
}

export interface AvailabilityUpdateItem {
  room_type_id: string
  date_from: string
  date_to: string
  availability?: number
  min_stay_arrival?: number
  max_stay?: number
  closed_to_arrival?: boolean
  closed_to_departure?: boolean
  stop_sell?: boolean
}

export interface RateUpdateItem {
  rate_plan_id: string
  date_from: string
  date_to: string
  rate?: number
}

export interface CalendarUpdateRequest {
  availability_updates?: AvailabilityUpdateItem[]
  rate_updates?: RateUpdateItem[]
}

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

export function fetchChannexProperties(): Promise<ChannexProperty[]> {
  return apiFetch<ChannexProperty[]>('/channex/properties')
}

export function syncChannexProperties(): Promise<SyncResult> {
  return apiFetch<SyncResult>('/channex/properties/sync', { method: 'POST' })
}

// ---------------------------------------------------------------------------
// Calendar
// ---------------------------------------------------------------------------

export function fetchChannexCalendar(
  channexPropertyId: string,
  dateFrom: string,
  dateTo: string,
): Promise<CalendarData> {
  const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo })
  return apiFetch<CalendarData>(`/channex/calendar/${channexPropertyId}?${params}`)
}

export function updateChannexCalendar(
  channexPropertyId: string,
  updates: CalendarUpdateRequest,
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/channex/calendar/${channexPropertyId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  })
}

// ---------------------------------------------------------------------------
// Reservations
// ---------------------------------------------------------------------------

export function fetchChannexReservations(params?: {
  channex_property_id?: string
  updated_since?: string
}): Promise<unknown[]> {
  const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : ''
  return apiFetch<unknown[]>(`/channex/reservations${qs}`)
}

export function syncChannexReservations(params?: {
  channex_property_id?: string
  since?: string
}): Promise<SyncResult> {
  const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : ''
  return apiFetch<SyncResult>(`/channex/reservations/sync${qs}`, { method: 'POST' })
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

export function fetchChannexMessages(params?: {
  channex_booking_id?: string
  direction?: 'inbound' | 'outbound'
  booking_id?: number
  limit?: number
}): Promise<ChannexMessage[]> {
  const qs = params
    ? '?' + new URLSearchParams(Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
      )).toString()
    : ''
  return apiFetch<ChannexMessage[]>(`/channex/messages${qs}`)
}

export function sendChannexMessage(
  channexBookingId: string,
  body: string,
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>('/channex/messages', {
    method: 'POST',
    body: JSON.stringify({ channex_booking_id: channexBookingId, body }),
  })
}

export function syncChannexMessages(since?: string): Promise<SyncResult> {
  const qs = since ? `?since=${encodeURIComponent(since)}` : ''
  return apiFetch<SyncResult>(`/channex/messages/sync${qs}`, { method: 'POST' })
}

// ---------------------------------------------------------------------------
// Reviews
// ---------------------------------------------------------------------------

export function fetchChannexReviews(params?: {
  status?: 'new' | 'responded'
  booking_id?: number
  limit?: number
}): Promise<ChannexReview[]> {
  const qs = params
    ? '?' + new URLSearchParams(Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
      )).toString()
    : ''
  return apiFetch<ChannexReview[]>(`/channex/reviews${qs}`)
}

export function respondToChannexReview(
  channexReviewId: string,
  responseText: string,
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/channex/reviews/${channexReviewId}/respond`,
    {
      method: 'POST',
      body: JSON.stringify({ response_text: responseText }),
    },
  )
}

export function syncChannexReviews(since?: string): Promise<SyncResult> {
  const qs = since ? `?since=${encodeURIComponent(since)}` : ''
  return apiFetch<SyncResult>(`/channex/reviews/sync${qs}`, { method: 'POST' })
}

// ---------------------------------------------------------------------------
// Webhooks
// ---------------------------------------------------------------------------

export function fetchChannexWebhookEvents(params?: {
  status?: string
  event_type?: string
  limit?: number
}): Promise<ChannexWebhookEvent[]> {
  const qs = params
    ? '?' + new URLSearchParams(Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
      )).toString()
    : ''
  return apiFetch<ChannexWebhookEvent[]>(`/channex/webhook-events${qs}`)
}

export function registerChannexWebhook(callbackUrl: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>('/channex/webhooks/register', {
    method: 'POST',
    body: JSON.stringify({ callback_url: callbackUrl }),
  })
}
