/**
 * Guests CRM Tab — search, create, view booking history.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Search, Plus, User, Mail, Phone, MapPin, Star,
  Building, Users, X, ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter, DialogBody,
} from '@/components/ui/dialog'
import {
  fetchGuests, createGuest, updateGuest, getGuest, fetchGuestBookings,
  type Guest, type GuestPayload,
} from '@/api/guests'

// -------------------------------------------------------------------------
const GUEST_TYPE_CONFIG = {
  individual: { icon: User, label: 'Individual', color: 'bg-blue-100 text-blue-700' },
  corporate: { icon: Building, label: 'Corporate', color: 'bg-purple-100 text-purple-700' },
  vip: { icon: Star, label: 'VIP', color: 'bg-amber-100 text-amber-700' },
  group: { icon: Users, label: 'Group', color: 'bg-emerald-100 text-emerald-700' },
}

function GuestTypeBadge({ type }: { type: Guest['guest_type'] }) {
  const cfg = GUEST_TYPE_CONFIG[type] ?? GUEST_TYPE_CONFIG.individual
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

// -------------------------------------------------------------------------
// Create / Edit Guest Dialog
// -------------------------------------------------------------------------
function GuestFormDialog({
  open,
  onClose,
  guest,
}: {
  open: boolean
  onClose: () => void
  guest?: Guest | null
}) {
  const qc = useQueryClient()
  const isEdit = !!guest

  const [form, setForm] = useState<GuestPayload>({
    first_name: guest?.first_name ?? '',
    last_name: guest?.last_name ?? '',
    email: guest?.email ?? '',
    phone: guest?.phone ?? '',
    address: guest?.address ?? '',
    city: guest?.city ?? '',
    state: guest?.state ?? '',
    country: guest?.country ?? '',
    postal_code: guest?.postal_code ?? '',
    guest_type: guest?.guest_type ?? 'individual',
    notes: guest?.notes ?? '',
  })

  const mutation = useMutation({
    mutationFn: () =>
      isEdit ? updateGuest(guest!.id, form) : createGuest(form),
    onSuccess: (result) => {
      if (!isEdit) {
        qc.setQueryData<Guest[]>(['guests', ''], old => [...(old ?? []), result])
      }
      void qc.invalidateQueries({ queryKey: ['guests'] })
      onClose()
    },
  })

  const F = (field: keyof GuestPayload, value: string) =>
    setForm(prev => ({ ...prev, [field]: value || null }))

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Guest' : 'New Guest'}</DialogTitle>
        </DialogHeader>
        <DialogBody className="space-y-4 pt-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>First Name *</Label>
              <Input value={form.first_name} onChange={e => F('first_name', e.target.value)} placeholder="John" />
            </div>
            <div className="space-y-1.5">
              <Label>Last Name *</Label>
              <Input value={form.last_name} onChange={e => F('last_name', e.target.value)} placeholder="Doe" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Email</Label>
              <Input type="email" value={form.email ?? ''} onChange={e => F('email', e.target.value)} placeholder="john@example.com" />
            </div>
            <div className="space-y-1.5">
              <Label>Phone</Label>
              <Input value={form.phone ?? ''} onChange={e => F('phone', e.target.value)} placeholder="+1 555-0100" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Guest Type</Label>
            <div className="flex gap-2 flex-wrap">
              {(Object.keys(GUEST_TYPE_CONFIG) as Guest['guest_type'][]).map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setForm(prev => ({ ...prev, guest_type: t }))}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                    form.guest_type === t
                      ? GUEST_TYPE_CONFIG[t].color + ' border-current ring-1 ring-current'
                      : 'border-border text-muted-foreground hover:border-foreground'
                  }`}
                >
                  {GUEST_TYPE_CONFIG[t].label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>City</Label>
              <Input value={form.city ?? ''} onChange={e => F('city', e.target.value)} placeholder="Miami" />
            </div>
            <div className="space-y-1.5">
              <Label>Country</Label>
              <Input value={form.country ?? ''} onChange={e => F('country', e.target.value)} placeholder="US" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Notes</Label>
            <textarea
              className="w-full min-h-16 rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              value={form.notes ?? ''}
              onChange={e => F('notes', e.target.value)}
              placeholder="VIP preferences, allergies, notes..."
            />
          </div>
          {mutation.error && (
            <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !form.first_name}
          >
            {mutation.isPending ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Guest'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// -------------------------------------------------------------------------
// Guest Detail Panel
// -------------------------------------------------------------------------
function GuestDetail({ guestId, onClose }: { guestId: number; onClose: () => void }) {
  const { data: guest, isLoading: loadingGuest } = useQuery({
    queryKey: ['guest', guestId],
    queryFn: () => getGuest(guestId),
  })
  const { data: bookings = [], isLoading: loadingBookings } = useQuery({
    queryKey: ['guest-bookings', guestId],
    queryFn: () => fetchGuestBookings(guestId),
  })
  const [editing, setEditing] = useState(false)

  if (loadingGuest) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-20 w-full" />
      </div>
    )
  }
  if (!guest) return null

  const bkgs = bookings as Array<{
    id: number; check_in_date: string; check_out_date: string; booking_state: string; net_amount: string
  }>

  return (
    <div className="border-l bg-background h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-semibold text-lg">{guest.full_name}</h3>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setEditing(true)}>Edit</Button>
          <Button size="sm" variant="ghost" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="space-y-2">
          <GuestTypeBadge type={guest.guest_type} />
          {guest.email && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Mail className="h-3.5 w-3.5" />{guest.email}
            </div>
          )}
          {guest.phone && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Phone className="h-3.5 w-3.5" />{guest.phone}
            </div>
          )}
          {(guest.city || guest.country) && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="h-3.5 w-3.5" />
              {[guest.city, guest.state, guest.country].filter(Boolean).join(', ')}
            </div>
          )}
          {parseFloat(guest.balance) !== 0 && (
            <div className="text-sm font-medium">
              Balance: <span className={parseFloat(guest.balance) > 0 ? 'text-emerald-600' : 'text-red-600'}>
                ${parseFloat(guest.balance).toFixed(2)}
              </span>
            </div>
          )}
          {guest.notes && (
            <p className="text-sm text-muted-foreground bg-muted/40 rounded-md p-2">{guest.notes}</p>
          )}
        </div>

        <div>
          <div className="flex items-center gap-2 mb-3">
            <h4 className="text-sm font-semibold">Booking History</h4>
            <Badge variant="secondary">{guest.booking_count}</Badge>
          </div>
          {loadingBookings ? (
            <Skeleton className="h-24 w-full rounded-lg" />
          ) : bkgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No bookings yet</p>
          ) : (
            <div className="space-y-2">
              {bkgs.map(b => (
                <div key={b.id} className="rounded-lg border bg-card px-3 py-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">
                      {new Date(b.check_in_date + 'T00:00:00').toLocaleDateString()} →{' '}
                      {new Date(b.check_out_date + 'T00:00:00').toLocaleDateString()}
                    </span>
                    <span className="text-muted-foreground">${parseFloat(b.net_amount).toFixed(0)}</span>
                  </div>
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                    b.booking_state === 'checked_in' ? 'bg-emerald-100 text-emerald-700' :
                    b.booking_state === 'checked_out' ? 'bg-gray-100 text-gray-600' :
                    'bg-blue-100 text-blue-700'
                  }`}>{b.booking_state.replace('_', ' ')}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {editing && (
        <GuestFormDialog
          open={editing}
          onClose={() => setEditing(false)}
          guest={guest}
        />
      )}
    </div>
  )
}

// -------------------------------------------------------------------------
// Main Tab
// -------------------------------------------------------------------------
export function GuestsTab() {
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const { data: guests = [], isLoading } = useQuery({
    queryKey: ['guests', search],
    queryFn: () => fetchGuests(search || undefined),
    staleTime: 30_000,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Guests</h2>
          <p className="text-muted-foreground text-sm">Guest profiles and booking history</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-1.5" />New Guest
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Search by name, email or phone…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      <div className={`flex gap-4 ${selectedId ? 'flex-col lg:flex-row' : ''}`}>
        {/* Guest list */}
        <div className={selectedId ? 'flex-1 min-w-0' : 'w-full'}>
          {isLoading ? (
            <div className="space-y-2">
              {[0,1,2,3].map(i => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
            </div>
          ) : guests.length === 0 ? (
            <div className="rounded-xl border border-dashed p-10 text-center space-y-2">
              <User className="h-8 w-8 text-muted-foreground mx-auto" />
              <p className="text-sm font-medium">{search ? 'No guests match your search' : 'No guests yet'}</p>
              {!search && (
                <Button variant="outline" onClick={() => setShowCreate(true)}>
                  <Plus className="h-4 w-4 mr-1.5" />Add first guest
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="text-left px-4 py-2.5">Name</th>
                    <th className="text-left px-4 py-2.5 hidden sm:table-cell">Email</th>
                    <th className="text-left px-4 py-2.5 hidden md:table-cell">Phone</th>
                    <th className="text-left px-4 py-2.5">Type</th>
                    <th className="text-right px-4 py-2.5"></th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {guests.map(g => (
                    <tr
                      key={g.id}
                      className={`hover:bg-muted/30 cursor-pointer transition-colors ${selectedId === g.id ? 'bg-muted/20' : ''}`}
                      onClick={() => setSelectedId(selectedId === g.id ? null : g.id)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium shrink-0">
                            {g.first_name[0]?.toUpperCase() ?? '?'}{g.last_name[0]?.toUpperCase() ?? ''}
                          </div>
                          <span className="font-medium">{g.full_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground hidden sm:table-cell">
                        {g.email ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground hidden md:table-cell">
                        {g.phone ?? '—'}
                      </td>
                      <td className="px-4 py-3"><GuestTypeBadge type={g.guest_type} /></td>
                      <td className="px-4 py-3 text-right">
                        <ChevronRight className={`h-4 w-4 text-muted-foreground transition-transform ${selectedId === g.id ? 'rotate-90' : ''}`} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selectedId && (
          <div className="w-full lg:w-80 xl:w-96 shrink-0 rounded-xl border overflow-hidden">
            <GuestDetail guestId={selectedId} onClose={() => setSelectedId(null)} />
          </div>
        )}
      </div>

      <GuestFormDialog open={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  )
}
