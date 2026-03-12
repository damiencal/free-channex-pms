import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchLatestAnalysis,
  fetchAnalysisHistory,
  triggerListingAnalysis,
  type ListingAnalysis,
} from '@/api/listingOptimizer'

export function useListingAnalysis(propertyId: number | null) {
  return useQuery<ListingAnalysis>({
    queryKey: ['optimizer', 'analysis', propertyId],
    queryFn: () => fetchLatestAnalysis(propertyId!),
    enabled: propertyId != null,
    staleTime: 30 * 60 * 1000,
    retry: (failureCount, error: unknown) => {
      // Don't retry 404 — user hasn't run an analysis yet
      if ((error as { status?: number })?.status === 404) return false
      return failureCount < 2
    },
  })
}

export function useListingAnalysisHistory(propertyId: number | null, limit = 10) {
  return useQuery<ListingAnalysis[]>({
    queryKey: ['optimizer', 'history', propertyId, limit],
    queryFn: () => fetchAnalysisHistory(propertyId!, limit),
    enabled: propertyId != null,
    staleTime: 30 * 60 * 1000,
  })
}

export function useTriggerListingAnalysis(propertyId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => triggerListingAnalysis(propertyId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['optimizer', 'analysis', propertyId] })
      qc.invalidateQueries({ queryKey: ['optimizer', 'history', propertyId] })
    },
  })
}
