import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  addCompSetMember,
  type CompSetMemberPayload,
  type CompSetPayload,
  createCompSet,
  deleteCompSet,
  fetchCompSet,
  fetchCompSets,
  fetchMarketSnapshots,
  fetchPacingData,
  fetchPortfolioKPIs,
  fetchTrends,
  refreshCompSet,
  removeCompSetMember,
  triggerMetricsCompute,
  updateCompSet,
} from '@/api/analytics'
import { usePropertyStore } from '@/store/usePropertyStore'

// ---------------------------------------------------------------------------
// Portfolio KPIs
// ---------------------------------------------------------------------------

export function usePortfolioKPIs(months = 12) {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  return useQuery({
    queryKey: ['analytics', 'portfolio', propertyId, months],
    queryFn: () => fetchPortfolioKPIs({ property_id: propertyId ?? undefined, months }),
    staleTime: 10 * 60 * 1000,
  })
}

export function useTriggerMetricsCompute() {
  const qc = useQueryClient()
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  return useMutation({
    mutationFn: () => triggerMetricsCompute(propertyId ?? undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analytics'] }),
  })
}

// ---------------------------------------------------------------------------
// Pacing
// ---------------------------------------------------------------------------

export function usePacingData(targetMonth?: string) {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  return useQuery({
    queryKey: ['analytics', 'pacing', propertyId, targetMonth],
    queryFn: () => fetchPacingData(propertyId!, targetMonth),
    enabled: propertyId != null,
    staleTime: 10 * 60 * 1000,
  })
}

// ---------------------------------------------------------------------------
// Market Snapshots + Trends
// ---------------------------------------------------------------------------

export function useMarketSnapshots(days = 90) {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  return useQuery({
    queryKey: ['analytics', 'market', propertyId, days],
    queryFn: () => fetchMarketSnapshots({ property_id: propertyId ?? undefined, days }),
    staleTime: 15 * 60 * 1000,
  })
}

export function useTrends(months = 12) {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  return useQuery({
    queryKey: ['analytics', 'trends', propertyId, months],
    queryFn: () => fetchTrends({ property_id: propertyId ?? undefined, months }),
    staleTime: 10 * 60 * 1000,
  })
}

// ---------------------------------------------------------------------------
// Comp Sets
// ---------------------------------------------------------------------------

export function useCompSets() {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  return useQuery({
    queryKey: ['analytics', 'comp-sets', propertyId],
    queryFn: () => fetchCompSets(propertyId ?? undefined),
    staleTime: 10 * 60 * 1000,
  })
}

export function useCompSet(id: number | null) {
  return useQuery({
    queryKey: ['analytics', 'comp-sets', id, 'detail'],
    queryFn: () => fetchCompSet(id!),
    enabled: id != null,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateCompSet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CompSetPayload) => createCompSet(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analytics', 'comp-sets'] }),
  })
}

export function useUpdateCompSet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<CompSetPayload> }) =>
      updateCompSet(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analytics', 'comp-sets'] }),
  })
}

export function useDeleteCompSet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteCompSet(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analytics', 'comp-sets'] }),
  })
}

export function useAddCompSetMember() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ compSetId, payload }: { compSetId: number; payload: CompSetMemberPayload }) =>
      addCompSetMember(compSetId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analytics', 'comp-sets'] }),
  })
}

export function useRemoveCompSetMember() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ compSetId, memberId }: { compSetId: number; memberId: number }) =>
      removeCompSetMember(compSetId, memberId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analytics', 'comp-sets'] }),
  })
}

export function useRefreshCompSet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => refreshCompSet(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analytics', 'comp-sets'] }),
  })
}
