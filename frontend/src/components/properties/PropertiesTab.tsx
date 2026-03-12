import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, Search, MapPin, Clock, Users, Bed, Bath,
  ChevronLeft, PowerOff, Pencil,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import {
  fetchProperties, getProperty, createProperty, updateProperty, deactivateProperty,
  fetchLinkedListings, type PropertyPayload,
} from '@/api/platform'

// ── Detail sub-tabs ────────────────────────────────────────────────
type DetailTab = 'general' | 'pricing' | 'listings'
const DETAIL_TABS: { key: DetailTab; label: string }[] = [
  { key: 'general', label: 'General' },
  { key: 'pricing', label: 'Pricing & Rules' },
  { key: 'listings', label: 'Listings Linked' },
]

// ── Property Form Dialog ───────────────────────────────────────────
function PropertyForm({
  initial,
  onSave,
  saving,
}: {
  initial?: Partial<PropertyPayload>
  onSave: (p: PropertyPayload) => void
  saving: boolean
}) {
  const [form, setForm] = useState<PropertyPayload>({
    name: initial?.name ?? '',
    address: initial?.address ?? '',
    city: initial?.city ?? '',
    country: initial?.country ?? '',
    timezone: initial?.timezone ?? 'America/New_York',
    max_guests: initial?.max_guests ?? null,
    bedrooms: initial?.bedrooms ?? null,
    bathrooms: initial?.bathrooms ?? null,
    check_in_time: initial?.check_in_time ?? '15:00',
    check_out_time: initial?.check_out_time ?? '11:00',
    tags: initial?.tags ?? [],
    groups: initial?.groups ?? [],
    allow_overbooking: initial?.allow_overbooking ?? false,
    stop_auto_sync: initial?.stop_auto_sync ?? false,
  })

  const set = (k: keyof PropertyPayload, v: unknown) => setForm(prev => ({ ...prev, [k]: v }))

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <Label>Name</Label>
          <Input value={form.name} onChange={e => set('name', e.target.value)} />
        </div>
        <div>
          <Label>Address</Label>
          <Input value={form.address ?? ''} onChange={e => set('address', e.target.value)} />
        </div>
        <div>
          <Label>City</Label>
          <Input value={form.city ?? ''} onChange={e => set('city', e.target.value)} />
        </div>
        <div>
          <Label>Country</Label>
          <Input value={form.country ?? ''} onChange={e => set('country', e.target.value)} />
        </div>
        <div>
          <Label>Timezone</Label>
          <Input value={form.timezone ?? ''} onChange={e => set('timezone', e.target.value)} />
        </div>
        <div>
          <Label>Max Guests</Label>
          <Input type="number" value={form.max_guests ?? ''} onChange={e => set('max_guests', e.target.value ? Number(e.target.value) : null)} />
        </div>
        <div>
          <Label>Bedrooms</Label>
          <Input type="number" value={form.bedrooms ?? ''} onChange={e => set('bedrooms', e.target.value ? Number(e.target.value) : null)} />
        </div>
        <div>
          <Label>Bathrooms</Label>
          <Input type="number" value={form.bathrooms ?? ''} onChange={e => set('bathrooms', e.target.value ? Number(e.target.value) : null)} />
        </div>
        <div>
          <Label>Check-in Time</Label>
          <Input type="time" value={form.check_in_time ?? ''} onChange={e => set('check_in_time', e.target.value)} />
        </div>
        <div>
          <Label>Check-out Time</Label>
          <Input type="time" value={form.check_out_time ?? ''} onChange={e => set('check_out_time', e.target.value)} />
        </div>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Switch checked={form.allow_overbooking} onCheckedChange={v => set('allow_overbooking', v)} />
          <Label>Allow Overbooking</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch checked={form.stop_auto_sync} onCheckedChange={v => set('stop_auto_sync', v)} />
          <Label>Stop Auto Sync</Label>
        </div>
      </div>
      <Button onClick={() => onSave(form)} disabled={!form.name.trim() || saving} className="w-full">
        {saving ? 'Saving…' : 'Save Property'}
      </Button>
    </div>
  )
}

// ── Property Detail ────────────────────────────────────────────────
function PropertyDetail({
  propertyId,
  onBack,
}: {
  propertyId: number
  onBack: () => void
}) {
  const [tab, setTab] = useState<DetailTab>('general')
  const [showEdit, setShowEdit] = useState(false)
  const qc = useQueryClient()

  const { data: prop, isLoading } = useQuery({
    queryKey: ['property', propertyId],
    queryFn: () => getProperty(propertyId),
  })

  const { data: listings = [] } = useQuery({
    queryKey: ['linked-listings', propertyId],
    queryFn: () => fetchLinkedListings(propertyId),
    enabled: tab === 'listings',
  })

  const updateMut = useMutation({
    mutationFn: (payload: Partial<PropertyPayload>) => updateProperty(propertyId, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['property', propertyId] })
      void qc.invalidateQueries({ queryKey: ['properties'] })
      setShowEdit(false)
    },
  })

  const deactivateMut = useMutation({
    mutationFn: () => deactivateProperty(propertyId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['properties'] })
      onBack()
    },
  })

  if (isLoading || !prop) {
    return <div className="space-y-3">{[0,1,2].map(i => <Skeleton key={i} className="h-12" />)}</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={onBack}><ChevronLeft className="h-4 w-4" /></Button>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold truncate">{prop.name}</h3>
          <p className="text-xs text-muted-foreground">{[prop.city, prop.country].filter(Boolean).join(', ') || 'No location'}</p>
        </div>
        <Badge variant={prop.is_active ? 'default' : 'secondary'}>
          {prop.is_active ? 'Active' : 'Inactive'}
        </Badge>
        <Dialog open={showEdit} onOpenChange={setShowEdit}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm"><Pencil className="h-3.5 w-3.5 mr-1" /> Edit</Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
            <DialogHeader><DialogTitle>Edit Property</DialogTitle></DialogHeader>
            <PropertyForm
              initial={prop}
              onSave={p => updateMut.mutate(p)}
              saving={updateMut.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1 rounded-lg bg-muted p-1">
        {DETAIL_TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              tab === t.key ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'general' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <InfoTile icon={MapPin} label="Address" value={prop.address || '—'} />
            <InfoTile icon={Clock} label="Check-in" value={prop.check_in_time || '—'} />
            <InfoTile icon={Clock} label="Check-out" value={prop.check_out_time || '—'} />
            <InfoTile icon={Users} label="Max Guests" value={String(prop.max_guests ?? '—')} />
            <InfoTile icon={Bed} label="Bedrooms" value={String(prop.bedrooms ?? '—')} />
            <InfoTile icon={Bath} label="Bathrooms" value={String(prop.bathrooms ?? '—')} />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {prop.tags.map(t => <Badge key={t} variant="outline">{t}</Badge>)}
            {prop.groups.map(g => <Badge key={g} variant="secondary">{g}</Badge>)}
          </div>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <Switch
                checked={prop.allow_overbooking}
                onCheckedChange={v => updateMut.mutate({ allow_overbooking: v })}
              />
              <Label className="text-sm">Allow Overbooking</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={prop.stop_auto_sync}
                onCheckedChange={v => updateMut.mutate({ stop_auto_sync: v })}
              />
              <Label className="text-sm">Stop Auto Sync</Label>
            </div>
          </div>
          {prop.is_active && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => deactivateMut.mutate()}
              disabled={deactivateMut.isPending}
            >
              <PowerOff className="h-3.5 w-3.5 mr-1" /> Deactivate
            </Button>
          )}
        </div>
      )}

      {tab === 'pricing' && (
        <div className="rounded-lg border p-6 text-center text-sm text-muted-foreground">
          Pricing & Rules settings coming soon. Configure base rates, weekend rates, and minimum stay rules.
        </div>
      )}

      {tab === 'listings' && (
        <div className="rounded-xl border overflow-hidden">
          <div className="grid grid-cols-5 gap-2 px-4 py-2 bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground font-medium">
            <span className="col-span-2">Listing</span>
            <span>Channel</span>
            <span>Rate Plan</span>
            <span className="text-right">Status</span>
          </div>
          {listings.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No linked listings.</p>
          ) : listings.map(l => (
            <div key={l.id} className="grid grid-cols-5 gap-2 px-4 py-3 border-t items-center text-sm">
              <span className="col-span-2 truncate font-medium">{l.listing_name}</span>
              <Badge variant="outline" className="w-fit">{l.channel}</Badge>
              <span className="text-muted-foreground">{l.rate_plan || '—'}</span>
              <div className="text-right">
                <Badge variant={l.is_linked ? 'default' : 'secondary'}>
                  {l.is_linked ? 'Linked' : 'Unlinked'}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function InfoTile({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-center gap-1.5 text-muted-foreground mb-1">
        <Icon className="h-3.5 w-3.5" />
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-sm font-medium">{value}</p>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────
export function PropertiesTab() {
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const qc = useQueryClient()

  const { data: properties = [], isLoading } = useQuery({
    queryKey: ['properties'],
    queryFn: fetchProperties,
    staleTime: 60_000,
  })

  const createMut = useMutation({
    mutationFn: createProperty,
    onSuccess: () => {
      setShowCreate(false)
      void qc.invalidateQueries({ queryKey: ['properties'] })
    },
  })

  const filtered = properties.filter(p =>
    !search || p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.city ?? '').toLowerCase().includes(search.toLowerCase()),
  )

  if (selectedId !== null) {
    return <PropertyDetail propertyId={selectedId} onBack={() => setSelectedId(null)} />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h2 className="text-lg font-semibold">Properties</h2>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <Input className="pl-8 h-8 w-48 text-sm" placeholder="Search properties…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <Dialog open={showCreate} onOpenChange={setShowCreate}>
            <DialogTrigger asChild>
              <Button size="sm"><Plus className="h-3.5 w-3.5 mr-1" /> Add Property</Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
              <DialogHeader><DialogTitle>New Property</DialogTitle></DialogHeader>
              <PropertyForm onSave={p => createMut.mutate(p)} saving={createMut.isPending} />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">{[0,1,2].map(i => <Skeleton key={i} className="h-16 rounded-lg" />)}</div>
      ) : filtered.length === 0 ? (
        <p className="text-center text-sm text-muted-foreground py-12">No properties found.</p>
      ) : (
        <div className="rounded-xl border overflow-hidden">
          <div className="grid grid-cols-6 gap-2 px-4 py-2 bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground font-medium">
            <span className="col-span-2">Property</span>
            <span>Location</span>
            <span>Tags</span>
            <span>Groups</span>
            <span className="text-right">Status</span>
          </div>
          {filtered.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedId(p.id)}
              className="grid grid-cols-6 gap-2 px-4 py-3 border-t items-center text-sm w-full text-left hover:bg-muted/30 transition-colors"
            >
              <span className="col-span-2 font-medium truncate">{p.name}</span>
              <span className="text-muted-foreground truncate">{[p.city, p.country].filter(Boolean).join(', ') || '—'}</span>
              <div className="flex gap-1 flex-wrap">
                {p.tags.slice(0, 2).map(t => <Badge key={t} variant="outline" className="text-xs">{t}</Badge>)}
                {p.tags.length > 2 && <Badge variant="outline" className="text-xs">+{p.tags.length - 2}</Badge>}
              </div>
              <div className="flex gap-1 flex-wrap">
                {p.groups.slice(0, 2).map(g => <Badge key={g} variant="secondary" className="text-xs">{g}</Badge>)}
              </div>
              <div className="text-right">
                <Badge variant={p.is_active ? 'default' : 'secondary'}>
                  {p.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
