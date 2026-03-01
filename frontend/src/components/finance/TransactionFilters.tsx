import { type TransactionFilters } from '@/api/finance'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'

interface TransactionFiltersProps {
  filters: TransactionFilters
  onChange: (filters: TransactionFilters) => void
}

const DEFAULT_FILTERS: TransactionFilters = {
  limit: 50,
  offset: 0,
}

export function TransactionFilters({ filters, onChange }: TransactionFiltersProps) {
  function update(partial: Partial<TransactionFilters>) {
    onChange({ ...filters, ...partial, offset: 0 })
  }

  function clearFilters() {
    onChange({ ...DEFAULT_FILTERS })
  }

  // Determine the current category filter value for the select
  const categoryFilterValue =
    filters.categorized === 'false'
      ? '__uncategorized__'
      : filters.categorized === 'true'
        ? '__categorized__'
        : '__all__'

  return (
    <div className="flex flex-wrap items-center gap-2 py-2">
      {/* Category filter */}
      <Select
        value={categoryFilterValue}
        onValueChange={(val) => {
          if (val === '__all__') {
            update({ categorized: undefined })
          } else if (val === '__uncategorized__') {
            update({ categorized: 'false' })
          } else if (val === '__categorized__') {
            update({ categorized: 'true' })
          }
        }}
      >
        <SelectTrigger className="h-8 text-xs w-44">
          <SelectValue placeholder="All categories" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">All transactions</SelectItem>
          <SelectItem value="__uncategorized__">Uncategorized only</SelectItem>
          <SelectItem value="__categorized__">Categorized only</SelectItem>
        </SelectContent>
      </Select>

      {/* Date range */}
      <Input
        type="date"
        className="h-8 text-xs w-36"
        value={filters.start_date ?? ''}
        onChange={(e) => update({ start_date: e.target.value || undefined })}
        aria-label="Start date"
      />
      <span className="text-xs text-muted-foreground">to</span>
      <Input
        type="date"
        className="h-8 text-xs w-36"
        value={filters.end_date ?? ''}
        onChange={(e) => update({ end_date: e.target.value || undefined })}
        aria-label="End date"
      />

      {/* Amount range */}
      <Input
        type="number"
        className="h-8 text-xs w-24"
        placeholder="Min $"
        value={filters.min_amount ?? ''}
        onChange={(e) => update({ min_amount: e.target.value || undefined })}
        aria-label="Minimum amount"
      />
      <Input
        type="number"
        className="h-8 text-xs w-24"
        placeholder="Max $"
        value={filters.max_amount ?? ''}
        onChange={(e) => update({ max_amount: e.target.value || undefined })}
        aria-label="Maximum amount"
      />

      {/* Clear filters */}
      <Button
        variant="ghost"
        size="sm"
        className="h-8 text-xs"
        onClick={clearFilters}
      >
        Clear filters
      </Button>
    </div>
  )
}
