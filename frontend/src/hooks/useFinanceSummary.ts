import { useQuery } from '@tanstack/react-query'
import { fetchFinanceSummary } from '@/api/finance'
import { usePropertyStore } from '@/store/usePropertyStore'

export function useFinanceSummary() {
  const selectedPropertyId = usePropertyStore((s) => s.selectedPropertyId)

  return useQuery({
    queryKey: ['finance', 'summary', selectedPropertyId],
    queryFn: () => fetchFinanceSummary(selectedPropertyId),
    staleTime: 2 * 60 * 1000,
  })
}
