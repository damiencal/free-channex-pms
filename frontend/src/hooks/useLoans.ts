import { useQuery } from '@tanstack/react-query'
import { fetchLoans } from '@/api/finance'

export function useLoans() {
  return useQuery({
    queryKey: ['finance', 'loans'],
    queryFn: () => fetchLoans(),
    staleTime: 5 * 60 * 1000,
  })
}
