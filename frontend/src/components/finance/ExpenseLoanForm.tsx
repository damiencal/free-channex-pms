import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateExpense } from '@/hooks/useExpenses'
import { useLoans, useCreateLoan } from '@/hooks/useLoans'
import { useLoanPayment } from '@/hooks/useLoanPayment'
import { usePropertyStore } from '@/store/usePropertyStore'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const EXPENSE_CATEGORIES: { value: string; label: string }[] = [
  { value: 'repairs_maintenance', label: 'Repairs & Maintenance' },
  { value: 'supplies', label: 'Supplies' },
  { value: 'utilities', label: 'Utilities' },
  { value: 'non_mortgage_interest', label: 'Non-Mortgage Interest' },
  { value: 'owner_reimbursable', label: 'Owner Reimbursable' },
  { value: 'advertising', label: 'Advertising' },
  { value: 'travel_transportation', label: 'Travel & Transportation' },
  { value: 'professional_services', label: 'Professional Services' },
  { value: 'legal', label: 'Legal' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'resort_lot_rental', label: 'Resort Lot Rental' },
  { value: 'cleaning_service', label: 'Cleaning Service' },
]

const ATTRIBUTION_OPTIONS: { value: string; label: string }[] = [
  { value: 'jay', label: 'Jay' },
  { value: 'minnie', label: 'Minnie' },
  { value: 'shared', label: 'Shared' },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(value: string | number): string {
  return Number(value).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

function todayString(): string {
  return new Date().toISOString().split('T')[0]
}

function formatCategoryName(value: string): string {
  return EXPENSE_CATEGORIES.find((c) => c.value === value)?.label ?? value
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FormType = 'expense' | 'loan_payment' | 'create_loan'

interface Property {
  id: number
  slug: string
  display_name: string
}

// ---------------------------------------------------------------------------
// Feedback state
// ---------------------------------------------------------------------------

type FeedbackKind = 'success' | 'warning' | 'error'

interface Feedback {
  kind: FeedbackKind
  message: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ExpenseLoanForm() {
  const queryClient = useQueryClient()
  const { selectedPropertyId } = usePropertyStore()

  // Type toggle
  const [formType, setFormType] = useState<FormType>('expense')

  // Feedback
  const [feedback, setFeedback] = useState<Feedback | null>(null)

  // Expense fields
  const [expenseDate, setExpenseDate] = useState(todayString())
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [attribution, setAttribution] = useState('')
  const [vendor, setVendor] = useState('')

  // Loan payment fields
  const [loanId, setLoanId] = useState('')
  const [principal, setPrincipal] = useState('')
  const [interest, setInterest] = useState('')
  const [paymentDate, setPaymentDate] = useState(todayString())
  const [paymentRef, setPaymentRef] = useState('')

  // Create loan fields
  const [newLoanName, setNewLoanName] = useState('')
  const [newLoanBalance, setNewLoanBalance] = useState('')
  const [newLoanRate, setNewLoanRate] = useState('')
  const [newLoanStart, setNewLoanStart] = useState(todayString())

  // Hooks
  const expenseMutation = useCreateExpense()
  const loanPaymentMutation = useLoanPayment()
  const createLoanMutation = useCreateLoan()
  const { data: loans = [], isLoading: loansLoading } = useLoans()

  // ---------------------------------------------------------------------------
  // Derived state
  // ---------------------------------------------------------------------------

  const loanPaymentTotal =
    (parseFloat(principal) || 0) + (parseFloat(interest) || 0)

  // Resolve property_id from attribution and query cache
  function resolvePropertyId(attributionValue: string): number | null {
    if (attributionValue === 'shared') return null
    const properties = queryClient.getQueryData<Property[]>(['dashboard', 'properties'])
    if (!properties) return selectedPropertyId
    const match = properties.find((p) => p.slug === attributionValue)
    return match ? match.id : selectedPropertyId
  }

  // ---------------------------------------------------------------------------
  // Reset helpers
  // ---------------------------------------------------------------------------

  function resetExpenseFields() {
    setExpenseDate(todayString())
    setAmount('')
    setCategory('')
    setDescription('')
    setAttribution('')
    setVendor('')
  }

  function resetLoanFields() {
    setLoanId('')
    setPrincipal('')
    setInterest('')
    setPaymentDate(todayString())
    setPaymentRef('')
  }

  function resetCreateLoanFields() {
    setNewLoanName('')
    setNewLoanBalance('')
    setNewLoanRate('')
    setNewLoanStart(todayString())
  }

  // Clear feedback on any interaction
  function clearFeedback() {
    setFeedback(null)
  }

  // ---------------------------------------------------------------------------
  // Type toggle
  // ---------------------------------------------------------------------------

  function handleTypeChange(type: FormType) {
    setFormType(type)
    setFeedback(null)
  }

  // ---------------------------------------------------------------------------
  // Submit handlers
  // ---------------------------------------------------------------------------

  function handleExpenseSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!expenseDate || !amount || !category || !description || !attribution) {
      setFeedback({ kind: 'error', message: 'All required fields must be filled.' })
      return
    }
    if (parseFloat(amount) <= 0) {
      setFeedback({ kind: 'error', message: 'Amount must be greater than zero.' })
      return
    }

    const property_id = resolvePropertyId(attribution)

    expenseMutation.mutate(
      {
        expense_date: expenseDate,
        amount,
        category,
        description,
        attribution,
        property_id,
        vendor: vendor || null,
      },
      {
        onSuccess: () => {
          setFeedback({
            kind: 'success',
            message: `Expense recorded — ${formatCurrency(amount)} for ${formatCategoryName(category)}`,
          })
          resetExpenseFields()
        },
        onError: (error) => {
          const msg = error instanceof Error ? error.message : 'Failed to record expense.'
          setFeedback({ kind: 'error', message: msg })
        },
      },
    )
  }

  function handleLoanPaymentSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!loanId || !principal || !interest || !paymentDate || !paymentRef) {
      setFeedback({ kind: 'error', message: 'All required fields must be filled.' })
      return
    }

    loanPaymentMutation.mutate(
      {
        loan_id: parseInt(loanId, 10),
        principal,
        interest,
        payment_date: paymentDate,
        payment_ref: paymentRef,
      },
      {
        onSuccess: (data) => {
          if (data.status === 'skipped') {
            setFeedback({
              kind: 'warning',
              message: 'Already recorded (duplicate payment reference)',
            })
          } else {
            setFeedback({ kind: 'success', message: 'Payment recorded' })
            resetLoanFields()
          }
        },
        onError: (error) => {
          const msg = error instanceof Error ? error.message : 'Failed to record payment.'
          setFeedback({ kind: 'error', message: msg })
        },
      },
    )
  }

  function handleCreateLoanSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!newLoanName || !newLoanBalance || !newLoanRate || !newLoanStart) {
      setFeedback({ kind: 'error', message: 'All required fields must be filled.' })
      return
    }
    if (parseFloat(newLoanBalance) <= 0) {
      setFeedback({ kind: 'error', message: 'Balance must be greater than zero.' })
      return
    }

    createLoanMutation.mutate(
      {
        name: newLoanName,
        original_balance: newLoanBalance,
        interest_rate: newLoanRate,
        start_date: newLoanStart,
        property_id: selectedPropertyId,
      },
      {
        onSuccess: () => {
          setFeedback({
            kind: 'success',
            message: `Loan "${newLoanName}" created — ${formatCurrency(newLoanBalance)}`,
          })
          resetCreateLoanFields()
        },
        onError: (error) => {
          const msg = error instanceof Error ? error.message : 'Failed to create loan.'
          setFeedback({ kind: 'error', message: msg })
        },
      },
    )
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const isPending =
    formType === 'expense'
      ? expenseMutation.isPending
      : formType === 'loan_payment'
        ? loanPaymentMutation.isPending
        : createLoanMutation.isPending

  return (
    <div className="space-y-4">
      {/* Type toggle */}
      <div className="flex gap-2">
        <Button
          type="button"
          variant={formType === 'expense' ? 'default' : 'outline'}
          onClick={() => handleTypeChange('expense')}
        >
          Expense
        </Button>
        <Button
          type="button"
          variant={formType === 'loan_payment' ? 'default' : 'outline'}
          onClick={() => handleTypeChange('loan_payment')}
        >
          Loan Payment
        </Button>
        <Button
          type="button"
          variant={formType === 'create_loan' ? 'default' : 'outline'}
          onClick={() => handleTypeChange('create_loan')}
        >
          New Loan
        </Button>
      </div>

      {/* Inline feedback */}
      {feedback && (
        <p
          className={
            feedback.kind === 'success'
              ? 'text-sm text-green-600 dark:text-green-400'
              : feedback.kind === 'warning'
                ? 'text-sm text-amber-600 dark:text-amber-400'
                : 'text-sm text-red-600 dark:text-red-400'
          }
        >
          {feedback.message}
        </p>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Expense form                                                         */}
      {/* ------------------------------------------------------------------ */}

      {formType === 'expense' && (
        <form onSubmit={handleExpenseSubmit} className="space-y-4">
          {/* Date */}
          <div className="space-y-1">
            <Label htmlFor="expense-date">
              Date <span className="text-red-500">*</span>
            </Label>
            <Input
              id="expense-date"
              type="date"
              value={expenseDate}
              onChange={(e) => { setExpenseDate(e.target.value); clearFeedback() }}
              required
            />
          </div>

          {/* Amount */}
          <div className="space-y-1">
            <Label htmlFor="expense-amount">
              Amount <span className="text-red-500">*</span>
            </Label>
            <Input
              id="expense-amount"
              type="number"
              step="0.01"
              min="0.01"
              placeholder="0.00"
              value={amount}
              onChange={(e) => { setAmount(e.target.value); clearFeedback() }}
              required
            />
          </div>

          {/* Category */}
          <div className="space-y-1">
            <Label htmlFor="expense-category">
              Category <span className="text-red-500">*</span>
            </Label>
            <Select
              value={category}
              onValueChange={(val) => { setCategory(val); clearFeedback() }}
            >
              <SelectTrigger id="expense-category" className="w-full">
                <SelectValue placeholder="Select category" />
              </SelectTrigger>
              <SelectContent>
                {EXPENSE_CATEGORIES.map((cat) => (
                  <SelectItem key={cat.value} value={cat.value}>
                    {cat.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Description */}
          <div className="space-y-1">
            <Label htmlFor="expense-description">
              Description <span className="text-red-500">*</span>
            </Label>
            <Input
              id="expense-description"
              placeholder="e.g., Plumber repair kitchen sink"
              value={description}
              onChange={(e) => { setDescription(e.target.value); clearFeedback() }}
              required
            />
          </div>

          {/* Attribution */}
          <div className="space-y-1">
            <Label htmlFor="expense-attribution">
              Attribution <span className="text-red-500">*</span>
            </Label>
            <Select
              value={attribution}
              onValueChange={(val) => { setAttribution(val); clearFeedback() }}
            >
              <SelectTrigger id="expense-attribution" className="w-full">
                <SelectValue placeholder="Select attribution" />
              </SelectTrigger>
              <SelectContent>
                {ATTRIBUTION_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Vendor (optional) */}
          <div className="space-y-1">
            <Label htmlFor="expense-vendor">Vendor (optional)</Label>
            <Input
              id="expense-vendor"
              placeholder="Optional vendor name"
              value={vendor}
              onChange={(e) => { setVendor(e.target.value); clearFeedback() }}
            />
          </div>

          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? 'Recording...' : 'Record Expense'}
          </Button>
        </form>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Loan payment form                                                    */}
      {/* ------------------------------------------------------------------ */}

      {formType === 'loan_payment' && (
        <form onSubmit={handleLoanPaymentSubmit} className="space-y-4">
          {/* Loan selector */}
          <div className="space-y-1">
            <Label htmlFor="loan-id">
              Loan <span className="text-red-500">*</span>
            </Label>
            <Select
              value={loanId}
              onValueChange={(val) => { setLoanId(val); clearFeedback() }}
              disabled={loansLoading}
            >
              <SelectTrigger id="loan-id" className="w-full">
                <SelectValue
                  placeholder={loansLoading ? 'Loading loans...' : 'Select loan'}
                />
              </SelectTrigger>
              <SelectContent>
                {loans.map((loan) => (
                  <SelectItem key={loan.id} value={String(loan.id)}>
                    {loan.name} — {formatCurrency(loan.current_balance)} remaining
                  </SelectItem>
                ))}
                {loans.length === 0 && !loansLoading && (
                  <SelectItem value="__none__" disabled>
                    No active loans
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          {/* Principal */}
          <div className="space-y-1">
            <Label htmlFor="loan-principal">
              Principal <span className="text-red-500">*</span>
            </Label>
            <Input
              id="loan-principal"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={principal}
              onChange={(e) => { setPrincipal(e.target.value); clearFeedback() }}
              required
            />
          </div>

          {/* Interest */}
          <div className="space-y-1">
            <Label htmlFor="loan-interest">
              Interest <span className="text-red-500">*</span>
            </Label>
            <Input
              id="loan-interest"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={interest}
              onChange={(e) => { setInterest(e.target.value); clearFeedback() }}
              required
            />
          </div>

          {/* Total (read-only) */}
          <div className="space-y-1">
            <Label>Total Payment</Label>
            <p className="text-sm font-medium tabular-nums">
              {formatCurrency(loanPaymentTotal)}
            </p>
          </div>

          {/* Payment date */}
          <div className="space-y-1">
            <Label htmlFor="payment-date">
              Payment Date <span className="text-red-500">*</span>
            </Label>
            <Input
              id="payment-date"
              type="date"
              value={paymentDate}
              onChange={(e) => { setPaymentDate(e.target.value); clearFeedback() }}
              required
            />
          </div>

          {/* Payment reference */}
          <div className="space-y-1">
            <Label htmlFor="payment-ref">
              Payment Reference <span className="text-red-500">*</span>
            </Label>
            <Input
              id="payment-ref"
              placeholder="e.g., 2026-03"
              value={paymentRef}
              onChange={(e) => { setPaymentRef(e.target.value); clearFeedback() }}
              required
            />
            <p className="text-xs text-muted-foreground">
              Month reference used for idempotency (prevents duplicate entries)
            </p>
          </div>

          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? 'Recording...' : 'Record Payment'}
          </Button>
        </form>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Create loan form                                                     */}
      {/* ------------------------------------------------------------------ */}

      {formType === 'create_loan' && (
        <form onSubmit={handleCreateLoanSubmit} className="space-y-4">
          {/* Loan name */}
          <div className="space-y-1">
            <Label htmlFor="new-loan-name">
              Loan Name <span className="text-red-500">*</span>
            </Label>
            <Input
              id="new-loan-name"
              placeholder="e.g., Home Equity Loan"
              value={newLoanName}
              onChange={(e) => { setNewLoanName(e.target.value); clearFeedback() }}
              required
            />
          </div>

          {/* Original balance */}
          <div className="space-y-1">
            <Label htmlFor="new-loan-balance">
              Original Balance <span className="text-red-500">*</span>
            </Label>
            <Input
              id="new-loan-balance"
              type="number"
              step="0.01"
              min="0.01"
              placeholder="0.00"
              value={newLoanBalance}
              onChange={(e) => { setNewLoanBalance(e.target.value); clearFeedback() }}
              required
            />
          </div>

          {/* Interest rate */}
          <div className="space-y-1">
            <Label htmlFor="new-loan-rate">
              Interest Rate (%) <span className="text-red-500">*</span>
            </Label>
            <Input
              id="new-loan-rate"
              type="number"
              step="0.01"
              min="0"
              placeholder="e.g., 5.25"
              value={newLoanRate}
              onChange={(e) => { setNewLoanRate(e.target.value); clearFeedback() }}
              required
            />
          </div>

          {/* Start date */}
          <div className="space-y-1">
            <Label htmlFor="new-loan-start">
              Start Date <span className="text-red-500">*</span>
            </Label>
            <Input
              id="new-loan-start"
              type="date"
              value={newLoanStart}
              onChange={(e) => { setNewLoanStart(e.target.value); clearFeedback() }}
              required
            />
          </div>

          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? 'Creating...' : 'Create Loan'}
          </Button>
        </form>
      )}
    </div>
  )
}
