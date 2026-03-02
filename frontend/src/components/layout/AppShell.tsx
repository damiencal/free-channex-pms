import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Header } from './Header'
import { HomeTab } from '@/components/home/HomeTab'
import { CalendarTab } from '@/components/calendar/CalendarTab'
import { ActionsTab } from '@/components/actions/ActionsTab'
import { ReportsTab } from '@/components/reports/ReportsTab'
import { QueryTab } from '@/components/query/QueryTab'
import { FinanceTab } from '@/components/finance/FinanceTab'
import { apiFetch } from '@/api/client'
import { usePropertyStore } from '@/store/usePropertyStore'
import { useFinanceSummary } from '@/hooks/useFinanceSummary'

interface ActionsResponse {
  actions: unknown[]
  total: number
}

interface HealthResponse {
  status: string
  ollama: string  // 'available' | 'unavailable'
}

type TabValue = 'home' | 'calendar' | 'reports' | 'actions' | 'finance' | 'query'
const VALID_TABS: TabValue[] = ['home', 'calendar', 'reports', 'actions', 'finance', 'query']

function isValidTab(value: string | null): value is TabValue {
  return VALID_TABS.includes(value as TabValue)
}

/**
 * Top-level app shell: header + tab navigation.
 * Active tab synced with ?tab= URL search param for deep linking.
 */
export function AppShell() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get('tab')
  const activeTab: TabValue = isValidTab(rawTab) ? rawTab : 'home'

  const { selectedPropertyId } = usePropertyStore()

  // Poll /health every 30 seconds to gate the Query tab on Ollama availability
  const { data: healthData } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: async () => {
      const res = await fetch('/health')
      if (!res.ok) return { status: 'degraded', ollama: 'unavailable' }
      return res.json() as Promise<HealthResponse>
    },
    refetchInterval: 30_000,
  })
  const ollamaAvailable = healthData?.ollama === 'available'

  // Fetch actions total count for the badge on the Actions tab
  const { data: actionsData } = useQuery<ActionsResponse>({
    queryKey: ['dashboard', 'actions', selectedPropertyId],
    queryFn: () => {
      const params = selectedPropertyId !== null ? `?property_id=${selectedPropertyId}` : ''
      return apiFetch<ActionsResponse>(`/dashboard/actions${params}`)
    },
    staleTime: 5 * 60 * 1000,
  })

  const pendingCount = actionsData?.total ?? 0

  // Finance badge: sum of uncategorized transactions + unreconciled bookings
  const { data: financeSummary } = useFinanceSummary()
  const financeBadgeCount = (financeSummary?.uncategorized_count ?? 0)
    + (financeSummary?.unreconciled_count ?? 0)

  function handleTabChange(value: string) {
    setSearchParams(value === 'home' ? {} : { tab: value })
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <div className="print:hidden">
        <Header />
      </div>

      <main className="flex-1 p-4 md:p-6">
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          {/* Scrollable on mobile so all 4 tabs are reachable without wrapping */}
          <div className="mb-6 overflow-x-auto print:hidden">
            <TabsList>
              <TabsTrigger value="home">Home</TabsTrigger>
              <TabsTrigger value="calendar">Calendar</TabsTrigger>
              <TabsTrigger value="reports">Reports</TabsTrigger>
              <TabsTrigger value="actions" className="gap-2">
                Actions
                {pendingCount > 0 && (
                  <Badge variant="destructive" className="h-5 min-w-5 text-xs px-1.5">
                    {pendingCount}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="finance" className="gap-2">
                Finance
                {financeBadgeCount > 0 && (
                  <Badge variant="destructive" className="h-5 min-w-5 text-xs px-1.5">
                    {financeBadgeCount}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger
                value="query"
                disabled={!ollamaAvailable}
                className={!ollamaAvailable ? 'opacity-50' : ''}
              >
                Query
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="home">
            <HomeTab />
          </TabsContent>

          <TabsContent value="calendar">
            <CalendarTab />
          </TabsContent>

          <TabsContent value="reports">
            <ReportsTab />
          </TabsContent>

          <TabsContent value="actions">
            <ActionsTab />
          </TabsContent>

          <TabsContent value="finance">
            <FinanceTab />
          </TabsContent>

          <TabsContent value="query">
            <QueryTab disabled={!ollamaAvailable} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

