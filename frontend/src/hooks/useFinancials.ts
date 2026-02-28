import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/api/client'
import { usePropertyStore } from '@/store/usePropertyStore'

export interface MetricsResponse {
  ytd_revenue: string
  ytd_expenses: string
  current_month_profit: string
  yoy_revenue_change: string | null
  yoy_expense_change: string | null
  actions_count: number
}

export interface OccupancyMonth {
  year: number
  month: number
  occupied_nights: number
  total_nights: number
  occupancy_rate: number
}

export interface OccupancyProperty {
  property_slug: string
  property_display_name: string
  months: OccupancyMonth[]
}

export function useMetrics() {
  const selectedPropertyId = usePropertyStore((s) => s.selectedPropertyId)

  return useQuery<MetricsResponse>({
    queryKey: ['dashboard', 'metrics', selectedPropertyId],
    queryFn: () => {
      const params = selectedPropertyId !== null ? `?property_id=${selectedPropertyId}` : ''
      return apiFetch<MetricsResponse>(`/dashboard/metrics${params}`)
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useOccupancy() {
  const selectedPropertyId = usePropertyStore((s) => s.selectedPropertyId)

  return useQuery<OccupancyProperty[]>({
    queryKey: ['dashboard', 'occupancy', selectedPropertyId],
    queryFn: () => {
      const params = selectedPropertyId !== null ? `?property_id=${selectedPropertyId}` : ''
      return apiFetch<OccupancyProperty[]>(`/dashboard/occupancy${params}`)
    },
    staleTime: 5 * 60 * 1000,
  })
}
