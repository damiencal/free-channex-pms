import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  acceptRecommendation,
  bulkAcceptRecommendations,
  type BulkAcceptPayload,
  createEvent,
  deleteEvent,
  fetchEvents,
  fetchPricingRule,
  fetchRecommendations,
  generateRecommendations,
  type GeneratePayload,
  type MarketEvent,
  type MarketEventPayload,
  type PriceRecommendation,
  type PricingRule,
  type PricingRulePayload,
  rejectRecommendation,
  seedHolidays,
  updateEvent,
  upsertPricingRule,
} from '@/api/pricing'
import { usePropertyStore } from '@/store/usePropertyStore'

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

export function useRecommendations(params: {
  date_from?: string
  date_to?: string
  status?: string
} = {}) {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  return useQuery<PriceRecommendation[]>({
    queryKey: ['pricing', 'recommendations', propertyId, params],
    queryFn: () =>
      fetchRecommendations({
        property_id: propertyId ?? undefined,
        ...params,
      }),
    staleTime: 2 * 60 * 1000,
  })
}

export function useAcceptRecommendation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, price }: { id: number; price?: number }) => acceptRecommendation(id, price),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pricing', 'recommendations'] }),
  })
}

export function useRejectRecommendation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) => rejectRecommendation(id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pricing', 'recommendations'] }),
  })
}

export function useBulkAcceptRecommendations() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: BulkAcceptPayload) => bulkAcceptRecommendations(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pricing', 'recommendations'] }),
  })
}

export function useGenerateRecommendations() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: GeneratePayload) => generateRecommendations(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pricing', 'recommendations'] }),
  })
}

// ---------------------------------------------------------------------------
// Pricing Rules
// ---------------------------------------------------------------------------

export function usePricingRule(propertyId: number | null) {
  return useQuery<PricingRule>({
    queryKey: ['pricing', 'rules', propertyId],
    queryFn: () => fetchPricingRule(propertyId!),
    enabled: propertyId != null,
    staleTime: 10 * 60 * 1000,
  })
}

export function useUpsertPricingRule(propertyId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: PricingRulePayload) => upsertPricingRule(propertyId!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pricing', 'rules', propertyId] }),
  })
}

// ---------------------------------------------------------------------------
// Market Events
// ---------------------------------------------------------------------------

export function useMarketEvents(params: {
  include_global?: boolean
  start_date?: string
  end_date?: string
  event_type?: string
} = {}) {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  return useQuery<MarketEvent[]>({
    queryKey: ['pricing', 'events', propertyId, params],
    queryFn: () =>
      fetchEvents({
        property_id: propertyId ?? undefined,
        include_global: true,
        ...params,
      }),
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateEvent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: MarketEventPayload) => createEvent(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pricing', 'events'] }),
  })
}

export function useUpdateEvent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<MarketEventPayload> }) =>
      updateEvent(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pricing', 'events'] }),
  })
}

export function useDeleteEvent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteEvent(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pricing', 'events'] }),
  })
}

export function useSeedHolidays() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => seedHolidays(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pricing', 'events'] }),
  })
}
