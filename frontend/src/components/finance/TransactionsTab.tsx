import { useEffect, useState } from 'react'
import { type BankTransactionResponse, type TransactionFilters } from '@/api/finance'
import { useTransactions } from '@/hooks/useTransactions'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { TransactionRow } from './TransactionRow'
import { TransactionFilters as TransactionFiltersBar } from './TransactionFilters'
import { BulkActionToolbar } from './BulkActionToolbar'

const PAGE_SIZE = 50

export function TransactionsTab() {
  const [filters, setFilters] = useState<TransactionFilters>({
    limit: PAGE_SIZE,
    offset: 0,
  })
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [allTransactions, setAllTransactions] = useState<BankTransactionResponse[]>([])

  const { data, isLoading, isError, refetch } = useTransactions(filters)

  // Accumulate pages: reset on fresh query (offset 0), append on load-more
  useEffect(() => {
    if (!data) return
    if (filters.offset === 0) {
      setAllTransactions(data)
    } else {
      setAllTransactions((prev) => [...prev, ...data])
    }
  }, [data, filters.offset])

  // --------------------------------------------------------------------------
  // Filter handler
  // --------------------------------------------------------------------------

  function handleFilterChange(newFilters: TransactionFilters) {
    setFilters({ ...newFilters, limit: PAGE_SIZE, offset: 0 })
    setSelected(new Set())
    setAllTransactions([])
  }

  // --------------------------------------------------------------------------
  // Multi-select logic
  // --------------------------------------------------------------------------

  const allIds = allTransactions.map((t) => t.id)
  const isAllSelected = allIds.length > 0 && allIds.every((id) => selected.has(id))

  function toggleRow(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleAll() {
    setSelected(isAllSelected ? new Set() : new Set(allIds))
  }

  // --------------------------------------------------------------------------
  // Pagination
  // --------------------------------------------------------------------------

  const hasMore = data !== undefined && data.length === PAGE_SIZE
  const isLoadingMore = isLoading && (filters.offset ?? 0) > 0

  function loadMore() {
    setFilters((prev) => ({ ...prev, offset: (prev.offset ?? 0) + PAGE_SIZE }))
  }

  // --------------------------------------------------------------------------
  // Render
  // --------------------------------------------------------------------------

  return (
    <div className="flex flex-col gap-3">
      {/* Filters */}
      <TransactionFiltersBar filters={filters} onChange={handleFilterChange} />

      {/* Bulk toolbar (conditionally shown) */}
      {selected.size > 0 && (
        <BulkActionToolbar
          selectedCount={selected.size}
          totalCount={allTransactions.length}
          isAllSelected={isAllSelected}
          onSelectAll={toggleAll}
          onClearSelection={() => setSelected(new Set())}
          selectedIds={selected}
        />
      )}

      {/* Error state */}
      {isError && (
        <ErrorAlert
          message="Failed to load transactions."
          onRetry={() => void refetch()}
        />
      )}

      {/* Table */}
      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50 text-left border-b">
              <th className="w-10 px-2 py-2">
                <Checkbox
                  checked={isAllSelected}
                  onCheckedChange={toggleAll}
                  aria-label="Select all transactions"
                />
              </th>
              <th className="px-2 py-2 text-xs font-medium text-muted-foreground whitespace-nowrap">
                Date
              </th>
              <th className="px-2 py-2 text-xs font-medium text-muted-foreground">
                Description
              </th>
              <th className="px-2 py-2 text-xs font-medium text-muted-foreground text-right">
                Amount
              </th>
              <th className="px-2 py-2 text-xs font-medium text-muted-foreground">
                Category
              </th>
            </tr>
          </thead>
          <tbody>
            {/* Initial loading state */}
            {isLoading && allTransactions.length === 0 &&
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-muted/10' : ''}>
                  <td className="px-2 py-2 w-10">
                    <div className="size-4 rounded bg-muted animate-pulse" />
                  </td>
                  <td className="px-2 py-2">
                    <div className="h-4 w-20 rounded bg-muted animate-pulse" />
                  </td>
                  <td className="px-2 py-2">
                    <div className="h-4 w-40 rounded bg-muted animate-pulse" />
                  </td>
                  <td className="px-2 py-2 text-right">
                    <div className="h-4 w-16 rounded bg-muted animate-pulse ml-auto" />
                  </td>
                  <td className="px-2 py-2">
                    <div className="h-6 w-36 rounded bg-muted animate-pulse" />
                  </td>
                </tr>
              ))}

            {/* Transaction rows */}
            {allTransactions.map((txn, idx) => (
              <TransactionRow
                key={txn.id}
                txn={txn}
                selected={selected.has(txn.id)}
                onToggle={toggleRow}
                isEven={idx % 2 === 0}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty state */}
      {!isLoading && !isError && allTransactions.length === 0 && (
        <EmptyState
          title="No transactions"
          description="Import bank transactions from the Actions tab to get started."
        />
      )}

      {/* Load More */}
      {hasMore && (
        <div className="flex justify-center pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={loadMore}
            disabled={isLoadingMore}
          >
            {isLoadingMore ? 'Loading...' : 'Load More'}
          </Button>
        </div>
      )}
    </div>
  )
}
