import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Save, Plus, Trash2, Users, Globe, Bell, Calendar, Tag,
  DollarSign, Settings2,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Label } from '@/components/ui/label'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  fetchSettings, updateSettings, fetchTeamMembers, inviteTeamMember, removeTeamMember,
  type AppSettings,
} from '@/api/platform'

// ── Sub-tabs ───────────────────────────────────────────────────────
type SubTab = 'general' | 'team' | 'notifications' | 'calendar' | 'pricing-ratio' | 'tags' | 'channels' | 'categories'
const SUB_TABS: { key: SubTab; label: string; icon: React.ElementType }[] = [
  { key: 'general', label: 'General', icon: Settings2 },
  { key: 'team', label: 'Team & Permissions', icon: Users },
  { key: 'notifications', label: 'Notifications', icon: Bell },
  { key: 'calendar', label: 'Calendar', icon: Calendar },
  { key: 'pricing-ratio', label: 'Channel Pricing Ratio', icon: DollarSign },
  { key: 'tags', label: 'Tags', icon: Tag },
  { key: 'channels', label: 'Custom Channels', icon: Globe },
  { key: 'categories', label: 'I&E Categories', icon: DollarSign },
]

// ── Team section ───────────────────────────────────────────────────
function TeamSection() {
  const qc = useQueryClient()
  const [showInvite, setShowInvite] = useState(false)
  const [inviteForm, setInviteForm] = useState({ email: '', name: '', role: 'staff' })

  const { data: members = [], isLoading } = useQuery({
    queryKey: ['team-members'],
    queryFn: fetchTeamMembers,
    staleTime: 60_000,
  })

  const inviteMut = useMutation({
    mutationFn: () => inviteTeamMember(inviteForm),
    onSuccess: () => {
      setShowInvite(false)
      setInviteForm({ email: '', name: '', role: 'staff' })
      void qc.invalidateQueries({ queryKey: ['team-members'] })
    },
  })

  const removeMut = useMutation({
    mutationFn: removeTeamMember,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['team-members'] }),
  })

  const ROLE_COLORS: Record<string, string> = {
    owner: 'bg-purple-100 text-purple-700',
    admin: 'bg-blue-100 text-blue-700',
    manager: 'bg-emerald-100 text-emerald-700',
    staff: 'bg-gray-100 text-gray-600',
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Team Members</h3>
        <Dialog open={showInvite} onOpenChange={setShowInvite}>
          <DialogTrigger asChild>
            <Button size="sm"><Plus className="h-3.5 w-3.5 mr-1" /> Invite</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Invite Team Member</DialogTitle></DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Email</Label>
                <Input type="email" value={inviteForm.email} onChange={e => setInviteForm(p => ({ ...p, email: e.target.value }))} />
              </div>
              <div>
                <Label>Name</Label>
                <Input value={inviteForm.name} onChange={e => setInviteForm(p => ({ ...p, name: e.target.value }))} />
              </div>
              <div>
                <Label>Role</Label>
                <Select value={inviteForm.role} onValueChange={v => setInviteForm(p => ({ ...p, role: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="manager">Manager</SelectItem>
                    <SelectItem value="staff">Staff</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button
                onClick={() => inviteMut.mutate()}
                disabled={!inviteForm.email.trim() || !inviteForm.name.trim() || inviteMut.isPending}
                className="w-full"
              >
                {inviteMut.isPending ? 'Inviting…' : 'Send Invite'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[0,1,2].map(i => <Skeleton key={i} className="h-14" />)}</div>
      ) : (
        <div className="rounded-xl border overflow-hidden">
          {members.map(m => (
            <div key={m.id} className="flex items-center gap-3 px-4 py-3 border-b last:border-b-0 hover:bg-muted/30 transition-colors">
              <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium shrink-0">
                {m.name[0]?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{m.name}</p>
                <p className="text-xs text-muted-foreground truncate">{m.email}</p>
              </div>
              <Badge variant="outline" className={ROLE_COLORS[m.role] ?? ''}>{m.role}</Badge>
              <Badge variant={m.is_active ? 'default' : 'secondary'} className="text-xs">
                {m.is_active ? 'Active' : 'Inactive'}
              </Badge>
              {m.role !== 'owner' && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => removeMut.mutate(m.id)}
                  disabled={removeMut.isPending}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Tag list editor ────────────────────────────────────────────────
function TagListEditor({
  items,
  label,
  onSave,
  saving,
}: {
  items: string[]
  label: string
  onSave: (items: string[]) => void
  saving: boolean
}) {
  const [list, setList] = useState<string[]>(items)
  const [draft, setDraft] = useState('')

  function add() {
    const v = draft.trim()
    if (v && !list.includes(v)) {
      setList([...list, v])
      setDraft('')
    }
  }

  function remove(idx: number) {
    setList(list.filter((_, i) => i !== idx))
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {list.map((t, i) => (
          <Badge key={i} variant="outline" className="gap-1 pr-1">
            {t}
            <button onClick={() => remove(i)} className="ml-1 text-muted-foreground hover:text-destructive">×</button>
          </Badge>
        ))}
        {list.length === 0 && <p className="text-sm text-muted-foreground">No {label.toLowerCase()} yet.</p>}
      </div>
      <div className="flex gap-2">
        <Input
          className="h-8 text-sm"
          placeholder={`Add ${label.toLowerCase()}…`}
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
        />
        <Button size="sm" variant="outline" onClick={add} disabled={!draft.trim()}>Add</Button>
        <Button size="sm" onClick={() => onSave(list)} disabled={saving}>
          <Save className="h-3.5 w-3.5 mr-1" />{saving ? 'Saving…' : 'Save'}
        </Button>
      </div>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────
export function SettingsTab() {
  const [subTab, setSubTab] = useState<SubTab>('general')
  const qc = useQueryClient()

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: fetchSettings,
    staleTime: 60_000,
  })

  const updateMut = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['settings'] }),
  })

  const [generalForm, setGeneralForm] = useState<Partial<AppSettings>>({})

  // Sync form when settings load
  const loaded = settings && Object.keys(generalForm).length === 0
  if (loaded) {
    // Will trigger re-render once
    setTimeout(() => setGeneralForm({
      lead_channel: settings.lead_channel,
      default_check_in_time: settings.default_check_in_time,
      default_check_out_time: settings.default_check_out_time,
      timezone: settings.timezone,
      language: settings.language,
      currency: settings.currency,
    }), 0)
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Settings</h2>

      <div className="flex gap-6">
        {/* Sidebar nav */}
        <nav className="w-48 shrink-0 space-y-0.5">
          {SUB_TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setSubTab(t.key)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                subTab === t.key
                  ? 'bg-muted font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`}
            >
              <t.icon className="h-4 w-4" />
              {t.label}
            </button>
          ))}
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {isLoading && subTab !== 'team' ? (
            <div className="space-y-3">{[0,1,2].map(i => <Skeleton key={i} className="h-12" />)}</div>
          ) : (
            <>
              {subTab === 'general' && settings && (
                <div className="space-y-4 max-w-md">
                  <div>
                    <Label>Lead Channel</Label>
                    <Input
                      value={generalForm.lead_channel ?? ''}
                      onChange={e => setGeneralForm(p => ({ ...p, lead_channel: e.target.value }))}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>Default Check-in Time</Label>
                      <Input
                        type="time"
                        value={generalForm.default_check_in_time ?? ''}
                        onChange={e => setGeneralForm(p => ({ ...p, default_check_in_time: e.target.value }))}
                      />
                    </div>
                    <div>
                      <Label>Default Check-out Time</Label>
                      <Input
                        type="time"
                        value={generalForm.default_check_out_time ?? ''}
                        onChange={e => setGeneralForm(p => ({ ...p, default_check_out_time: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div>
                    <Label>Timezone</Label>
                    <Input
                      value={generalForm.timezone ?? ''}
                      onChange={e => setGeneralForm(p => ({ ...p, timezone: e.target.value }))}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>Language</Label>
                      <Input
                        value={generalForm.language ?? ''}
                        onChange={e => setGeneralForm(p => ({ ...p, language: e.target.value }))}
                      />
                    </div>
                    <div>
                      <Label>Currency</Label>
                      <Input
                        value={generalForm.currency ?? ''}
                        onChange={e => setGeneralForm(p => ({ ...p, currency: e.target.value }))}
                      />
                    </div>
                  </div>
                  <Button
                    onClick={() => updateMut.mutate(generalForm)}
                    disabled={updateMut.isPending}
                  >
                    <Save className="h-3.5 w-3.5 mr-1" />
                    {updateMut.isPending ? 'Saving…' : 'Save Settings'}
                  </Button>
                </div>
              )}

              {subTab === 'team' && <TeamSection />}

              {subTab === 'notifications' && (
                <div className="rounded-lg border p-6 text-center text-sm text-muted-foreground">
                  Configure push notifications and email alerts for bookings, messages, and tasks.
                </div>
              )}

              {subTab === 'calendar' && (
                <div className="rounded-lg border p-6 text-center text-sm text-muted-foreground">
                  Calendar display preferences. Configure week start day and default calendar view.
                </div>
              )}

              {subTab === 'pricing-ratio' && settings && (
                <div className="space-y-4 max-w-md">
                  <p className="text-sm text-muted-foreground">
                    Set pricing ratios per channel. A ratio of 1.0 means the base price is used as-is.
                  </p>
                  {Object.entries(settings.channel_pricing_ratios).map(([ch, ratio]) => (
                    <div key={ch} className="flex items-center gap-3">
                      <Badge variant="outline" className="w-20 justify-center capitalize">{ch}</Badge>
                      <Input
                        type="number"
                        step="0.01"
                        className="w-24 h-8 text-sm"
                        defaultValue={ratio}
                        onBlur={e => {
                          const v = parseFloat(e.target.value)
                          if (!isNaN(v)) {
                            updateMut.mutate({
                              channel_pricing_ratios: { ...settings.channel_pricing_ratios, [ch]: v },
                            })
                          }
                        }}
                      />
                      <span className="text-xs text-muted-foreground">× base price</span>
                    </div>
                  ))}
                </div>
              )}

              {subTab === 'tags' && settings && (
                <TagListEditor
                  items={settings.tags}
                  label="Tags"
                  onSave={tags => updateMut.mutate({ tags })}
                  saving={updateMut.isPending}
                />
              )}

              {subTab === 'channels' && settings && (
                <TagListEditor
                  items={settings.custom_channels}
                  label="Custom Channels"
                  onSave={custom_channels => updateMut.mutate({ custom_channels })}
                  saving={updateMut.isPending}
                />
              )}

              {subTab === 'categories' && settings && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-semibold mb-3">Income Categories</h3>
                    <TagListEditor
                      items={settings.income_categories}
                      label="Income Category"
                      onSave={income_categories => updateMut.mutate({ income_categories })}
                      saving={updateMut.isPending}
                    />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold mb-3">Expense Categories</h3>
                    <TagListEditor
                      items={settings.expense_categories}
                      label="Expense Category"
                      onSave={expense_categories => updateMut.mutate({ expense_categories })}
                      saving={updateMut.isPending}
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
