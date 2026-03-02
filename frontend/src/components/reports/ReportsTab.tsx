import { useSearchParams } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { PLTab } from './PLTab'
import { BalanceSheetTab } from './BalanceSheetTab'
import { IncomeStatementTab } from './IncomeStatementTab'

type ReportsSubTab = 'pl' | 'balance-sheet' | 'income-statement'
const VALID_SUBTABS: ReportsSubTab[] = ['pl', 'balance-sheet', 'income-statement']

function isValidSubTab(value: string | null): value is ReportsSubTab {
  return VALID_SUBTABS.includes(value as ReportsSubTab)
}

export function ReportsTab() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawSubTab = searchParams.get('rtab')
  const activeSubTab: ReportsSubTab = isValidSubTab(rawSubTab) ? rawSubTab : 'pl'

  function handleSubTabChange(value: string) {
    const newParams = new URLSearchParams(searchParams)
    if (value === 'pl') {
      newParams.delete('rtab')
    } else {
      newParams.set('rtab', value)
    }
    setSearchParams(newParams)
  }

  return (
    <div className="space-y-4">
      <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="pl">P&amp;L</TabsTrigger>
            <TabsTrigger value="balance-sheet">Balance Sheet</TabsTrigger>
            <TabsTrigger value="income-statement">Income Statement</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="pl">
          <PLTab />
        </TabsContent>
        <TabsContent value="balance-sheet">
          <BalanceSheetTab />
        </TabsContent>
        <TabsContent value="income-statement">
          <IncomeStatementTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
