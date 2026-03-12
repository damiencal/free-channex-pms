import { useState } from 'react'
import { Loader2, Plus, ChevronUp } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { usePropertyStore } from '@/store/usePropertyStore'

interface Property {
  id: number
  slug: string
  display_name: string
}

interface FormFields {
  confirmation_code: string
  guest_name: string
  check_in_date: string
  check_out_date: string
  net_amount: string
  property_slug: string
  notes: string
}

const EMPTY_FORM: FormFields = {
  confirmation_code: '',
  guest_name: '',
  check_in_date: '',
  check_out_date: '',
  net_amount: '',
  property_slug: '',
  notes: '',
}

/**
 * Collapsible inline form for manual RVshare booking entry.
 * Collapses by default; expands when user clicks "Add RVshare Booking".
 * Validates on blur and submits to /ingestion/rvshare/entry (not /api/).
 */
export function RVshareEntryForm() {
  const queryClient = useQueryClient()
  const { selectedPropertyId } = usePropertyStore()

  const [open, setOpen] = useState(false)
  const [fields, setFields] = useState<FormFields>(EMPTY_FORM)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitted, setSubmitted] = useState(false)
  const [backendError, setBackendError] = useState<string | null>(null)

  // Read properties from TanStack Query cache (populated by AppShell Header)
  const { data: properties = [] } = useQuery<Property[]>({
    queryKey: ['dashboard', 'properties'],
  })

  // Pre-select property matching selectedPropertyId from store.
  // Adjusted during rendering (not in an effect) to avoid cascading renders.
  const [syncedForId, setSyncedForId] = useState<number | null>(-1)
  if (properties.length > 0 && selectedPropertyId !== syncedForId) {
    setSyncedForId(selectedPropertyId)
    if (selectedPropertyId !== null) {
      const match = properties.find((p) => p.id === selectedPropertyId)
      if (match) {
        setFields((prev) => ({ ...prev, property_slug: match.slug }))
      }
    }
  }

  // --- Validation helpers ---

  function validateField(name: keyof FormFields, value: string, allFields?: FormFields): string {
    const current = allFields ?? fields
    switch (name) {
      case 'confirmation_code':
      case 'guest_name':
        return value.trim() === '' ? 'Required' : ''
      case 'check_in_date':
        return value === '' ? 'Required' : ''
      case 'check_out_date':
        if (value === '') return 'Required'
        if (current.check_in_date && value <= current.check_in_date) {
          return 'Must be after check-in date'
        }
        return ''
      case 'net_amount': {
        if (value === '') return 'Required'
        const n = parseFloat(value)
        if (isNaN(n) || n <= 0) return 'Must be a positive number'
        return ''
      }
      case 'property_slug':
        return value === '' ? 'Required' : ''
      default:
        return ''
    }
  }

  function validateAll(currentFields: FormFields): Record<string, string> {
    const next: Record<string, string> = {}
    const requiredFields: Array<keyof FormFields> = [
      'confirmation_code',
      'guest_name',
      'check_in_date',
      'check_out_date',
      'net_amount',
      'property_slug',
    ]
    for (const name of requiredFields) {
      const err = validateField(name, currentFields[name], currentFields)
      if (err) next[name] = err
    }
    return next
  }

  // --- Event handlers ---

  function handleChange(name: keyof FormFields, value: string) {
    setFields((prev) => ({ ...prev, [name]: value }))
    // Clear error for the field while typing
    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev }
        delete next[name]
        return next
      })
    }
  }

  function handleBlur(name: keyof FormFields) {
    const err = validateField(name, fields[name])
    if (err) {
      setErrors((prev) => ({ ...prev, [name]: err }))
    }
  }

  // Handle select blur (Select doesn't fire native blur the same way)
  function handleSelectChange(value: string) {
    handleChange('property_slug', value)
    if (!value) {
      setErrors((prev) => ({ ...prev, property_slug: 'Required' }))
    } else {
      setErrors((prev) => {
        const next = { ...prev }
        delete next['property_slug']
        return next
      })
    }
  }

  function handleCancel() {
    setOpen(false)
    setFields((prev) => {
      // Keep property_slug pre-selection
      return { ...EMPTY_FORM, property_slug: prev.property_slug }
    })
    setErrors({})
    setSubmitted(false)
    setBackendError(null)
  }

  // --- Mutation ---

  const mutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const res = await fetch('/ingestion/rvshare/entry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`)
      }
      return res.json()
    },
    onSuccess: () => {
      setSubmitted(true)
      setBackendError(null)
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['ingestion', 'history'] })
      // Collapse and reset after 2 seconds
      setTimeout(() => {
        setOpen(false)
        setFields(EMPTY_FORM)
        setSubmitted(false)
      }, 2000)
    },
    onError: (err: Error) => {
      setBackendError(err.message)
    },
  })

  function handleSubmit() {
    // Validate all fields before submitting
    const allErrors = validateAll(fields)
    if (Object.keys(allErrors).length > 0) {
      setErrors(allErrors)
      return
    }
    mutation.mutate({
      confirmation_code: fields.confirmation_code.trim(),
      guest_name: fields.guest_name.trim(),
      check_in_date: fields.check_in_date,
      check_out_date: fields.check_out_date,
      net_amount: parseFloat(fields.net_amount),
      property_slug: fields.property_slug,
      notes: fields.notes.trim() || null,
    })
  }

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          {open ? <ChevronUp className="size-3.5" /> : <Plus className="size-3.5" />}
          Add RVshare Booking
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="mt-3 rounded-lg border bg-card p-4 space-y-4">
          {submitted ? (
            <p className="text-sm text-green-600 dark:text-green-400 font-medium">
              Booking added
            </p>
          ) : (
            <>
              {/* Form grid: 2 columns on md+, 1 column on mobile */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                {/* Confirmation Code */}
                <div className="space-y-1.5">
                  <Label htmlFor="rvs-confirmation_code">Confirmation Code</Label>
                  <Input
                    id="rvs-confirmation_code"
                    value={fields.confirmation_code}
                    onChange={(e) => handleChange('confirmation_code', e.target.value)}
                    onBlur={() => handleBlur('confirmation_code')}
                    placeholder="e.g. RV-123456"
                    aria-invalid={!!errors.confirmation_code}
                  />
                  {errors.confirmation_code && (
                    <p className="text-destructive text-xs">{errors.confirmation_code}</p>
                  )}
                </div>

                {/* Guest Name */}
                <div className="space-y-1.5">
                  <Label htmlFor="rvs-guest_name">Guest Name</Label>
                  <Input
                    id="rvs-guest_name"
                    value={fields.guest_name}
                    onChange={(e) => handleChange('guest_name', e.target.value)}
                    onBlur={() => handleBlur('guest_name')}
                    placeholder="Full name"
                    aria-invalid={!!errors.guest_name}
                  />
                  {errors.guest_name && (
                    <p className="text-destructive text-xs">{errors.guest_name}</p>
                  )}
                </div>

                {/* Check-in Date */}
                <div className="space-y-1.5">
                  <Label htmlFor="rvs-check_in_date">Check-in Date</Label>
                  <Input
                    id="rvs-check_in_date"
                    type="date"
                    value={fields.check_in_date}
                    onChange={(e) => handleChange('check_in_date', e.target.value)}
                    onBlur={() => handleBlur('check_in_date')}
                    aria-invalid={!!errors.check_in_date}
                  />
                  {errors.check_in_date && (
                    <p className="text-destructive text-xs">{errors.check_in_date}</p>
                  )}
                </div>

                {/* Check-out Date */}
                <div className="space-y-1.5">
                  <Label htmlFor="rvs-check_out_date">Check-out Date</Label>
                  <Input
                    id="rvs-check_out_date"
                    type="date"
                    value={fields.check_out_date}
                    onChange={(e) => handleChange('check_out_date', e.target.value)}
                    onBlur={() => handleBlur('check_out_date')}
                    aria-invalid={!!errors.check_out_date}
                  />
                  {errors.check_out_date && (
                    <p className="text-destructive text-xs">{errors.check_out_date}</p>
                  )}
                </div>

                {/* Net Amount */}
                <div className="space-y-1.5">
                  <Label htmlFor="rvs-net_amount">Net Amount ($)</Label>
                  <Input
                    id="rvs-net_amount"
                    type="number"
                    step="0.01"
                    min="0"
                    value={fields.net_amount}
                    onChange={(e) => handleChange('net_amount', e.target.value)}
                    onBlur={() => handleBlur('net_amount')}
                    placeholder="0.00"
                    aria-invalid={!!errors.net_amount}
                  />
                  {errors.net_amount && (
                    <p className="text-destructive text-xs">{errors.net_amount}</p>
                  )}
                </div>

                {/* Property */}
                <div className="space-y-1.5">
                  <Label>Property</Label>
                  <Select value={fields.property_slug} onValueChange={handleSelectChange}>
                    <SelectTrigger className="w-full" aria-invalid={!!errors.property_slug}>
                      <SelectValue placeholder="Select property" />
                    </SelectTrigger>
                    <SelectContent>
                      {properties.map((p) => (
                        <SelectItem key={p.slug} value={p.slug}>
                          {p.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.property_slug && (
                    <p className="text-destructive text-xs">{errors.property_slug}</p>
                  )}
                </div>

                {/* Notes — full width */}
                <div className="space-y-1.5 md:col-span-2">
                  <Label htmlFor="rvs-notes">Notes (optional)</Label>
                  <textarea
                    id="rvs-notes"
                    value={fields.notes}
                    onChange={(e) => handleChange('notes', e.target.value)}
                    placeholder="Any additional notes about this booking"
                    rows={2}
                    className="border-input bg-background placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 flex w-full rounded-md border px-3 py-1.5 text-sm shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                  />
                </div>
              </div>

              {/* Backend error */}
              {backendError && (
                <p className="text-destructive text-sm">{backendError}</p>
              )}

              {/* Actions */}
              <div className="flex flex-col-reverse md:flex-row gap-2 md:justify-start">
                <Button
                  size="sm"
                  onClick={handleSubmit}
                  disabled={mutation.isPending}
                  className="w-full md:w-auto"
                >
                  {mutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                  Add Booking
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCancel}
                  disabled={mutation.isPending}
                  className="w-full md:w-auto"
                >
                  Cancel
                </Button>
              </div>
            </>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
