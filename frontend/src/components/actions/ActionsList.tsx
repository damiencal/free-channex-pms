import { Accordion } from '@/components/ui/accordion'
import { ActionItem } from './ActionItem'
import type { ActionItem as ActionItemType } from '@/hooks/useActions'

interface ActionsListProps {
  items: ActionItemType[]
}

/**
 * Renders a sortable list of action items as a single-open accordion.
 * Items are already sorted by urgency from the backend.
 */
export function ActionsList({ items }: ActionsListProps) {
  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      <Accordion type="single" collapsible>
        {items.map((item) => (
          <ActionItem
            key={`${item.type}-${item.booking_id}`}
            item={item}
          />
        ))}
      </Accordion>
    </div>
  )
}
