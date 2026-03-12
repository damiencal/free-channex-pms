import { apiFetch } from './client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PriceRecommendation {
  id: number
  property_id: number
  date: string
  recommended_price: string
  base_price: string
  min_stay: number
  status: 'pending' | 'accepted' | 'rejected' | 'expired'
  accepted_price: string | null
  rejection_reason: string | null
  demand_score: string | null
  seasonal_factor: string | null
  event_factor: string | null
  weekend_factor: string | null
  last_minute_factor: string | null
  early_bird_factor: string | null
  confidence: string | null
  generated_at: string
}

export interface PricingRule {
  id?: number
  property_id: number
  strategy: 'manual' | 'dynamic' | 'hybrid'
  min_price: string | null
  max_price: string | null
  weekend_markup_pct: string
  orphan_day_discount_pct: string
  last_minute_window_days: number
  last_minute_discount_pct: string
  early_bird_window_days: number
  early_bird_discount_pct: string
  demand_sensitivity: string
  min_stay: number
  weekend_min_stay: number
  updated_at: string | null
}

export interface PricingRulePayload {
  strategy?: 'manual' | 'dynamic' | 'hybrid'
  min_price?: number | null
  max_price?: number | null
  weekend_markup_pct?: number
  orphan_day_discount_pct?: number
  last_minute_window_days?: number
  last_minute_discount_pct?: number
  early_bird_window_days?: number
  early_bird_discount_pct?: number
  demand_sensitivity?: number
  min_stay?: number
  weekend_min_stay?: number
}

export interface MarketEvent {
  id: number
  property_id: number | null
  name: string
  event_type: 'holiday' | 'local_event' | 'season' | 'conference' | 'custom'
  start_date: string
  end_date: string
  demand_modifier: string
  recurrence: 'none' | 'yearly'
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface MarketEventPayload {
  name: string
  event_type?: string
  start_date: string
  end_date: string
  demand_modifier?: number
  recurrence?: string
  description?: string
  property_id?: number | null
  is_active?: boolean
}

export interface GeneratePayload {
  property_id: number
  date_from: string
  date_to: string
}

export interface BulkAcceptPayload {
  ids: number[]
  price?: number
}

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

export const fetchRecommendations = (params: {
  property_id?: number
  date_from?: string
  date_to?: string
  status?: string
}): Promise<PriceRecommendation[]> => {
  const qs = new URLSearchParams()
  if (params.property_id != null) qs.set('property_id', String(params.property_id))
  if (params.date_from) qs.set('date_from', params.date_from)
  if (params.date_to) qs.set('date_to', params.date_to)
  if (params.status) qs.set('status', params.status)
  return apiFetch<PriceRecommendation[]>(`/pricing/recommendations?${qs}`)
}

export const acceptRecommendation = (id: number, price?: number): Promise<PriceRecommendation> =>
  apiFetch<PriceRecommendation>(`/pricing/recommendations/${id}/accept`, {
    method: 'POST',
    body: JSON.stringify({ price: price ?? null }),
  })

export const rejectRecommendation = (id: number, reason?: string): Promise<PriceRecommendation> =>
  apiFetch<PriceRecommendation>(`/pricing/recommendations/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason: reason ?? null }),
  })

export const bulkAcceptRecommendations = (payload: BulkAcceptPayload): Promise<{ accepted: number; requested: number }> =>
  apiFetch(`/pricing/recommendations/bulk-accept`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const generateRecommendations = (payload: GeneratePayload): Promise<{ status: string; message: string }> =>
  apiFetch(`/pricing/generate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

// ---------------------------------------------------------------------------
// Pricing Rules
// ---------------------------------------------------------------------------

export const fetchPricingRule = (propertyId: number): Promise<PricingRule> =>
  apiFetch<PricingRule>(`/pricing/rules/${propertyId}`)

export const upsertPricingRule = (propertyId: number, payload: PricingRulePayload): Promise<PricingRule> =>
  apiFetch<PricingRule>(`/pricing/rules/${propertyId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })

// ---------------------------------------------------------------------------
// Market Events
// ---------------------------------------------------------------------------

export const fetchEvents = (params: {
  property_id?: number
  include_global?: boolean
  start_date?: string
  end_date?: string
  event_type?: string
  is_active?: boolean
} = {}): Promise<MarketEvent[]> => {
  const qs = new URLSearchParams()
  if (params.property_id != null) qs.set('property_id', String(params.property_id))
  if (params.include_global != null) qs.set('include_global', String(params.include_global))
  if (params.start_date) qs.set('start_date', params.start_date)
  if (params.end_date) qs.set('end_date', params.end_date)
  if (params.event_type) qs.set('event_type', params.event_type)
  if (params.is_active != null) qs.set('is_active', String(params.is_active))
  return apiFetch<MarketEvent[]>(`/events?${qs}`)
}

export const createEvent = (payload: MarketEventPayload): Promise<MarketEvent> =>
  apiFetch<MarketEvent>('/events', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const updateEvent = (id: number, payload: Partial<MarketEventPayload>): Promise<MarketEvent> =>
  apiFetch<MarketEvent>(`/events/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })

export const deleteEvent = (id: number): Promise<void> =>
  apiFetch<void>(`/events/${id}`, { method: 'DELETE' })

export const seedHolidays = (): Promise<{ created: number; skipped: number }> =>
  apiFetch(`/events/seed-holidays`, { method: 'POST' })
