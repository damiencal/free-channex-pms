import { apiFetch } from './client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ListingRecommendation {
  priority: 'high' | 'medium' | 'low'
  category: 'title' | 'description' | 'photos' | 'amenities' | 'pricing'
  finding: string
  action: string
  impact: string
}

export interface ListingAnalysis {
  id: number
  property_id: number
  overall_score: number | null
  title_score: number | null
  description_score: number | null
  photos_score: number | null
  amenities_score: number | null
  pricing_score: number | null
  recommendations: ListingRecommendation[]
  model_used: string | null
  analyzed_at: string
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export const triggerListingAnalysis = (propertyId: number): Promise<ListingAnalysis> =>
  apiFetch<ListingAnalysis>(`/listing-optimizer/${propertyId}/analyze`, { method: 'POST' })

export const fetchLatestAnalysis = (propertyId: number): Promise<ListingAnalysis> =>
  apiFetch<ListingAnalysis>(`/listing-optimizer/${propertyId}/results`)

export const fetchAnalysisHistory = (propertyId: number, limit = 10): Promise<ListingAnalysis[]> =>
  apiFetch<ListingAnalysis[]>(`/listing-optimizer/${propertyId}/history?limit=${limit}`)
