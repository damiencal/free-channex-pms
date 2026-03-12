import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, Trash2, MessageSquare, Star, DollarSign,
  ClipboardList, Zap, AlertCircle,
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
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  fetchAutomationRules, createAutomationRule, toggleAutomationRule,
  deleteAutomationRule, fetchPendingActions,
  type AutomationRule, type AutomationRulePayload, type PendingAction,
} from '@/api/platform'

// ── Types & categories ─────────────────────────────────────────────
type RuleType = AutomationRule['type']
const RULE_TYPES: { key: RuleType; label: string; icon: React.ElementType }[] = [
  { key: 'message', label: 'Message', icon: MessageSquare },
  { key: 'review', label: 'Review', icon: Star },
  { key: 'price', label: 'Price', icon: DollarSign },
  { key: 'task', label: 'Task', icon: ClipboardList },
]

// ── Top-level tabs ─────────────────────────────────────────────────
type TopTab = 'overview' | RuleType
const TOP_TABS: { key: TopTab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'message', label: 'Message Rules' },
  { key: 'review', label: 'Review Rules' },
  { key: 'price', label: 'Price Rules' },
  { key: 'task', label: 'Task Rules' },
]

// ── Create rule dialog ─────────────────────────────────────────────
function CreateRuleForm({
  defaultType,
  onSave,
  saving,
}: {
  defaultType: RuleType
  onSave: (p: AutomationRulePayload) => void
  saving: boolean
}) {
  const [form, setForm] = useState<AutomationRulePayload>({
    name: '',
    type: defaultType,
    trigger: '',
    is_active: true,
  })

  return (
    <div className="space-y-4">
      <div>
        <Label>Name</Label>
        <Input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
      </div>
      <div>
        <Label>Type</Label>
        <Select value={form.type} onValueChange={v => setForm(p => ({ ...p, type: v as RuleType }))}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {RULE_TYPES.map(t => <SelectItem key={t.key} value={t.key}>{t.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label>Trigger</Label>
        <Input
          placeholder="e.g. booking_confirmed, check_in_24h, new_review"
          value={form.trigger}
          onChange={e => setForm(p => ({ ...p, trigger: e.target.value }))}
        />
      </div>
      <Button
        onClick={() => onSave(form)}
        disabled={!form.name.trim() || !form.trigger.trim() || saving}
        className="w-full"
      >
        {saving ? 'Creating…' : 'Create Rule'}
      </Button>
    </div>
  )
}

// ── Pending actions table ──────────────────────────────────────────
function PendingActionsTable({ actions, isLoading }: { actions: PendingAction[]; isLoading: boolean }) {
  if (isLoading) {
    return <div className="space-y-2">{[0,1,2].map(i => <Skeleton key={i} className="h-10" />)}</div>
  }
  if (actions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        No pending automation actions.
      </p>
    )
  }
  return (
    <div className="rounded-xl border overflow-hidden">
      <div className="grid grid-cols-6 gap-2 px-4 py-2 bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground font-medium">
        <span>Type</span>
        <span>Event</span>
        <span>Property</span>
        <span>Channel</span>
        <span>Date</span>
        <span className="text-right">Status</span>
      </div>
      {actions.map(a => (
        <div key={a.id} className="grid grid-cols-6 gap-2 px-4 py-2.5 border-t items-center text-sm">
          <Badge variant="outline">{a.type}</Badge>
          <span className="truncate">{a.event}</span>
          <span className="truncate text-muted-foreground">{a.property_name}</span>
          <span className="text-muted-foreground">{a.channel}</span>
          <span className="text-muted-foreground">{new Date(a.date).toLocaleDateString()}</span>
          <div className="text-right">
            <Badge variant={a.status === 'completed' ? 'default' : a.status === 'pending' ? 'secondary' : 'outline'}>
              {a.status}
            </Badge>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Rule list ──────────────────────────────────────────────────────
function RuleRow({
  rule,
  onToggle,
  onDelete,
}: {
  rule: AutomationRule
  onToggle: (id: number, active: boolean) => void
  onDelete: (id: number) => void
}) {
  const typeInfo = RULE_TYPES.find(t => t.key === rule.type)
  const Icon = typeInfo?.icon ?? Zap

  return (
    <div className="flex items-center gap-3 px-4 py-3 border-b last:border-b-0 hover:bg-muted/30 transition-colors">
      <div className="p-2 rounded-lg bg-muted">
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{rule.name}</p>
        <p className="text-xs text-muted-foreground">
          Trigger: {rule.trigger} · {rule.channel || 'All channels'}
        </p>
      </div>
      <Switch
        checked={rule.is_active}
        onCheckedChange={v => onToggle(rule.id, v)}
      />
      <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={() => onDelete(rule.id)}>
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────
export function AutomationTab() {
  const [topTab, setTopTab] = useState<TopTab>('overview')
  const [showCreate, setShowCreate] = useState(false)
  const qc = useQueryClient()

  const { data: rules = [], isLoading: loadingRules } = useQuery({
    queryKey: ['automation-rules'],
    queryFn: fetchAutomationRules,
    staleTime: 60_000,
  })

  const { data: pending = [], isLoading: loadingPending } = useQuery({
    queryKey: ['automation-pending'],
    queryFn: fetchPendingActions,
    staleTime: 60_000,
    enabled: topTab === 'overview',
  })

  const createMut = useMutation({
    mutationFn: createAutomationRule,
    onSuccess: () => {
      setShowCreate(false)
      void qc.invalidateQueries({ queryKey: ['automation-rules'] })
    },
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => toggleAutomationRule(id, active),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['automation-rules'] }),
  })

  const deleteMut = useMutation({
    mutationFn: deleteAutomationRule,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['automation-rules'] }),
  })

  const filtered = topTab === 'overview' ? rules : rules.filter(r => r.type === topTab)
  const rulesByType = (type: RuleType) => rules.filter(r => r.type === type)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h2 className="text-lg font-semibold">Automation</h2>
        <Dialog open={showCreate} onOpenChange={setShowCreate}>
          <DialogTrigger asChild>
            <Button size="sm"><Plus className="h-3.5 w-3.5 mr-1" /> New Rule</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create Automation Rule</DialogTitle></DialogHeader>
            <CreateRuleForm
              defaultType={topTab !== 'overview' ? topTab as RuleType : 'message'}
              onSave={p => createMut.mutate(p)}
              saving={createMut.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Top tab bar */}
      <div className="flex gap-1 overflow-x-auto rounded-lg bg-muted p-1">
        {TOP_TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTopTab(t.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-all ${
              topTab === t.key ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t.label}
            {t.key !== 'overview' && (
              <span className="ml-1.5 text-xs text-muted-foreground">
                ({rulesByType(t.key as RuleType).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {topTab === 'overview' && (
        <div className="space-y-6">
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {RULE_TYPES.map(t => {
              const count = rulesByType(t.key).length
              const active = rulesByType(t.key).filter(r => r.is_active).length
              return (
                <button
                  key={t.key}
                  onClick={() => setTopTab(t.key)}
                  className="rounded-xl border bg-card p-4 text-left hover:bg-muted/30 transition-colors"
                >
                  <t.icon className="h-5 w-5 mb-2 text-muted-foreground" />
                  <p className="text-2xl font-bold">{count}</p>
                  <p className="text-xs text-muted-foreground">{t.label} rules · {active} active</p>
                </button>
              )
            })}
          </div>

          {/* Pending actions */}
          <div>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-500" />
              Pending Actions
            </h3>
            <PendingActionsTable actions={pending} isLoading={loadingPending} />
          </div>
        </div>
      )}

      {topTab !== 'overview' && (
        <div className="rounded-xl border overflow-hidden">
          {loadingRules ? (
            <div className="p-4 space-y-2">{[0,1,2].map(i => <Skeleton key={i} className="h-14" />)}</div>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-12">
              No {topTab} rules yet. Create one to get started.
            </p>
          ) : (
            filtered.map(r => (
              <RuleRow
                key={r.id}
                rule={r}
                onToggle={(id, active) => toggleMut.mutate({ id, active })}
                onDelete={id => deleteMut.mutate(id)}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}
