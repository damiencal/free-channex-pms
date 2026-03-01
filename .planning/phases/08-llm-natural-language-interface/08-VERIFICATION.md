---
phase: 08-llm-natural-language-interface
verified: 2026-03-01T01:45:55Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 8: LLM Natural Language Interface Verification Report

**Phase Goal:** Kim (and Thomas) can ask financial questions in plain English and receive accurate answers backed by SQL queries against the live ledger — never from LLM arithmetic
**Verified:** 2026-03-01T01:45:55Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Kim can type a plain-English financial question and receive an accurate answer | VERIFIED | Full pipeline: QueryTab → useChatStream → POST /api/query/ask → Ollama Phase A SQL gen → SQLAlchemy execution → Phase B narrative streaming. All wiring confirmed real, not stubs. |
| 2 | Every number comes from SQL execution — LLM never performs arithmetic | VERIFIED | SYSTEM_PROMPT rule 2 forbids LLM arithmetic; NARRATIVE_SYSTEM_PROMPT rule 1 forbids narrative LLM computation; all numbers flow through `execute_query()` → `results` SSE event → `setResults()` → `ResultTable`. |
| 3 | Thomas can see the SQL query via "Show SQL" | VERIFIED | `validated_sql` yielded as `event: sql` (with newline-collapse fix applied); `useChatStream` routes to `store.setSql()`; `ChatMessage` renders collapsible "Show SQL" disclosure with `<pre>` code block. |
| 4 | Ambiguous questions get clarification, not hallucinated numbers | VERIFIED | `is_clarification` detection in `query.py` (raw_sql == raw_text AND not starts-with-SELECT); clarification path yields only `token` + `done` events — no `sql` or `results` events emitted; SYSTEM_PROMPT rule 3 instructs LLM to ask ONE clarifying question instead of guessing. |

**Score:** 4/4 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/query/__init__.py` | Package marker | VERIFIED | Exists, 1-line package comment |
| `app/query/prompt.py` | Schema-aware system prompt + message builders | VERIFIED | 263 lines; exports SYSTEM_PROMPT, NARRATIVE_SYSTEM_PROMPT, build_sql_messages, build_narrative_messages, extract_sql_from_response; all 6 tables present; sign convention documented; 3 example queries |
| `app/query/sql_validator.py` | sqlglot SELECT-only validator | VERIFIED | 58 lines; exports SQLValidationError + validate_sql; uses sqlglot.parse + isinstance(exp.Select) AST check; rejects multi-statement, empty, non-SELECT |
| `app/query/ollama_client.py` | Singleton Ollama AsyncClient | VERIFIED | 35 lines; exports get_ollama_client(); lazy init from get_config().ollama_url; deferred import prevents circular startup issue |
| `app/api/query.py` | POST /api/query/ask SSE endpoint | VERIFIED | 206 lines; EventSourceResponse wrapping async generator; Phase A non-streaming SQL gen (temp 0.1) → validate → execute; Phase B streaming narrative (temp 0.3); statement_timeout 15s; Decimal/date serialization; clarification detection; structured error events |
| `app/main.py` | Query router registration | VERIFIED | `from app.api.query import router as query_router` at line 34; `app.include_router(query_router)` at line 143; correctly placed before SPA mount |
| `frontend/src/store/useChatStore.ts` | Ephemeral Zustand chat store | VERIFIED | 99 lines; exports useChatStore, ChatMessage, QueryResult, ChatError; NO persist middleware confirmed; all store actions: addUserMessage, addAssistantMessage, appendToken, setSql, setResults, setError, setDone |
| `frontend/src/hooks/useChatStream.ts` | SSE stream consumer hook | VERIFIED | 112 lines; exports useChatStream; uses plain fetch (not EventSource, not apiFetch); ReadableStream + TextDecoder; buffer-based SSE line parsing; assistantId captured before stream loop; dispatches token/sql/results/error/done events |
| `frontend/src/components/query/QueryTab.tsx` | Top-level Query tab | VERIFIED | 36 lines; imports useChatStore + useChatStream; renders StarterPrompts on empty state, ChatWindow when messages exist; disabled prop shows unavailable message |
| `frontend/src/components/query/ChatWindow.tsx` | Scrollable message list | VERIFIED | 27 lines; useEffect auto-scroll on messages.length + last message content; bottom-anchor ref |
| `frontend/src/components/query/ChatMessage.tsx` | Message bubbles + SQL disclosure | VERIFIED | 114 lines; user (right/primary) + assistant (left/muted) bubbles; streaming dot indicator; "Show SQL" collapsible with `<pre>` block; ResultTable integration; error display with expandable details |
| `frontend/src/components/query/StarterPrompts.tsx` | 4 clickable starter questions | VERIFIED | 42 lines; 4 questions covering Jay revenue, Airbnb bookings, top expenses, Minnie occupancy; shadcn Card components; onSelect callback |
| `frontend/src/components/query/ChatInput.tsx` | Chat text input | VERIFIED | 73 lines; auto-resize textarea (4-line cap); Enter sends, Shift+Enter newline; disabled state; send button disabled on empty or disabled prop |
| `frontend/src/components/query/ResultTable.tsx` | Collapsible data table | VERIFIED | 87 lines; Intl.NumberFormat USD formatting for money columns (regex pattern match); 100-row display cap; truncation note; collapsed by default |
| `frontend/src/components/layout/AppShell.tsx` | Query tab with Ollama gate | VERIFIED | QueryTab imported; health polling useQuery (30s refetchInterval, plain fetch('/health')); ollamaAvailable derived; TabsTrigger disabled + opacity-50 when unavailable; TabsContent renders QueryTab with disabled prop |
| `frontend/vite.config.ts` | /health proxy for dev | VERIFIED | /health proxy to http://localhost:8000 added alongside /api proxy |
| `config/base.yaml` | ollama_model config | VERIFIED | ollama_model: "llama3.2:latest" present (overrides default "mistral" from app/config.py) |
| `pyproject.toml` | New dependencies | VERIFIED | ollama, sse-starlette, sqlglot all listed in dependencies |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/query/prompt.py` | Database schema | DDL-style table descriptions in SYSTEM_PROMPT | WIRED | All 6 tables (properties, bookings, journal_entries, journal_lines, accounts, expenses) with column types; sign convention; property name guidance |
| `app/query/ollama_client.py` | `app/config.py` | `get_config().ollama_url` | WIRED | Deferred import inside get_ollama_client() function body; `AsyncClient(host=get_config().ollama_url)` |
| `app/query/sql_validator.py` | sqlglot | `isinstance(statements[0], exp.Select)` | WIRED | AST-level check confirmed at line 53 |
| `app/api/query.py` | `app/query/prompt.py` | build_sql_messages, build_narrative_messages, extract_sql_from_response | WIRED | All three imported and called in generate() |
| `app/api/query.py` | `app/query/sql_validator.py` | validate_sql, SQLValidationError | WIRED | Imported and called at line 144 before execute_query |
| `app/api/query.py` | `app/query/ollama_client.py` | get_ollama_client | WIRED | Called at line 115 inside generate() |
| `app/api/query.py` | sse_starlette | EventSourceResponse | WIRED | Imported at line 32; return EventSourceResponse(generate()) at line 206 |
| `app/api/query.py` | SQLAlchemy | text() + db.execute() | WIRED | execute_query() sets statement_timeout then executes user SQL; Decimal/date serialization applied |
| `app/main.py` | `app/api/query.py` | include_router | WIRED | query_router registered at line 143 |
| `frontend/src/hooks/useChatStream.ts` | `/api/query/ask` | fetch POST with ReadableStream | WIRED | `fetch('/api/query/ask', { method: 'POST', ... })` at line 23; getReader() on response.body |
| `frontend/src/hooks/useChatStream.ts` | `frontend/src/store/useChatStore.ts` | store actions via getState() | WIRED | useChatStore.getState() called in async context to avoid stale closures; all 5 event types (token, sql, results, error, done) routed to store actions |
| `frontend/src/components/query/QueryTab.tsx` | `frontend/src/hooks/useChatStream.ts` | sendMessage callback | WIRED | useChatStream() called; sendMessage passed to handleSend which is passed to StarterPrompts.onSelect and ChatInput.onSend |
| `frontend/src/components/layout/AppShell.tsx` | `/health` | useQuery polling (30s) | WIRED | fetch('/health') in queryFn; ollamaAvailable = healthData?.ollama === 'available' |
| `frontend/src/components/layout/AppShell.tsx` | `frontend/src/components/query/QueryTab.tsx` | TabsContent rendering | WIRED | `<QueryTab disabled={!ollamaAvailable} />` in TabsContent value="query" |

---

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| DASH-04 | User can ask financial questions in plain English via Ollama-powered interface | SATISFIED | Full chat UI with SSE streaming pipeline from question to narrative answer |
| DASH-05 | LLM interface generates SQL queries (never performs arithmetic directly) | SATISFIED | Phase A SQL gen → sqlglot validation → SQLAlchemy execution; both SYSTEM_PROMPT and NARRATIVE_SYSTEM_PROMPT explicitly forbid LLM arithmetic |
| DASH-06 | LLM interface shows generated SQL for transparency and debugging | SATISFIED | `event: sql` yielded (newline-collapsed); ChatMessage renders "Show SQL" collapsible always visible when sql field is set |

---

## Anti-Patterns Found

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `frontend/src/components/query/ChatInput.tsx` | `placeholder=` attribute | Info | HTML textarea placeholder attribute — not a code stub. Correct usage. |

No blocker or warning anti-patterns found. The only "placeholder" match is a valid HTML attribute in the textarea element, not a code stub.

---

## Human Verification Required

### 1. End-to-end streaming response

**Test:** With Ollama running (llama3.2:latest available), open the Query tab and ask "How much did Jay make in January?"
**Expected:** Tokens stream incrementally; after completion "Show SQL" link appears; clicking it reveals a valid PostgreSQL SELECT; "View data (N rows)" expands to a table with financial amounts formatted as $X,XXX.XX
**Why human:** Token streaming, UI transitions, and correct LLM output quality cannot be verified statically

### 2. Clarification behavior

**Test:** Ask an ambiguous question such as "How much did we make?" (no property, no time period)
**Expected:** LLM responds with a clarifying question ("Which property do you mean?") — no SQL or data table appears
**Why human:** LLM inference behavior cannot be verified statically; requires live Ollama response

### 3. Ollama health gate

**Test:** Stop Ollama, wait up to 30 seconds, observe Query tab; then start Ollama again, wait up to 30 seconds
**Expected:** Tab grays out (opacity-50, disabled) when Ollama is down; re-enables automatically when Ollama returns without page reload
**Why human:** Real-time health polling behavior requires runtime observation

### 4. Ephemeral chat history

**Test:** Have a conversation in the Query tab, then reload the page
**Expected:** Chat history is completely cleared — confirms no localStorage/sessionStorage persistence
**Why human:** Browser state cannot be verified statically

---

## Summary

Phase 8 goal is fully achieved at the structural and wiring level. The complete text-to-SQL pipeline is implemented and connected end-to-end:

**Backend pipeline (Plans 01 + 02):** Schema-aware SYSTEM_PROMPT covering all 6 database tables with sign convention; sqlglot AST-based SELECT-only validator; lazy Ollama AsyncClient singleton; POST /api/query/ask SSE endpoint implementing two-phase LLM pipeline (non-streaming SQL gen + streaming narrative); statement_timeout safety guard; clarification detection; structured error events; query router registered in main.py.

**Frontend (Plans 03 + 04):** Ephemeral Zustand store (no persist middleware); buffer-based SSE line parser routing token/sql/results/error/done events to store actions with stable assistantId reference; 6 chat components — StarterPrompts (4 representative questions), ChatInput (auto-resize textarea), ResultTable (collapsible + USD currency formatting), ChatMessage (Show SQL disclosure + error display), ChatWindow (auto-scroll), QueryTab (empty-state orchestration). Query tab wired into AppShell with 30-second Ollama health polling and disabled gate.

**Discovered issues corrected during Plans (documented in 08-04-SUMMARY):** ollama_model configured as "llama3.2:latest" in base.yaml (mistral not installed); SSE multi-line SQL data collapsed to single line before yielding (sse-starlette SSE spec behavior); /health Vite proxy added for dev mode.

Four human verification items remain — all require live Ollama and browser interaction. Automated structural verification is complete and passes.

---

_Verified: 2026-03-01T01:45:55Z_
_Verifier: Claude (gsd-verifier)_
