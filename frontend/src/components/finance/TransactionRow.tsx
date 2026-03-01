import { Checkbox } from '@/components/ui/checkbox'
import { type BankTransactionResponse } from '@/api/finance'
import { CategorySelect } from './CategorySelect'

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
})

interface TransactionRowProps {
  txn: BankTransactionResponse
  selected: boolean
  onToggle: (id: number) => void
  isEven: boolean
}

export function TransactionRow({ txn, selected, onToggle, isEven }: TransactionRowProps) {
  // Parse date avoiding timezone shift (per [07-04] decision)
  const [year, month, day] = txn.date.split('-').map(Number)
  const dateStr = new Date(year, month - 1, day).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  const amount = parseFloat(txn.amount)
  const isNegative = amount < 0
  const amountStr = currencyFormatter.format(amount)

  return (
    <tr
      className={[
        'transition-colors hover:bg-muted/50',
        selected ? 'bg-muted/30' : isEven ? 'bg-muted/10' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {/* Checkbox */}
      <td className="w-10 px-2 py-1.5">
        <Checkbox
          checked={selected}
          onCheckedChange={() => onToggle(txn.id)}
          aria-label="Select transaction"
        />
      </td>

      {/* Date */}
      <td className="px-2 py-1.5 text-sm whitespace-nowrap">{dateStr}</td>

      {/* Description */}
      <td className="px-2 py-1.5 text-sm">
        <span className="block truncate max-w-[200px]" title={txn.description ?? undefined}>
          {txn.description ?? '\u2014'}
        </span>
      </td>

      {/* Amount */}
      <td
        className={[
          'px-2 py-1.5 text-sm text-right whitespace-nowrap tabular-nums',
          isNegative ? 'text-destructive' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {amountStr}
      </td>

      {/* Category */}
      <td className="px-2 py-1.5">
        <CategorySelect txn={txn} />
      </td>
    </tr>
  )
}
