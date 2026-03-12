/**
 * Front Desk Tab — Hotel PMS command center.
 *
 * Shows today's arrivals, departures, in-house guests, and a room status grid.
 * Provides one-click check-in, check-out and no-show actions.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  LogIn, LogOut, BedDouble, CheckCircle2,
  RefreshCw, UserCheck, Users, Building2, Sparkles,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { apiFetch } from '@/api/client'
import { fetchRooms, setRoomStatus, type Room } from '@/api/rooms'
import { usePropertyStore } from '@/store/usePropertyStore'

// -------------------------------------------------------------------------
// Types
// -------------------------------------------------------------------------
interface Booking {
  id: number
  guest_name: string
  guest_email: string | null
  guest_phone: string | null
  check_in_date: string
  check_out_date: string
  booking_state: string
  adults: number
  children: number
  room_id: number | null
  net_amount: string
  platform: string
  platform_booking_id: string
}

function today(): string {
  return new Date().toISOString().split('T')[0]
}

function formatDate(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

// -------------------------------------------------------------------------
// Room status config
// -------------------------------------------------------------------------
const ROOM_STATUS_CONFIG: Record<Room['status'], { label: string; dot: string; bg: string; border: string }> = {
  clean: { label: 'Clean', dot: 'bg-emerald-500', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  dirty: { label: 'Dirty', dot: 'bg-amber-500', bg: 'bg-amber-50', border: 'border-amber-200' },
  maintenance: { label: 'Maint.', dot: 'bg-red-500', bg: 'bg-red-50', border: 'border-red-200' },
  out_of_order: { label: 'OOO', dot: 'bg-gray-500', bg: 'bg-gray-100', border: 'border-gray-300' },
}

const BOOKING_STATE_CONFIG: Record<string, { label: string; color: string }> = {
  reservation: { label: 'Reservation', color: 'bg-blue-100 text-blue-700' },
  checked_in: { label: 'In House', color: 'bg-emerald-100 text-emerald-700' },
  checked_out: { label: 'Checked Out', color: 'bg-gray-100 text-gray-600' },
  no_show: { label: 'No Show', color: 'bg-orange-100 text-orange-700' },
  cancelled: { label: 'Cancelled', color: 'bg-red-100 text-red-600' },
}

// stateTransition removed — using direct API functions instead

// -------------------------------------------------------------------------
// Components
// -------------------------------------------------------------------------
function ArrivalCard({ booking, onCheckIn, onNoShow, isLoading }: {
  booking: Booking
  onCheckIn: () => void
  onNoShow: () => void
  isLoading: boolean
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3">
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate">{booking.guest_name || 'Guest'}</p>
        <p className="text-xs text-muted-foreground">
          {formatDate(booking.check_in_date)} → {formatDate(booking.check_out_date)}
          {' · '}{booking.adults + (booking.children || 0)} guest{booking.adults > 1 ? 's' : ''}
        </p>
        {booking.guest_phone && (
          <p className="text-xs text-muted-foreground">{booking.guest_phone}</p>
        )}
      </div>
      <div className="flex gap-2 shrink-0">
        <Button
          size="sm"
          variant="outline"
          className="text-xs h-7"
          onClick={onNoShow}
          disabled={isLoading}
        >
          No Show
        </Button>
        <Button
          size="sm"
          className="text-xs h-7 bg-emerald-600 hover:bg-emerald-700"
          onClick={onCheckIn}
          disabled={isLoading}
        >
          <LogIn className="h-3 w-3 mr-1" />
          Check In
        </Button>
      </div>
    </div>
  )
}

function DepartureCard({ booking, onCheckOut, isLoading }: {
  booking: Booking
  onCheckOut: () => void
  isLoading: boolean
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3">
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate">{booking.guest_name || 'Guest'}</p>
        <p className="text-xs text-muted-foreground">
          Checkout: {formatDate(booking.check_out_date)}
          {' · '}{booking.adults + (booking.children || 0)} guest{booking.adults > 1 ? 's' : ''}
        </p>
      </div>
      <Button
        size="sm"
        className="text-xs h-7 bg-blue-600 hover:bg-blue-700 shrink-0"
        onClick={onCheckOut}
        disabled={isLoading}
      >
        <LogOut className="h-3 w-3 mr-1" />
        Check Out
      </Button>
    </div>
  )
}

function RoomCard({ room, booking, onStatusChange }: {
  room: Room
  booking?: Booking
  onStatusChange: (status: Room['status']) => void
}) {
  const cfg = ROOM_STATUS_CONFIG[room.status]
  const STATUSES: Room['status'][] = ['clean', 'dirty', 'maintenance', 'out_of_order']

  return (
    <div className={`rounded-xl border-2 ${cfg.bg} ${cfg.border} p-3 space-y-2 min-w-0`}>
      <div className="flex items-center justify-between gap-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={`inline-block w-2 h-2 rounded-full ${cfg.dot} shrink-0`} />
          <span className="font-semibold text-sm truncate">{room.number || room.name}</span>
        </div>
        <select
          className="text-xs bg-transparent border-0 cursor-pointer py-0 focus:ring-0 focus:outline-none text-muted-foreground"
          value={room.status}
          onChange={(e) => onStatusChange(e.target.value as Room['status'])}
        >
          {STATUSES.map(s => (
            <option key={s} value={s}>{ROOM_STATUS_CONFIG[s].label}</option>
          ))}
        </select>
      </div>
      <p className="text-xs text-muted-foreground truncate">{room.name}</p>
      {booking ? (
        <div className="text-xs space-y-0.5">
          <p className="font-medium truncate">{booking.guest_name}</p>
          <p className="text-muted-foreground">
            {formatDate(booking.check_in_date)} – {formatDate(booking.check_out_date)}
          </p>
          <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${BOOKING_STATE_CONFIG[booking.booking_state]?.color ?? 'bg-gray-100 text-gray-600'}`}>
            {BOOKING_STATE_CONFIG[booking.booking_state]?.label ?? booking.booking_state}
          </span>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground italic">Vacant</p>
      )}
    </div>
  )
}

// -------------------------------------------------------------------------
// Main Tab
// -------------------------------------------------------------------------
export function FrontDeskTab() {
  const { selectedPropertyId } = usePropertyStore()
  const queryClient = useQueryClient()
  const todayStr = today()

  const { data: allBookings = [], isLoading: loadingBookings } = useQuery({
    queryKey: ['bookings', 'frontdesk', selectedPropertyId],
    queryFn: () => {
      const qs = new URLSearchParams({ limit: '500' })
      if (selectedPropertyId != null) qs.set('property_id', String(selectedPropertyId))
      return apiFetch<Booking[]>(`/bookings?${qs}`)
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const { data: rooms = [], isLoading: loadingRooms } = useQuery({
    queryKey: ['rooms', selectedPropertyId],
    queryFn: () => fetchRooms(selectedPropertyId),
    staleTime: 30_000,
  })

  // Build booking lookup by room_id
  const bookingByRoom = new Map<number, Booking>()
  for (const b of allBookings) {
    if (b.room_id && (b.booking_state === 'checked_in' || b.booking_state === 'reservation')) {
      bookingByRoom.set(b.room_id, b)
    }
  }

  // Filter arrivals & departures
  const arrivals = allBookings.filter(
    b => b.check_in_date === todayStr && b.booking_state === 'reservation'
  )
  const departures = allBookings.filter(
    b => b.check_out_date === todayStr && b.booking_state === 'checked_in'
  )
  const inHouse = allBookings.filter(b => b.booking_state === 'checked_in')
  const reservations = allBookings.filter(b => b.booking_state === 'reservation')

  // Mutations
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set())

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) =>
      apiFetch<Booking>(`/bookings/${id}/${action}`, { method: 'POST' }),
    onMutate: ({ id }) => setPendingIds(prev => new Set(prev).add(id)),
    onSettled: (_, __, { id }) => {
      setPendingIds(prev => { const s = new Set(prev); s.delete(id); return s })
      void queryClient.invalidateQueries({ queryKey: ['bookings'] })
    },
  })

  const roomStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: Room['status'] }) =>
      setRoomStatus(id, status),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['rooms'] }),
  })

  const isLoading = loadingBookings || loadingRooms

  // Summary stats
  const cleanRooms = rooms.filter(r => r.status === 'clean' && r.is_active)
  const dirtyRooms = rooms.filter(r => r.status === 'dirty')
  const maintenanceRooms = rooms.filter(r => r.status === 'maintenance' || r.status === 'out_of_order')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Front Desk</h2>
          <p className="text-muted-foreground text-sm">
            {new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void queryClient.invalidateQueries({ queryKey: ['bookings'] })}>
          <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
          Refresh
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="p-4 space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground">
            <LogIn className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-wide">Arrivals</span>
          </div>
          {isLoading ? <Skeleton className="h-7 w-10" /> : (
            <p className="text-2xl font-bold">{arrivals.length}</p>
          )}
        </Card>
        <Card className="p-4 space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground">
            <LogOut className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-wide">Departures</span>
          </div>
          {isLoading ? <Skeleton className="h-7 w-10" /> : (
            <p className="text-2xl font-bold">{departures.length}</p>
          )}
        </Card>
        <Card className="p-4 space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Users className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-wide">In House</span>
          </div>
          {isLoading ? <Skeleton className="h-7 w-10" /> : (
            <p className="text-2xl font-bold">{inHouse.length}</p>
          )}
        </Card>
        <Card className="p-4 space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground">
            <BedDouble className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-wide">Reserved</span>
          </div>
          {isLoading ? <Skeleton className="h-7 w-10" /> : (
            <p className="text-2xl font-bold">{reservations.length}</p>
          )}
        </Card>
      </div>

      {/* Arrivals + Departures side-by-side */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Arrivals */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <LogIn className="h-4 w-4 text-emerald-600" />
            <h3 className="font-semibold">Today's Arrivals</h3>
            <Badge variant="secondary">{arrivals.length}</Badge>
          </div>
          {loadingBookings ? (
            <div className="space-y-2">{[0,1,2].map(i => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}</div>
          ) : arrivals.length === 0 ? (
            <div className="rounded-lg border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
              No arrivals today
            </div>
          ) : (
            <div className="space-y-2">
              {arrivals.map(b => (
                <ArrivalCard
                  key={b.id}
                  booking={b}
                  isLoading={pendingIds.has(b.id)}
                  onCheckIn={() => actionMutation.mutate({ id: b.id, action: 'check-in' })}
                  onNoShow={() => actionMutation.mutate({ id: b.id, action: 'no-show' })}
                />
              ))}
            </div>
          )}
        </div>

        {/* Departures */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <LogOut className="h-4 w-4 text-blue-600" />
            <h3 className="font-semibold">Today's Departures</h3>
            <Badge variant="secondary">{departures.length}</Badge>
          </div>
          {loadingBookings ? (
            <div className="space-y-2">{[0,1,2].map(i => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}</div>
          ) : departures.length === 0 ? (
            <div className="rounded-lg border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
              No departures today
            </div>
          ) : (
            <div className="space-y-2">
              {departures.map(b => (
                <DepartureCard
                  key={b.id}
                  booking={b}
                  isLoading={pendingIds.has(b.id)}
                  onCheckOut={() => actionMutation.mutate({ id: b.id, action: 'check-out' })}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Room Status Grid */}
      {rooms.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <h3 className="font-semibold">Room Status</h3>
            </div>
            {/* Legend */}
            <div className="hidden sm:flex items-center gap-3 text-xs text-muted-foreground">
              {Object.entries(ROOM_STATUS_CONFIG).map(([k, v]) => (
                <span key={k} className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${v.dot}`} />
                  {v.label}
                </span>
              ))}
            </div>
          </div>
          {/* Room status summary pills */}
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="px-2 py-1 rounded-full bg-emerald-100 text-emerald-700 font-medium">
              <Sparkles className="inline h-3 w-3 mr-1" />{cleanRooms.length} Clean
            </span>
            <span className="px-2 py-1 rounded-full bg-amber-100 text-amber-700 font-medium">
              {dirtyRooms.length} Dirty
            </span>
            <span className="px-2 py-1 rounded-full bg-red-100 text-red-700 font-medium">
              {maintenanceRooms.length} Maintenance/OOO
            </span>
            <span className="px-2 py-1 rounded-full bg-blue-100 text-blue-700 font-medium">
              <UserCheck className="inline h-3 w-3 mr-1" />{inHouse.length} Occupied
            </span>
          </div>
          {loadingRooms ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {rooms.filter(r => r.is_active).map(room => (
                <RoomCard
                  key={room.id}
                  room={room}
                  booking={room.id != null ? bookingByRoom.get(room.id) : undefined}
                  onStatusChange={(status) => roomStatusMutation.mutate({ id: room.id, status })}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* In-house list */}
      {inHouse.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <h3 className="font-semibold">Currently In House</h3>
            <Badge variant="secondary">{inHouse.length}</Badge>
          </div>
          <div className="overflow-x-auto rounded-xl border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="text-left px-4 py-2.5">Guest</th>
                  <th className="text-left px-4 py-2.5">Check-in</th>
                  <th className="text-left px-4 py-2.5">Check-out</th>
                  <th className="text-left px-4 py-2.5 hidden sm:table-cell">Guests</th>
                  <th className="text-right px-4 py-2.5">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {inHouse.map(b => (
                  <tr key={b.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 font-medium">{b.guest_name}</td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDate(b.check_in_date)}</td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDate(b.check_out_date)}</td>
                    <td className="px-4 py-3 text-muted-foreground hidden sm:table-cell">{b.adults + (b.children || 0)}</td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-xs h-7"
                        disabled={pendingIds.has(b.id)}
                        onClick={() => actionMutation.mutate({ id: b.id, action: 'check-out' })}
                      >
                        <LogOut className="h-3 w-3 mr-1" />Check Out
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* No rooms configured */}
      {!loadingRooms && rooms.length === 0 && (
        <div className="rounded-xl border border-dashed p-8 text-center space-y-2">
          <Building2 className="h-8 w-8 text-muted-foreground mx-auto" />
          <p className="text-sm font-medium">No rooms configured</p>
          <p className="text-xs text-muted-foreground">Add rooms in the Setup → Rooms tab to see the room status grid.</p>
        </div>
      )}
    </div>
  )
}
