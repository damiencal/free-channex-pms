import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ResultTable } from './ResultTable'
import type { ChatMessage as ChatMessageType } from '@/store/useChatStore'

interface ChatMessageProps {
  message: ChatMessageType
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [sqlOpen, setSqlOpen] = useState(false)
  const [errorDetailOpen, setErrorDetailOpen] = useState(false)

  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg bg-primary px-4 py-3 text-sm text-primary-foreground">
          {message.content}
        </div>
      </div>
    )
  }

  // Assistant message
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] w-full sm:max-w-[80%]">
        <div className="rounded-lg bg-muted px-4 py-3 text-sm">
          {/* Streaming indicator */}
          {message.isStreaming && !message.content && !message.error && (
            <div className="flex gap-1 items-center py-1">
              <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
              <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
              <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
            </div>
          )}

          {/* Error display */}
          {message.error && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2">
              <p className="text-destructive text-sm">{message.error.message}</p>
              {message.error.detail && (
                <Collapsible
                  open={errorDetailOpen}
                  onOpenChange={setErrorDetailOpen}
                >
                  <CollapsibleTrigger className="flex items-center gap-1 mt-2 text-xs text-muted-foreground hover:text-foreground transition-colors">
                    {errorDetailOpen ? (
                      <ChevronDown className="h-3 w-3" />
                    ) : (
                      <ChevronRight className="h-3 w-3" />
                    )}
                    Show details
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <pre className="mt-2 rounded bg-muted px-2 py-1 text-xs font-mono overflow-x-auto whitespace-pre-wrap break-all">
                      {message.error.detail}
                    </pre>
                  </CollapsibleContent>
                </Collapsible>
              )}
            </div>
          )}

          {/* Message content */}
          {message.content && (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
        </div>

        {/* SQL disclosure — shown when SQL is available */}
        {message.sql && (
          <div className="mt-1 px-1">
            <Collapsible open={sqlOpen} onOpenChange={setSqlOpen}>
              <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
                {sqlOpen ? (
                  <ChevronDown className="h-3 w-3" />
                ) : (
                  <ChevronRight className="h-3 w-3" />
                )}
                Show SQL
              </CollapsibleTrigger>
              <CollapsibleContent>
                <pre className="mt-2 overflow-x-auto rounded-md border bg-muted px-3 py-2 text-xs font-mono whitespace-pre">
                  {message.sql}
                </pre>
              </CollapsibleContent>
            </Collapsible>
          </div>
        )}

        {/* Results table */}
        {message.results && (
          <div className="mt-1 px-1">
            {message.results.rows.length > 0 ? (
              <ResultTable results={message.results} />
            ) : (
              <p className="text-xs text-muted-foreground mt-2">
                No results found.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
