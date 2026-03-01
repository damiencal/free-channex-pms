import { useState } from 'react'
import { useChatStore } from '@/store/useChatStore'

export function useChatStream() {
  const [isStreaming, setIsStreaming] = useState(false)

  async function sendMessage(message: string) {
    const store = useChatStore.getState()

    store.addUserMessage(message)
    const assistantId = store.addAssistantMessage()

    setIsStreaming(true)

    // Build conversation history from current messages (last 10)
    const currentMessages = useChatStore.getState().messages
    const history = currentMessages
      .slice(-10)
      .filter((m) => m.role === 'user' || (m.role === 'assistant' && !m.isStreaming))
      .map((m) => ({ role: m.role, content: m.content }))

    try {
      const response = await fetch('/api/query/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history }),
      })

      if (!response.ok) {
        useChatStore.getState().setError(assistantId, {
          type: 'unknown',
          message: `Request failed (HTTP ${response.status}). Please try again.`,
          detail: `HTTP ${response.status}: ${response.statusText}`,
        })
        return
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent = 'message'

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        // Keep the last (potentially incomplete) line in the buffer
        buffer = lines[lines.length - 1] ?? ''

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i]!.trimEnd()

          if (line.startsWith('event: ')) {
            currentEvent = line.slice('event: '.length).trim()
          } else if (line.startsWith('data: ')) {
            const data = line.slice('data: '.length)
            const storeRef = useChatStore.getState()

            switch (currentEvent) {
              case 'token':
                storeRef.appendToken(assistantId, data)
                break
              case 'sql':
                storeRef.setSql(assistantId, data)
                break
              case 'results':
                try {
                  storeRef.setResults(assistantId, JSON.parse(data) as Parameters<typeof storeRef.setResults>[1])
                } catch {
                  // Malformed results JSON — skip
                }
                break
              case 'error':
                try {
                  storeRef.setError(assistantId, JSON.parse(data) as Parameters<typeof storeRef.setError>[1])
                } catch {
                  storeRef.setError(assistantId, {
                    type: 'unknown',
                    message: 'An unexpected error occurred.',
                    detail: data,
                  })
                }
                break
              case 'done':
                storeRef.setDone(assistantId)
                break
              default:
                // Unknown event — ignore
                break
            }

            // Reset event type after processing data line
            currentEvent = 'message'
          }
          // Blank lines (SSE message separators) are ignored — event resets happen after data
        }
      }
    } catch (err) {
      useChatStore.getState().setError(assistantId, {
        type: 'unknown',
        message: 'Network error. Please check your connection and try again.',
        detail: err instanceof Error ? err.message : String(err),
      })
    } finally {
      setIsStreaming(false)
    }
  }

  return { sendMessage, isStreaming }
}
