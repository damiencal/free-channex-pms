import { apiFetch } from './client'

export interface MessageTemplate {
  id: number
  name: string
  trigger_event: 'booking_confirmed' | 'check_in' | 'check_out' | 'review_request'
  offset_hours: number
  subject: string | null
  body_template: string
  channel: 'channex' | 'email'
  is_active: boolean
  property_id: number | null
}

export interface TemplatePayload {
  name: string
  trigger_event: MessageTemplate['trigger_event']
  offset_hours: number
  subject?: string | null
  body_template: string
  channel: MessageTemplate['channel']
  is_active?: boolean
  property_id?: number | null
}

export interface TriggeredMessageLog {
  id: number
  template_id: number
  booking_id: number | null
  status: 'scheduled' | 'sent' | 'failed' | 'skipped'
  scheduled_for: string | null
  sent_at: string | null
  rendered_body: string | null
  error_message: string | null
  created_at: string
}

export function fetchTemplates(): Promise<MessageTemplate[]> {
  return apiFetch<MessageTemplate[]>('/messaging/templates')
}

export function createTemplate(payload: TemplatePayload): Promise<MessageTemplate> {
  return apiFetch<MessageTemplate>('/messaging/templates', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateTemplate(id: number, payload: Partial<TemplatePayload>): Promise<MessageTemplate> {
  return apiFetch<MessageTemplate>(`/messaging/templates/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteTemplate(id: number): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(`/messaging/templates/${id}`, { method: 'DELETE' })
}

export function fetchMessageLogs(params?: {
  template_id?: number
  booking_id?: number
  status?: string
}): Promise<TriggeredMessageLog[]> {
  const qs = new URLSearchParams()
  if (params?.template_id != null) qs.set('template_id', String(params.template_id))
  if (params?.booking_id != null) qs.set('booking_id', String(params.booking_id))
  if (params?.status) qs.set('status', params.status)
  const q = qs.toString()
  return apiFetch<TriggeredMessageLog[]>(`/messaging/logs${q ? `?${q}` : ''}`)
}
