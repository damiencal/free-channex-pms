---
phase: 08-llm-natural-language-interface
plan: 03
subsystem: ui
tags: [react, zustand, sse, streaming, chat, tailwind, shadcn]

# Dependency graph
requires:
  - phase: 08-01
    provides: Backend /api/query/ask SSE endpoint with token/sql/results/error/done events
  - phase: 07-dashboard
    provides: React + Vite + shadcn/ui shell, Zustand pattern, Tailwind dark mode

provides:
  - Ephemeral Zustand chat store (useChatStore) with ChatMessage/QueryResult/ChatError types
  - SSE streaming hook (useChatStream) consuming /api/query/ask via plain fetch + ReadableStream
  - 6 self-contained query components in frontend/src/components/query/
  - QueryTab ready to mount as a tab in AppShell (Plan 04)

affects: [08-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useChatStore.getState() inside async callbacks to avoid stale closures"
    - "Buffer-based SSE line parsing: split on newline, keep last incomplete line in buffer"
    - "assistantId captured before stream loop — stable reference for token routing"
    - "Plain fetch (not apiFetch) for SSE — apiFetch calls response.json(), blocking body stream access"

key-files:
  created:
    - frontend/src/store/useChatStore.ts
    - frontend/src/hooks/useChatStream.ts
    - frontend/src/components/query/QueryTab.tsx
    - frontend/src/components/query/ChatWindow.tsx
    - frontend/src/components/query/ChatMessage.tsx
    - frontend/src/components/query/StarterPrompts.tsx
    - frontend/src/components/query/ChatInput.tsx
    - frontend/src/components/query/ResultTable.tsx
  modified: []

key-decisions:
  - "useChatStore has NO persist middleware — chat is ephemeral by design, clears on reload"
  - "assistantId captured before reader.read() loop prevents token misrouting during concurrent messages"
  - "Plain fetch not apiFetch for SSE — apiFetch calls response.json() which consumes response body"
  - "Buffer keeps last partial line between chunk reads — handles SSE packets split across TCP chunks"
  - "currentEvent resets to 'message' after each data: line — matches SSE spec event-field behavior"
  - "Intl.NumberFormat currency formatting only for money columns (pattern match on column name)"
  - "ResultTable collapsed by default with ChevronRight/ChevronDown toggle"
  - "ChatInput uses textarea (not input) with auto-resize up to 4 lines"
  - "Enter sends, Shift+Enter inserts newline — standard chat keyboard convention"
  - "QueryTab disabled prop shows unavailability message — Plan 04 passes this from Ollama health check"

patterns-established:
  - "SSE hook pattern: plain fetch POST, ReadableStream + TextDecoder, buffer-based line split"
  - "Zustand getState() in async functions vs useChatStore() hook in render"
  - "Collapsible pattern: shadcn Collapsible + CollapsibleTrigger + CollapsibleContent with chevron icon"

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 8 Plan 03: Chat Frontend Summary

**Zustand ephemeral chat store, SSE streaming hook, and 6 query UI components (StarterPrompts, ChatInput, ResultTable, ChatMessage, ChatWindow, QueryTab) ready to mount in AppShell**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T01:08:49Z
- **Completed:** 2026-03-01T01:10:37Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- useChatStore: ephemeral Zustand store with message CRUD actions, no persist middleware
- useChatStream: SSE consumer hook that POSTs to /api/query/ask and routes events (token/sql/results/error/done) to store actions via captured assistantId
- 6 chat components: StarterPrompts (4 question cards), ChatInput (auto-resize textarea + send), ResultTable (collapsible table + currency formatting), ChatMessage (user/assistant bubbles + Show SQL + error display), ChatWindow (auto-scroll), QueryTab (orchestrates all with empty-state)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Zustand chat store and SSE streaming hook** - `03000f9` (feat)
2. **Task 2: Create all chat UI components** - `03c0cc3` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `frontend/src/store/useChatStore.ts` - Ephemeral chat state with ChatMessage/QueryResult/ChatError types and store actions
- `frontend/src/hooks/useChatStream.ts` - SSE streaming hook: fetch POST /api/query/ask, ReadableStream parsing, event routing
- `frontend/src/components/query/QueryTab.tsx` - Top-level composition: empty state vs conversation, always-visible ChatInput
- `frontend/src/components/query/ChatWindow.tsx` - Scrollable message list with auto-scroll to bottom on new tokens
- `frontend/src/components/query/ChatMessage.tsx` - User/assistant bubbles, Show SQL collapsible, ResultTable, error display
- `frontend/src/components/query/StarterPrompts.tsx` - 4 clickable starter question cards using shadcn Card
- `frontend/src/components/query/ChatInput.tsx` - Auto-resize textarea, Enter-to-send, Shift+Enter for newline, disabled state
- `frontend/src/components/query/ResultTable.tsx` - Collapsible data table, currency formatting for money columns, 100-row cap

## Decisions Made

- **No persist middleware on useChatStore** — Chat history is intentionally ephemeral; clears on page reload. Avoids stale conversation context across sessions.
- **assistantId captured before stream loop** — Prevents stale closure bug where concurrent messages could route tokens to wrong message bubble.
- **Plain fetch not apiFetch** — apiFetch calls `response.json()` which would consume the response body before the SSE stream can be read.
- **Buffer-based SSE parsing** — Decoder chunks may split across newlines; keeping the last partial line in a buffer handles TCP packet boundaries correctly.
- **currentEvent resets after data: line** — Matches SSE spec: each event block's `event:` applies only to the next `data:` in that block.
- **Intl.NumberFormat only for money columns** — Pattern matches column name against money-related keywords; avoids formatting non-financial numbers as currency.
- **QueryTab disabled prop** — Plan 04 (AppShell wiring) passes Ollama health status; QueryTab renders unavailability message and disables input.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 8 query files created and TypeScript-clean
- QueryTab exports a single component ready to mount as a tab in AppShell
- Plan 04 (AppShell wiring) can import QueryTab from `@/components/query/QueryTab` and pass `disabled={!ollamaHealthy}` prop

---
*Phase: 08-llm-natural-language-interface*
*Completed: 2026-03-01*
