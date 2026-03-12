import { apiFetch } from './client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PortfolioMetric {
  id: number
  property_id: number | null
  metric_date: string
  occupancy_rate: string | null
  adr: string | null
  revpar: string | null
  trevpar: string | null
  revenue: string | null
  available_nights: number | null
  booked_nights: number | null
  booking_count: number | null
  booking_pace: string | null
  booking_pace_ly: string | null
}

export interface PacingData {
  property_id: number
  target_month: string
  this_year_bookings: number
  last_year_bookings: number
  pace_index: number
  market_avg_occupancy: number | null
  weekly_pickup: Array<{
    week_start: string
    this_year: number
    last_year: number
  }>
}

export interface MarketSnapshot {
  id: number
  property_id: number | null
  snapshot_date: string
  avg_daily_rate: string | null
  occupancy_rate: string | null
  demand_index: string | null
  supply_count: number | null
  source: string
}

export interface CompSet {
  id: number
  property_id: number
  name: string
  filters_json: Record<string, unknown>
  created_at: string
  updated_at: string
  members?: CompSetMember[]
}

export interface CompSetMember {
  id: number
  comp_set_id: number
  name: string
  external_listing_id: string | null
  source: string
  ref_property_id: number | null
  avg_rate: string | null
  avg_occupancy: string | null
  last_updated: string | null
}

export interface CompSetPayload {
  property_id: number
  name: string
  filters_json?: Record<string, unknown>
}

export interface CompSetMemberPayload {
  name: string
  external_listing_id?: string
  source?: string
  ref_property_id?: number
}

// ---------------------------------------------------------------------------
// Portfolio KPIs
// ---------------------------------------------------------------------------

export const fetchPortfolioKPIs = (params: {
  property_id?: number
  months?: number
} = {}): Promise<PortfolioMetric[]> => {
  const qs = new URLSearchParams()
  if (params.property_id != null) qs.set('property_id', String(params.property_id))
  if (params.months != null) qs.set('months', String(params.months))
  return apiFetch<PortfolioMetric[]>(`/analytics/portfolio?${qs}`)
}

export const triggerMetricsCompute = (propertyId?: number): Promise<{ status: string }> => {
  const qs = propertyId != null ? `?property_id=${propertyId}` : ''
  return apiFetch(`/analytics/compute${qs}`, { method: 'POST' })
}

// ---------------------------------------------------------------------------
// Pacing
// ---------------------------------------------------------------------------

export const fetchPacingData = (propertyId: number, targetMonth?: string): Promise<PacingData> => {
  const qs = new URLSearchParams({ property_id: String(propertyId) })
  if (targetMonth) qs.set('target_month', targetMonth)
  return apiFetch<PacingData>(`/analytics/pacing?${qs}`)
}

// ---------------------------------------------------------------------------
// Market Snapshots
// ---------------------------------------------------------------------------

export const fetchMarketSnapshots = (params: {
  property_id?: number
  days?: number
} = {}): Promise<MarketSnapshot[]> => {
  const qs = new URLSearchParams()
  if (params.property_id != null) qs.set('property_id', String(params.property_id))
  if (params.days != null) qs.set('days', String(params.days))
  return apiFetch<MarketSnapshot[]>(`/analytics/market?${qs}`)
}

// ---------------------------------------------------------------------------
// Trends
// ---------------------------------------------------------------------------

export const fetchTrends = (params: {
  property_id?: number
  months?: number
} = {}): Promise<PortfolioMetric[]> => {
  const qs = new URLSearchParams()
  if (params.property_id != null) qs.set('property_id', String(params.property_id))
  if (params.months != null) qs.set('months', String(params.months))
  return apiFetch<PortfolioMetric[]>(`/analytics/trends?${qs}`)
}

// ---------------------------------------------------------------------------
// Comp Sets
// ---------------------------------------------------------------------------

export const fetchCompSets = (propertyId?: number): Promise<CompSet[]> => {
  const qs = propertyId != null ? `?property_id=${propertyId}` : ''
  return apiFetch<CompSet[]>(`/comp-sets${qs}`)
}

export const createCompSet = (payload: CompSetPayload): Promise<CompSet> =>
  apiFetch<CompSet>('/comp-sets', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const fetchCompSet = (id: number): Promise<CompSet> =>
  apiFetch<CompSet>(`/comp-sets/${id}`)

export const updateCompSet = (id: number, payload: Partial<CompSetPayload>): Promise<CompSet> =>
  apiFetch<CompSet>(`/comp-sets/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })

export const deleteCompSet = (id: number): Promise<void> =>
  apiFetch<void>(`/comp-sets/${id}`, { method: 'DELETE' })

export const addCompSetMember = (compSetId: number, payload: CompSetMemberPayload): Promise<CompSetMember> =>
  apiFetch<CompSetMember>(`/comp-sets/${compSetId}/members`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const removeCompSetMember = (compSetId: number, memberId: number): Promise<void> =>
  apiFetch<void>(`/comp-sets/${compSetId}/members/${memberId}`, { method: 'DELETE' })

export const refreshCompSet = (id: number): Promise<{ updated: number; total: number }> =>
  apiFetch(`/comp-sets/${id}/refresh`, { method: 'POST' })
