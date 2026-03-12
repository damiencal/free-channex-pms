import { apiFetch } from './client'

export interface NightAuditState {
  property_id: number
  current_selling_date: string
  last_audit: NightAuditEntry | null
}

export interface NightAuditEntry {
  id: number
  property_id: number
  audit_date: string
  selling_date: string
  performed_by: number | null
  notes: string | null
  created_at: string
}

export interface NightAuditHistory {
  total: number
  offset: number
  limit: number
  results: NightAuditEntry[]
}

export const getCurrentAuditState = (property_id: number): Promise<NightAuditState> =>
  apiFetch<NightAuditState>(`/night-audit?property_id=${property_id}`)

export const runNightAudit = (property_id: number, notes?: string): Promise<NightAuditEntry> =>
  apiFetch<NightAuditEntry>('/night-audit', {
    method: 'POST',
    body: JSON.stringify({ property_id, notes }),
  })

export const fetchAuditHistory = (property_id: number, limit = 30): Promise<NightAuditHistory> =>
  apiFetch<NightAuditHistory>(`/night-audit/history?property_id=${property_id}&limit=${limit}`)
