import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/api/client'
import { usePropertyStore } from '@/store/usePropertyStore'

export interface ResortFormAction {
  type: 'resort_form'
  booking_id: number
  guest_name: string
  check_in_date: string
  property_slug: string
  urgency: number
  submission_id: number
}

export interface VrboMessageAction {
  type: 'vrbo_message'
  booking_id: number
  guest_name: string
  message_type: string
  scheduled_for: string | null
  property_slug: string
  log_id: number
}

export interface UnreconciledAction {
  type: 'unreconciled'
  booking_id: number
  platform: string
  guest_name: string
  net_amount: string
  check_in_date: string
  property_slug: string
}

export type ActionItem = ResortFormAction | VrboMessageAction | UnreconciledAction

export interface ActionsResponse {
  actions: ActionItem[]
  total: number
}

export function useActions() {
  const selectedPropertyId = usePropertyStore((s) => s.selectedPropertyId)

  return useQuery<ActionsResponse>({
    queryKey: ['dashboard', 'actions', selectedPropertyId],
    queryFn: () => {
      const params = selectedPropertyId !== null ? `?property_id=${selectedPropertyId}` : ''
      return apiFetch<ActionsResponse>(`/dashboard/actions${params}`)
    },
    staleTime: 5 * 60 * 1000,
  })
}
