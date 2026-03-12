import { apiFetch } from './client'

export interface CleaningTask {
  id: number
  booking_id: number | null
  property_id: number
  scheduled_date: string
  assigned_to: string | null
  status: 'pending' | 'in_progress' | 'completed' | 'skipped'
  notes: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface TaskPayload {
  booking_id?: number | null
  property_id: number
  scheduled_date: string
  assigned_to?: string | null
  status?: CleaningTask['status']
  notes?: string | null
}

export function fetchTasks(params?: {
  property_id?: number | null
  status?: string
  date?: string
}): Promise<CleaningTask[]> {
  const qs = new URLSearchParams()
  if (params?.property_id != null) qs.set('property_id', String(params.property_id))
  if (params?.status) qs.set('status', params.status)
  if (params?.date) qs.set('date', params.date)
  const q = qs.toString()
  return apiFetch<CleaningTask[]>(`/tasks${q ? `?${q}` : ''}`)
}

export function createTask(payload: TaskPayload): Promise<CleaningTask> {
  return apiFetch<CleaningTask>('/tasks', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateTask(id: number, payload: Partial<TaskPayload>): Promise<CleaningTask> {
  return apiFetch<CleaningTask>(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function deleteTask(id: number): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(`/tasks/${id}`, { method: 'DELETE' })
}

export function notifyTask(id: number): Promise<{ notified: boolean }> {
  return apiFetch<{ notified: boolean }>(`/tasks/${id}/notify`, { method: 'POST' })
}
