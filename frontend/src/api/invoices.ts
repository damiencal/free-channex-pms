import { apiFetch } from './client'

export interface Invoice {
  id: number
  invoice_number: string
  booking_id: number
  property_id: number
  guest_id: number | null
  guest_name: string
  guest_email: string | null
  status: 'open' | 'paid' | 'void' | 'partially_paid'
  subtotal: string
  tax_amount: string
  total: string
  amount_paid: string
  balance: string
  notes: string | null
  created_at: string
  updated_at: string
  items?: InvoiceItem[]
  payments?: Payment[]
}

export interface InvoiceItem {
  id: number
  invoice_id: number
  item_type: string
  description: string
  quantity: string
  unit_price: string
  amount: string
  tax_type_id: number | null
  tax_amount: string
  created_at: string
}

export interface Payment {
  id: number
  invoice_id: number
  booking_id: number
  amount: string
  payment_method: string
  reference: string | null
  notes: string | null
  payment_date: string
  created_at: string
}

export interface InvoicePayload {
  booking_id?: number | null
  property_id?: number | null
  guest_id?: number | null
  guest_name: string
  guest_email?: string | null
  notes?: string | null
}

export interface InvoiceItemPayload {
  item_type?: string
  description: string
  quantity?: number
  unit_price: number
  tax_type_id?: number | null
}

export interface PaymentPayload {
  invoice_id: number
  booking_id?: number | null
  amount: number
  payment_method?: string
  reference?: string | null
  notes?: string | null
  payment_date?: string | null
}

export const fetchInvoices = (params?: { property_id?: number | null; booking_id?: number; status?: string }): Promise<Invoice[]> => {
  const qs = new URLSearchParams()
  if (params?.property_id != null) qs.set('property_id', String(params.property_id))
  if (params?.booking_id != null) qs.set('booking_id', String(params.booking_id))
  if (params?.status) qs.set('status', params.status)
  return apiFetch<Invoice[]>(`/invoices${qs.toString() ? `?${qs}` : ''}`)
}
export const getInvoice = (id: number): Promise<Invoice> =>
  apiFetch<Invoice>(`/invoices/${id}`)
export const createInvoice = (payload: InvoicePayload): Promise<Invoice> =>
  apiFetch<Invoice>('/invoices', { method: 'POST', body: JSON.stringify(payload) })
export const updateInvoice = (id: number, payload: { notes?: string; status?: string }): Promise<Invoice> =>
  apiFetch<Invoice>(`/invoices/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const voidInvoice = (id: number): Promise<Invoice> =>
  apiFetch<Invoice>(`/invoices/${id}/void`, { method: 'POST' })
export const addInvoiceItem = (invoiceId: number, payload: InvoiceItemPayload): Promise<InvoiceItem> =>
  apiFetch<InvoiceItem>(`/invoices/${invoiceId}/items`, { method: 'POST', body: JSON.stringify(payload) })
export const removeInvoiceItem = (itemId: number): Promise<void> =>
  apiFetch<void>(`/invoice-items/${itemId}`, { method: 'DELETE' })
export const recordPayment = (payload: PaymentPayload): Promise<Payment> =>
  apiFetch<Payment>('/payments', { method: 'POST', body: JSON.stringify(payload) })
export const refundPayment = (paymentId: number, notes?: string): Promise<Payment> =>
  apiFetch<Payment>(`/payments/${paymentId}${notes ? `?notes=${encodeURIComponent(notes)}` : ''}`, { method: 'DELETE' })
