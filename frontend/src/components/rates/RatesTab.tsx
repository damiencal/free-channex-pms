/**
 * Rates Tab — manage rate plans and per-date pricing.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, DollarSign, Tag, Trash2, ChevronLeft, ChevronRight, Save, Pencil,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from '@/components/ui/dialog'
import {
  fetchRatePlans, createRatePlan, updateRatePlan, deleteRatePlan,
  fetchRateDates, setRateDates, clearRateDates,
  type RatePlan, type RateDate, type RatePlanPayload,
} from '@/api/rates'
import { fetchProperties, type Property } from '@/api/platform'
import { usePropertyStore } from '@/store/usePropertyStore'

// -------------------------------------------------------------------------
function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + 'T12:00:00')
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

function weekStart(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00')
  const dow = d.getDay()
  d.setDate(d.getDate() - dow)
  return d.toISOString().slice(0, 10)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// -------------------------------------------------------------------------
// Rate Plan dialog
// -------------------------------------------------------------------------
function RatePlanDialog({
  open, onClose, propertyId, plan,
}: { open: boolean; onClose: () => void; propertyId: number | null; plan?: RatePlan }) {
  const qc = useQueryClient()
  const isEdit = !!plan
  const [localPropertyId, setLocalPropertyId] = useState<number | null>(null)
  const effectivePropertyId = propertyId ?? localPropertyId

  const { data: properties = [] } = useQuery<Property[]>({
    queryKey: ['properties'],
    queryFn: fetchProperties,
    enabled: open && propertyId === null && !isEdit,
    staleTime: 300_000,
  })

  const [form, setForm] = useState<Omit<RatePlanPayload, 'property_id'>>(() => ({
    name: plan?.name ?? '',
    base_rate: plan ? parseFloat(plan.base_rate) : 0,
    currency: plan?.currency ?? 'USD',
    min_stay: plan?.min_stay ?? 1,
    description: plan?.description ?? undefined,
  }))

  const mutation = useMutation({
    mutationFn: () => isEdit
      ? updateRatePlan(plan!.id, form)
      : createRatePlan({ ...form, property_id: effectivePropertyId! }),
    onSuccess: (saved) => {
      if (isEdit) {
        qc.setQueryData<RatePlan[]>(['rate-plans', propertyId], old =>
          (old ?? []).map(p => p.id === saved.id ? saved : p)
        )
      } else {
        qc.setQueryData<RatePlan[]>(['rate-plans', effectivePropertyId], old => [...(old ?? []), saved])
      }
      void qc.invalidateQueries({ queryKey: ['rate-plans'] })
      onClose()
      setLocalPropertyId(null)
      setForm({ name: '', base_rate: 0, currency: 'USD', min_stay: 1 })
    },
  })

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle>{isEdit ? 'Edit Rate Plan' : 'New Rate Plan'}</DialogTitle></DialogHeader>
        <DialogBody className="space-y-3 pt-4">
          {propertyId === null && !isEdit && (
            <div className="space-y-1.5">
              <Label>Property *</Label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={localPropertyId ?? ''}
                onChange={e => setLocalPropertyId(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Select a property…</option>
                {properties.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
          )}
          <div className="space-y-1.5">
            <Label>Plan Name *</Label>
            <Input placeholder="Standard, Weekend, Promo..." value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Base Rate ($/night) *</Label>
              <Input type="number" step="0.01" placeholder="200.00" value={form.base_rate ?? ''} onChange={e => setForm(p => ({ ...p, base_rate: parseFloat(e.target.value) || 0 }))} />
            </div>
            <div className="space-y-1.5">
              <Label>Min Stay (nights)</Label>
              <Input type="number" min={1} value={form.min_stay ?? 1} onChange={e => setForm(p => ({ ...p, min_stay: Number(e.target.value) }))} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Input placeholder="Optional notes..." value={form.description ?? ''} onChange={e => setForm(p => ({ ...p, description: e.target.value || undefined }))} />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.name || !form.base_rate || (!isEdit && !effectivePropertyId)}>
            {mutation.isPending ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Plan'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// -------------------------------------------------------------------------
// Rate Grid — 2-week view with editable cells
// -------------------------------------------------------------------------
function RateGrid({ plan }: { plan: RatePlan }) {
  const qc = useQueryClient()
  const today = new Date().toISOString().slice(0, 10)
  const [weekOffset, setWeekOffset] = useState(0)
  const [edits, setEdits] = useState<Record<string, string>>({})

  const rangeStart = addDays(weekStart(today), weekOffset * 14)
  const rangeEnd = addDays(rangeStart, 13)

  // Build 14-day array
  const dates = Array.from({ length: 14 }, (_, i) => addDays(rangeStart, i))

  const { data: rateDates = [] } = useQuery<RateDate[]>({
    queryKey: ['rate-dates', plan.id, rangeStart, rangeEnd],
    queryFn: () => fetchRateDates(plan.id, rangeStart, rangeEnd),
    staleTime: 30_000,
  })

  const rateByDate = Object.fromEntries(rateDates.map(rd => [rd.date, rd.rate]))

  const saveRates = useMutation({
    mutationFn: () => {
      const rates = Object.entries(edits).map(([date, rate]) => ({ date, rate: parseFloat(rate) }))
      return setRateDates(plan.id, rates)
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['rate-dates', plan.id] })
      setEdits({})
    },
  })

  const clearRange = useMutation({
    mutationFn: () => clearRateDates(plan.id, rangeStart, rangeEnd),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['rate-dates', plan.id] }),
  })

  const hasEdits = Object.keys(edits).length > 0

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => setWeekOffset(w => w - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium px-2">
            {formatDate(rangeStart)} – {formatDate(rangeEnd)}
          </span>
          <Button variant="ghost" size="sm" onClick={() => setWeekOffset(w => w + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex items-center gap-2">
          {hasEdits && (
            <Button size="sm" onClick={() => saveRates.mutate()} disabled={saveRates.isPending}>
              <Save className="h-3.5 w-3.5 mr-1" />{saveRates.isPending ? 'Saving…' : `Save ${Object.keys(edits).length} changes`}
            </Button>
          )}
          <Button
            variant="ghost" size="sm"
            className="text-muted-foreground text-xs"
            onClick={() => { if (confirm('Clear all rate overrides for this 2-week window?')) clearRange.mutate() }}
          >
            Clear Range
          </Button>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-7 gap-1">
        {DAYS.map(d => (
          <div key={d} className="text-center text-xs font-medium text-muted-foreground py-1">{d}</div>
        ))}
        {dates.map(date => {
          const dow = new Date(date + 'T12:00:00').getDay()
          const isWeekend = dow === 0 || dow === 6
          const override = rateByDate[date]
          const editVal = edits[date]
          const displayRate = editVal !== undefined ? editVal : override ? String(parseFloat(override).toFixed(0)) : ''
          const isToday = date === today
          const isPast = date < today

          return (
            <div
              key={date}
              className={`rounded-lg border p-1.5 transition-colors ${
                isToday ? 'border-blue-400 bg-blue-50 dark:bg-blue-950/20' :
                isWeekend ? 'bg-orange-50/40 dark:bg-orange-950/10' : 'bg-card'
              } ${isPast ? 'opacity-50' : ''}`}
            >
              <div className="text-xs text-muted-foreground mb-1">
                {formatDate(date)}
              </div>
              <div className="relative">
                <span className="absolute left-1 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">$</span>
                <input
                  type="number"
                  className={`w-full pl-4 pr-1 py-1 text-sm rounded bg-transparent border-0 focus:outline-none focus:bg-muted/50 text-right ${
                    editVal !== undefined ? 'font-semibold text-blue-600' :
                    override ? 'text-foreground' : 'text-muted-foreground'
                  }`}
                  placeholder={plan.base_rate ? String(parseFloat(plan.base_rate).toFixed(0)) : '—'}
                  value={displayRate}
                  onChange={e => setEdits(prev => ({ ...prev, [date]: e.target.value }))}
                  disabled={isPast}
                />
              </div>
            </div>
          )
        })}
      </div>
      <p className="text-xs text-muted-foreground">
        Blank cells use the plan's base rate (${plan.base_rate}/night). Blue cells have pending edits.
      </p>
    </div>
  )
}

// -------------------------------------------------------------------------
// Main Tab
// -------------------------------------------------------------------------
export function RatesTab() {
  const { selectedPropertyId } = usePropertyStore()
  const [showCreate, setShowCreate] = useState(false)
  const [editingPlan, setEditingPlan] = useState<RatePlan | null>(null)
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null)
  const qc = useQueryClient()

  const { data: plans = [], isLoading } = useQuery<RatePlan[]>({
    queryKey: ['rate-plans', selectedPropertyId],
    queryFn: () => fetchRatePlans(selectedPropertyId ?? undefined),
    staleTime: 60_000,
  })

  const deletePlan = useMutation({
    mutationFn: (id: number) => deleteRatePlan(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['rate-plans'] })
      if (selectedPlanId) setSelectedPlanId(null)
    },
  })

  const selectedPlan = plans.find(p => p.id === selectedPlanId) ?? null

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Rate Plans</h2>
          <p className="text-muted-foreground text-sm">Manage pricing and per-date rate overrides</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-1.5" />New Rate Plan
        </Button>
      </div>

      <div className="flex gap-4 flex-col lg:flex-row">
        {/* Plans sidebar */}
        <div className="w-full lg:w-64 shrink-0">
          {isLoading ? (
            <div className="space-y-2">
              {[0,1,2].map(i => <Skeleton key={i} className="h-20 rounded-xl" />)}
            </div>
          ) : plans.length === 0 ? (
            <div className="rounded-xl border border-dashed p-8 text-center space-y-2">
              <Tag className="h-7 w-7 text-muted-foreground mx-auto" />
              <p className="text-sm font-medium">No rate plans</p>
              <Button variant="outline" size="sm" onClick={() => setShowCreate(true)}>
                <Plus className="h-3.5 w-3.5 mr-1" />Create one
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {plans.map(plan => (
                <div
                  key={plan.id}
                  className={`rounded-xl border p-3 cursor-pointer transition-all ${
                    selectedPlanId === plan.id ? 'border-primary bg-primary/5 shadow-sm' : 'bg-card hover:border-border/60 hover:shadow-sm'
                  }`}
                  onClick={() => setSelectedPlanId(selectedPlanId === plan.id ? null : plan.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="min-w-0">
                      <p className="font-medium text-sm truncate">{plan.name}</p>
                      <div className="flex items-center gap-1 mt-0.5">
                        <DollarSign className="h-3 w-3 text-muted-foreground" />
                        <span className="text-sm font-semibold">{parseFloat(plan.base_rate).toFixed(0)}</span>
                        <span className="text-xs text-muted-foreground">/night</span>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={e => {
                          e.stopPropagation()
                          setEditingPlan(plan)
                        }}
                        className="text-muted-foreground hover:text-foreground transition-colors mt-0.5"
                        title="Edit rate plan"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={e => {
                          e.stopPropagation()
                          if (confirm(`Delete rate plan "${plan.name}"?`)) deletePlan.mutate(plan.id)
                        }}
                        className="text-muted-foreground hover:text-destructive transition-colors mt-0.5"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  {plan.min_stay && plan.min_stay > 1 && (
                    <p className="text-xs text-muted-foreground mt-1">Min {plan.min_stay} nights</p>
                  )}
                  {plan.description && (
                    <p className="text-xs text-muted-foreground mt-1 truncate">{plan.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Rate grid */}
        <div className="flex-1 min-w-0">
          {!selectedPlan ? (
            <div className="rounded-xl border border-dashed p-12 text-center space-y-2 h-full flex flex-col items-center justify-center">
              <DollarSign className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm font-medium">Select a rate plan to edit pricing</p>
              <p className="text-xs text-muted-foreground max-w-xs">
                Click a rate plan on the left to view and edit per-date rate overrides.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border bg-card p-4 space-y-3">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">{selectedPlan.name}</h3>
                <span className="text-sm text-muted-foreground">
                  — base ${parseFloat(selectedPlan.base_rate).toFixed(2)}/night
                </span>
              </div>
              <RateGrid plan={selectedPlan} />
            </div>
          )}
        </div>
      </div>

      <RatePlanDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        propertyId={selectedPropertyId}
      />
      {editingPlan && (
        <RatePlanDialog
          open={!!editingPlan}
          onClose={() => setEditingPlan(null)}
          propertyId={selectedPropertyId}
          plan={editingPlan}
        />
      )}
    </div>
  )
}
