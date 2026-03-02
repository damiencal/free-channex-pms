import { apiFetch } from '@/api/client'

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface BankTransactionResponse {
  id: number
  transaction_id: string
  date: string // ISO date
  description: string | null
  amount: string // Decimal as string
  reconciliation_status: string
  category: string | null
  journal_entry_id: number | null
}

export interface ExpenseResponse {
  id: number
  expense_date: string
  amount: string
  category: string
  description: string
  attribution: string
  property_id: number | null
  vendor: string | null
  journal_entry_id: number | null
}

export interface LoanResponse {
  id: number
  name: string
  account_id: number
  original_balance: string
  interest_rate: string
  start_date: string
  current_balance: string
}

export interface LoanPaymentResult {
  status: string // "recorded" | "skipped"
  journal_entry_id: number | null
  message?: string
}

export interface PendingConfirmation {
  match_id: number
  booking: {
    id: number
    platform: string
    guest_name: string
    check_in_date: string | null
    net_amount: string
  }
  deposit: {
    id: number
    date: string | null
    amount: string
    description: string | null
  }
}

export interface UnreconciledDeposit {
  id: number
  date: string | null
  amount: string
  description: string | null
}

export interface UnreconciledPayout {
  id: number
  platform: string
  guest_name: string
  check_in_date: string | null
  net_amount: string
}

export interface UnreconciledResponse {
  unmatched_payouts: UnreconciledPayout[]
  unmatched_deposits: UnreconciledDeposit[]
  needs_review: UnreconciledDeposit[]
  pending_confirmation: PendingConfirmation[]
}

export interface ReconciliationRunResult {
  auto_matched: number
  needs_review: number
  unmatched_payouts: number
  unmatched_deposits: number
}

export interface FinanceSummaryResponse {
  uncategorized_count: number
  unreconciled_count: number
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

export interface SingleCategoryRequest {
  category: string
  property_id?: number | null
  attribution?: string | null
}

export interface CategoryAssignment {
  id: number
  category: string
  property_id?: number | null
  attribution?: string | null
}

export interface ExpenseRequest {
  expense_date: string
  amount: string
  category: string
  description: string
  attribution: string
  property_id?: number | null
  vendor?: string | null
}

export interface CreateLoanRequest {
  name: string
  original_balance: string
  interest_rate: string
  start_date: string
  property_id?: number | null
}

export interface LoanPaymentRequest {
  loan_id: number
  principal: string
  interest: string
  payment_date: string
  payment_ref: string
}

export interface MatchConfirmRequest {
  booking_id: number
  bank_transaction_id: number
  confirmed_by?: string
}

// Transaction filter params
export interface TransactionFilters {
  categorized?: string // 'true' | 'false' | 'all'
  start_date?: string
  end_date?: string
  min_amount?: string
  max_amount?: string
  limit?: number
  offset?: number
}

// ---------------------------------------------------------------------------
// Fetch functions
// ---------------------------------------------------------------------------

export function fetchTransactions(filters: TransactionFilters = {}): Promise<BankTransactionResponse[]> {
  const params = new URLSearchParams()
  if (filters.categorized) params.set('categorized', filters.categorized)
  if (filters.start_date) params.set('start_date', filters.start_date)
  if (filters.end_date) params.set('end_date', filters.end_date)
  if (filters.min_amount) params.set('min_amount', filters.min_amount)
  if (filters.max_amount) params.set('max_amount', filters.max_amount)
  if (filters.limit !== undefined) params.set('limit', String(filters.limit))
  if (filters.offset !== undefined) params.set('offset', String(filters.offset))
  const qs = params.toString()
  return apiFetch<BankTransactionResponse[]>(`/accounting/bank-transactions${qs ? `?${qs}` : ''}`)
}

export function categorizeTransaction(
  txnId: number,
  body: SingleCategoryRequest,
): Promise<BankTransactionResponse> {
  return apiFetch<BankTransactionResponse>(`/accounting/bank-transactions/${txnId}/category`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function bulkCategorize(
  assignments: CategoryAssignment[],
): Promise<{ categorized: number; errors: unknown[] }> {
  return apiFetch<{ categorized: number; errors: unknown[] }>('/accounting/bank-transactions/categorize', {
    method: 'PATCH',
    body: JSON.stringify({ assignments }),
  })
}

export function createExpense(body: ExpenseRequest): Promise<ExpenseResponse> {
  return apiFetch<ExpenseResponse>('/accounting/expenses', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function fetchLoans(): Promise<LoanResponse[]> {
  return apiFetch<LoanResponse[]>('/accounting/loans')
}

export function createLoan(body: CreateLoanRequest): Promise<LoanResponse> {
  return apiFetch<LoanResponse>('/accounting/loans', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function recordLoanPayment(body: LoanPaymentRequest): Promise<LoanPaymentResult> {
  return apiFetch<LoanPaymentResult>('/accounting/loans/payments', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function fetchUnreconciled(propertyId?: number | null): Promise<UnreconciledResponse> {
  const params = propertyId != null ? `?property_id=${propertyId}` : ''
  return apiFetch<UnreconciledResponse>(`/accounting/reconciliation/unreconciled${params}`)
}

export function runReconciliation(): Promise<ReconciliationRunResult> {
  return apiFetch<ReconciliationRunResult>('/accounting/reconciliation/run', { method: 'POST' })
}

export function confirmMatch(body: MatchConfirmRequest): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/accounting/reconciliation/confirm', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function rejectMatch(matchId: number): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/accounting/reconciliation/reject/${matchId}`, {
    method: 'POST',
  })
}

export function fetchFinanceSummary(propertyId?: number | null): Promise<FinanceSummaryResponse> {
  const params = propertyId != null ? `?property_id=${propertyId}` : ''
  return apiFetch<FinanceSummaryResponse>(`/accounting/finance-summary${params}`)
}
