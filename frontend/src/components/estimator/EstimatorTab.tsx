import { useState } from 'react'
import { EstimatorForm } from './EstimatorForm'
import { EstimatorResults } from './EstimatorResults'
import type { RevenueEstimate } from '@/api/estimator'

export function EstimatorTab() {
  const [result, setResult] = useState<RevenueEstimate | null>(null)

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Revenue Estimator Pro</h2>
        <p className="text-sm text-muted-foreground">
          Project monthly and annual revenue for a new listing based on comparable properties.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <EstimatorForm onResult={setResult} />
        {result ? (
          <EstimatorResults data={result} onReset={() => setResult(null)} />
        ) : (
          <div className="flex items-center justify-center rounded-lg border border-dashed text-muted-foreground min-h-[300px]">
            <p className="text-sm">Fill in the form to see revenue projections.</p>
          </div>
        )}
      </div>
    </div>
  )
}
