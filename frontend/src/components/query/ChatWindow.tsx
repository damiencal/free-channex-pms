import { useEffect, useRef } from 'react'
import { ChatMessage } from './ChatMessage'
import type { ChatMessage as ChatMessageType } from '@/store/useChatStore'

interface ChatWindowProps {
  messages: ChatMessageType[]
}

export function ChatWindow({ messages }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const lastMessageContent = messages[messages.length - 1]?.content ?? ''

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, lastMessageContent])

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-4 p-4">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
