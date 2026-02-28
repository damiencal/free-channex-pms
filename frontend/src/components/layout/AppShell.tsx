import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Header } from './Header'
import { apiFetch } from '@/api/client'
import { usePropertyStore } from '@/store/usePropertyStore'

interface ActionsResponse {
  actions: unknown[]
  total: number
}

type TabValue = 'home' | 'calendar' | 'reports' | 'actions'
const VALID_TABS: TabValue[] = ['home', 'calendar', 'reports', 'actions']

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

  function handleTabChange(value: string) {
    setSearchParams(value === 'home' ? {} : { tab: value })
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />

      <main className="flex-1 p-4 md:p-6">
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          <TabsList className="mb-6">
            <TabsTrigger value="home">Home</TabsTrigger>
            <TabsTrigger value="calendar">Calendar</TabsTrigger>
            <TabsTrigger value="reports">Reports</TabsTrigger>
            <TabsTrigger value="actions" className="gap-2">
              Actions
              {pendingCount > 0 && (
                <Badge variant="destructive" className="h-5 min-w-5 text-xs">
                  {pendingCount}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="home">
            {/* HomeTab is populated in Task 2 — imported lazily to avoid circular deps */}
            <HomeTabSlot />
          </TabsContent>

          <TabsContent value="calendar">
            <div className="text-muted-foreground py-12 text-center">
              Calendar view — coming soon
            </div>
          </TabsContent>

          <TabsContent value="reports">
            <div className="text-muted-foreground py-12 text-center">
              Reports view — coming soon
            </div>
          </TabsContent>

          <TabsContent value="actions">
            <div className="text-muted-foreground py-12 text-center">
              Actions view — coming soon
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

/**
 * Slot for the Home tab — defined here to keep AppShell self-contained.
 * Task 2 will replace this placeholder with the real HomeTab component.
 */
function HomeTabSlot() {
  return (
    <div id="home-tab-slot">
      {/* HomeTab will be rendered here after Task 2 */}
    </div>
  )
}
