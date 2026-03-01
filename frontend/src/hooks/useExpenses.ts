import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createExpense, type ExpenseRequest } from '@/api/finance'

export function useCreateExpense() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: ExpenseRequest) => createExpense(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
    },
  })
}
