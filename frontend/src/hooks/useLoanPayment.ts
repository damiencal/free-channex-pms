import { useMutation, useQueryClient } from '@tanstack/react-query'
import { recordLoanPayment, type LoanPaymentRequest } from '@/api/finance'

export function useLoanPayment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: LoanPaymentRequest) => recordLoanPayment(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['finance', 'loans'] })
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
    },
  })
}
