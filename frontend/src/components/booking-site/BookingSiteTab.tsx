import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, Globe, ExternalLink, Eye, EyeOff, Settings2,
  Palette, Search as SearchIcon, BarChart3, Percent, Home,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import {
  fetchBookingSites, createBookingSite, updateBookingSite,
  publishBookingSite, unpublishBookingSite,
  fetchSiteListings, updateSiteListing,
  type BookingSite, type BookingSitePayload, type BookingSiteListing,
} from '@/api/platform'

// ── Detail sub-tabs ────────────────────────────────────────────────
type DetailTab = 'listings' | 'domain' | 'design' | 'seo' | 'rateplans' | 'promo' | 'publish'
const DETAIL_TABS: { key: DetailTab; label: string; icon: React.ElementType }[] = [
  { key: 'listings', label: 'Listings', icon: Settings2 },
  { key: 'domain', label: 'Domain', icon: Globe },
  { key: 'design', label: 'Design', icon: Palette },
  { key: 'seo', label: 'SEO & Analytics', icon: SearchIcon },
  { key: 'rateplans', label: 'Rate Plans', icon: BarChart3 },
  { key: 'promo', label: 'Promo Codes', icon: Percent },
  { key: 'publish', label: 'Publish', icon: ExternalLink },
]

// ── Create form ────────────────────────────────────────────────────
function CreateSiteForm({
  onSave,
  saving,
}: {
  onSave: (p: BookingSitePayload) => void
  saving: boolean
}) {
  const [name, setName] = useState('')

  return (
    <div className="space-y-4">
      <div>
        <Label>Site Name</Label>
        <Input value={name} onChange={e => setName(e.target.value)} placeholder="My Booking Site" />
      </div>
      <Button
        onClick={() => onSave({ name })}
        disabled={!name.trim() || saving}
        className="w-full"
      >
        {saving ? 'Creating…' : 'Create Site'}
      </Button>
    </div>
  )
}

// ── Listings panel ─────────────────────────────────────────────────
function ListingsPanel({ site }: { site: BookingSite }) {
  const qc = useQueryClient()

  const { data: listings = [], isLoading } = useQuery<BookingSiteListing[]>({
    queryKey: ['booking-site-listings', site.id],
    queryFn: () => fetchSiteListings(site.id),
    staleTime: 30_000,
  })

  const toggleMut = useMutation({
    mutationFn: ({ listingId, is_visible }: { listingId: number; is_visible: boolean }) =>
      updateSiteListing(site.id, listingId, { is_visible }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['booking-site-listings', site.id] })
      void qc.invalidateQueries({ queryKey: ['booking-sites'] })
    },
  })

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map(i => <Skeleton key={i} className="h-14 rounded-lg" />)}
      </div>
    )
  }

  if (listings.length === 0) {
    return (
      <div className="rounded-lg border p-8 text-center">
        <Home className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">
          No properties found. Add properties to Channex to see them here.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground mb-3">
        Toggle which properties appear on this booking site. {listings.filter(l => l.is_visible).length} of {listings.length} visible.
      </p>
      {listings.map(listing => (
        <div
          key={listing.id}
          className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3"
        >
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm truncate">{listing.display_name}</p>
            <p className="text-xs text-muted-foreground">
              {[
                listing.bedrooms != null && `${listing.bedrooms} bed`,
                listing.bathrooms != null && `${listing.bathrooms} bath`,
                listing.max_guests != null && `${listing.max_guests} guests`,
                listing.city,
              ].filter(Boolean).join(' · ')}
            </p>
          </div>
          <Switch
            checked={listing.is_visible}
            onCheckedChange={checked =>
              toggleMut.mutate({ listingId: listing.id, is_visible: checked })
            }
            disabled={toggleMut.isPending}
          />
        </div>
      ))}
    </div>
  )
}

// ── Site detail editor ─────────────────────────────────────────────
function SiteDetail({
  site,
  onBack,
}: {
  site: BookingSite
  onBack: () => void
}) {
  const [tab, setTab] = useState<DetailTab>('listings')
  const qc = useQueryClient()

  const [form, setForm] = useState({
    hero_title: site.hero_title ?? '',
    hero_subtitle: site.hero_subtitle ?? '',
    contact_phone: site.contact_phone ?? '',
    contact_email: site.contact_email ?? '',
    seo_title: site.seo_title ?? '',
    seo_description: site.seo_description ?? '',
    seo_keywords: site.seo_keywords ?? '',
    custom_domain: site.custom_domain ?? '',
  })

  const updateMut = useMutation({
    mutationFn: (payload: Partial<BookingSitePayload>) => updateBookingSite(site.id, payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['booking-sites'] }),
  })

  const publishMut = useMutation({
    mutationFn: () => publishBookingSite(site.id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['booking-sites'] }),
  })

  const unpublishMut = useMutation({
    mutationFn: () => unpublishBookingSite(site.id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['booking-sites'] }),
  })

  function saveField(key: keyof BookingSitePayload, value: string) {
    updateMut.mutate({ [key]: value || null })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>← Back</Button>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold truncate">{site.name}</h3>
          <p className="text-xs text-muted-foreground">
            {site.domain || 'No domain'} · {site.listing_count} listing{site.listing_count !== 1 ? 's' : ''}
          </p>
        </div>
        <Badge variant={site.is_published ? 'default' : 'secondary'}>
          {site.is_published ? 'Published' : 'Draft'}
        </Badge>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1 overflow-x-auto rounded-lg bg-muted p-1">
        {DETAIL_TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-all ${
              tab === t.key ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <t.icon className="h-3.5 w-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'design' && (
        <div className="space-y-4 max-w-lg">
          <div>
            <Label>Hero Title</Label>
            <Input
              value={form.hero_title}
              onChange={e => setForm(p => ({ ...p, hero_title: e.target.value }))}
              onBlur={() => saveField('hero_title', form.hero_title)}
            />
          </div>
          <div>
            <Label>Hero Subtitle</Label>
            <Input
              value={form.hero_subtitle}
              onChange={e => setForm(p => ({ ...p, hero_subtitle: e.target.value }))}
              onBlur={() => saveField('hero_subtitle', form.hero_subtitle)}
            />
          </div>
          <div>
            <Label>Contact Phone</Label>
            <Input
              value={form.contact_phone}
              onChange={e => setForm(p => ({ ...p, contact_phone: e.target.value }))}
              onBlur={() => saveField('contact_phone', form.contact_phone)}
            />
          </div>
          <div>
            <Label>Contact Email</Label>
            <Input
              type="email"
              value={form.contact_email}
              onChange={e => setForm(p => ({ ...p, contact_email: e.target.value }))}
              onBlur={() => saveField('contact_email', form.contact_email)}
            />
          </div>
          {updateMut.isPending && <p className="text-xs text-muted-foreground">Saving…</p>}
        </div>
      )}

      {tab === 'domain' && (
        <div className="space-y-4 max-w-lg">
          <div className="rounded-lg border p-4">
            <p className="text-sm font-medium mb-1">Default Domain</p>
            <p className="text-sm text-muted-foreground font-mono">{site.domain || 'Not assigned'}</p>
          </div>
          <div>
            <Label>Custom Domain</Label>
            <Input
              placeholder="bookings.example.com"
              value={form.custom_domain}
              onChange={e => setForm(p => ({ ...p, custom_domain: e.target.value }))}
              onBlur={() => saveField('custom_domain', form.custom_domain)}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Point a CNAME record to your default domain.
            </p>
          </div>
        </div>
      )}

      {tab === 'seo' && (
        <div className="space-y-4 max-w-lg">
          <div>
            <Label>SEO Title</Label>
            <Input
              value={form.seo_title}
              onChange={e => setForm(p => ({ ...p, seo_title: e.target.value }))}
              onBlur={() => saveField('seo_title', form.seo_title)}
            />
          </div>
          <div>
            <Label>Meta Description</Label>
            <Textarea
              value={form.seo_description}
              onChange={e => setForm(p => ({ ...p, seo_description: e.target.value }))}
              onBlur={() => saveField('seo_description', form.seo_description)}
              rows={3}
            />
          </div>
          <div>
            <Label>Keywords</Label>
            <Input
              placeholder="vacation, rental, beach"
              value={form.seo_keywords}
              onChange={e => setForm(p => ({ ...p, seo_keywords: e.target.value }))}
              onBlur={() => saveField('seo_keywords', form.seo_keywords)}
            />
          </div>
        </div>
      )}

      {tab === 'listings' && (
        <ListingsPanel site={site} />
      )}

      {tab === 'rateplans' && (
        <div className="rounded-lg border p-6 text-center text-sm text-muted-foreground">
          Configure rate plans with cancellation policies, payment schedules, and minimum/maximum stay rules.
        </div>
      )}

      {tab === 'promo' && (
        <div className="rounded-lg border p-6 text-center text-sm text-muted-foreground">
          Create promotion codes with percentage or fixed discounts and date ranges.
        </div>
      )}

      {tab === 'publish' && (
        <div className="space-y-4 max-w-lg">
          <div className="rounded-lg border p-4">
            <p className="text-sm font-medium mb-2">Publish Status</p>
            <p className="text-sm text-muted-foreground mb-4">
              {site.is_published
                ? 'Your booking site is live and accepting reservations.'
                : 'Your booking site is in draft mode and not visible to the public.'}
            </p>
            {site.is_published ? (
              <Button
                variant="outline"
                onClick={() => unpublishMut.mutate()}
                disabled={unpublishMut.isPending}
              >
                <EyeOff className="h-3.5 w-3.5 mr-1" /> Unpublish
              </Button>
            ) : (
              <Button
                onClick={() => publishMut.mutate()}
                disabled={publishMut.isPending}
              >
                <Eye className="h-3.5 w-3.5 mr-1" /> Publish Now
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────
export function BookingSiteTab() {
  const [selectedSite, setSelectedSite] = useState<BookingSite | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const qc = useQueryClient()

  const { data: sites = [], isLoading } = useQuery({
    queryKey: ['booking-sites'],
    queryFn: fetchBookingSites,
    staleTime: 60_000,
  })

  const createMut = useMutation({
    mutationFn: createBookingSite,
    onSuccess: () => {
      setShowCreate(false)
      void qc.invalidateQueries({ queryKey: ['booking-sites'] })
    },
  })

  if (selectedSite) {
    const live = sites.find(s => s.id === selectedSite.id) ?? selectedSite
    return <SiteDetail site={live} onBack={() => setSelectedSite(null)} />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold">Booking Sites</h2>
        <Dialog open={showCreate} onOpenChange={setShowCreate}>
          <DialogTrigger asChild>
            <Button size="sm"><Plus className="h-3.5 w-3.5 mr-1" /> New Site</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create Booking Site</DialogTitle></DialogHeader>
            <CreateSiteForm onSave={p => createMut.mutate(p)} saving={createMut.isPending} />
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="space-y-3">{[0,1,2].map(i => <Skeleton key={i} className="h-16 rounded-lg" />)}</div>
      ) : sites.length === 0 ? (
        <div className="text-center py-16 space-y-2">
          <Globe className="h-10 w-10 text-muted-foreground/40 mx-auto" />
          <p className="text-sm text-muted-foreground">No booking sites yet. Create one to start accepting direct bookings.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sites.map(s => (
            <button
              key={s.id}
              onClick={() => setSelectedSite(s)}
              className="rounded-xl border bg-card p-4 text-left hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="min-w-0">
                  <p className="font-medium truncate">{s.name}</p>
                  <p className="text-xs text-muted-foreground font-mono truncate">
                    {s.custom_domain || s.domain || 'No domain'}
                  </p>
                </div>
                <Badge variant={s.is_published ? 'default' : 'secondary'} className="shrink-0">
                  {s.is_published ? 'Live' : 'Draft'}
                </Badge>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>{s.listing_count} listing{s.listing_count !== 1 ? 's' : ''}</span>
                <span>·</span>
                <span>{s.type}</span>
                <span>·</span>
                <span>Created {new Date(s.created_at).toLocaleDateString()}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
