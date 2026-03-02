import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchPL,
  fetchBalanceSheet,
  fetchIncomeStatement,
  type PLParams,
  type BalanceSheetParams,
  type IncomeStatementParams,
} from '@/api/reports'

export function usePL() {
  const [params, setParams] = useState<PLParams | null>(null)

  const query = useQuery({
    queryKey: ['reports', 'pl', params],
    queryFn: () => fetchPL(params!),
    enabled: params !== null,
    staleTime: 5 * 60 * 1000,
  })

  return { ...query, generate: setParams, hasGenerated: params !== null }
}

export function useBalanceSheet() {
  const [params, setParams] = useState<BalanceSheetParams | null>(null)

  const query = useQuery({
    queryKey: ['reports', 'balance-sheet', params],
    queryFn: () => fetchBalanceSheet(params!),
    enabled: params !== null,
    staleTime: 5 * 60 * 1000,
  })

  return { ...query, generate: setParams, hasGenerated: params !== null }
}

export function useIncomeStatement() {
  const [params, setParams] = useState<IncomeStatementParams | null>(null)

  const query = useQuery({
    queryKey: ['reports', 'income-statement', params],
    queryFn: () => fetchIncomeStatement(params!),
    enabled: params !== null,
    staleTime: 5 * 60 * 1000,
  })

  return { ...query, generate: setParams, hasGenerated: params !== null }
}
