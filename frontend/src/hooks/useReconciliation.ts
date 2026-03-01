import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  confirmMatch,
  fetchUnreconciled,
  rejectMatch,
  runReconciliation,
  type MatchConfirmRequest,
} from '@/api/finance'
import { usePropertyStore } from '@/store/usePropertyStore'

export function useReconciliation() {
  const selectedPropertyId = usePropertyStore((s) => s.selectedPropertyId)

  return useQuery({
    queryKey: ['finance', 'reconciliation', selectedPropertyId],
    queryFn: () => fetchUnreconciled(selectedPropertyId),
    staleTime: 2 * 60 * 1000,
  })
}

export function useRunReconciliation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => runReconciliation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
    },
  })
}

export function useConfirmMatch() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: MatchConfirmRequest) => confirmMatch(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
    },
  })
}

export function useRejectMatch() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (matchId: number) => rejectMatch(matchId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
    },
  })
}
