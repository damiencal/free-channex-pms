import { useRef, useState, type KeyboardEvent } from 'react'
import { SendHorizonal } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function adjustHeight() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    // Cap at 4 lines (1.5rem line-height * 4 = 6rem = 96px, plus padding)
    const lineHeight = 24
    const maxHeight = lineHeight * 4 + 24 // 4 lines + padding
    el.style.height = Math.min(el.scrollHeight, maxHeight) + 'px'
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value)
    adjustHeight()
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleSend() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    // Reset height after clearing
    setTimeout(() => {
      const el = textareaRef.current
      if (el) el.style.height = 'auto'
    }, 0)
  }

  return (
    <div className="border-t bg-background px-4 py-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask a question about your properties..."
          rows={1}
          className="flex-1 resize-none overflow-hidden rounded-lg border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
          style={{ lineHeight: '1.5rem' }}
        />
        <Button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          size="icon"
          className="h-9 w-9 shrink-0"
        >
          <SendHorizonal className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
