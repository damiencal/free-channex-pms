import { useState } from 'react'
import { Plus, Trash2, RefreshCw, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
  useCompSets,
  useCreateCompSet,
  useDeleteCompSet,
  useRefreshCompSet,
  useAddCompSetMember,
  useRemoveCompSetMember,
  useCompSet,
} from '@/hooks/useAnalytics'
import { usePropertyStore } from '@/store/usePropertyStore'

function CompSetDetail({ id }: { id: number }) {
  const { data: cs, isLoading } = useCompSet(id)
  const addMember = useAddCompSetMember()
  const removeMember = useRemoveCompSetMember()
  const refresh = useRefreshCompSet()
  const [name, setName] = useState('')
  const [refId, setRefId] = useState('')

  if (isLoading || !cs) return <div className="text-sm text-muted-foreground">Loading…</div>

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h4 className="font-medium">{cs.name}</h4>
        <Button
          size="sm"
          variant="outline"
          onClick={() => refresh.mutate(id)}
          disabled={refresh.isPending}
        >
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${refresh.isPending ? 'animate-spin' : ''}`} />
          Refresh Rates
        </Button>
      </div>

      {cs.members?.map((m) => (
        <div key={m.id} className="flex items-center gap-2 rounded border px-3 py-2 text-sm">
          <div className="flex-1">
            <p className="font-medium">{m.name}</p>
            {m.avg_rate && (
              <p className="text-xs text-muted-foreground">
                Avg Rate: ${parseFloat(m.avg_rate).toFixed(0)} ·{' '}
                {m.avg_occupancy
                  ? `${(parseFloat(m.avg_occupancy) * 100).toFixed(0)}% occ.`
                  : 'No occupancy data'}
              </p>
            )}
          </div>
          <Button
            size="icon"
            variant="ghost"
            className="text-muted-foreground hover:text-destructive"
            onClick={() => removeMember.mutate({ compSetId: id, memberId: m.id })}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ))}

      <div className="flex gap-2">
        <Input
          placeholder="Property name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1"
        />
        <Input
          placeholder="Property ID (optional)"
          value={refId}
          onChange={(e) => setRefId(e.target.value)}
          className="w-36"
          type="number"
        />
        <Button
          size="sm"
          onClick={() => {
            if (!name.trim()) return
            addMember.mutate({
              compSetId: id,
              payload: {
                name: name.trim(),
                source: refId ? 'internal' : 'manual',
                ref_property_id: refId ? parseInt(refId) : undefined,
              },
            })
            setName('')
            setRefId('')
          }}
          disabled={!name.trim() || addMember.isPending}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

export function CompSetManager() {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  const { data: compSets, isLoading } = useCompSets()
  const createCompSet = useCreateCompSet()
  const deleteCompSet = useDeleteCompSet()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [newName, setNewName] = useState('')
  const [open, setOpen] = useState(false)

  if (!propertyId) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Select a property to manage comp sets.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h3 className="text-lg font-semibold">Competitive Sets</h3>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm" className="ml-auto">
              <Plus className="mr-1.5 h-4 w-4" />
              New Comp Set
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Comp Set</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label>Name</Label>
                <Input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Nearby 2BR Villas"
                />
              </div>
              <Button
                className="w-full"
                disabled={!newName.trim() || createCompSet.isPending}
                onClick={() =>
                  createCompSet.mutate(
                    { property_id: propertyId, name: newName.trim() },
                    {
                      onSuccess: (cs) => {
                        setOpen(false)
                        setNewName('')
                        setSelectedId(cs.id)
                      },
                    }
                  )
                }
              >
                Create
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : !compSets?.length ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            <Users className="mx-auto mb-2 h-8 w-8 opacity-30" />
            <p>No comp sets defined.</p>
            <p className="text-sm">Create one to benchmark against comparable properties.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Comp set list */}
          <div className="space-y-2">
            {compSets.map((cs) => (
              <div
                key={cs.id}
                className={`flex cursor-pointer items-center gap-2 rounded border px-3 py-2.5 transition-colors ${
                  selectedId === cs.id ? 'bg-muted' : 'hover:bg-muted/50'
                }`}
                onClick={() => setSelectedId(cs.id)}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{cs.name}</p>
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  className="text-muted-foreground hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteCompSet.mutate(cs.id)
                    if (selectedId === cs.id) setSelectedId(null)
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          {/* Detail panel */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">
                {selectedId ? 'Comp Set Members' : 'Select a comp set to manage members'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedId ? (
                <CompSetDetail id={selectedId} />
              ) : (
                <p className="text-sm text-muted-foreground">Click a comp set on the left.</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
