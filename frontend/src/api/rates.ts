import { apiFetch } from './client'

export interface RatePlan {
  id: number
  property_id: number
  room_type_id: number | null
  name: string
  code: string | null
  description: string | null
  base_rate: string
  currency: string
  min_stay: number | null
  max_stay: number | null
  parent_rate_plan_id: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RateDate {
  id: number
  rate_plan_id: number
  date: string
  rate: string
  min_stay: number | null
}

export interface RatePlanPayload {
  property_id: number
  room_type_id?: number | null
  name: string
  code?: string | null
  description?: string | null
  base_rate?: number
  currency?: string
  min_stay?: number | null
  max_stay?: number | null
  parent_rate_plan_id?: number | null
  is_active?: boolean
}

export interface RateDateEntry {
  date: string
  rate: number
  min_stay?: number | null
}

export const fetchRatePlans = (property_id?: number | null): Promise<RatePlan[]> => {
  const qs = property_id != null ? `?property_id=${property_id}` : ''
  return apiFetch<RatePlan[]>(`/rate-plans${qs}`)
}
export const createRatePlan = (payload: RatePlanPayload): Promise<RatePlan> =>
  apiFetch<RatePlan>('/rate-plans', { method: 'POST', body: JSON.stringify(payload) })
export const updateRatePlan = (id: number, payload: Partial<RatePlanPayload>): Promise<RatePlan> =>
  apiFetch<RatePlan>(`/rate-plans/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteRatePlan = (id: number): Promise<void> =>
  apiFetch<void>(`/rate-plans/${id}`, { method: 'DELETE' })

export const fetchRateDates = (planId: number, date_from?: string, date_to?: string): Promise<RateDate[]> => {
  const qs = new URLSearchParams()
  if (date_from) qs.set('date_from', date_from)
  if (date_to) qs.set('date_to', date_to)
  return apiFetch<RateDate[]>(`/rate-plans/${planId}/rates${qs.toString() ? `?${qs}` : ''}`)
}
export const setRateDates = (planId: number, rates: RateDateEntry[]): Promise<RateDate[]> =>
  apiFetch<RateDate[]>(`/rate-plans/${planId}/rates`, {
    method: 'POST',
    body: JSON.stringify({ rates }),
  })
export const clearRateDates = (planId: number, date_from: string, date_to: string): Promise<void> =>
  apiFetch<void>(`/rate-plans/${planId}/rates?date_from=${date_from}&date_to=${date_to}`, {
    method: 'DELETE',
  })
