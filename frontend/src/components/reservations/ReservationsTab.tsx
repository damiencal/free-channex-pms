import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, LogIn, LogOut, Plus, ChevronLeft, Pencil, Ban, UserX, Trash2, ClipboardList } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { EmptyState } from '@/components/shared/EmptyState'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  fetchBookings, checkInBooking, checkOutBooking, createManualBooking,
  updateBooking, cancelBooking, noShowBooking, deleteBooking, fetchBookingAuditLog,
  type Booking,
} from '@/api/bookings'
import { fetchProperties, type Property } from '@/api/platform'
import { usePropertyStore } from '@/store/usePropertyStore'

const BOOKING_STATE_CONFIG: Record<string, { label: string; color: string }> = {
  reservation: { label: 'Reserved', color: 'bg-blue-100 text-blue-700 border-blue-200' },
  checked_in:  { label: 'In House', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  checked_out: { label: 'Checked Out', color: 'bg-gray-100 text-gray-600 border-gray-200' },
  no_show:     { label: 'No Show', color: 'bg-orange-100 text-orange-700 border-orange-200' },
  cancelled:   { label: 'Cancelled', color: 'bg-red-100 text-red-600 border-red-200' },
}

const PLATFORM_COLORS: Record<string, string> = {
  airbnb: 'bg-rose-100 text-rose-700 border-rose-200',
  booking: 'bg-blue-100 text-blue-700 border-blue-200',
  vrbo: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  manual: 'bg-muted text-muted-foreground border-border',
}

function platformBadgeClass(platform: string) {
  return PLATFORM_COLORS[platform.toLowerCase()] ?? 'bg-muted text-muted-foreground border-border'
}

function formatDate(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatCurrency(value: string) {
  const num = parseFloat(value)
  if (isNaN(num)) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}

function BookingRow({ booking, onClick }: { booking: Booking; onClick: () => void }) {
  const qc = useQueryClient()
  const nights = Math.round(
    (new Date(booking.check_out_date).getTime() - new Date(booking.check_in_date).getTime()) /
      (1000 * 60 * 60 * 24),
  )

  const isUnknown = !booking.guest_name || booking.guest_name === 'Unknown'
  const stateConfig = BOOKING_STATE_CONFIG[booking.booking_state] ?? BOOKING_STATE_CONFIG.reservation

  const checkInMut = useMutation({
    mutationFn: () => checkInBooking(booking.id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['bookings'] }),
  })
  const checkOutMut = useMutation({
    mutationFn: () => checkOutBooking(booking.id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['bookings'] }),
  })

  return (
    <div
      className="rounded-lg border bg-card p-4 flex flex-col sm:flex-row sm:items-center gap-3 cursor-pointer hover:bg-muted/40 transition-colors"
      onClick={onClick}
    >
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <p className={`font-medium text-sm ${isUnknown ? 'text-muted-foreground italic' : ''}`}>
            {isUnknown ? 'Guest name pending' : booking.guest_name}
          </p>
          <Badge variant="outline" className={`text-xs ${platformBadgeClass(booking.platform)}`}>
            {booking.platform}
          </Badge>
          {booking.booking_state && (
            <Badge variant="outline" className={`text-xs ${stateConfig.color}`}>
              {stateConfig.label}
            </Badge>
          )}
        </div>
        {booking.guest_email && (
          <p className="text-xs text-muted-foreground truncate">{booking.guest_email}</p>
        )}
        {booking.guest_phone && (
          <p className="text-xs text-muted-foreground">{booking.guest_phone}</p>
        )}
        <p className="text-xs text-muted-foreground font-mono">
          Ref: {booking.platform_booking_id}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground shrink-0">
        <div className="text-center">
          <p className="text-xs uppercase tracking-wide mb-0.5">Check-in</p>
          <p className="text-foreground font-medium">{formatDate(booking.check_in_date)}</p>
        </div>
        <div className="text-center">
          <p className="text-xs uppercase tracking-wide mb-0.5">Check-out</p>
          <p className="text-foreground font-medium">{formatDate(booking.check_out_date)}</p>
        </div>
        <div className="text-center">
          <p className="text-xs uppercase tracking-wide mb-0.5">Nights</p>
          <p className="text-foreground font-medium">{nights}</p>
        </div>
        <div className="text-center">
          <p className="text-xs uppercase tracking-wide mb-0.5">Amount</p>
          <p className="text-foreground font-medium">{formatCurrency(booking.net_amount)}</p>
        </div>
        {booking.booking_state === 'reservation' && (
          <Button
            size="sm"
            className="bg-emerald-600 hover:bg-emerald-700 text-white h-8"
            onClick={(e) => { e.stopPropagation(); checkInMut.mutate() }}
            disabled={checkInMut.isPending}
          >
            <LogIn className="h-3.5 w-3.5 mr-1" />Check In
          </Button>
        )}
        {booking.booking_state === 'checked_in' && (
          <Button
            size="sm"
            variant="outline"
            className="h-8"
            onClick={(e) => { e.stopPropagation(); checkOutMut.mutate() }}
            disabled={checkOutMut.isPending}
          >
            <LogOut className="h-3.5 w-3.5 mr-1" />Check Out
          </Button>
        )}
      </div>
    </div>
  )
}

function ReservationsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="rounded-lg border bg-card p-4 flex items-center gap-4">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-56" />
          </div>
          <div className="flex gap-6">
            {Array.from({ length: 4 }, (_, j) => (
              <div key={j} className="space-y-1 text-center">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-20" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Status filter tabs ──────────────────────────────────────────────
const STATUS_FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'reservation', label: 'Pending' },
  { key: 'checked_in', label: 'In-stay' },
  { key: 'checked_out', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
  { key: 'no_show', label: 'No Show' },
] as const
type StatusFilter = (typeof STATUS_FILTERS)[number]['key']

// ── Edit Booking Dialog ─────────────────────────────────────────────
function EditBookingDialog({
  booking,
  open,
  onClose,
}: {
  booking: Booking
  open: boolean
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    guest_name: booking.guest_name,
    guest_email: booking.guest_email ?? '',
    check_in_date: booking.check_in_date,
    check_out_date: booking.check_out_date,
    net_amount: booking.net_amount,
    notes: booking.notes ?? '',
  })
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const mut = useMutation({
    mutationFn: () => updateBooking(booking.id, {
      guest_name: form.guest_name.trim(),
      guest_email: form.guest_email || null,
      check_in_date: form.check_in_date,
      check_out_date: form.check_out_date,
      net_amount: parseFloat(form.net_amount) || 0,
      notes: form.notes || null,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bookings'] })
      onClose()
    },
  })

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Reservation</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1">
            <Label>Guest Name *</Label>
            <Input value={form.guest_name} onChange={(e) => set('guest_name', e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>Guest Email</Label>
            <Input type="email" value={form.guest_email} onChange={(e) => set('guest_email', e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Check-in *</Label>
              <Input type="date" value={form.check_in_date} onChange={(e) => set('check_in_date', e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>Check-out *</Label>
              <Input type="date" value={form.check_out_date} onChange={(e) => set('check_out_date', e.target.value)} />
            </div>
          </div>
          <div className="space-y-1">
            <Label>Total Amount ($)</Label>
            <Input type="number" min="0" step="0.01" value={form.net_amount} onChange={(e) => set('net_amount', e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>Notes</Label>
            <Input value={form.notes} onChange={(e) => set('notes', e.target.value)} placeholder="Optional notes…" />
          </div>
          {mut.isError && <p className="text-sm text-destructive">Failed to update reservation.</p>}
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mut.mutate()} disabled={mut.isPending || !form.guest_name.trim()}>
            {mut.isPending ? 'Saving…' : 'Save Changes'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ── Booking Detail Panel ────────────────────────────────────────────
function BookingDetail({
  booking,
  onBack,
  properties,
}: {
  booking: Booking
  onBack: () => void
  properties: Property[]
}) {
  const qc = useQueryClient()
  const [showEdit, setShowEdit] = useState(false)

  const stateConfig = BOOKING_STATE_CONFIG[booking.booking_state] ?? BOOKING_STATE_CONFIG.reservation
  const propName = properties.find((p) => p.id === booking.property_id)?.name ?? `Property #${booking.property_id}`
  const nights = Math.round(
    (new Date(booking.check_out_date).getTime() - new Date(booking.check_in_date).getTime()) /
      (1000 * 60 * 60 * 24),
  )

  const { data: auditLog } = useQuery({
    queryKey: ['booking-audit', booking.id],
    queryFn: () => fetchBookingAuditLog(booking.id),
    staleTime: 60 * 1000,
  })

  const checkInMut = useMutation({
    mutationFn: () => checkInBooking(booking.id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['bookings'] }),
  })
  const checkOutMut = useMutation({
    mutationFn: () => checkOutBooking(booking.id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['bookings'] }),
  })
  const noShowMut = useMutation({
    mutationFn: () => noShowBooking(booking.id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['bookings'] }),
  })
  const cancelMut = useMutation({
    mutationFn: () => cancelBooking(booking.id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['bookings'] }),
  })
  const deleteMut = useMutation({
    mutationFn: () => deleteBooking(booking.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bookings'] })
      onBack()
    },
  })

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack} className="gap-1">
            <ChevronLeft className="h-4 w-4" />Back
          </Button>
          <h2 className="text-lg font-semibold truncate">{booking.guest_name || 'Guest name pending'}</h2>
          <Badge variant="outline" className={`text-xs ${platformBadgeClass(booking.platform)}`}>
            {booking.platform}
          </Badge>
          <Badge variant="outline" className={`text-xs ${stateConfig.color}`}>
            {stateConfig.label}
          </Badge>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {booking.booking_state === 'reservation' && (
            <>
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white h-8"
                onClick={() => checkInMut.mutate()} disabled={checkInMut.isPending}>
                <LogIn className="h-3.5 w-3.5 mr-1" />Check In
              </Button>
              <Button size="sm" variant="outline" className="h-8"
                onClick={() => noShowMut.mutate()} disabled={noShowMut.isPending}>
                <UserX className="h-3.5 w-3.5 mr-1" />No Show
              </Button>
            </>
          )}
          {booking.booking_state === 'checked_in' && (
            <Button size="sm" variant="outline" className="h-8"
              onClick={() => checkOutMut.mutate()} disabled={checkOutMut.isPending}>
              <LogOut className="h-3.5 w-3.5 mr-1" />Check Out
            </Button>
          )}
          {(booking.booking_state === 'reservation' || booking.booking_state === 'checked_in') && (
            <Button size="sm" variant="outline" className="h-8 text-destructive border-destructive/30 hover:bg-destructive/10"
              onClick={() => cancelMut.mutate()} disabled={cancelMut.isPending}>
              <Ban className="h-3.5 w-3.5 mr-1" />Cancel
            </Button>
          )}
          <Button size="sm" variant="outline" className="h-8" onClick={() => setShowEdit(true)}>
            <Pencil className="h-3.5 w-3.5 mr-1" />Edit
          </Button>
          <Button size="sm" variant="outline" className="h-8 text-destructive border-destructive/30 hover:bg-destructive/10"
            onClick={() => { if (confirm('Delete this reservation?')) deleteMut.mutate() }}
            disabled={deleteMut.isPending}>
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Detail cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Guest Info */}
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">Guest Information</h3>
          <div className="space-y-2 text-sm">
            <div><span className="text-muted-foreground">Name: </span><span className="font-medium">{booking.guest_name || '—'}</span></div>
            <div><span className="text-muted-foreground">Email: </span><span>{booking.guest_email || '—'}</span></div>
            <div><span className="text-muted-foreground">Phone: </span><span>{booking.guest_phone || '—'}</span></div>
            <div><span className="text-muted-foreground">Adults: </span><span>{booking.adults}</span>
              {booking.children > 0 && <span className="text-muted-foreground ml-2">Children: </span>}
              {booking.children > 0 && <span>{booking.children}</span>}
            </div>
          </div>
        </div>

        {/* Booking Info */}
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">Booking Details</h3>
          <div className="space-y-2 text-sm">
            <div><span className="text-muted-foreground">Reference: </span><span className="font-mono">{booking.platform_booking_id}</span></div>
            <div><span className="text-muted-foreground">Property: </span><span>{propName}</span></div>
            <div><span className="text-muted-foreground">Check-in: </span><span className="font-medium">{formatDate(booking.check_in_date)}</span></div>
            <div><span className="text-muted-foreground">Check-out: </span><span className="font-medium">{formatDate(booking.check_out_date)}</span></div>
            <div><span className="text-muted-foreground">Nights: </span><span>{nights}</span></div>
            <div><span className="text-muted-foreground">Amount: </span><span className="font-medium">{formatCurrency(booking.net_amount)}</span></div>
          </div>
        </div>
      </div>

      {/* Notes */}
      {booking.notes && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wide mb-2">Notes</h3>
          <p className="text-sm">{booking.notes}</p>
        </div>
      )}

      {/* Audit Log */}
      {auditLog && auditLog.length > 0 && (
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <ClipboardList className="h-4 w-4 text-muted-foreground" />
            <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">Activity Log</h3>
          </div>
          <div className="space-y-2">
            {auditLog.map((entry) => (
              <div key={entry.id} className="flex items-start gap-3 text-sm">
                <span className="text-muted-foreground shrink-0 text-xs pt-0.5">
                  {new Date(entry.created_at).toLocaleString()}
                </span>
                <span className="font-medium capitalize">{entry.action.replace(/_/g, ' ')}</span>
                {entry.notes && <span className="text-muted-foreground">— {entry.notes}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {showEdit && (
        <EditBookingDialog
          booking={booking}
          open
          onClose={() => setShowEdit(false)}
        />
      )}
    </div>
  )
}



// ── New Reservation Dialog ──────────────────────────────────────────
function NewReservationDialog({
  open,
  onClose,
  defaultPropertyId,
  properties,
}: {
  open: boolean
  onClose: () => void
  defaultPropertyId: number | null
  properties: Property[]
}) {
  const qc = useQueryClient()
  const today = new Date().toISOString().slice(0, 10)
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)

  const [form, setForm] = useState({
    property_id: defaultPropertyId ?? (properties[0]?.id ?? 0),
    guest_name: '',
    guest_email: '',
    check_in_date: today,
    check_out_date: tomorrow,
    net_amount: '',
    notes: '',
  })

  // Sync property_id once properties load (handles "All Properties" race condition)
  useEffect(() => {
    if (form.property_id === 0 && properties.length > 0) {
      setForm((f) => ({ ...f, property_id: defaultPropertyId ?? properties[0].id }))
    }
  }, [properties, defaultPropertyId])

  const mut = useMutation({
    mutationFn: () => createManualBooking({
      property_id: form.property_id,
      guest_name: form.guest_name.trim(),
      guest_email: form.guest_email || undefined,
      check_in_date: form.check_in_date,
      check_out_date: form.check_out_date,
      net_amount: parseFloat(form.net_amount) || 0,
      notes: form.notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bookings'] })
      onClose()
    },
  })

  const set = (k: keyof typeof form, v: string | number) =>
    setForm((f) => ({ ...f, [k]: v }))

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>New Reservation</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          {properties.length > 0 && (
            <div className="space-y-1">
              <Label>Property *</Label>
              <select
                className="w-full border rounded h-9 px-2 text-sm bg-background"
                value={form.property_id}
                onChange={(e) => set('property_id', Number(e.target.value))}
              >
                {properties.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
          )}
          <div className="space-y-1">
            <Label>Guest Name *</Label>
            <Input
              placeholder="John Smith"
              value={form.guest_name}
              onChange={(e) => set('guest_name', e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>Guest Email</Label>
            <Input
              type="email"
              placeholder="guest@example.com"
              value={form.guest_email}
              onChange={(e) => set('guest_email', e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Check-in *</Label>
              <Input
                type="date"
                value={form.check_in_date}
                onChange={(e) => set('check_in_date', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>Check-out *</Label>
              <Input
                type="date"
                value={form.check_out_date}
                onChange={(e) => set('check_out_date', e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-1">
            <Label>Total Amount ($)</Label>
            <Input
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00"
              value={form.net_amount}
              onChange={(e) => set('net_amount', e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>Notes</Label>
            <Input
              placeholder="Optional notes..."
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
            />
          </div>
          {mut.isError && (
            <p className="text-sm text-destructive">Failed to create reservation.</p>
          )}
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => mut.mutate()}
            disabled={mut.isPending || !form.guest_name.trim() || !form.check_in_date || !form.check_out_date}
          >
            {mut.isPending ? 'Creating…' : 'Create Reservation'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function ReservationsTab() {
  const { selectedPropertyId } = usePropertyStore()
  const [search, setSearch] = useState('')
  const [platform, setPlatform] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [showNewDialog, setShowNewDialog] = useState(false)
  const [selectedBookingId, setSelectedBookingId] = useState<number | null>(null)

  const { data: bookings, isLoading, error } = useQuery({
    queryKey: ['bookings', selectedPropertyId],
    queryFn: () => fetchBookings({ property_id: selectedPropertyId }),
    staleTime: 5 * 60 * 1000,
  })

  const { data: properties = [] } = useQuery({
    queryKey: ['properties'],
    queryFn: fetchProperties,
    staleTime: 10 * 60 * 1000,
  })

  const platforms = ['all', ...Array.from(new Set((bookings ?? []).map((b) => b.platform.toLowerCase())))]

  const filtered = (bookings ?? []).filter((b) => {
    const matchesPlatform = platform === 'all' || b.platform.toLowerCase() === platform
    const matchesStatus = statusFilter === 'all' || b.booking_state === statusFilter
    const matchesSearch =
      !search ||
      b.guest_name.toLowerCase().includes(search.toLowerCase()) ||
      (b.guest_email ?? '').toLowerCase().includes(search.toLowerCase()) ||
      (b.guest_phone ?? '').toLowerCase().includes(search.toLowerCase()) ||
      b.platform_booking_id.toLowerCase().includes(search.toLowerCase())
    return matchesPlatform && matchesStatus && matchesSearch
  })

  // Sort: upcoming first, then by check-in date descending for past
  const today = new Date().toISOString().slice(0, 10)
  const sorted = [...filtered].sort((a, b) => {
    const aUpcoming = a.check_out_date >= today ? 0 : 1
    const bUpcoming = b.check_out_date >= today ? 0 : 1
    if (aUpcoming !== bUpcoming) return aUpcoming - bUpcoming
    return aUpcoming === 0
      ? a.check_in_date.localeCompare(b.check_in_date)
      : b.check_in_date.localeCompare(a.check_in_date)
  })

  // Count per status for badge numbers
  const allBookings = bookings ?? []
  const statusCounts: Record<string, number> = { all: allBookings.length }
  for (const b of allBookings) {
    statusCounts[b.booking_state] = (statusCounts[b.booking_state] ?? 0) + 1
  }

  // If a booking is selected, show the detail panel
  const selectedBooking = selectedBookingId != null
    ? (bookings ?? []).find((b) => b.id === selectedBookingId) ?? null
    : null

  if (selectedBooking) {
    return (
      <BookingDetail
        booking={selectedBooking}
        onBack={() => setSelectedBookingId(null)}
        properties={properties}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h2 className="text-lg font-semibold">Reservations</h2>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <Input
              className="pl-8 h-8 w-48 text-sm"
              placeholder="Search guests…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          {platforms.length > 2 && (
            <div className="flex rounded-md border overflow-hidden text-sm">
              {platforms.map((p) => (
                <button
                  key={p}
                  onClick={() => setPlatform(p)}
                  className={`px-3 py-1.5 capitalize transition-colors ${
                    platform === p
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-background hover:bg-muted text-muted-foreground'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
          <Button size="sm" onClick={() => setShowNewDialog(true)}>
            <Plus className="h-4 w-4 mr-1" />
            New Reservation
          </Button>
        </div>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-1 overflow-x-auto rounded-lg bg-muted p-1">
        {STATUS_FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setStatusFilter(f.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-all flex items-center gap-1.5 ${
              statusFilter === f.key ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {f.label}
            {(statusCounts[f.key] ?? 0) > 0 && (
              <span className="text-xs bg-muted-foreground/10 rounded px-1.5">
                {statusCounts[f.key]}
              </span>
            )}
          </button>
        ))}
      </div>

      {error && <ErrorAlert message="Failed to load reservations." />}
      {isLoading && <ReservationsSkeleton />}

      {!isLoading && !error && filtered.length === 0 && (
        <EmptyState title="No reservations found." />
      )}

      {!isLoading && !error && sorted.length > 0 && (
        <div className="space-y-3">
          {sorted.map((b) => (
            <BookingRow key={b.id} booking={b} onClick={() => setSelectedBookingId(b.id)} />
          ))}
        </div>
      )}

      {showNewDialog && (
        <NewReservationDialog
          open
          onClose={() => setShowNewDialog(false)}
          defaultPropertyId={selectedPropertyId}
          properties={properties}
        />
      )}
    </div>
  )
}
