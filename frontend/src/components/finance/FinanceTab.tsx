import { useSearchParams } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { TransactionsTab } from './TransactionsTab'
import { ExpensesLoansTab } from './ExpensesLoansTab'
import { ReconciliationTab } from './ReconciliationTab'

type FinanceSubTab = 'transactions' | 'expenses-loans' | 'reconciliation'
const VALID_SUBTABS: FinanceSubTab[] = ['transactions', 'expenses-loans', 'reconciliation']

function isValidSubTab(value: string | null): value is FinanceSubTab {
  return VALID_SUBTABS.includes(value as FinanceSubTab)
}

export function FinanceTab() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawSubTab = searchParams.get('ftab')
  const activeSubTab: FinanceSubTab = isValidSubTab(rawSubTab) ? rawSubTab : 'transactions'

  function handleSubTabChange(value: string) {
    const newParams = new URLSearchParams(searchParams)
    if (value === 'transactions') {
      newParams.delete('ftab')
    } else {
      newParams.set('ftab', value)
    }
    setSearchParams(newParams)
  }

  return (
    <div className="space-y-4">
      <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="transactions">Transactions</TabsTrigger>
            <TabsTrigger value="expenses-loans">Expenses & Loans</TabsTrigger>
            <TabsTrigger value="reconciliation">Reconciliation</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="transactions">
          <TransactionsTab />
        </TabsContent>
        <TabsContent value="expenses-loans">
          <ExpensesLoansTab />
        </TabsContent>
        <TabsContent value="reconciliation">
          <ReconciliationTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
