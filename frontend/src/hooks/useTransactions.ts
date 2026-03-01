import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  bulkCategorize,
  categorizeTransaction,
  fetchTransactions,
  type CategoryAssignment,
  type SingleCategoryRequest,
  type TransactionFilters,
} from '@/api/finance'
import { usePropertyStore } from '@/store/usePropertyStore'

export function useTransactions(filters: TransactionFilters = {}) {
  const selectedPropertyId = usePropertyStore((s) => s.selectedPropertyId)

  return useQuery({
    queryKey: ['finance', 'transactions', selectedPropertyId, filters],
    queryFn: () => fetchTransactions(filters),
    staleTime: 2 * 60 * 1000,
  })
}

export function useCategorizeTransaction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ txnId, body }: { txnId: number; body: SingleCategoryRequest }) =>
      categorizeTransaction(txnId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
    },
  })
}

export function useBulkCategorize() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (assignments: CategoryAssignment[]) => bulkCategorize(assignments),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
    },
  })
}
