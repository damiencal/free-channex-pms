import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, RefreshCw, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { EmptyState } from '@/components/shared/EmptyState'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  fetchLocalChannexProperties,
  fetchChannexCalendar,
  updateChannexCalendar,
  type RateUpdateItem,
} from '@/api/channex'

function addDays(iso: string, days: number): string {
  const d = new Date(iso + 'T00:00:00')
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

function weekStart(iso: string): string {
  const d = new Date(iso + 'T00:00:00')
  const day = d.getDay() // 0=Sun
  d.setDate(d.getDate() - day)
  return d.toISOString().slice(0, 10)
}

function formatDisplayDate(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

function generateDates(fromIso: string, count: number): string[] {
  return Array.from({ length: count }, (_, i) => addDays(fromIso, i))
}

interface RatePlan {
  id: string
  title?: string
  name?: string
  [key: string]: unknown
}

/** Parse rates from Channex calendar data, merging rate plan metadata with per-date rate values. */
function parseRates(
  ratePlans: unknown[],
  ratesById: Record<string, Record<string, string | null>>,
): { id: string; name: string; rates: Record<string, string | null> }[] {
  return (ratePlans as RatePlan[]).map((rp) => {
    const dateRates = ratesById[rp.id] ?? {}
    return {
      id: rp.id,
      name: (rp.title ?? rp.name ?? rp.id) as string,
      rates: dateRates,
    }
  })
}

function PriceTableSkeleton() {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="min-w-full">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-2 text-left">
              <Skeleton className="h-4 w-24" />
            </th>
            {Array.from({ length: 7 }, (_, i) => (
              <th key={i} className="px-3 py-2">
                <Skeleton className="h-4 w-16 mx-auto" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 3 }, (_, i) => (
            <tr key={i} className="border-b">
              <td className="px-4 py-2">
                <Skeleton className="h-4 w-32" />
              </td>
              {Array.from({ length: 7 }, (_, j) => (
                <td key={j} className="px-3 py-2">
                  <Skeleton className="h-8 w-20 mx-auto" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const DAYS_SHOWN = 14

export function PriceTab() {
  const today = new Date().toISOString().slice(0, 10)
  const [startDate, setStartDate] = useState(() => weekStart(today))
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(null)

  // Editable overrides: { ratePlanId_YYYY-MM-DD: string }
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')

  const { data: localProperties, isLoading: propertiesLoading } = useQuery({
    queryKey: ['channex', 'local-properties'],
    queryFn: fetchLocalChannexProperties,
    staleTime: 10 * 60 * 1000,
  })

  // Auto-select first linked property
  const linkedProperties = (localProperties ?? []).filter((p) => p.channex_property_id)
  if (selectedPropertyId === null && linkedProperties.length > 0) {
    setSelectedPropertyId(linkedProperties[0].channex_property_id)
  }

  const endDate = addDays(startDate, DAYS_SHOWN - 1)
  const dates = generateDates(startDate, DAYS_SHOWN)

  const {
    data: calendarData,
    isLoading: calendarLoading,
    error: calendarError,
    refetch,
  } = useQuery({
    queryKey: ['channex', 'calendar', selectedPropertyId, startDate],
    queryFn: () => fetchChannexCalendar(selectedPropertyId!, startDate, endDate),
    enabled: !!selectedPropertyId,
    staleTime: 2 * 60 * 1000,
  })

  const ratePlans = calendarData
    ? parseRates(calendarData.rate_plans as unknown[], calendarData.rates ?? {})
    : []

  const saveMutation = useMutation({
    mutationFn: async () => {
      const rateUpdates: RateUpdateItem[] = []
      for (const [key, value] of Object.entries(edits)) {
        const [ratePlanId, date] = key.split('___')
        const rate = parseFloat(value)
        if (isNaN(rate) || !ratePlanId || !date) continue
        rateUpdates.push({ rate_plan_id: ratePlanId, date_from: date, date_to: date, rate })
      }
      if (rateUpdates.length === 0) return
      return updateChannexCalendar(selectedPropertyId!, { rate_updates: rateUpdates })
    },
    onSuccess: () => {
      setEdits({})
      setSaveStatus('saved')
      void refetch()
      setTimeout(() => setSaveStatus('idle'), 3000)
    },
    onError: () => setSaveStatus('error'),
  })

  function handleRateChange(ratePlanId: string, date: string, value: string) {
    const key = `${ratePlanId}___${date}`
    setEdits((prev) => ({ ...prev, [key]: value }))
    setSaveStatus('idle')
  }

  function getRateValue(ratePlanId: string, date: string, originalRate: string | null): string {
    const key = `${ratePlanId}___${date}`
    return edits[key] ?? originalRate ?? ''
  }

  function isEdited(ratePlanId: string, date: string): boolean {
    return `${ratePlanId}___${date}` in edits
  }

  const isDirty = Object.keys(edits).length > 0
  const isLoading = propertiesLoading || (!!selectedPropertyId && calendarLoading)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h2 className="text-lg font-semibold">Pricing</h2>
        <div className="flex items-center gap-2 flex-wrap">
          {linkedProperties.length > 1 && (
            <Select
              value={selectedPropertyId ?? ''}
              onValueChange={setSelectedPropertyId}
            >
              <SelectTrigger className="h-8 w-48 text-sm">
                <SelectValue placeholder="Select property" />
              </SelectTrigger>
              <SelectContent>
                {linkedProperties.map((p) => (
                  <SelectItem key={p.channex_property_id} value={p.channex_property_id}>
                    {p.property_display_name ?? p.channex_property_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => { setStartDate(addDays(startDate, -DAYS_SHOWN)); setEdits({}) }}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-sm text-muted-foreground px-2 whitespace-nowrap">
              {formatDisplayDate(startDate)} – {formatDisplayDate(endDate)}
            </span>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => { setStartDate(addDays(startDate, DAYS_SHOWN)); setEdits({}) }}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5"
            onClick={() => void refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          {isDirty && (
            <Button
              size="sm"
              className="h-8 gap-1.5"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
            >
              <Save className="w-3.5 h-3.5" />
              {saveMutation.isPending ? 'Saving…' : 'Save Changes'}
            </Button>
          )}
          {saveStatus === 'saved' && (
            <span className="text-xs text-green-600 font-medium">Saved!</span>
          )}
          {saveStatus === 'error' && (
            <span className="text-xs text-destructive font-medium">Save failed</span>
          )}
        </div>
      </div>

      {calendarError && <ErrorAlert message="Failed to load pricing data." />}

      {!selectedPropertyId && !propertiesLoading && (
        <EmptyState title="No Channex properties found. Set up your properties in settings." />
      )}

      {isLoading && <PriceTableSkeleton />}

      {!isLoading && selectedPropertyId && ratePlans.length === 0 && !calendarError && (
        <EmptyState title="No rate plans found for this property." />
      )}

      {!isLoading && ratePlans.length > 0 && (
        <div className="overflow-x-auto rounded-lg border">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">
                  Rate Plan
                </th>
                {dates.map((date) => (
                  <th
                    key={date}
                    className={`px-2 py-2 text-center font-medium whitespace-nowrap min-w-[80px] ${
                      date === today ? 'bg-primary/10 text-primary' : 'text-muted-foreground'
                    }`}
                  >
                    {new Date(date + 'T00:00:00').toLocaleDateString(undefined, {
                      weekday: 'short',
                      month: 'numeric',
                      day: 'numeric',
                    })}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ratePlans.map((rp, idx) => (
                <tr key={rp.id} className={`border-b last:border-b-0 ${idx % 2 === 1 ? 'bg-muted/20' : ''}`}>
                  <td className="px-4 py-2 font-medium whitespace-nowrap">{rp.name}</td>
                  {dates.map((date) => {
                    const value = getRateValue(rp.id, date, rp.rates[date])
                    const edited = isEdited(rp.id, date)
                    return (
                      <td key={date} className={`px-2 py-1.5 ${date === today ? 'bg-primary/5' : ''}`}>
                        <Input
                          type="number"
                          min={0}
                          step={1}
                          value={value}
                          onChange={(e) => handleRateChange(rp.id, date, e.target.value)}
                          className={`h-7 w-20 text-center text-sm ${edited ? 'border-amber-400 bg-amber-50' : ''}`}
                          placeholder="—"
                        />
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
