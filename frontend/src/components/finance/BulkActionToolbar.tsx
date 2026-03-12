import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { bulkCategorize, type CategoryAssignment } from '@/api/finance'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import {
  EXPENSE_CATEGORIES,
  NON_EXPENSE_CATEGORIES,
  formatCategoryName,
} from './categoryConstants'

const ATTRIBUTION_OPTIONS = ['jay', 'minnie', 'shared'] as const

interface BulkActionToolbarProps {
  selectedCount: number
  totalCount: number
  isAllSelected: boolean
  onSelectAll: () => void
  onClearSelection: () => void
  selectedIds: Set<number>
}

export function BulkActionToolbar({
  selectedCount,
  totalCount,
  isAllSelected,
  onSelectAll,
  onClearSelection,
  selectedIds,
}: BulkActionToolbarProps) {
  const queryClient = useQueryClient()
  const [pendingCategory, setPendingCategory] = useState<string | null>(null)
  const [successText, setSuccessText] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (assignments: CategoryAssignment[]) => bulkCategorize(assignments),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
      setSuccessText(`${data.categorized} transactions categorized`)
      setTimeout(() => setSuccessText(null), 2000)
      setPendingCategory(null)
      onClearSelection()
    },
  })

  function fireBulk(category: string, attribution?: string) {
    const assignments: CategoryAssignment[] = Array.from(selectedIds).map((id) => ({
      id,
      category,
      attribution: attribution ?? null,
    }))
    mutation.mutate(assignments)
  }

  return (
    <div className="bg-muted rounded-lg px-4 py-2 flex items-center justify-between gap-4 flex-wrap">
      {/* Left: selection info + select/clear all */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium">
          {selectedCount} of {totalCount} selected
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs"
          onClick={isAllSelected ? onClearSelection : onSelectAll}
        >
          {isAllSelected ? 'Clear All' : 'Select All'}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs"
          onClick={onClearSelection}
        >
          Clear
        </Button>
      </div>

      {/* Right: bulk category assignment */}
      <div className="flex items-center gap-2">
        {successText && (
          <span className="text-xs text-green-600 font-medium">{successText}</span>
        )}
        {mutation.isPending && (
          <span className="text-xs text-muted-foreground">Saving...</span>
        )}
        {mutation.isError && (
          <span className="text-xs text-destructive">Error saving</span>
        )}

        {pendingCategory !== null ? (
          // Step 2: attribution prompt
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {formatCategoryName(pendingCategory)} —
            </span>
            <Select
              onValueChange={(attribution) => {
                fireBulk(pendingCategory, attribution)
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
          </div>
        ) : (
          // Step 1: category picker
          <Select
            onValueChange={(cat) => {
              if (EXPENSE_CATEGORIES.includes(cat)) {
                setPendingCategory(cat)
              } else {
                fireBulk(cat)
              }
            }}
          >
            <SelectTrigger className="h-7 text-xs w-44">
              <SelectValue placeholder="Assign category..." />
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
        )}
      </div>
    </div>
  )
}
