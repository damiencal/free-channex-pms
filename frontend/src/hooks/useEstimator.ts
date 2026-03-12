import { useMutation } from '@tanstack/react-query'
import { estimateRevenue, type EstimatorRequest, type RevenueEstimate } from '@/api/estimator'
import { useState } from 'react'

export function useEstimator() {
  const [result, setResult] = useState<RevenueEstimate | null>(null)

  const mutation = useMutation({
    mutationFn: (payload: EstimatorRequest) => estimateRevenue(payload),
    onSuccess: (data) => setResult(data),
  })

  return {
    estimate: mutation.mutate,
    result,
    isLoading: mutation.isPending,
    error: mutation.error,
    reset: () => setResult(null),
  }
}
