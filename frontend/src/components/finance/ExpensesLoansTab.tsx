import { Card } from '@/components/ui/card'
import { ExpenseLoanForm } from './ExpenseLoanForm'

export function ExpensesLoansTab() {
  return (
    <div className="max-w-2xl">
      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4">Record Entry</h2>
        <p className="text-sm text-muted-foreground mb-6">
          Record expenses or loan payments. Entries create journal entries in the accounting ledger.
        </p>
        <ExpenseLoanForm />
      </Card>
    </div>
  )
}
