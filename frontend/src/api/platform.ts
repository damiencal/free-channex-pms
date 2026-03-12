import { apiFetch } from './client'

// ── Properties ──────────────────────────────────────────────────────
export interface Property {
  id: number
  name: string
  address: string | null
  city: string | null
  country: string | null
  timezone: string | null
  latitude: number | null
  longitude: number | null
  max_guests: number | null
  bedrooms: number | null
  bathrooms: number | null
  check_in_time: string | null
  check_out_time: string | null
  tags: string[]
  groups: string[]
  is_active: boolean
  allow_overbooking: boolean
  stop_auto_sync: boolean
  created_at: string
  updated_at: string
}

export interface PropertyPayload {
  name: string
  address?: string | null
  city?: string | null
  country?: string | null
  timezone?: string | null
  latitude?: number | null
  longitude?: number | null
  max_guests?: number | null
  bedrooms?: number | null
  bathrooms?: number | null
  check_in_time?: string | null
  check_out_time?: string | null
  tags?: string[]
  groups?: string[]
  allow_overbooking?: boolean
  stop_auto_sync?: boolean
}

export function fetchProperties(): Promise<Property[]> {
  return apiFetch<Property[]>('/properties')
}

export function getProperty(id: number): Promise<Property> {
  return apiFetch<Property>(`/properties/${id}`)
}

export function createProperty(payload: PropertyPayload): Promise<Property> {
  return apiFetch<Property>('/properties', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateProperty(id: number, payload: Partial<PropertyPayload>): Promise<Property> {
  return apiFetch<Property>(`/properties/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function deactivateProperty(id: number): Promise<Property> {
  return apiFetch<Property>(`/properties/${id}/deactivate`, { method: 'POST' })
}

// ── Connected Accounts / Linked Listings ────────────────────────────
export interface ConnectedAccount {
  id: number
  channel: string
  account_name: string
  status: 'active' | 'inactive' | 'error'
  listing_count: number
  api_token_hint: string | null
  last_synced_at: string | null
  created_at: string
}

export interface LinkedListing {
  id: number
  property_id: number | null
  account_id: number
  channel: string
  listing_name: string
  rate_plan: string | null
  inventory: number
  is_linked: boolean
}

export function fetchConnectedAccounts(): Promise<ConnectedAccount[]> {
  return apiFetch<ConnectedAccount[]>('/connected-accounts')
}

export function createConnection(payload: { name: string; api_token: string }): Promise<ConnectedAccount> {
  return apiFetch<ConnectedAccount>('/connected-accounts', {
    method: 'POST', body: JSON.stringify(payload),
  })
}

export function deleteConnection(id: number): Promise<void> {
  return apiFetch<void>(`/connected-accounts/${id}`, { method: 'DELETE' })
}

export function testConnection(id: number): Promise<{ status: string; message: string; listing_count: number }> {
  return apiFetch<{ status: string; message: string; listing_count: number }>(
    `/connected-accounts/${id}/test`, { method: 'POST' },
  )
}

export function syncConnection(id: number): Promise<{ synced: number; status: string }> {
  return apiFetch<{ synced: number; status: string }>(
    `/connected-accounts/${id}/sync`, { method: 'POST' },
  )
}

export function fetchLinkedListings(propertyId?: number): Promise<LinkedListing[]> {
  const qs = propertyId ? `?property_id=${propertyId}` : ''
  return apiFetch<LinkedListing[]>(`/linked-listings${qs}`)
}

export function linkListing(listingId: number, propertyId: number): Promise<LinkedListing> {
  return apiFetch<LinkedListing>(`/linked-listings/${listingId}/link`, {
    method: 'POST', body: JSON.stringify({ property_id: propertyId }),
  })
}

export function unlinkListing(listingId: number): Promise<LinkedListing> {
  return apiFetch<LinkedListing>(`/linked-listings/${listingId}/unlink`, { method: 'POST' })
}

// ── Automation Rules ────────────────────────────────────────────────
export interface AutomationRule {
  id: number
  name: string
  type: 'message' | 'review' | 'price' | 'task'
  trigger: string
  is_active: boolean
  property_id: number | null
  channel: string | null
  conditions: Record<string, unknown>
  actions: Record<string, unknown>
  created_at: string
}

export interface AutomationRulePayload {
  name: string
  type: AutomationRule['type']
  trigger: string
  is_active?: boolean
  property_id?: number | null
  channel?: string | null
  conditions?: Record<string, unknown>
  actions?: Record<string, unknown>
}

export function fetchAutomationRules(): Promise<AutomationRule[]> {
  return apiFetch<AutomationRule[]>('/automation/rules')
}

export function createAutomationRule(payload: AutomationRulePayload): Promise<AutomationRule> {
  return apiFetch<AutomationRule>('/automation/rules', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateAutomationRule(id: number, payload: Partial<AutomationRulePayload>): Promise<AutomationRule> {
  return apiFetch<AutomationRule>(`/automation/rules/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function deleteAutomationRule(id: number): Promise<void> {
  return apiFetch<void>(`/automation/rules/${id}`, { method: 'DELETE' })
}

export function toggleAutomationRule(id: number, is_active: boolean): Promise<AutomationRule> {
  return apiFetch<AutomationRule>(`/automation/rules/${id}/toggle`, {
    method: 'POST', body: JSON.stringify({ is_active }),
  })
}

export interface PendingAction {
  id: number
  type: string
  event: string
  date: string
  property_name: string
  channel: string
  status: 'pending' | 'completed' | 'skipped'
}

export function fetchPendingActions(): Promise<PendingAction[]> {
  return apiFetch<PendingAction[]>('/automation/pending')
}

// ── Booking Site ────────────────────────────────────────────────────
export interface BookingSite {
  id: number
  name: string
  type: 'hosted' | 'self-hosted'
  domain: string | null
  custom_domain: string | null
  listing_count: number
  is_published: boolean
  hero_title: string | null
  hero_subtitle: string | null
  site_logo_url: string | null
  contact_phone: string | null
  contact_email: string | null
  seo_title: string | null
  seo_description: string | null
  seo_keywords: string | null
  created_at: string
}

export interface BookingSitePayload {
  name: string
  type?: 'hosted' | 'self-hosted'
  domain?: string | null
  custom_domain?: string | null
  hero_title?: string | null
  hero_subtitle?: string | null
  contact_phone?: string | null
  contact_email?: string | null
  seo_title?: string | null
  seo_description?: string | null
  seo_keywords?: string | null
}

export interface RatePlanConfig {
  id: number
  site_id: number
  name: string
  cancellation_policy: string
  payment_schedule: string
  min_stay: number
  max_stay: number
  meals: string[]
  pricing_mode: 'independent' | 'derived'
}

export interface PromotionCode {
  id: number
  site_id: number
  code: string
  discount_percent: number | null
  discount_amount: number | null
  valid_from: string | null
  valid_to: string | null
  is_active: boolean
}

export function fetchBookingSites(): Promise<BookingSite[]> {
  return apiFetch<BookingSite[]>('/booking-sites')
}

export function getBookingSite(id: number): Promise<BookingSite> {
  return apiFetch<BookingSite>(`/booking-sites/${id}`)
}

export function createBookingSite(payload: BookingSitePayload): Promise<BookingSite> {
  return apiFetch<BookingSite>('/booking-sites', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateBookingSite(id: number, payload: Partial<BookingSitePayload>): Promise<BookingSite> {
  return apiFetch<BookingSite>(`/booking-sites/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function publishBookingSite(id: number): Promise<BookingSite> {
  return apiFetch<BookingSite>(`/booking-sites/${id}/publish`, { method: 'POST' })
}

export function unpublishBookingSite(id: number): Promise<BookingSite> {
  return apiFetch<BookingSite>(`/booking-sites/${id}/unpublish`, { method: 'POST' })
}

// ── Booking Site Listings ────────────────────────────────────────────
export interface BookingSiteListing {
  id: number
  site_id: number
  property_id: number
  sort_order: number
  is_visible: boolean
  display_name: string
  slug: string
  bedrooms: number | null
  bathrooms: number | null
  max_guests: number | null
  property_type: string | null
  address: string | null
  city: string | null
  country: string | null
}

export function fetchSiteListings(siteId: number): Promise<BookingSiteListing[]> {
  return apiFetch<BookingSiteListing[]>(`/booking-sites/${siteId}/listings`)
}

export function updateSiteListing(
  siteId: number,
  listingId: number,
  payload: { is_visible?: boolean; sort_order?: number },
): Promise<BookingSiteListing> {
  return apiFetch<BookingSiteListing>(`/booking-sites/${siteId}/listings/${listingId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteSiteListing(siteId: number, listingId: number): Promise<void> {
  return apiFetch<void>(`/booking-sites/${siteId}/listings/${listingId}`, { method: 'DELETE' })
}

// ── Metrics ─────────────────────────────────────────────────────────
export interface RealtimeStats {
  check_ins_today: number
  check_outs_today: number
  in_stay: number
  vacant: number
  occupancy_rate: number
  total_properties: number
  inquiries_today: number
  bookings_today: number
  cancelled_today: number
  tasks_today: number
}

export interface MonthlyReport {
  month: string
  reservations: number
  total_income: number
  total_expense: number
  net_profit: number
  generated_at: string | null
}

export interface IncomeExpenseEntry {
  id: number
  item: string
  amount: number
  payment_method: string
  channel: string | null
  time: string
  operator: string
  reservation_id: number | null
  property_name: string | null
  note: string | null
}

export function fetchRealtimeStats(propertyId?: number | null): Promise<RealtimeStats> {
  const qs = propertyId ? `?property_id=${propertyId}` : ''
  return apiFetch<RealtimeStats>(`/metrics/realtime${qs}`)
}

export function fetchMonthlyReports(propertyId?: number | null): Promise<MonthlyReport[]> {
  const qs = propertyId ? `?property_id=${propertyId}` : ''
  return apiFetch<MonthlyReport[]>(`/metrics/monthly-reports${qs}`)
}

export function fetchIncomeExpenses(params?: {
  property_id?: number | null
  month?: string
}): Promise<IncomeExpenseEntry[]> {
  const qs = new URLSearchParams()
  if (params?.property_id) qs.set('property_id', String(params.property_id))
  if (params?.month) qs.set('month', params.month)
  const q = qs.toString()
  return apiFetch<IncomeExpenseEntry[]>(`/metrics/income-expenses${q ? `?${q}` : ''}`)
}

// ── Settings ────────────────────────────────────────────────────────
export interface AppSettings {
  lead_channel: string
  channel_pricing_ratios: Record<string, number>
  default_check_in_time: string
  default_check_out_time: string
  timezone: string
  language: string
  currency: string
  tags: string[]
  custom_channels: string[]
  income_categories: string[]
  expense_categories: string[]
}

export function fetchSettings(): Promise<AppSettings> {
  return apiFetch<AppSettings>('/settings')
}

export function updateSettings(payload: Partial<AppSettings>): Promise<AppSettings> {
  return apiFetch<AppSettings>('/settings', { method: 'PUT', body: JSON.stringify(payload) })
}

export interface TeamMember {
  id: number
  email: string
  name: string
  role: 'owner' | 'admin' | 'manager' | 'staff'
  permissions: string[]
  is_active: boolean
  created_at: string
}

export function fetchTeamMembers(): Promise<TeamMember[]> {
  return apiFetch<TeamMember[]>('/settings/team')
}

export function inviteTeamMember(payload: { email: string; name: string; role: string }): Promise<TeamMember> {
  return apiFetch<TeamMember>('/settings/team/invite', { method: 'POST', body: JSON.stringify(payload) })
}

export function removeTeamMember(id: number): Promise<void> {
  return apiFetch<void>(`/settings/team/${id}`, { method: 'DELETE' })
}
