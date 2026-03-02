import { apiFetch } from '@/api/client'

// ---------------------------------------------------------------------------
// Request param types
// ---------------------------------------------------------------------------

export interface PLParams {
  start_date?: string
  end_date?: string
  month?: number
  quarter?: string
  year?: number
  ytd?: boolean
  breakdown?: 'combined' | 'property'
}

export interface BalanceSheetParams {
  as_of: string // ISO date
}

export interface IncomeStatementParams {
  start_date?: string
  end_date?: string
  month?: number
  quarter?: string
  year?: number
  ytd?: boolean
  breakdown?: 'totals' | 'monthly'
}

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface PLCombinedResponse {
  period: { start_date: string; end_date: string }
  breakdown: 'combined'
  revenue: {
    by_platform: Record<
      string,
      { months: Array<{ month: string; amount: string }>; subtotal: string }
    >
    total: string
  }
  expenses: {
    by_category: Record<string, string>
    total: string
  }
  net_income: string
}

export interface BalanceSheetResponse {
  as_of: string
  assets: { accounts: Array<{ number?: string; name: string; balance: string }>; total: string }
  liabilities: { accounts: Array<{ number?: string; name: string; balance: string }>; total: string }
  equity: { accounts: Array<{ name: string; balance: string }>; total: string }
  total_liabilities_and_equity: string
}

export interface IncomeStatementTotalsResponse {
  period: { start_date: string; end_date: string }
  breakdown: 'totals'
  revenue: { by_account: Record<string, string>; total: string }
  expenses: { by_account: Record<string, string>; total: string }
  net_income: string
}

export interface IncomeStatementMonthlyResponse {
  period: { start_date: string; end_date: string }
  breakdown: 'monthly'
  months: Array<{
    month: string
    revenue: { by_account: Record<string, string>; total: string }
    expenses: { by_account: Record<string, string>; total: string }
    net_income: string
  }>
  totals: {
    revenue: { by_account: Record<string, string>; total: string }
    expenses: { by_account: Record<string, string>; total: string }
    net_income: string
  }
}

// ---------------------------------------------------------------------------
// Fetch functions
// ---------------------------------------------------------------------------

export function fetchPL(params: PLParams): Promise<PLCombinedResponse> {
  const qs = new URLSearchParams()
  if (params.start_date) qs.set('start_date', params.start_date)
  if (params.end_date) qs.set('end_date', params.end_date)
  if (params.month != null) qs.set('month', String(params.month))
  if (params.quarter) qs.set('quarter', params.quarter)
  if (params.year != null) qs.set('year', String(params.year))
  if (params.ytd) qs.set('ytd', 'true')
  qs.set('breakdown', params.breakdown ?? 'combined')
  return apiFetch<PLCombinedResponse>(`/reports/pl?${qs.toString()}`)
}

export function fetchBalanceSheet(params: BalanceSheetParams): Promise<BalanceSheetResponse> {
  return apiFetch<BalanceSheetResponse>(`/reports/balance-sheet?as_of=${params.as_of}`)
}

export function fetchIncomeStatement(
  params: IncomeStatementParams,
): Promise<IncomeStatementTotalsResponse | IncomeStatementMonthlyResponse> {
  const qs = new URLSearchParams()
  if (params.start_date) qs.set('start_date', params.start_date)
  if (params.end_date) qs.set('end_date', params.end_date)
  if (params.month != null) qs.set('month', String(params.month))
  if (params.quarter) qs.set('quarter', params.quarter)
  if (params.year != null) qs.set('year', String(params.year))
  if (params.ytd) qs.set('ytd', 'true')
  qs.set('breakdown', params.breakdown ?? 'totals')
  return apiFetch<IncomeStatementTotalsResponse | IncomeStatementMonthlyResponse>(
    `/reports/income-statement?${qs.toString()}`,
  )
}
