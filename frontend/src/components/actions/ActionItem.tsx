import { useState } from 'react'
import { FileText, MessageSquare, DollarSign, Loader2 } from 'lucide-react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import {
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { apiFetch } from '@/api/client'
import type { ActionItem as ActionItemType } from '@/hooks/useActions'

interface ActionItemProps {
  item: ActionItemType
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr)
  const now = new Date()
  // Compare calendar dates only
  const diffMs = target.setHours(0, 0, 0, 0) - now.setHours(0, 0, 0, 0)
  return Math.round(diffMs / (1000 * 60 * 60 * 24))
}

function resortFormDescription(checkInDate: string): string {
  const days = daysUntil(checkInDate)
  if (days < 0) return 'Resort form overdue'
  if (days === 0) return 'Resort form due today'
  return `Resort form due in ${days} day${days === 1 ? '' : 's'}`
}

function vrboMessageDescription(messageType: string): string {
  return `${messageType} message ready to send`
}

function unreconciledDescription(platform: string, amount: string): string {
  const formatted = parseFloat(amount).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
  })
  return `${platform} booking — ${formatted} unreconciled`
}

/**
 * Single expandable action item inside the Accordion.
 * Collapsed: icon, guest name, brief description, property badge.
 * Expanded: details and an action button (or informational text).
 */
export function ActionItem({ item }: ActionItemProps) {
  const queryClient = useQueryClient()
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Determine icon, color, and description based on type
  let Icon = FileText
  let iconClass = 'text-amber-500'
  let description = ''

  if (item.type === 'resort_form') {
    Icon = FileText
    iconClass = 'text-amber-500'
    description = resortFormDescription(item.check_in_date)
  } else if (item.type === 'vrbo_message') {
    Icon = MessageSquare
    iconClass = 'text-blue-500'
    description = vrboMessageDescription(item.message_type)
  } else {
    Icon = DollarSign
    iconClass = 'text-muted-foreground'
    description = unreconciledDescription(item.platform, item.net_amount)
  }

  // Resort form mutation: POST /api/compliance/submit/{booking_id}
  const submitFormMutation = useMutation({
    mutationFn: () =>
      apiFetch<{ status: string }>(`/compliance/submit/${(item as { booking_id: number }).booking_id}`, {
        method: 'POST',
      }),
    onSuccess: () => {
      setSuccessMsg('Form submitted successfully')
      void queryClient.invalidateQueries({ queryKey: ['dashboard', 'actions'] })
    },
  })

  // VRBO message mutation: POST /api/communication/confirm/{log_id}
  const confirmMessageMutation = useMutation({
    mutationFn: () =>
      apiFetch<{ status: string }>(`/communication/confirm/${(item as { log_id: number }).log_id}`, {
        method: 'POST',
      }),
    onSuccess: () => {
      setSuccessMsg('Marked as sent')
      void queryClient.invalidateQueries({ queryKey: ['dashboard', 'actions'] })
    },
  })

  const accordionValue = `${item.type}-${item.booking_id}`

  return (
    <AccordionItem value={accordionValue}>
      <AccordionTrigger className="hover:no-underline px-4">
        <div className="flex flex-1 items-center gap-3 min-w-0">
          <Icon className={`h-4 w-4 shrink-0 ${iconClass}`} />
          <div className="flex flex-1 items-center justify-between gap-3 min-w-0">
            <div className="flex flex-col items-start min-w-0">
              <span className="font-semibold text-sm leading-tight">{item.guest_name}</span>
              <span className="text-muted-foreground text-xs leading-tight mt-0.5">{description}</span>
            </div>
            <Badge variant="secondary" className="shrink-0 text-xs font-mono">
              {item.property_slug}
            </Badge>
          </div>
        </div>
      </AccordionTrigger>

      <AccordionContent className="px-4">
        <div className="rounded-lg bg-muted/40 p-4 space-y-3">
          {item.type === 'resort_form' && (
            <>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">Check-in</span>
                  <p className="font-medium">{formatDate(item.check_in_date)}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Property</span>
                  <p className="font-medium">{item.property_slug}</p>
                </div>
              </div>
              {successMsg ? (
                <p className="text-sm text-green-600 dark:text-green-400">{successMsg}</p>
              ) : (
                <Button
                  size="sm"
                  disabled={submitFormMutation.isPending}
                  onClick={() => submitFormMutation.mutate()}
                >
                  {submitFormMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                  Submit
                </Button>
              )}
              {submitFormMutation.isError && (
                <p className="text-sm text-destructive">
                  {submitFormMutation.error instanceof Error
                    ? submitFormMutation.error.message
                    : 'Failed to submit form'}
                </p>
              )}
            </>
          )}

          {item.type === 'vrbo_message' && (
            <>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">Message type</span>
                  <p className="font-medium capitalize">{item.message_type}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Scheduled</span>
                  <p className="font-medium">
                    {item.scheduled_for ? formatDate(item.scheduled_for) : 'Not scheduled'}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">Property</span>
                  <p className="font-medium">{item.property_slug}</p>
                </div>
              </div>
              {successMsg ? (
                <p className="text-sm text-green-600 dark:text-green-400">{successMsg}</p>
              ) : (
                <Button
                  size="sm"
                  disabled={confirmMessageMutation.isPending}
                  onClick={() => confirmMessageMutation.mutate()}
                >
                  {confirmMessageMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                  Mark as Sent
                </Button>
              )}
              {confirmMessageMutation.isError && (
                <p className="text-sm text-destructive">
                  {confirmMessageMutation.error instanceof Error
                    ? confirmMessageMutation.error.message
                    : 'Failed to confirm message'}
                </p>
              )}
            </>
          )}

          {item.type === 'unreconciled' && (
            <>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">Platform</span>
                  <p className="font-medium capitalize">{item.platform}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Check-in</span>
                  <p className="font-medium">{formatDate(item.check_in_date)}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Amount</span>
                  <p className="font-medium">
                    {parseFloat(item.net_amount).toLocaleString('en-US', {
                      style: 'currency',
                      currency: 'USD',
                    })}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">Property</span>
                  <p className="font-medium">{item.property_slug}</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground italic">
                Reconciliation is done via CSV upload — no action available here.
              </p>
            </>
          )}
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}
