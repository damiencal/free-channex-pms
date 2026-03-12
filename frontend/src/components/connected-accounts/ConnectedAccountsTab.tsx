import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link2, AlertTriangle, Wifi, WifiOff, Plus, Trash2, RefreshCw, CheckCircle2, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  fetchConnectedAccounts,
  fetchLinkedListings,
  createConnection,
  deleteConnection,
  testConnection,
  syncConnection,
  type ConnectedAccount,
} from '@/api/platform'

const STATUS_STYLES: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  active:   { label: 'Active', color: 'bg-emerald-100 text-emerald-700', icon: Wifi },
  inactive: { label: 'Inactive', color: 'bg-gray-100 text-gray-600', icon: WifiOff },
  error:    { label: 'Error', color: 'bg-red-100 text-red-600', icon: AlertTriangle },
}

const CHANNEL_COLORS: Record<string, string> = {
  airbnb:  'bg-rose-100 text-rose-700 border-rose-200',
  booking: 'bg-blue-100 text-blue-700 border-blue-200',
  vrbo:    'bg-cyan-100 text-cyan-700 border-cyan-200',
  expedia: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  channex: 'bg-violet-100 text-violet-700 border-violet-200',
}

function channelClass(channel: string) {
  return CHANNEL_COLORS[channel.toLowerCase()] ?? 'bg-muted text-muted-foreground border-border'
}

// ── Add Connection Dialog ────────────────────────────────────────────
function AddConnectionDialog({
  open,
  onClose,
  onSave,
}: {
  open: boolean
  onClose: () => void
  onSave: (name: string, token: string) => Promise<unknown>
}) {
  const [name, setName] = useState('')
  const [token, setToken] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() || !token.trim()) return
    setSaving(true)
    setError(null)
    try {
      await onSave(name.trim(), token.trim())
      setName('')
      setToken('')
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add connection'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  function handleClose() {
    if (saving) return
    setName('')
    setToken('')
    setError(null)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) handleClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Connect Channex Account</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="conn-name">Connection Name</Label>
            <Input
              id="conn-name"
              placeholder="e.g. My Channex Account"
              value={name}
              onChange={e => setName(e.target.value)}
              disabled={saving}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="conn-token">API Token</Label>
            <Input
              id="conn-token"
              type="password"
              placeholder="Your Channex user-api-key"
              value={token}
              onChange={e => setToken(e.target.value)}
              disabled={saving}
            />
            <p className="text-xs text-muted-foreground">
              Found in Channex → Settings → API Access.
            </p>
          </div>
          {error && (
            <p className="text-sm text-red-600 flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5" />
              {error}
            </p>
          )}
          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={handleClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving || !name.trim() || !token.trim()}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : null}
              {saving ? 'Connecting…' : 'Connect'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ── Account Row ──────────────────────────────────────────────────────
function AccountRow({ account }: { account: ConnectedAccount }) {
  const queryClient = useQueryClient()
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const deleteMut = useMutation({
    mutationFn: () => deleteConnection(account.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['connected-accounts'] }),
  })

  const testMut = useMutation({
    mutationFn: () => testConnection(account.id),
    onSuccess: data => {
      setActionMsg(data.message)
      queryClient.invalidateQueries({ queryKey: ['connected-accounts'] })
      setTimeout(() => setActionMsg(null), 4000)
    },
  })

  const syncMut = useMutation({
    mutationFn: () => syncConnection(account.id),
    onSuccess: data => {
      setActionMsg(`Synced ${data.synced} propert${data.synced === 1 ? 'y' : 'ies'}.`)
      queryClient.invalidateQueries({ queryKey: ['connected-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['linked-listings'] })
      setTimeout(() => setActionMsg(null), 4000)
    },
  })

  const style = STATUS_STYLES[account.status] ?? STATUS_STYLES.inactive
  const StatusIcon = style.icon
  const busy = testMut.isPending || syncMut.isPending || deleteMut.isPending

  return (
    <div className="px-4 py-3 border-t space-y-1">
      <div className="grid grid-cols-[2fr_1fr_1fr_auto] gap-2 items-center text-sm">
        {/* Channel + name */}
        <div className="flex items-center gap-3 min-w-0">
          <Badge variant="outline" className={channelClass(account.channel)}>
            {account.channel}
          </Badge>
          <div className="min-w-0">
            <p className="font-medium truncate">{account.account_name}</p>
            {account.api_token_hint && (
              <p className="text-xs text-muted-foreground font-mono">{account.api_token_hint}</p>
            )}
          </div>
        </div>

        {/* Listing count */}
        <span>{account.listing_count} listing{account.listing_count !== 1 ? 's' : ''}</span>

        {/* Status */}
        <div>
          <Badge variant="outline" className={`${style.color} gap-1`}>
            <StatusIcon className="h-3 w-3" />
            {style.label}
          </Badge>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => testMut.mutate()}
            disabled={busy}
            title="Test connection"
          >
            {testMut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => syncMut.mutate()}
            disabled={busy}
            title="Sync properties"
          >
            {syncMut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-destructive hover:text-destructive hover:bg-red-50"
            onClick={() => { if (confirm('Delete this connection?')) deleteMut.mutate() }}
            disabled={busy}
            title="Delete connection"
          >
            {deleteMut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </div>

      {/* Inline feedback */}
      {actionMsg && (
        <p className="text-xs text-muted-foreground pl-1">{actionMsg}</p>
      )}
      {account.last_synced_at && (
        <p className="text-xs text-muted-foreground pl-1">
          Last synced: {new Date(account.last_synced_at).toLocaleString()}
        </p>
      )}
    </div>
  )
}

// ── Main Tab ─────────────────────────────────────────────────────────
export function ConnectedAccountsTab() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ['connected-accounts'],
    queryFn: fetchConnectedAccounts,
    staleTime: 60_000,
  })

  const { data: allListings = [] } = useQuery({
    queryKey: ['linked-listings'],
    queryFn: () => fetchLinkedListings(),
    staleTime: 60_000,
  })

  const addMut = useMutation({
    mutationFn: ({ name, api_token }: { name: string; api_token: string }) =>
      createConnection({ name, api_token }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['connected-accounts'] }),
  })

  const unlinked = allListings.filter(l => !l.is_linked)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Connected Accounts</h2>
          <p className="text-sm text-muted-foreground">
            {accounts.length} account{accounts.length !== 1 ? 's' : ''} connected
          </p>
        </div>
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-1.5" />
          Connect Channex
        </Button>
      </div>

      {/* Unlinked listings alert */}
      {unlinked.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/20 px-4 py-3 flex items-center gap-2 text-sm text-amber-700">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            <span className="font-medium">{unlinked.length} unlinked listing{unlinked.length !== 1 ? 's' : ''}.</span>
            {' '}Link them to properties to sync availability.
          </span>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">{[0,1,2].map(i => <Skeleton key={i} className="h-20 rounded-lg" />)}</div>
      ) : accounts.length === 0 ? (
        <div className="text-center py-16 space-y-3">
          <Link2 className="h-10 w-10 text-muted-foreground/40 mx-auto" />
          <p className="text-sm text-muted-foreground">No accounts connected yet.</p>
          <Button size="sm" variant="outline" onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-1.5" />
            Add your first Channex connection
          </Button>
        </div>
      ) : (
        <div className="rounded-xl border overflow-hidden">
          <div className="grid grid-cols-[2fr_1fr_1fr_auto] gap-2 px-4 py-2 bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground font-medium">
            <span>Account</span>
            <span>Listings</span>
            <span>Status</span>
            <span className="pr-1">Actions</span>
          </div>
          {accounts.map(a => <AccountRow key={a.id} account={a} />)}
        </div>
      )}

      {/* Unlinked listings detail */}
      {unlinked.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-3">Unlinked Listings</h3>
          <div className="rounded-xl border overflow-hidden">
            <div className="grid grid-cols-4 gap-2 px-4 py-2 bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground font-medium">
              <span className="col-span-2">Listing</span>
              <span>Channel</span>
              <span className="text-right">Inventory</span>
            </div>
            {unlinked.map(l => (
              <div key={l.id} className="grid grid-cols-4 gap-2 px-4 py-2.5 border-t items-center text-sm">
                <span className="col-span-2 truncate font-medium">{l.listing_name}</span>
                <Badge variant="outline" className={channelClass(l.channel)}>{l.channel}</Badge>
                <span className="text-right text-muted-foreground">{l.inventory}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <AddConnectionDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSave={(name, api_token) => addMut.mutateAsync({ name, api_token })}
      />
    </div>
  )
}
