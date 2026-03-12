/**
 * Invoices / Folio Tab — create invoices, add charges, record payments.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus, FileText, CreditCard, Trash2,
  CheckCircle, AlertCircle, Clock, Ban,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from '@/components/ui/dialog'
import {
  fetchInvoices, getInvoice, createInvoice, voidInvoice,
  addInvoiceItem, removeInvoiceItem, recordPayment, refundPayment,
  type Invoice, type InvoicePayload, type InvoiceItemPayload,
} from '@/api/invoices'
import { fetchProperties, type Property } from '@/api/platform'
import { usePropertyStore } from '@/store/usePropertyStore'

// -------------------------------------------------------------------------
const STATUS_CONFIG: Record<Invoice['status'], { label: string; color: string; icon: React.ElementType }> = {
  open: { label: 'Open', color: 'bg-blue-100 text-blue-700', icon: Clock },
  paid: { label: 'Paid', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  void: { label: 'Void', color: 'bg-gray-100 text-gray-500', icon: Ban },
  partially_paid: { label: 'Partial', color: 'bg-amber-100 text-amber-700', icon: AlertCircle },
}

function StatusBadge({ status }: { status: Invoice['status'] }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.open
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
      <Icon className="h-3 w-3" />{cfg.label}
    </span>
  )
}

// -------------------------------------------------------------------------
// Create Invoice Dialog
// -------------------------------------------------------------------------
function CreateInvoiceDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const { selectedPropertyId } = usePropertyStore()
  const [localPropertyId, setLocalPropertyId] = useState<number | null>(null)
  const effectivePropertyId = selectedPropertyId ?? localPropertyId

  const { data: properties = [] } = useQuery<Property[]>({
    queryKey: ['properties'],
    queryFn: fetchProperties,
    enabled: open && selectedPropertyId === null,
    staleTime: 300_000,
  })

  const [form, setForm] = useState<InvoicePayload>({
    guest_name: '',
    booking_id: undefined,
  })

  const mutation = useMutation({
    mutationFn: () => createInvoice({ ...form, property_id: effectivePropertyId! }),
    onSuccess: (newInvoice) => {
      qc.setQueryData<Invoice[]>(['invoices', selectedPropertyId], old => [newInvoice, ...(old ?? [])])
      void qc.invalidateQueries({ queryKey: ['invoices'] })
      onClose()
    },
  })

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle>New Invoice</DialogTitle></DialogHeader>
        <DialogBody className="space-y-3 pt-4">
          {selectedPropertyId === null && (
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
            <Label>Guest Name *</Label>
            <Input
              placeholder="John Doe"
              value={form.guest_name}
              onChange={e => setForm(p => ({ ...p, guest_name: e.target.value }))}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Booking ID (optional)</Label>
            <Input
              type="number"
              placeholder="123"
              value={form.booking_id ?? ''}
              onChange={e => setForm(p => ({ ...p, booking_id: e.target.value ? Number(e.target.value) : undefined }))}
            />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.guest_name || !effectivePropertyId}>
            {mutation.isPending ? 'Creating…' : 'Create Invoice'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// -------------------------------------------------------------------------
// Add Charge Dialog
// -------------------------------------------------------------------------
function AddChargeDialog({
  open, onClose, invoiceId,
}: { open: boolean; onClose: () => void; invoiceId: number }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<InvoiceItemPayload>({ description: '', quantity: 1, unit_price: 0 })

  const mutation = useMutation({
    mutationFn: () => addInvoiceItem(invoiceId, form),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['invoice', invoiceId] })
      void qc.invalidateQueries({ queryKey: ['invoices'] })
      onClose()
      setForm({ description: '', quantity: 1, unit_price: 0 })
    },
  })

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle>Add Charge</DialogTitle></DialogHeader>
        <DialogBody className="space-y-3 pt-4">
          <div className="space-y-1.5">
            <Label>Description *</Label>
            <Input
              placeholder="Room charge, minibar, etc."
              value={form.description}
              onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Quantity</Label>
              <Input
                type="number" min={1}
                value={form.quantity}
                onChange={e => setForm(p => ({ ...p, quantity: Number(e.target.value) }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Unit Price *</Label>
              <Input
                type="number" step="0.01" placeholder="0.00"
                value={form.unit_price}
                onChange={e => setForm(p => ({ ...p, unit_price: parseFloat(e.target.value) || 0 }))}
              />
            </div>
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !form.description || !form.unit_price}
          >
            {mutation.isPending ? 'Adding…' : 'Add Charge'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// -------------------------------------------------------------------------
// Record Payment Dialog
// -------------------------------------------------------------------------
function RecordPaymentDialog({
  open, onClose, invoiceId, bookingId,
}: { open: boolean; onClose: () => void; invoiceId: number; bookingId: number | undefined }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({ amount: 0, payment_method: 'cash', reference: undefined as string | undefined })

  const mutation = useMutation({
    mutationFn: () => recordPayment({ invoice_id: invoiceId, booking_id: bookingId, amount: form.amount, payment_method: form.payment_method, reference: form.reference }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['invoice', invoiceId] })
      void qc.invalidateQueries({ queryKey: ['invoices'] })
      onClose()
      setForm({ amount: 0, payment_method: 'cash', reference: undefined })
    },
  })

  const methods = ['cash', 'credit_card', 'debit_card', 'bank_transfer', 'check', 'other']

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle>Record Payment</DialogTitle></DialogHeader>
        <DialogBody className="space-y-3 pt-4">
          <div className="space-y-1.5">
            <Label>Amount *</Label>
            <Input
              type="number" step="0.01" placeholder="0.00"
              value={form.amount}
              onChange={e => setForm(p => ({ ...p, amount: parseFloat(e.target.value) || 0 }))}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Payment Method</Label>
            <select
              className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={form.payment_method}
              onChange={e => setForm(p => ({ ...p, payment_method: e.target.value }))}
            >
              {methods.map(m => <option key={m} value={m}>{m.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Reference (optional)</Label>
            <Input
              placeholder="Transaction ref #"
              value={form.reference ?? ''}
              onChange={e => setForm(p => ({ ...p, reference: e.target.value || undefined }))}
            />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !form.amount}
          >
            {mutation.isPending ? 'Recording…' : 'Record Payment'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// -------------------------------------------------------------------------
// Invoice Detail
// -------------------------------------------------------------------------
function InvoiceDetail({ invoiceId }: { invoiceId: number }) {
  const qc = useQueryClient()
  const { data: invoice, isLoading } = useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => getInvoice(invoiceId),
  })
  const [showCharge, setShowCharge] = useState(false)
  const [showPayment, setShowPayment] = useState(false)

  const removeItem = useMutation({
    mutationFn: (itemId: number) => removeInvoiceItem(itemId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['invoice', invoiceId] })
      void qc.invalidateQueries({ queryKey: ['invoices'] })
    },
  })

  const doVoid = useMutation({
    mutationFn: () => voidInvoice(invoiceId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['invoice', invoiceId] })
      void qc.invalidateQueries({ queryKey: ['invoices'] })
    },
  })

  const doRefund = useMutation({
    mutationFn: (paymentId: number) => refundPayment(paymentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['invoice', invoiceId] })
      void qc.invalidateQueries({ queryKey: ['invoices'] })
    },
  })

  if (isLoading) return (
    <div className="p-4 space-y-3">
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-32 w-full rounded-lg" />
    </div>
  )
  if (!invoice) return <div className="p-4 text-sm text-muted-foreground">Invoice not found</div>

  const isVoid = invoice.status === 'void'
  const balance = parseFloat(invoice.balance)

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-base font-semibold">{invoice.invoice_number}</p>
          <p className="text-sm text-muted-foreground">{invoice.guest_name}</p>
        </div>
        <div className="space-y-1 text-right">
          <StatusBadge status={invoice.status} />
          {!isVoid && (
            <p className="text-xs text-muted-foreground">
              Balance: <span className={balance > 0 ? 'text-red-600 font-medium' : 'text-emerald-600 font-medium'}>
                ${balance.toFixed(2)}
              </span>
            </p>
          )}
        </div>
      </div>

      {/* Line Items */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold">Charges</h4>
          {!isVoid && (
            <Button size="sm" variant="outline" onClick={() => setShowCharge(true)}>
              <Plus className="h-3.5 w-3.5 mr-1" />Add
            </Button>
          )}
        </div>
        {invoice.items?.length === 0 ? (
          <p className="text-xs text-muted-foreground py-2">No charges yet</p>
        ) : (
          <div className="rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs text-muted-foreground">
                <tr>
                  <th className="text-left px-3 py-2">Description</th>
                  <th className="text-right px-3 py-2">Qty</th>
                  <th className="text-right px-3 py-2">Price</th>
                  <th className="text-right px-3 py-2">Total</th>
                  {!isVoid && <th className="px-3 py-2"></th>}
                </tr>
              </thead>
              <tbody className="divide-y">
                {(invoice.items ?? []).map(item => (
                  <tr key={item.id}>
                    <td className="px-3 py-2">{item.description}</td>
                    <td className="px-3 py-2 text-right text-muted-foreground">{item.quantity}</td>
                    <td className="px-3 py-2 text-right text-muted-foreground">${parseFloat(item.unit_price).toFixed(2)}</td>
                    <td className="px-3 py-2 text-right font-medium">${parseFloat(item.amount).toFixed(2)}</td>
                    {!isVoid && (
                      <td className="px-2 py-2 text-right">
                        <button
                          onClick={() => removeItem.mutate(item.id)}
                          className="text-muted-foreground hover:text-destructive transition-colors"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
                <tr className="bg-muted/20 font-semibold">
                  <td colSpan={3} className="px-3 py-2 text-right">Total</td>
                  <td className="px-3 py-2 text-right">${parseFloat(invoice.total).toFixed(2)}</td>
                  {!isVoid && <td />}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Payments */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold">Payments</h4>
          {!isVoid && balance > 0 && (
            <Button size="sm" variant="outline" onClick={() => setShowPayment(true)}>
              <CreditCard className="h-3.5 w-3.5 mr-1" />Collect
            </Button>
          )}
        </div>
        {invoice.payments?.length === 0 ? (
          <p className="text-xs text-muted-foreground py-2">No payments recorded</p>
        ) : (
          <div className="space-y-1.5">
            {(invoice.payments ?? []).map(p => (
              <div key={p.id} className="flex items-center justify-between text-sm rounded-lg bg-muted/30 px-3 py-2">
                <div>
                  <span className="font-medium capitalize">{p.payment_method.replace('_', ' ')}</span>
                  {p.reference && <span className="text-muted-foreground ml-2 text-xs">#{p.reference}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-emerald-600 font-medium">
                    +${parseFloat(p.amount).toFixed(2)}
                  </span>
                  {!isVoid && (
                    <button
                      onClick={() => doRefund.mutate(p.id)}
                      className="text-muted-foreground hover:text-destructive transition-colors"
                      title="Refund"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Void */}
      {!isVoid && invoice.status !== 'paid' && (
        <div className="pt-2 border-t">
          <Button
            variant="outline"
            size="sm"
            className="text-destructive hover:text-destructive border-destructive/30"
            onClick={() => { if (confirm('Void this invoice?')) doVoid.mutate() }}
            disabled={doVoid.isPending}
          >
            <Ban className="h-3.5 w-3.5 mr-1.5" />Void Invoice
          </Button>
        </div>
      )}

      {showCharge && (
        <AddChargeDialog open invoiceId={invoiceId} onClose={() => setShowCharge(false)} />
      )}
      {showPayment && (
        <RecordPaymentDialog open invoiceId={invoiceId} bookingId={invoice?.booking_id ?? undefined} onClose={() => setShowPayment(false)} />
      )}
    </div>
  )
}

// -------------------------------------------------------------------------
// Main Tab
// -------------------------------------------------------------------------
export function InvoicesTab() {
  const { selectedPropertyId } = usePropertyStore()
  const [showCreate, setShowCreate] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['invoices', selectedPropertyId],
    queryFn: () => fetchInvoices({ property_id: selectedPropertyId ?? undefined }),
    staleTime: 30_000,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Invoices &amp; Folios</h2>
          <p className="text-muted-foreground text-sm">Guest billing and payment collection</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-1.5" />New Invoice
        </Button>
      </div>

      <div className="flex gap-4 flex-col lg:flex-row">
        {/* Invoice list */}
        <div className="flex-1 min-w-0">
          {isLoading ? (
            <div className="space-y-2">
              {[0,1,2,3].map(i => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
            </div>
          ) : invoices.length === 0 ? (
            <div className="rounded-xl border border-dashed p-10 text-center space-y-2">
              <FileText className="h-8 w-8 text-muted-foreground mx-auto" />
              <p className="text-sm font-medium">No invoices yet</p>
              <Button variant="outline" onClick={() => setShowCreate(true)}>
                <Plus className="h-4 w-4 mr-1.5" />Create first invoice
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="text-left px-4 py-2.5">Invoice #</th>
                    <th className="text-left px-4 py-2.5">Guest</th>
                    <th className="text-right px-4 py-2.5">Total</th>
                    <th className="text-right px-4 py-2.5">Balance</th>
                    <th className="text-left px-4 py-2.5">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {invoices.map(inv => (
                    <tr
                      key={inv.id}
                      className={`cursor-pointer hover:bg-muted/30 transition-colors ${selectedId === inv.id ? 'bg-muted/20' : ''}`}
                      onClick={() => setSelectedId(selectedId === inv.id ? null : inv.id)}
                    >
                      <td className="px-4 py-3 font-mono text-xs font-medium">{inv.invoice_number}</td>
                      <td className="px-4 py-3 font-medium">{inv.guest_name}</td>
                      <td className="px-4 py-3 text-right">${parseFloat(inv.total).toFixed(2)}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={parseFloat(inv.balance) > 0 ? 'text-red-600 font-medium' : 'text-muted-foreground'}>
                          ${parseFloat(inv.balance).toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selectedId && (
          <div className="w-full lg:w-80 xl:w-96 shrink-0 rounded-xl border overflow-y-auto max-h-[70vh]">
            <InvoiceDetail invoiceId={selectedId} />
          </div>
        )}
      </div>

      <CreateInvoiceDialog open={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  )
}
