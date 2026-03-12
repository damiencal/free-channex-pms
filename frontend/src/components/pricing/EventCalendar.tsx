import { useState } from 'react'
import { format, addDays } from 'date-fns'
import { Plus, Trash2, CalendarDays, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  useMarketEvents,
  useCreateEvent,
  useDeleteEvent,
  useSeedHolidays,
} from '@/hooks/usePricing'
import type { MarketEventPayload } from '@/api/pricing'
import { usePropertyStore } from '@/store/usePropertyStore'

const EVENT_TYPE_COLORS: Record<string, string> = {
  holiday: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  local_event: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  season: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  conference: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
  custom: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
}

const modifierLabel = (v: string) => {
  const n = parseFloat(v)
  if (n > 1) return `+${Math.round((n - 1) * 100)}% demand`
  if (n < 1) return `-${Math.round((1 - n) * 100)}% demand`
  return 'Neutral'
}

type FormState = {
  name: string
  event_type: string
  start_date: string
  end_date: string
  demand_modifier: string
  recurrence: string
  description: string
}

const DEFAULT_FORM: FormState = {
  name: '',
  event_type: 'local_event',
  start_date: format(new Date(), 'yyyy-MM-dd'),
  end_date: format(addDays(new Date(), 1), 'yyyy-MM-dd'),
  demand_modifier: '1.2',
  recurrence: 'none',
  description: '',
}

export function EventCalendar() {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  const { data: events, isLoading } = useMarketEvents()
  const createEvent = useCreateEvent()
  const deleteEvent = useDeleteEvent()
  const seedHolidays = useSeedHolidays()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<FormState>(DEFAULT_FORM)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload: MarketEventPayload = {
      name: form.name,
      event_type: form.event_type,
      start_date: form.start_date,
      end_date: form.end_date,
      demand_modifier: parseFloat(form.demand_modifier),
      recurrence: form.recurrence,
      description: form.description || undefined,
      property_id: propertyId ?? null,
    }
    createEvent.mutate(payload, {
      onSuccess: () => {
        setOpen(false)
        setForm(DEFAULT_FORM)
      },
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h3 className="text-lg font-semibold">Market Events</h3>
        <div className="ml-auto flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => seedHolidays.mutate()}
            disabled={seedHolidays.isPending}
          >
            <Sparkles className="mr-1.5 h-4 w-4" />
            Seed Holidays
          </Button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="mr-1.5 h-4 w-4" />
                Add Event
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Market Event</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-3">
                <div className="space-y-1.5">
                  <Label>Event Name</Label>
                  <Input
                    required
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder="e.g. Local Music Festival"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>Type</Label>
                    <Select
                      value={form.event_type}
                      onValueChange={(v) => setForm((f) => ({ ...f, event_type: v }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="holiday">Holiday</SelectItem>
                        <SelectItem value="local_event">Local Event</SelectItem>
                        <SelectItem value="season">Season</SelectItem>
                        <SelectItem value="conference">Conference</SelectItem>
                        <SelectItem value="custom">Custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Recurrence</Label>
                    <Select
                      value={form.recurrence}
                      onValueChange={(v) => setForm((f) => ({ ...f, recurrence: v }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">One-time</SelectItem>
                        <SelectItem value="yearly">Yearly</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>Start Date</Label>
                    <Input
                      type="date"
                      required
                      value={form.start_date}
                      onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>End Date</Label>
                    <Input
                      type="date"
                      required
                      value={form.end_date}
                      onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label>Demand Modifier (e.g. 1.3 = +30%)</Label>
                  <Input
                    type="number"
                    step="0.05"
                    min="0.1"
                    max="5"
                    required
                    value={form.demand_modifier}
                    onChange={(e) => setForm((f) => ({ ...f, demand_modifier: e.target.value }))}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Description (optional)</Label>
                  <Input
                    value={form.description}
                    onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                    placeholder="Notes about this event…"
                  />
                </div>
                <Button type="submit" className="w-full" disabled={createEvent.isPending}>
                  {createEvent.isPending ? 'Adding…' : 'Add Event'}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {seedHolidays.isSuccess && (
        <p className="text-sm text-green-600 dark:text-green-400">
          Seeded {seedHolidays.data?.created} holidays ({seedHolidays.data?.skipped} already existed).
        </p>
      )}

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading events…</div>
      ) : !events?.length ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            <CalendarDays className="mx-auto mb-2 h-8 w-8 opacity-30" />
            <p>No market events defined.</p>
            <p className="text-sm">Click "Seed Holidays" to get started with common US holidays.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {events.map((event) => (
            <Card key={event.id} className="flex items-center gap-3 px-4 py-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm truncate">{event.name}</span>
                  <Badge
                    className={`text-[10px] h-4 ${EVENT_TYPE_COLORS[event.event_type] ?? ''}`}
                    variant="outline"
                  >
                    {event.event_type}
                  </Badge>
                  {event.recurrence === 'yearly' && (
                    <Badge variant="outline" className="text-[10px] h-4">
                      Recurring
                    </Badge>
                  )}
                  {!event.property_id && (
                    <Badge variant="secondary" className="text-[10px] h-4">
                      Global
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {format(new Date(event.start_date + 'T12:00:00'), 'MMM d')} –{' '}
                  {format(new Date(event.end_date + 'T12:00:00'), 'MMM d, yyyy')} ·{' '}
                  {modifierLabel(event.demand_modifier)}
                </p>
              </div>
              {event.property_id && (
                <Button
                  size="icon"
                  variant="ghost"
                  className="shrink-0 text-muted-foreground hover:text-destructive"
                  onClick={() => deleteEvent.mutate(event.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
