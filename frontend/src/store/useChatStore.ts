import { create } from 'zustand'

export interface QueryResult {
  columns: string[]
  rows: Record<string, unknown>[]
}

export interface ChatError {
  type: string      // 'sql_invalid' | 'sql_execution' | 'ollama_down' | 'unknown'
  message: string   // user-friendly message
  detail?: string   // technical detail for Thomas
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sql?: string
  results?: QueryResult
  error?: ChatError
  isStreaming: boolean
}

interface ChatStore {
  messages: ChatMessage[]
  addUserMessage: (content: string) => string       // returns id
  addAssistantMessage: () => string                  // returns id
  appendToken: (id: string, token: string) => void
  setSql: (id: string, sql: string) => void
  setResults: (id: string, results: QueryResult) => void
  setError: (id: string, error: ChatError) => void
  setDone: (id: string) => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],

  addUserMessage: (content: string) => {
    const id = crypto.randomUUID()
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role: 'user', content, isStreaming: false },
      ],
    }))
    return id
  },

  addAssistantMessage: () => {
    const id = crypto.randomUUID()
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role: 'assistant', content: '', isStreaming: true },
      ],
    }))
    return id
  },

  appendToken: (id: string, token: string) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, content: msg.content + token } : msg
      ),
    }))
  },

  setSql: (id: string, sql: string) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, sql } : msg
      ),
    }))
  },

  setResults: (id: string, results: QueryResult) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, results } : msg
      ),
    }))
  },

  setError: (id: string, error: ChatError) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, error, isStreaming: false } : msg
      ),
    }))
  },

  setDone: (id: string) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, isStreaming: false } : msg
      ),
    }))
  },
}))
