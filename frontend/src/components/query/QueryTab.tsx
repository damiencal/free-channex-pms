import { useChatStore } from '@/store/useChatStore'
import { useChatStream } from '@/hooks/useChatStream'
import { StarterPrompts } from './StarterPrompts'
import { ChatWindow } from './ChatWindow'
import { ChatInput } from './ChatInput'

interface QueryTabProps {
  disabled?: boolean
}

export function QueryTab({ disabled = false }: QueryTabProps) {
  const messages = useChatStore((state) => state.messages)
  const { sendMessage, isStreaming } = useChatStream()

  function handleSend(text: string) {
    if (disabled) return
    void sendMessage(text)
  }

  return (
    <div className="flex h-full flex-col">
      {disabled ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-muted-foreground text-center max-w-sm">
            Query is unavailable -- Ollama is not running. The Query tab will re-enable automatically when Ollama is available.
          </p>
        </div>
      ) : messages.length === 0 ? (
        <StarterPrompts onSelect={handleSend} />
      ) : (
        <ChatWindow messages={messages} />
      )}
      <ChatInput onSend={handleSend} disabled={disabled || isStreaming} />
    </div>
  )
}
