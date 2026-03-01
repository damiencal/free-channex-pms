import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { categorizeTransaction, type BankTransactionResponse } from '@/api/finance'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

// ---------------------------------------------------------------------------
// Category constants
// ---------------------------------------------------------------------------

export const EXPENSE_CATEGORIES = [
  'repairs_maintenance',
  'supplies',
  'utilities',
  'non_mortgage_interest',
  'owner_reimbursable',
  'advertising',
  'travel_transportation',
  'professional_services',
  'legal',
  'insurance',
  'resort_lot_rental',
  'cleaning_service',
]

export const NON_EXPENSE_CATEGORIES = [
  'owner_deposit',
  'loan_payment',
  'transfer',
  'personal',
]

export const ALL_CATEGORIES = [...EXPENSE_CATEGORIES, ...NON_EXPENSE_CATEGORIES]

const ATTRIBUTION_OPTIONS = ['jay', 'minnie', 'shared'] as const

export function formatCategoryName(cat: string): string {
  return cat
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface CategorySelectProps {
  txn: BankTransactionResponse
  onSaved?: () => void
}

export function CategorySelect({ txn, onSaved }: CategorySelectProps) {
  const queryClient = useQueryClient()
  const [pendingCategory, setPendingCategory] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const mutation = useMutation({
    mutationFn: ({
      category,
      attribution,
    }: {
      category: string
      attribution?: string
    }) =>
      categorizeTransaction(txn.id, {
        category,
        attribution: attribution ?? null,
      }),
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 1500)
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
      onSaved?.()
      setPendingCategory(null)
    },
  })

  // Step 2: Attribution prompt for expense categories
  if (pendingCategory !== null) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-muted-foreground truncate max-w-[100px]">
          {formatCategoryName(pendingCategory)}:
        </span>
        <Select
          onValueChange={(attribution) => {
            mutation.mutate({ category: pendingCategory, attribution })
          }}
        >
          <SelectTrigger className="h-7 text-xs w-28">
            <SelectValue placeholder="Who?" />
          </SelectTrigger>
          <SelectContent>
            {ATTRIBUTION_OPTIONS.map((opt) => (
              <SelectItem key={opt} value={opt}>
                {opt.charAt(0).toUpperCase() + opt.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <button
          onClick={() => setPendingCategory(null)}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Cancel
        </button>
        {mutation.isPending && (
          <span className="text-xs text-muted-foreground">Saving...</span>
        )}
        {mutation.isError && (
          <span className="text-xs text-destructive">Error</span>
        )}
      </div>
    )
  }

  // Step 1: Category select
  return (
    <div className="flex items-center gap-1.5">
      <Select
        defaultValue={txn.category ?? undefined}
        onValueChange={(cat) => {
          if (EXPENSE_CATEGORIES.includes(cat)) {
            // Two-step: wait for attribution
            setPendingCategory(cat)
          } else {
            // Non-expense: save immediately
            mutation.mutate({ category: cat })
          }
        }}
      >
        <SelectTrigger className="h-7 text-xs w-40">
          <SelectValue placeholder="Uncategorized" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Expense Categories</SelectLabel>
            {EXPENSE_CATEGORIES.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {formatCategoryName(cat)}
              </SelectItem>
            ))}
          </SelectGroup>
          <SelectGroup>
            <SelectLabel>Other Categories</SelectLabel>
            {NON_EXPENSE_CATEGORIES.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {formatCategoryName(cat)}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      {saved && (
        <span className="text-xs text-green-600 font-medium">Saved</span>
      )}
      {mutation.isPending && (
        <span className="text-xs text-muted-foreground">Saving...</span>
      )}
      {mutation.isError && (
        <span className="text-xs text-destructive">Error</span>
      )}
    </div>
  )
}
