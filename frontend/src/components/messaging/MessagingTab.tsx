import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, ToggleLeft, ToggleRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  fetchTemplates,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  type MessageTemplate,
  type TemplatePayload,
} from '@/api/messaging'

const TRIGGER_LABELS: Record<MessageTemplate['trigger_event'], string> = {
  booking_confirmed: 'Booking Confirmed',
  check_in: 'Check-in',
  check_out: 'Check-out',
  review_request: 'Review Request',
}

const CHANNEL_LABELS: Record<MessageTemplate['channel'], string> = {
  channex: 'Channex Message',
  email: 'Email',
}

const EMPTY_FORM: TemplatePayload = {
  name: '',
  trigger_event: 'booking_confirmed',
  offset_hours: 0,
  subject: '',
  body_template: '',
  channel: 'channex',
  is_active: true,
  property_id: null,
}

// ---------------------------------------------------------------------------
// Template form
// ---------------------------------------------------------------------------

function TemplateForm({
  initial,
  onSave,
  onCancel,
  saving,
  error,
}: {
  initial: TemplatePayload
  onSave: (p: TemplatePayload) => void
  onCancel: () => void
  saving: boolean
  error?: string | null
}) {
  const [form, setForm] = useState<TemplatePayload>(initial)

  function field<K extends keyof TemplatePayload>(key: K, value: TemplatePayload[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  return (
    <div className="border rounded-xl p-4 space-y-3 bg-muted/30">
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2 space-y-1">
          <Label className="text-xs">Template Name</Label>
          <Input
            value={form.name}
            onChange={(e) => field('name', e.target.value)}
            placeholder="e.g. Check-in Welcome Message"
            className="h-8 text-sm"
          />
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Trigger Event</Label>
          <Select
            value={form.trigger_event}
            onValueChange={(v) => field('trigger_event', v as MessageTemplate['trigger_event'])}
          >
            <SelectTrigger className="h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(TRIGGER_LABELS).map(([k, label]) => (
                <SelectItem key={k} value={k}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Offset Hours</Label>
          <Input
            type="number"
            value={form.offset_hours}
            onChange={(e) => field('offset_hours', parseInt(e.target.value, 10) || 0)}
            className="h-8 text-sm"
            placeholder="-2 = 2h before, 24 = 1 day after"
          />
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Channel</Label>
          <Select
            value={form.channel}
            onValueChange={(v) => field('channel', v as MessageTemplate['channel'])}
          >
            <SelectTrigger className="h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(CHANNEL_LABELS).map(([k, label]) => (
                <SelectItem key={k} value={k}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {form.channel === 'email' && (
          <div className="space-y-1">
            <Label className="text-xs">Subject</Label>
            <Input
              value={form.subject ?? ''}
              onChange={(e) => field('subject', e.target.value)}
              placeholder="Email subject line"
              className="h-8 text-sm"
            />
          </div>
        )}
      </div>

      <div className="space-y-1">
        <Label className="text-xs">
          Body Template{' '}
          <span className="text-muted-foreground">(Jinja2: {'{{ guest_name }}, {{ check_in }}, {{ check_out }}'})</span>
        </Label>
        <Textarea
          value={form.body_template}
          onChange={(e) => field('body_template', e.target.value)}
          placeholder="Hi {{ guest_name }}, your check-in is on {{ check_in }}…"
          className="text-sm min-h-[100px] font-mono text-xs"
        />
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}

      <div className="flex gap-2">
        <Button
          size="sm"
          disabled={saving || !form.name.trim() || !form.body_template.trim()}
          onClick={() => onSave(form)}
        >
          {saving ? 'Saving…' : 'Save Template'}
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Template row
// ---------------------------------------------------------------------------

function TemplateRow({ tmpl }: { tmpl: MessageTemplate }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)

  const toggleMutation = useMutation({
    mutationFn: () => updateTemplate(tmpl.id, { is_active: !tmpl.is_active }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['messaging', 'templates'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteTemplate(tmpl.id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['messaging', 'templates'] }),
  })

  const updateMutation = useMutation({
    mutationFn: (payload: TemplatePayload) => updateTemplate(tmpl.id, payload),
    onSuccess: () => {
      setEditing(false)
      void queryClient.invalidateQueries({ queryKey: ['messaging', 'templates'] })
    },
  })

  if (editing) {
    return (
      <TemplateForm
        initial={{
          name: tmpl.name,
          trigger_event: tmpl.trigger_event,
          offset_hours: tmpl.offset_hours,
          subject: tmpl.subject,
          body_template: tmpl.body_template,
          channel: tmpl.channel,
          is_active: tmpl.is_active,
          property_id: tmpl.property_id,
        }}
        onSave={(p) => updateMutation.mutate(p)}
        onCancel={() => setEditing(false)}
        saving={updateMutation.isPending}
        error={updateMutation.isError ? String(updateMutation.error) : null}
      />
    )
  }

  return (
    <div className="flex items-start gap-3 rounded-xl border p-3 bg-card shadow-sm">
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm">{tmpl.name}</span>
          <Badge variant={tmpl.is_active ? 'default' : 'secondary'} className="text-xs">
            {tmpl.is_active ? 'Active' : 'Paused'}
          </Badge>
          <Badge variant="outline" className="text-xs">{TRIGGER_LABELS[tmpl.trigger_event]}</Badge>
          <Badge variant="outline" className="text-xs">{CHANNEL_LABELS[tmpl.channel]}</Badge>
          {tmpl.offset_hours !== 0 && (
            <span className="text-xs text-muted-foreground">
              {tmpl.offset_hours > 0 ? `+${tmpl.offset_hours}h after` : `${Math.abs(tmpl.offset_hours)}h before`}
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground line-clamp-2 font-mono">{tmpl.body_template}</p>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => toggleMutation.mutate()}
          disabled={toggleMutation.isPending}
          title={tmpl.is_active ? 'Pause' : 'Activate'}
        >
          {tmpl.is_active
            ? <ToggleRight className="w-4 h-4 text-green-600" />
            : <ToggleLeft className="w-4 h-4 text-muted-foreground" />}
        </Button>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setEditing(true)}>
          <Pencil className="w-3.5 h-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-destructive hover:text-destructive"
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// MessagingTab
// ---------------------------------------------------------------------------

export function MessagingTab() {
  const [showAdd, setShowAdd] = useState(false)
  const queryClient = useQueryClient()

  const { data: templates = [], isLoading, isError, error } = useQuery<MessageTemplate[]>({
    queryKey: ['messaging', 'templates'],
    queryFn: fetchTemplates,
  })

  const createMutation = useMutation({
    mutationFn: createTemplate,
    onSuccess: () => {
      setShowAdd(false)
      void queryClient.invalidateQueries({ queryKey: ['messaging', 'templates'] })
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Automated Messaging</h2>
          <p className="text-sm text-muted-foreground">
            Define templates triggered by booking events.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowAdd((v) => !v)} className="gap-1.5">
          <Plus className="w-4 h-4" />
          Add Template
        </Button>
      </div>

      {showAdd && (
        <TemplateForm
          initial={EMPTY_FORM}
          onSave={(p) => createMutation.mutate(p)}
          onCancel={() => setShowAdd(false)}
          saving={createMutation.isPending}
          error={createMutation.isError ? String(createMutation.error) : null}
        />
      )}

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
        </div>
      ) : isError ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Failed to load'}
        </p>
      ) : templates.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed p-10 text-center text-muted-foreground text-sm">
          No templates yet. Create one to automate guest communication.
        </div>
      ) : (
        <div className="space-y-2">
          {templates.map((t) => <TemplateRow key={t.id} tmpl={t} />)}
        </div>
      )}
    </div>
  )
}
