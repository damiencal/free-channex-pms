/**
 * Rooms Setup Tab — manage room types and individual rooms.
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Bed, Settings, Hash, Trash2, Pencil } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from '@/components/ui/dialog'
import {
  fetchRoomTypes, createRoomType, updateRoomType, deleteRoomType,
  fetchRooms, createRoom, updateRoom, deleteRoom, setRoomStatus,
  type RoomType, type Room, type RoomTypePayload, type RoomPayload,
} from '@/api/rooms'
import { fetchProperties, type Property } from '@/api/platform'
import { usePropertyStore } from '@/store/usePropertyStore'

// -------------------------------------------------------------------------
const ROOM_STATUS_CONFIG = {
  clean: { label: 'Clean', color: 'bg-emerald-100 text-emerald-700', dot: 'bg-emerald-500' },
  dirty: { label: 'Dirty', color: 'bg-amber-100 text-amber-700', dot: 'bg-amber-500' },
  maintenance: { label: 'Maintenance', color: 'bg-red-100 text-red-700', dot: 'bg-red-500' },
  out_of_order: { label: 'Out of Order', color: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400' },
}

// -------------------------------------------------------------------------
// Room Type Dialog
// -------------------------------------------------------------------------
function RoomTypeDialog({
  open, onClose, propertyId, roomType,
}: { open: boolean; onClose: () => void; propertyId: number | null; roomType?: RoomType }) {
  const qc = useQueryClient()
  const isEdit = !!roomType
  const [localPropertyId, setLocalPropertyId] = useState<number | null>(null)
  const effectivePropertyId = propertyId ?? localPropertyId

  const { data: properties = [] } = useQuery<Property[]>({
    queryKey: ['properties'],
    queryFn: fetchProperties,
    enabled: open && propertyId === null && !isEdit,
    staleTime: 300_000,
  })

  const [form, setForm] = useState<Omit<RoomTypePayload, 'property_id'>>(() => ({
    name: roomType?.name ?? '',
    code: roomType?.code ?? '',
    max_occupancy: roomType?.max_occupancy ?? 2,
    base_rate: roomType?.base_rate ? parseFloat(roomType.base_rate) : 0,
    description: roomType?.description ?? undefined,
  }))

  const mutation = useMutation({
    mutationFn: () => isEdit
      ? updateRoomType(roomType!.id, form)
      : createRoomType({ ...form, property_id: effectivePropertyId! }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['room-types'] })
      onClose()
      setLocalPropertyId(null)
      setForm({ name: '', code: '', max_occupancy: 2, base_rate: 0 })
    },
  })

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle>{isEdit ? 'Edit Room Type' : 'New Room Type'}</DialogTitle></DialogHeader>
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
            <Label>Name *</Label>
            <Input placeholder="Deluxe King" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Short Name</Label>
              <Input placeholder="DLX" value={form.code ?? ''} onChange={e => setForm(p => ({ ...p, code: e.target.value || null }))} />
            </div>
            <div className="space-y-1.5">
              <Label>Max Occupancy</Label>
              <Input type="number" min={1} value={form.max_occupancy ?? ''} onChange={e => setForm(p => ({ ...p, max_occupancy: Number(e.target.value) }))} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Default Rate ($/night)</Label>
            <Input type="number" step="0.01" placeholder="200.00" value={form.base_rate ?? ''} onChange={e => setForm(p => ({ ...p, base_rate: parseFloat(e.target.value) || 0 }))} />
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Input placeholder="Ocean view, king bed..." value={form.description ?? ''} onChange={e => setForm(p => ({ ...p, description: e.target.value || undefined }))} />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.name || (!isEdit && !effectivePropertyId)}>
            {mutation.isPending ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Room Type'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// -------------------------------------------------------------------------
// Room Dialog
// -------------------------------------------------------------------------
function RoomDialog({
  open, onClose, propertyId, roomTypes, room,
}: {
  open: boolean; onClose: () => void;
  propertyId: number | null; roomTypes: RoomType[]; room?: Room
}) {
  const qc = useQueryClient()
  const isEdit = !!room
  const [form, setForm] = useState<RoomPayload>(() => ({
    property_id: room?.property_id ?? propertyId ?? roomTypes[0]?.property_id ?? 0,
    room_type_id: room?.room_type_id ?? roomTypes[0]?.id ?? 0,
    name: room?.name ?? '',
    floor: room?.floor ?? undefined,
    notes: room?.notes ?? undefined,
  }))

  // Sync default room_type_id when roomTypes loads (component may mount before data arrives)
  useEffect(() => {
    if (!isEdit && roomTypes.length > 0 && !form.room_type_id) {
      const rt = roomTypes[0]
      setForm(p => ({
        ...p,
        room_type_id: rt.id,
        property_id: propertyId ?? rt.property_id ?? 0,
      }))
    }
  }, [roomTypes, form.room_type_id, propertyId, isEdit])

  // When room type changes, sync property_id from the selected room type
  const handleRoomTypeChange = (roomTypeId: number) => {
    const rt = roomTypes.find(r => r.id === roomTypeId)
    setForm(p => ({
      ...p,
      room_type_id: roomTypeId,
      property_id: propertyId ?? rt?.property_id ?? 0,
    }))
  }

  const effectivePropertyId = propertyId ?? form.property_id

  const mutation = useMutation({
    mutationFn: () => isEdit
      ? updateRoom(room!.id, form)
      : createRoom({ ...form, property_id: effectivePropertyId }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['rooms'] })
      onClose()
      if (!isEdit) {
        setForm({ property_id: propertyId ?? roomTypes[0]?.property_id ?? 0, room_type_id: roomTypes[0]?.id ?? 0, name: '', floor: undefined, notes: undefined })
      }
    },
  })

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle>{isEdit ? 'Edit Room' : 'New Room'}</DialogTitle></DialogHeader>
        <DialogBody className="space-y-3 pt-4">
          <div className="space-y-1.5">
            <Label>Room Name / Number *</Label>
            <Input placeholder="101" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
          </div>
          <div className="space-y-1.5">
            <Label>Room Type *</Label>
            <select
              className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={form.room_type_id ?? ''}
              onChange={e => handleRoomTypeChange(Number(e.target.value))}
            >
              {roomTypes.map(rt => (
                <option key={rt.id} value={rt.id}>{rt.name}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Floor</Label>
              <Input type="number" placeholder="1" value={form.floor ?? ''} onChange={e => setForm(p => ({ ...p, floor: e.target.value || null }))} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Notes</Label>
            <Input placeholder="Corner room, accessible..." value={form.notes ?? ''} onChange={e => setForm(p => ({ ...p, notes: e.target.value || undefined }))} />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.name || !form.room_type_id}>
            {mutation.isPending ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Room'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// -------------------------------------------------------------------------
// Room Card with inline status change
// -------------------------------------------------------------------------
function RoomCard({ room, roomTypes, onDelete }: { room: Room; roomTypes: RoomType[]; onDelete: (id: number) => void }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const statusMutation = useMutation({
    mutationFn: (status: Room['status']) => setRoomStatus(room.id, status),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['rooms'] }),
  })
  const cfg = ROOM_STATUS_CONFIG[room.status] ?? ROOM_STATUS_CONFIG.clean

  return (
    <>
      <div className="rounded-xl border bg-card p-3 flex flex-col gap-2 hover:shadow-sm transition-shadow">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
              <span className="font-semibold">{room.name}</span>
            </div>
            {room.floor && (
              <p className="text-xs text-muted-foreground ml-3.5">Floor {room.floor}</p>
            )}
          </div>
          <div className="flex gap-1">
            <button
              onClick={() => setEditing(true)}
              className="text-muted-foreground hover:text-foreground transition-colors"
              title="Edit room"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => { if (confirm(`Delete room ${room.name}?`)) onDelete(room.id) }}
              className="text-muted-foreground hover:text-destructive transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        <select
          className={`text-xs rounded-full px-2 py-0.5 border-0 font-medium cursor-pointer ${cfg.color} focus:outline-none`}
          value={room.status}
          onChange={e => statusMutation.mutate(e.target.value as Room['status'])}
          disabled={statusMutation.isPending}
        >
          {Object.entries(ROOM_STATUS_CONFIG).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        {room.notes && <p className="text-xs text-muted-foreground">{room.notes}</p>}
      </div>
      {editing && (
        <RoomDialog
          open={editing}
          onClose={() => setEditing(false)}
          propertyId={room.property_id}
          roomTypes={roomTypes}
          room={room}
        />
      )}
    </>
  )
}

// -------------------------------------------------------------------------
// Main Tab
// -------------------------------------------------------------------------
export function RoomsTab() {
  const { selectedPropertyId } = usePropertyStore()
  const [activeTab, setActiveTab] = useState<'types' | 'rooms'>('rooms')
  const [showTypeDialog, setShowTypeDialog] = useState(false)
  const [editingType, setEditingType] = useState<RoomType | null>(null)
  const [showRoomDialog, setShowRoomDialog] = useState(false)
  const qc = useQueryClient()

  const { data: roomTypes = [], isLoading: loadingTypes } = useQuery<RoomType[]>({
    queryKey: ['room-types', selectedPropertyId],
    queryFn: () => fetchRoomTypes(selectedPropertyId ?? undefined),
    staleTime: 60_000,
  })

  const { data: rooms = [], isLoading: loadingRooms } = useQuery<Room[]>({
    queryKey: ['rooms', selectedPropertyId],
    queryFn: () => fetchRooms(selectedPropertyId ?? undefined),
    staleTime: 30_000,
  })

  const deleteType = useMutation({
    mutationFn: (id: number) => deleteRoomType(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['room-types'] }),
  })

  const deleteRm = useMutation({
    mutationFn: (id: number) => deleteRoom(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['rooms'] }),
  })

  // Group rooms by room type
  const roomsByType = roomTypes.reduce<Record<number, Room[]>>((acc, rt) => {
    acc[rt.id] = rooms.filter(r => r.room_type_id === rt.id)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Rooms</h2>
          <p className="text-muted-foreground text-sm">Room inventory and housekeeping status</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowTypeDialog(true)}>
            <Settings className="h-4 w-4 mr-1.5" />New Room Type
          </Button>
          <Button onClick={() => setShowRoomDialog(true)} disabled={roomTypes.length === 0}>
            <Plus className="h-4 w-4 mr-1.5" />Add Room
          </Button>
        </div>
      </div>

      {/* Tab pills */}
      <div className="flex gap-1 rounded-lg bg-muted p-1 w-fit">
        {(['rooms', 'types'] as const).map(t => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              activeTab === t ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t === 'rooms' ? 'Rooms' : 'Room Types'}
          </button>
        ))}
      </div>

      {activeTab === 'rooms' && (
        <div className="space-y-6">
          {loadingRooms ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {[0,1,2,3,4,5].map(i => <Skeleton key={i} className="h-24 rounded-xl" />)}
            </div>
          ) : roomTypes.length === 0 ? (
            <div className="rounded-xl border border-dashed p-10 text-center space-y-2">
              <Bed className="h-8 w-8 text-muted-foreground mx-auto" />
              <p className="text-sm font-medium">No room types yet</p>
              <Button variant="outline" onClick={() => setShowTypeDialog(true)}>
                <Plus className="h-4 w-4 mr-1.5" />Create a room type first
              </Button>
            </div>
          ) : (
            roomTypes.map(rt => {
              const rtRooms = roomsByType[rt.id] ?? []
              return (
                <div key={rt.id}>
                  <div className="flex items-center gap-2 mb-3">
                    <Bed className="h-4 w-4 text-muted-foreground" />
                    <h3 className="text-sm font-semibold">{rt.name}</h3>
                    <span className="text-xs text-muted-foreground">({rtRooms.length} rooms)</span>
                    {rt.base_rate && (
                      <span className="text-xs text-muted-foreground ml-auto">${parseFloat(rt.base_rate).toFixed(0)}/night</span>
                    )}
                  </div>
                  {rtRooms.length === 0 ? (
                    <p className="text-xs text-muted-foreground pl-6">No rooms in this type</p>
                  ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 pl-6">
                      {rtRooms.map(r => (
                        <RoomCard key={r.id} room={r} roomTypes={roomTypes} onDelete={id => deleteRm.mutate(id)} />
                      ))}
                    </div>
                  )}
                </div>
              )
            })
          )}

          {/* Summary pills */}
          {rooms.length > 0 && (
            <div className="flex gap-2 flex-wrap pt-2 border-t">
              {(Object.keys(ROOM_STATUS_CONFIG) as Room['status'][]).map(s => {
                const count = rooms.filter(r => r.status === s).length
                if (!count) return null
                const cfg = ROOM_STATUS_CONFIG[s]
                return (
                  <span key={s} className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${cfg.color}`}>
                    <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                    {count} {cfg.label}
                  </span>
                )
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === 'types' && (
        <div>
          {loadingTypes ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {[0,1,2].map(i => <Skeleton key={i} className="h-28 rounded-xl" />)}
            </div>
          ) : roomTypes.length === 0 ? (
            <div className="rounded-xl border border-dashed p-10 text-center space-y-2">
              <Hash className="h-8 w-8 text-muted-foreground mx-auto" />
              <p className="text-sm font-medium">No room types created</p>
              <Button variant="outline" onClick={() => setShowTypeDialog(true)}>
                <Plus className="h-4 w-4 mr-1.5" />Create first room type
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {roomTypes.map(rt => (
                <div key={rt.id} className="rounded-xl border bg-card p-4 space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold">{rt.name}</h4>
                      {rt.code && <p className="text-xs text-muted-foreground">{rt.code}</p>}
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => setEditingType(rt)}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                        title="Edit room type"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => { if (confirm(`Delete room type "${rt.name}"?`)) deleteType.mutate(rt.id) }}
                        className="text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <div className="flex gap-4 text-sm text-muted-foreground">
                    {rt.max_occupancy && (
                      <span className="flex items-center gap-1">
                        <span className="text-xs">Max:</span>{rt.max_occupancy} guests
                      </span>
                    )}
                    {rt.base_rate && (
                      <span className="flex items-center gap-1">
                        <span className="text-xs">Rate:</span>${parseFloat(rt.base_rate).toFixed(0)}/nt
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {(roomsByType[rt.id] ?? []).length} rooms assigned
                  </p>
                  {rt.description && <p className="text-xs text-muted-foreground">{rt.description}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <RoomTypeDialog
        open={showTypeDialog}
        onClose={() => setShowTypeDialog(false)}
        propertyId={selectedPropertyId}
      />
      {editingType && (
        <RoomTypeDialog
          open={!!editingType}
          onClose={() => setEditingType(null)}
          propertyId={selectedPropertyId}
          roomType={editingType}
        />
      )}
      <RoomDialog
        open={showRoomDialog}
        onClose={() => setShowRoomDialog(false)}
        propertyId={selectedPropertyId}
        roomTypes={roomTypes}
      />
    </div>
  )
}
