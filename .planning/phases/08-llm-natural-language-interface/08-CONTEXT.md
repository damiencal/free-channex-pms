# Phase 8: LLM Natural Language Interface - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Plain-English query interface for financial and booking data. Kim and Thomas type questions, the system generates SQL, executes it against the live ledger, and presents results with natural language descriptions. The LLM never performs arithmetic — every number comes from SQL. Scoped to financial and booking questions only; general data exploration is out of scope.

</domain>

<decisions>
## Implementation Decisions

### Query experience
- Chat interface with message history (not search bar)
- Session history is ephemeral — clears on page reload, no persistence to DB
- Conversational context — follow-up questions can reference earlier messages in the same session (e.g., "what about VRBO?" after asking about Airbnb)
- Show 3-4 clickable starter prompts when chat is empty to help Kim get started (e.g., "How much did Jay make this month?")

### Answer presentation
- Text answer + collapsible data table + "Show SQL" link on every response
- LLM generates SQL only — never performs arithmetic; SQL computes, LLM describes the result
- "Show SQL" link always visible (not behind a developer toggle) — transparency for both Kim and Thomas
- Data tables collapsed by default; user clicks to expand
- Financial numbers formatted US-style ($1,234.56 with commas and dollar sign); future TODO for European locale support

### Error & ambiguity handling
- Ambiguous questions prompt clarification — system asks follow-up ("Which property? What time period?") rather than guessing
- Empty results show a clear "no data" message with alternative query suggestions (e.g., "No VRBO bookings in March. Try: 'show all bookings in March'")
- Failed SQL shows friendly error + "Show details" expandable link with technical info for Thomas
- Query scope limited to financial and booking topics — off-topic questions get: "I can answer questions about revenue, expenses, bookings, and occupancy."

### Model & performance
- Mistral 7B via Ollama (already running locally) — no benchmarking needed
- Response time tolerance up to 30 seconds — accuracy over speed
- Streaming token-by-token response (ChatGPT-style) — feels responsive even on slower queries
- When Ollama is down: Query tab disabled/grayed out in dashboard; re-enables automatically when health check passes

### Claude's Discretion
- Exact starter prompt questions (should be representative of common queries)
- Schema prompt construction approach (how much schema context to inject)
- SQL validation and sanitization strategy (read-only enforcement)
- Chat UI component design (message bubbles, typing indicators, etc.)
- How many prior messages to include in conversational context window

</decisions>

<specifics>
## Specific Ideas

- "Must show its work" — the SQL that produced the answer must always be available for inspection via clickable link
- Kim should be able to use it without understanding SQL — the natural language answer is primary, data/SQL are supplementary
- Thomas uses "Show SQL" for debugging and verification — it's a trust mechanism
- Mistral 7B is already deployed and running on local Ollama instance

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-llm-natural-language-interface*
*Context gathered: 2026-02-28*
