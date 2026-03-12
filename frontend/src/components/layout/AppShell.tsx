import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Header } from './Header'
import { HomeTab } from '@/components/home/HomeTab'
import { CalendarTab } from '@/components/calendar/CalendarTab'
import { InboxTab } from '@/components/inbox/InboxTab'
import { TasksTab } from '@/components/tasks/TasksTab'
import { PriceTab } from '@/components/price/PriceTab'
import { ReservationsTab } from '@/components/reservations/ReservationsTab'
import { ReviewsTab } from '@/components/reviews/ReviewsTab'
import { FrontDeskTab } from '@/components/frontdesk/FrontDeskTab'
import { GuestsTab } from '@/components/guests/GuestsTab'
import { InvoicesTab } from '@/components/invoices/InvoicesTab'
import { RoomsTab } from '@/components/rooms/RoomsTab'
import { RatesTab } from '@/components/rates/RatesTab'
import { NightAuditTab } from '@/components/nightaudit/NightAuditTab'
import { DashboardTab } from '@/components/dashboard/DashboardTab'
import { PropertiesTab } from '@/components/properties/PropertiesTab'
import { AutomationTab } from '@/components/automation/AutomationTab'
import { BookingSiteTab } from '@/components/booking-site/BookingSiteTab'
import { MetricsTab } from '@/components/metrics/MetricsTab'
import { ConnectedAccountsTab } from '@/components/connected-accounts/ConnectedAccountsTab'
import { SettingsTab } from '@/components/settings/SettingsTab'
import { PricingTab } from '@/components/pricing/PricingTab'
import { AnalyticsTab } from '@/components/analytics/AnalyticsTab'
import { MarketTab } from '@/components/market/MarketTab'
import { EstimatorTab } from '@/components/estimator/EstimatorTab'
import { OptimizerTab } from '@/components/optimizer/OptimizerTab'
import { apiFetch } from '@/api/client'
import { usePropertyStore } from '@/store/usePropertyStore'
import { useAuth } from '@/store/useAuth'

type TabValue =
  | 'home' | 'inbox' | 'calendar' | 'price' | 'reservations' | 'tasks' | 'reviews'
  | 'frontdesk' | 'guests' | 'invoices' | 'rooms' | 'rates' | 'nightaudit'
  | 'properties' | 'automation' | 'bookingsite' | 'metrics' | 'accounts' | 'settings'
  | 'pricing' | 'analytics' | 'market' | 'estimator' | 'optimizer'
const VALID_TABS: TabValue[] = [
  'home', 'inbox', 'calendar', 'price', 'reservations', 'tasks', 'reviews',
  'frontdesk', 'guests', 'invoices', 'rooms', 'rates', 'nightaudit',
  'properties', 'automation', 'bookingsite', 'metrics', 'accounts', 'settings',
  'pricing', 'analytics', 'market', 'estimator', 'optimizer',
]

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

  // Inbox unread badge
  const { data: inboxThreads } = useQuery<{ unread_count: number }[]>({
    queryKey: ['inbox', 'threads', selectedPropertyId],
    queryFn: async () => {
      const qs = selectedPropertyId != null ? `?property_id=${selectedPropertyId}` : ''
      return apiFetch<{ unread_count: number }[]>(`/inbox/threads${qs}`)
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
  })
  const inboxUnread = (inboxThreads ?? []).reduce((sum, t) => sum + (t.unread_count ?? 0), 0)

  const { logout, user } = useAuth()

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
          {/* Scrollable on mobile so all tabs are reachable without wrapping */}
          <div className="mb-6 overflow-x-auto print:hidden">
            <TabsList>
              <TabsTrigger value="home">Dashboard</TabsTrigger>
              <TabsTrigger value="inbox" className="gap-2">
                Inbox
                {inboxUnread > 0 && (
                  <Badge variant="destructive" className="h-5 min-w-5 text-xs px-1.5">
                    {inboxUnread}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="calendar">Calendar</TabsTrigger>
              <TabsTrigger value="price">Price</TabsTrigger>
              <TabsTrigger value="reservations">Reservations</TabsTrigger>
              <TabsTrigger value="tasks">Tasks</TabsTrigger>
              <TabsTrigger value="reviews">Reviews</TabsTrigger>
              <TabsTrigger value="frontdesk">Front Desk</TabsTrigger>
              <TabsTrigger value="guests">Guests</TabsTrigger>
              <TabsTrigger value="invoices">Invoices</TabsTrigger>
              <TabsTrigger value="rooms">Rooms</TabsTrigger>
              <TabsTrigger value="rates">Rates</TabsTrigger>
              <TabsTrigger value="nightaudit">Night Audit</TabsTrigger>
              <TabsTrigger value="properties">Properties</TabsTrigger>
              <TabsTrigger value="automation">Automation</TabsTrigger>
              <TabsTrigger value="bookingsite">Booking Site</TabsTrigger>
              <TabsTrigger value="metrics">Metrics</TabsTrigger>
              <TabsTrigger value="accounts">Accounts</TabsTrigger>
              <TabsTrigger value="settings">Settings</TabsTrigger>
              <TabsTrigger value="pricing">Dynamic Pricing</TabsTrigger>
              <TabsTrigger value="analytics">Analytics</TabsTrigger>
              <TabsTrigger value="market">Market</TabsTrigger>
              <TabsTrigger value="estimator">Estimator</TabsTrigger>
              <TabsTrigger value="optimizer">Optimizer</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="home">
            <div className="space-y-8">
              <DashboardTab />
              <HomeTab />
            </div>
          </TabsContent>

          <TabsContent value="inbox">
            <InboxTab />
          </TabsContent>

          <TabsContent value="calendar">
            <CalendarTab />
          </TabsContent>

          <TabsContent value="price">
            <PriceTab />
          </TabsContent>

          <TabsContent value="reservations">
            <ReservationsTab />
          </TabsContent>

          <TabsContent value="tasks">
            <TasksTab />
          </TabsContent>

          <TabsContent value="reviews">
            <ReviewsTab />
          </TabsContent>

          <TabsContent value="frontdesk">
            <FrontDeskTab />
          </TabsContent>

          <TabsContent value="guests">
            <GuestsTab />
          </TabsContent>

          <TabsContent value="invoices">
            <InvoicesTab />
          </TabsContent>

          <TabsContent value="rooms">
            <RoomsTab />
          </TabsContent>

          <TabsContent value="rates">
            <RatesTab />
          </TabsContent>

          <TabsContent value="nightaudit">
            <NightAuditTab />
          </TabsContent>

          <TabsContent value="properties">
            <PropertiesTab />
          </TabsContent>

          <TabsContent value="automation">
            <AutomationTab />
          </TabsContent>

          <TabsContent value="bookingsite">
            <BookingSiteTab />
          </TabsContent>

          <TabsContent value="metrics">
            <MetricsTab />
          </TabsContent>

          <TabsContent value="accounts">
            <ConnectedAccountsTab />
          </TabsContent>

          <TabsContent value="settings">
            <SettingsTab />
          </TabsContent>

          <TabsContent value="pricing">
            <PricingTab />
          </TabsContent>

          <TabsContent value="analytics">
            <AnalyticsTab />
          </TabsContent>

          <TabsContent value="market">
            <MarketTab />
          </TabsContent>

          <TabsContent value="estimator">
            <EstimatorTab />
          </TabsContent>

          <TabsContent value="optimizer">
            <OptimizerTab />
          </TabsContent>
        </Tabs>

        {user && (
          <div className="fixed bottom-4 right-4 print:hidden">
            <button
              onClick={logout}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Sign out ({user.email})
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

