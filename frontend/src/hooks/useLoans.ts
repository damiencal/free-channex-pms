import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createLoan, fetchLoans, type CreateLoanRequest } from '@/api/finance'

export function useLoans() {
  return useQuery({
    queryKey: ['finance', 'loans'],
    queryFn: () => fetchLoans(),
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateLoan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: CreateLoanRequest) => createLoan(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['finance', 'loans'] })
    },
  })
}
