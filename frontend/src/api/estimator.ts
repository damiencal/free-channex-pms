import { apiFetch } from './client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MonthlyEstimate {
  month: string
  estimated_revenue: number
  estimated_adr: number
  estimated_occupancy: number
}

export interface RevenueEstimate {
  annual_estimate: number
  monthly_estimates: MonthlyEstimate[]
  adr_estimate: number
  occupancy_estimate: number
  confidence: 'very_low' | 'low' | 'medium' | 'high' | 'very_high'
  comparable_property_ids: number[]
  data_points: number
  note?: string
}

export interface EstimatorRequest {
  bedrooms: number
  property_type?: string
  latitude?: number | null
  longitude?: number | null
  amenities?: string[]
  months_ahead?: number
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export const estimateRevenue = (payload: EstimatorRequest): Promise<RevenueEstimate> =>
  apiFetch<RevenueEstimate>('/estimator/analyze', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
