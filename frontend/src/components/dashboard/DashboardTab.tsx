/**
 * Enhanced Dashboard — Hostex-style with occupancy, check-ins/outs, operational KPIs.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LogIn, LogOut, Home, DoorOpen, MessageCircle, CalendarPlus,
  Ban, ClipboardList, Users,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { fetchRealtimeStats, type RealtimeStats } from '@/api/platform'
import { fetchBookings, type Booking } from '@/api/bookings'
import { usePropertyStore } from '@/store/usePropertyStore'

// ── Helpers ─────────────────────────────────────────────────────────
const today = () => new Date().toISOString().slice(0, 10)
const tomorrow = () => {
  const d = new Date(); d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10)
}
function formatDate(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// ── KPI Card ────────────────────────────────────────────────────────
function KpiCard({
  icon: Icon, label, value, color, isLoading,
}: {
  icon: React.ElementType; label: string; value: number; color: string; isLoading: boolean
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border bg-card p-4">
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        {isLoading ? <Skeleton className="h-7 w-10" /> : (
          <p className="text-2xl font-bold">{value}</p>
        )}
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}

// ── Sub-tab config ──────────────────────────────────────────────────
type SubTab = 'check-ins' | 'check-outs' | 'tasks' | 'deposits' | 'new-bookings'
const SUB_TABS: { key: SubTab; label: string }[] = [
  { key: 'check-ins', label: 'Check-ins' },
  { key: 'check-outs', label: 'Check-outs' },
  { key: 'tasks', label: 'Tasks' },
  { key: 'deposits', label: 'Deposits' },
  { key: 'new-bookings', label: 'New Bookings' },
]

// ── Booking row for lists ───────────────────────────────────────────
function BookingRow({ b }: { b: Booking }) {
  return (
    <div className="flex items-center justify-between py-3 px-4 hover:bg-muted/30 transition-colors border-b last:border-b-0">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium shrink-0">
          {(b.guest_name ?? '?')[0]?.toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{b.guest_name || 'Unknown'}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="text-[10px] px-1.5 py-0">{b.platform}</Badge>
            {b.adults > 0 && <span>{b.adults} adult{b.adults !== 1 ? 's' : ''}</span>}
          </div>
        </div>
      </div>
      <div className="text-right shrink-0 ml-4">
        <p className="text-sm font-medium">{formatDate(b.check_in_date)} → {formatDate(b.check_out_date)}</p>
        <p className="text-xs text-muted-foreground">
          {b.booking_state && (
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
              b.booking_state === 'reservation' ? 'bg-blue-100 text-blue-700' :
              b.booking_state === 'checked_in' ? 'bg-emerald-100 text-emerald-700' :
              b.booking_state === 'checked_out' ? 'bg-gray-100 text-gray-600' :
              b.booking_state === 'cancelled' ? 'bg-red-100 text-red-600' :
              'bg-orange-100 text-orange-700'
            }`}>
              {b.booking_state.replace('_', ' ')}
            </span>
          )}
        </p>
      </div>
    </div>
  )
}

// ── Day toggle ──────────────────────────────────────────────────────
type DayMode = 'today' | 'tomorrow'

// ── Main Component ──────────────────────────────────────────────────
export function DashboardTab() {
  const { selectedPropertyId } = usePropertyStore()
  const [dayMode, setDayMode] = useState<DayMode>('today')
  const [subTab, setSubTab] = useState<SubTab>('check-ins')

  const targetDate = dayMode === 'today' ? today() : tomorrow()

  const { data: stats, isLoading: loadingStats } = useQuery<RealtimeStats>({
    queryKey: ['realtime-stats', selectedPropertyId],
    queryFn: () => fetchRealtimeStats(selectedPropertyId),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const { data: bookings = [] } = useQuery({
    queryKey: ['bookings', selectedPropertyId],
    queryFn: () => fetchBookings({ property_id: selectedPropertyId }),
    staleTime: 60_000,
  })

  // Derive lists from bookings
  const checkIns = bookings.filter(b =>
    b.check_in_date === targetDate &&
    (b.booking_state === 'reservation' || !b.booking_state)
  )
  const checkOuts = bookings.filter(b =>
    b.check_out_date === targetDate &&
    b.booking_state === 'checked_in'
  )
  const newBookings = bookings
    .filter(b => b.created_at.slice(0, 10) === today())
    .sort((a, c) => c.created_at.localeCompare(a.created_at))
  const cancelled = bookings
    .filter(b => b.booking_state === 'cancelled' && b.updated_at.slice(0, 10) === today())

  // Unallocated: bookings with no room_id
  const unallocated = bookings.filter(b =>
    !b.room_id && b.booking_state === 'reservation' && b.check_in_date >= today()
  )

  const occupancyText = stats
    ? `${stats.in_stay}/${stats.total_properties}`
    : '—/—'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground text-sm">
            Today's Occupancy Rate: <span className="font-semibold text-foreground">{occupancyText}</span>
          </p>
        </div>
        {/* Day/Month toggle */}
        <div className="flex gap-1 rounded-lg bg-muted p-1">
          {(['today', 'tomorrow'] as DayMode[]).map(d => (
            <button
              key={d}
              onClick={() => setDayMode(d)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium capitalize transition-all ${
                dayMode === d ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <KpiCard icon={LogIn} label="Check-ins" value={stats?.check_ins_today ?? checkIns.length} color="bg-emerald-100 text-emerald-600" isLoading={loadingStats} />
        <KpiCard icon={LogOut} label="Check-outs" value={stats?.check_outs_today ?? checkOuts.length} color="bg-blue-100 text-blue-600" isLoading={loadingStats} />
        <KpiCard icon={Home} label="In-stay" value={stats?.in_stay ?? 0} color="bg-purple-100 text-purple-600" isLoading={loadingStats} />
        <KpiCard icon={DoorOpen} label="Vacant" value={stats?.vacant ?? 0} color="bg-gray-100 text-gray-600" isLoading={loadingStats} />
        <KpiCard icon={MessageCircle} label="Inquiries" value={stats?.inquiries_today ?? 0} color="bg-amber-100 text-amber-600" isLoading={loadingStats} />
        <KpiCard icon={CalendarPlus} label="Bookings" value={stats?.bookings_today ?? newBookings.length} color="bg-teal-100 text-teal-600" isLoading={loadingStats} />
        <KpiCard icon={Ban} label="Cancelled" value={stats?.cancelled_today ?? cancelled.length} color="bg-red-100 text-red-600" isLoading={loadingStats} />
        <KpiCard icon={ClipboardList} label="Tasks" value={stats?.tasks_today ?? 0} color="bg-orange-100 text-orange-600" isLoading={loadingStats} />
      </div>

      {/* Unallocated reservations alert */}
      {unallocated.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/20 px-4 py-3 flex items-center gap-2 text-sm text-amber-700">
          <Users className="h-4 w-4 shrink-0" />
          <span className="font-medium">{unallocated.length} unallocated reservation{unallocated.length !== 1 ? 's' : ''}.</span>
          <span className="text-muted-foreground">Assign rooms to these bookings.</span>
        </div>
      )}

      {/* Sub-tab pills */}
      <div className="flex gap-1 overflow-x-auto rounded-lg bg-muted p-1">
        {SUB_TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setSubTab(t.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-all ${
              subTab === t.key ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Sub-tab content */}
      <div className="rounded-xl border bg-card overflow-hidden">
        {/* Table header */}
        <div className="grid grid-cols-5 gap-2 px-4 py-2 bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground font-medium">
          <span className="col-span-2">Guest</span>
          <span>Property</span>
          <span>Check-in / out</span>
          <span className="text-right">Next booking</span>
        </div>

        {subTab === 'check-ins' && (
          checkIns.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              You don't have any upcoming check-ins at the moment.
            </div>
          ) : checkIns.map(b => <BookingRow key={b.id} b={b} />)
        )}

        {subTab === 'check-outs' && (
          checkOuts.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              No check-outs scheduled for {dayMode}.
            </div>
          ) : checkOuts.map(b => <BookingRow key={b.id} b={b} />)
        )}

        {subTab === 'tasks' && (
          <div className="py-12 text-center text-sm text-muted-foreground">
            No tasks for {dayMode}.
          </div>
        )}

        {subTab === 'deposits' && (
          <div className="py-12 text-center text-sm text-muted-foreground">
            No deposits pending.
          </div>
        )}

        {subTab === 'new-bookings' && (
          newBookings.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              No new bookings today.
            </div>
          ) : newBookings.map(b => <BookingRow key={b.id} b={b} />)
        )}
      </div>
    </div>
  )
}
