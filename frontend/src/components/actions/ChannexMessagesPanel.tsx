import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchChannexMessages, sendChannexMessage, type ChannexMessage } from '@/api/channex'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/EmptyState'
import { ErrorAlert } from '@/components/shared/ErrorAlert'

interface ThreadProps {
  bookingId: string
  messages: ChannexMessage[]
  guestName: string
}

function MessageThread({ bookingId, messages, guestName }: ThreadProps) {
  const [reply, setReply] = useState('')
  const queryClient = useQueryClient()

  const sendMutation = useMutation({
    mutationFn: () => sendChannexMessage(bookingId, reply),
    onSuccess: () => {
      setReply('')
      void queryClient.invalidateQueries({ queryKey: ['channex', 'messages'] })
    },
  })

  const inbound = messages.filter((m) => m.direction === 'inbound')

  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="font-medium">{guestName || 'Guest'}</div>
        <Badge variant="secondary" className="text-xs">
          {inbound.length} unanswered
        </Badge>
      </div>

      {/* Message thread */}
      <div className="space-y-2 max-h-48 overflow-y-auto text-sm">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`rounded-lg px-3 py-2 max-w-[75%] ${
                m.direction === 'outbound'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-foreground'
              }`}
            >
              <p>{m.body}</p>
              {m.sent_at && (
                <p className="text-xs opacity-60 mt-1">
                  {new Date(m.sent_at).toLocaleString()}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Reply form */}
      <div className="flex gap-2">
        <Textarea
          placeholder="Type a reply…"
          value={reply}
          onChange={(e) => setReply(e.target.value)}
          className="text-sm resize-none min-h-[60px]"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && reply.trim()) {
              sendMutation.mutate()
            }
          }}
        />
        <Button
          size="sm"
          disabled={!reply.trim() || sendMutation.isPending}
          onClick={() => sendMutation.mutate()}
          className="self-end shrink-0"
        >
          {sendMutation.isPending ? 'Sending…' : 'Send'}
        </Button>
      </div>
      {sendMutation.isError && (
        <p className="text-xs text-destructive">
          {sendMutation.error instanceof Error
            ? sendMutation.error.message
            : 'Failed to send message'}
        </p>
      )}
    </div>
  )
}

/**
 * Channex Messages Panel — shows inbound guest message threads grouped
 * by Channex booking, with inline reply input.
 */
export function ChannexMessagesPanel() {
  const { data, isLoading, isError, error, refetch } = useQuery<ChannexMessage[]>({
    queryKey: ['channex', 'messages'],
    queryFn: () => fetchChannexMessages({ direction: 'inbound', limit: 100 }),
    staleTime: 2 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1].map((i) => (
          <div key={i} className="rounded-xl border bg-card p-4 shadow-sm">
            <Skeleton className="h-4 w-32 mb-2" />
            <Skeleton className="h-12 w-full" />
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <ErrorAlert
        message={error instanceof Error ? error.message : 'Failed to load messages.'}
        onRetry={() => void refetch()}
      />
    )
  }

  const messages = data ?? []

  // Group by channex_booking_id
  const grouped = messages.reduce<Record<string, ChannexMessage[]>>((acc, m) => {
    const key = m.channex_booking_id
    if (!acc[key]) acc[key] = []
    acc[key].push(m)
    return acc
  }, {})

  const bookingIds = Object.keys(grouped)

  if (bookingIds.length === 0) {
    return <EmptyState title="No unread messages" />
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        Guest Messages
        <Badge variant="secondary" className="ml-2">
          {bookingIds.length}
        </Badge>
      </h3>
      {bookingIds.map((bookingId) => {
        const msgs = grouped[bookingId]
        const guestName = msgs[0]?.guest_name ?? ''
        return (
          <MessageThread
            key={bookingId}
            bookingId={bookingId}
            messages={msgs}
            guestName={guestName}
          />
        )
      })}
    </div>
  )
}
