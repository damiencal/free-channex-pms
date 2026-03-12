import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Send, Sparkles, MessageCircle, RefreshCw,
  Calendar, Users, StickyNote, LogIn, LogOut,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  fetchInboxThreads,
  fetchThreadMessages,
  fetchAiSuggestion,
  sendInboxMessage,
  type InboxThread,
  type InboxMessage,
} from '@/api/inbox'
import { fetchBookings } from '@/api/bookings'
import { usePropertyStore } from '@/store/usePropertyStore'

// ── Filter types ────────────────────────────────────────────────────
type InboxFilter = 'all' | 'unread' | 'pending'

// ---------------------------------------------------------------------------
// Thread list panel
// ---------------------------------------------------------------------------

function ThreadList({
  threads,
  selected,
  onSelect,
}: {
  threads: InboxThread[]
  selected: string | null
  onSelect: (id: string) => void
}) {
  if (threads.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-sm gap-2 p-8">
        <MessageCircle className="w-8 h-8 opacity-40" />
        <span>No messages yet</span>
      </div>
    )
  }

  return (
    <div className="divide-y">
      {threads.map((t) => (
        <button
          key={t.channex_booking_id}
          onClick={() => onSelect(t.channex_booking_id)}
          className={`w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors ${
            selected === t.channex_booking_id ? 'bg-muted' : ''
          }`}
        >
          <div className="flex items-center justify-between gap-2 mb-0.5">
            <span className="font-medium text-sm truncate">{t.guest_name || 'Guest'}</span>
            {t.unread_count > 0 && (
              <Badge variant="destructive" className="h-4 min-w-4 text-xs px-1 shrink-0">
                {t.unread_count}
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground truncate">{t.last_message_body || '—'}</p>
          {t.last_message_at && (
            <p className="text-xs text-muted-foreground/60 mt-0.5">
              {new Date(t.last_message_at).toLocaleDateString()}
            </p>
          )}
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Message thread panel
// ---------------------------------------------------------------------------

function MessageBubble({ msg }: { msg: InboxMessage }) {
  const isOutbound = msg.direction === 'outbound'
  return (
    <div className={`flex ${isOutbound ? 'justify-end' : 'justify-start'} mb-2`}>
      <div
        className={`max-w-[75%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed ${
          isOutbound
            ? 'bg-primary text-primary-foreground rounded-br-sm'
            : 'bg-muted rounded-bl-sm'
        }`}
      >
        <p className="whitespace-pre-wrap">{msg.body}</p>
        <p
          className={`text-xs mt-1 ${
            isOutbound ? 'text-primary-foreground/60' : 'text-muted-foreground'
          }`}
        >
          {msg.sent_at ? new Date(msg.sent_at).toLocaleString() : new Date(msg.created_at).toLocaleString()}
        </p>
      </div>
    </div>
  )
}

function ThreadPanel({ channexBookingId }: { channexBookingId: string }) {
  const [draft, setDraft] = useState('')
  const queryClient = useQueryClient()

  const { data: messages = [], isLoading } = useQuery<InboxMessage[]>({
    queryKey: ['inbox', 'messages', channexBookingId],
    queryFn: () => fetchThreadMessages(channexBookingId),
    refetchInterval: 30_000,
  })

  const aiMutation = useMutation({
    mutationFn: () => fetchAiSuggestion(channexBookingId),
    onSuccess: (data) => {
      setDraft(data.suggestion)
    },
  })

  const sendMutation = useMutation({
    mutationFn: () => sendInboxMessage(channexBookingId, draft),
    onSuccess: () => {
      setDraft('')
      void queryClient.invalidateQueries({ queryKey: ['inbox', 'messages', channexBookingId] })
      void queryClient.invalidateQueries({ queryKey: ['inbox', 'threads'] })
    },
  })

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        <Skeleton className="h-12 w-3/4" />
        <Skeleton className="h-12 w-1/2 ml-auto" />
        <Skeleton className="h-12 w-2/3" />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1 px-4 py-3">
        {messages.map((m) => (
          <MessageBubble key={m.id} msg={m} />
        ))}
      </ScrollArea>

      <div className="border-t p-4 space-y-2">
        <Textarea
          placeholder="Type a message…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="min-h-[80px] resize-none text-sm"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && draft.trim()) {
              sendMutation.mutate()
            }
          }}
        />

        <div className="flex items-center justify-between gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => aiMutation.mutate()}
            disabled={aiMutation.isPending}
            className="gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {aiMutation.isPending ? 'Thinking…' : 'AI Suggest'}
          </Button>

          {aiMutation.isError && (
            <p className="text-xs text-destructive flex-1">
              {aiMutation.error instanceof Error ? aiMutation.error.message : 'AI error'}
            </p>
          )}

          <Button
            size="sm"
            onClick={() => sendMutation.mutate()}
            disabled={!draft.trim() || sendMutation.isPending}
            className="gap-1.5 ml-auto"
          >
            <Send className="w-3.5 h-3.5" />
            {sendMutation.isPending ? 'Sending…' : 'Send'}
          </Button>
        </div>

        {sendMutation.isError && (
          <p className="text-xs text-destructive">
            {sendMutation.error instanceof Error ? sendMutation.error.message : 'Send failed'}
          </p>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Booking Sidebar — shows booking details for selected thread
// ---------------------------------------------------------------------------

function BookingSidebar({ channexBookingId }: { channexBookingId: string }) {
  const { selectedPropertyId } = usePropertyStore()

  const { data: bookings = [] } = useQuery({
    queryKey: ['bookings', selectedPropertyId],
    queryFn: () => fetchBookings({ property_id: selectedPropertyId }),
    staleTime: 60_000,
  })

  // Find a booking matching this thread
  const booking = bookings.find(
    b => b.platform_booking_id === channexBookingId,
  )

  if (!booking) {
    return (
      <div className="p-4 text-center text-xs text-muted-foreground">
        <StickyNote className="h-6 w-6 mx-auto mb-2 opacity-40" />
        No booking linked
      </div>
    )
  }

  const nights = Math.round(
    (new Date(booking.check_out_date).getTime() - new Date(booking.check_in_date).getTime()) / 86400000,
  )

  return (
    <div className="p-4 space-y-4 text-sm">
      <h3 className="font-semibold text-xs uppercase tracking-wide text-muted-foreground">Booking Details</h3>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <LogIn className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">Check-in</span>
          <span className="ml-auto font-medium">{booking.check_in_date}</span>
        </div>
        <div className="flex items-center gap-2">
          <LogOut className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">Check-out</span>
          <span className="ml-auto font-medium">{booking.check_out_date}</span>
        </div>
        <div className="flex items-center gap-2">
          <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">Nights</span>
          <span className="ml-auto font-medium">{nights}</span>
        </div>
        <div className="flex items-center gap-2">
          <Users className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">Guests</span>
          <span className="ml-auto font-medium">
            {booking.adults > 0 ? `${booking.adults} adult${booking.adults !== 1 ? 's' : ''}` : '—'}
            {booking.children > 0 ? `, ${booking.children} child` : ''}
          </span>
        </div>
      </div>

      <div className="border-t pt-3 space-y-1">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Platform</span>
          <Badge variant="outline" className="text-xs">{booking.platform}</Badge>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Amount</span>
          <span className="font-medium">
            {parseFloat(booking.net_amount) > 0 ? `$${parseFloat(booking.net_amount).toFixed(0)}` : '—'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Status</span>
          <Badge variant="outline" className="text-xs capitalize">{booking.booking_state?.replace('_', ' ') || '—'}</Badge>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// InboxTab
// ---------------------------------------------------------------------------

export function InboxTab() {
  const [selectedThread, setSelectedThread] = useState<string | null>(null)
  const [filter, setFilter] = useState<InboxFilter>('all')
  const { selectedPropertyId } = usePropertyStore()
  const queryClient = useQueryClient()

  const { data: threads = [], isLoading, isError, error } = useQuery<InboxThread[]>({
    queryKey: ['inbox', 'threads', selectedPropertyId],
    queryFn: () => fetchInboxThreads(selectedPropertyId),
    refetchInterval: 60_000,
  })

  function reload() {
    void queryClient.invalidateQueries({ queryKey: ['inbox', 'threads'] })
  }

  const filteredThreads = threads.filter(t => {
    if (filter === 'unread') return t.unread_count > 0
    if (filter === 'pending') return t.unread_count > 0 // Treat pending same as unread for now
    return true
  })

  const FILTER_TABS: { key: InboxFilter; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'unread', label: `Unread (${threads.filter(t => t.unread_count > 0).length})` },
    { key: 'pending', label: 'Pending' },
  ]

  return (
    <div className="flex gap-0 border rounded-xl overflow-hidden h-[calc(100vh-180px)] min-h-[500px]">
      {/* Left panel: thread list */}
      <div className="w-72 shrink-0 border-r flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30">
          <h2 className="font-semibold text-sm">Inbox</h2>
          <Button variant="ghost" size="icon" onClick={reload} className="h-7 w-7">
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
        </div>

        {/* Filter tabs */}
        <div className="flex border-b">
          {FILTER_TABS.map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`flex-1 px-2 py-2 text-xs font-medium transition-colors ${
                filter === f.key
                  ? 'border-b-2 border-primary text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <ScrollArea className="flex-1">
          {isLoading ? (
            <div className="p-3 space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full rounded-lg" />
              ))}
            </div>
          ) : isError ? (
            <p className="text-xs text-destructive p-4">
              {error instanceof Error ? error.message : 'Failed to load'}
            </p>
          ) : (
            <ThreadList
              threads={filteredThreads}
              selected={selectedThread}
              onSelect={setSelectedThread}
            />
          )}
        </ScrollArea>
      </div>

      {/* Middle panel: message thread */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedThread ? (
          <>
            <div className="px-4 py-3 border-b bg-muted/30">
              <p className="text-sm font-medium truncate">
                {threads.find((t) => t.channex_booking_id === selectedThread)?.guest_name ?? 'Conversation'}
              </p>
              <p className="text-xs text-muted-foreground truncate">{selectedThread}</p>
            </div>
            <ThreadPanel channexBookingId={selectedThread} />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
            <div className="text-center space-y-2">
              <MessageCircle className="w-10 h-10 opacity-30 mx-auto" />
              <p>Select a conversation</p>
            </div>
          </div>
        )}
      </div>

      {/* Right panel: booking sidebar */}
      {selectedThread && (
        <div className="w-64 shrink-0 border-l bg-muted/10 overflow-y-auto">
          <BookingSidebar channexBookingId={selectedThread} />
        </div>
      )}
    </div>
  )
}
