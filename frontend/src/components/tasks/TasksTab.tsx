import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Bell, Trash2, StickyNote } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  fetchTasks,
  createTask,
  updateTask,
  deleteTask,
  notifyTask,
  type CleaningTask,
  type TaskPayload,
} from '@/api/tasks'
import { usePropertyStore } from '@/store/usePropertyStore'

const COLUMNS: { key: CleaningTask['status']; label: string; color: string }[] = [
  { key: 'pending', label: 'Pending', color: 'bg-amber-50 border-amber-200' },
  { key: 'in_progress', label: 'In Progress', color: 'bg-blue-50 border-blue-200' },
  { key: 'completed', label: 'Completed', color: 'bg-green-50 border-green-200' },
  { key: 'skipped', label: 'Skipped', color: 'bg-muted border-border' },
]

const STATUS_CYCLE: Record<CleaningTask['status'], CleaningTask['status']> = {
  pending: 'in_progress',
  in_progress: 'completed',
  completed: 'pending',
  skipped: 'pending',
}

// ---------------------------------------------------------------------------
// Task card
// ---------------------------------------------------------------------------

function TaskCard({ task }: { task: CleaningTask }) {
  const queryClient = useQueryClient()

  const updateMutation = useMutation({
    mutationFn: (status: CleaningTask['status']) => updateTask(task.id, { status }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteTask(task.id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  })

  const notifyMutation = useMutation({
    mutationFn: () => notifyTask(task.id),
  })

  return (
    <div className="bg-card rounded-lg border p-3 shadow-sm space-y-2 group">
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-0.5 min-w-0">
          <p className="text-sm font-medium truncate">
            {task.assigned_to ?? 'Unassigned'}
          </p>
          <p className="text-xs text-muted-foreground">
            {new Date(task.scheduled_date + 'T00:00:00').toLocaleDateString(undefined, {
              weekday: 'short',
              month: 'short',
              day: 'numeric',
            })}
          </p>
        </div>
        {task.booking_id && (
          <Badge variant="secondary" className="text-xs shrink-0">Booking #{task.booking_id}</Badge>
        )}
      </div>

      {task.notes && (
        <p className="text-xs text-muted-foreground flex gap-1 items-start">
          <StickyNote className="w-3 h-3 mt-0.5 shrink-0" />
          <span className="line-clamp-2">{task.notes}</span>
        </p>
      )}

      <div className="flex items-center gap-1 pt-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-xs"
          disabled={updateMutation.isPending}
          onClick={() => updateMutation.mutate(STATUS_CYCLE[task.status])}
        >
          → {STATUS_CYCLE[task.status].replace('_', ' ')}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          disabled={notifyMutation.isPending || !task.assigned_to}
          onClick={() => notifyMutation.mutate()}
          title="Email assignee"
        >
          <Bell className="w-3 h-3" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-destructive hover:text-destructive"
          disabled={deleteMutation.isPending}
          onClick={() => deleteMutation.mutate()}
        >
          <Trash2 className="w-3 h-3" />
        </Button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Add task form
// ---------------------------------------------------------------------------

function AddTaskForm({
  propertyId,
  onClose,
}: {
  propertyId: number
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<TaskPayload>({
    property_id: propertyId,
    scheduled_date: new Date().toISOString().slice(0, 10),
    assigned_to: '',
    notes: '',
    status: 'pending',
  })

  const createMutation = useMutation({
    mutationFn: () => createTask({ ...form, assigned_to: form.assigned_to || null, notes: form.notes || null }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks'] })
      onClose()
    },
  })

  return (
    <div className="border rounded-xl p-4 bg-muted/30 space-y-3 mb-4">
      <h3 className="text-sm font-semibold">New Cleaning Task</h3>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label className="text-xs">Scheduled Date</Label>
          <Input
            type="date"
            value={form.scheduled_date}
            onChange={(e) => setForm((f) => ({ ...f, scheduled_date: e.target.value }))}
            className="h-8 text-sm"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Assigned To</Label>
          <Input
            placeholder="Name or email"
            value={form.assigned_to ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, assigned_to: e.target.value }))}
            className="h-8 text-sm"
          />
        </div>
      </div>
      <div className="space-y-1">
        <Label className="text-xs">Notes</Label>
        <Textarea
          placeholder="Optional notes…"
          value={form.notes ?? ''}
          onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
          className="text-sm min-h-[60px] resize-none"
        />
      </div>
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending || !form.scheduled_date}
        >
          {createMutation.isPending ? 'Creating…' : 'Create Task'}
        </Button>
        <Button size="sm" variant="ghost" onClick={onClose}>Cancel</Button>
      </div>
      {createMutation.isError && (
        <p className="text-xs text-destructive">
          {createMutation.error instanceof Error ? createMutation.error.message : 'Failed'}
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// TasksTab
// ---------------------------------------------------------------------------

export function TasksTab() {
  const [showAdd, setShowAdd] = useState(false)
  const { selectedPropertyId } = usePropertyStore()

  const { data: tasks = [], isLoading, isError, error } = useQuery<CleaningTask[]>({
    queryKey: ['tasks', selectedPropertyId],
    queryFn: () => fetchTasks({ property_id: selectedPropertyId }),
    refetchInterval: 60_000,
  })

  const byStatus = (status: CleaningTask['status']) => tasks.filter((t) => t.status === status)

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {COLUMNS.map((col) => (
          <div key={col.key} className="space-y-2">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-sm text-destructive">
        {error instanceof Error ? error.message : 'Failed to load tasks'}
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Cleaning Tasks</h2>
        <Button
          size="sm"
          onClick={() => setShowAdd((v) => !v)}
          className="gap-1.5"
        >
          <Plus className="w-4 h-4" />
          Add Task
        </Button>
      </div>

      {showAdd && selectedPropertyId != null && (
        <AddTaskForm propertyId={selectedPropertyId} onClose={() => setShowAdd(false)} />
      )}
      {showAdd && selectedPropertyId == null && (
        <p className="text-sm text-muted-foreground">Select a property first.</p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {COLUMNS.map((col) => {
          const colTasks = byStatus(col.key)
          return (
            <div key={col.key} className="space-y-2">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium">{col.label}</h3>
                <Badge variant="secondary" className="h-5 min-w-5 text-xs px-1.5">
                  {colTasks.length}
                </Badge>
              </div>
              <div className={`min-h-[120px] rounded-xl border-2 ${col.color} p-2 space-y-2`}>
                {colTasks.map((t) => (
                  <TaskCard key={t.id} task={t} />
                ))}
                {colTasks.length === 0 && (
                  <p className="text-xs text-muted-foreground/50 text-center pt-6">Empty</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
