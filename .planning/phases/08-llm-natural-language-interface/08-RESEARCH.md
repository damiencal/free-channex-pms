# Phase 8: LLM Natural Language Interface - Research

**Researched:** 2026-02-28
**Domain:** Text-to-SQL pipeline with Ollama (Mistral 7B), FastAPI SSE streaming, React chat UI
**Confidence:** HIGH (core stack verified via official sources; patterns verified with multiple sources)

---

## Summary

Phase 8 adds a natural-language query interface that converts user questions into SQL, executes the SQL against the live PostgreSQL ledger, and streams both the LLM narrative and structured results back to the browser. The implementation spans three layers: (1) a FastAPI streaming endpoint that talks to Ollama via the `ollama` Python library, (2) a SQL validation and execution layer using `sqlglot` for safety and SQLAlchemy `text()` for execution, and (3) a React chat UI using Zustand for session-scoped ephemeral state.

The Ollama Python library (`ollama` 0.6.1) provides an `AsyncClient` that yields `ChatResponse` objects as an async generator when `stream=True`. This integrates cleanly with FastAPI's `StreamingResponse` using `media_type="text/event-stream"` (via `sse-starlette` 3.3.2). The frontend reads the stream with `fetch` + `response.body.getReader()` and appends tokens to the last assistant message in the Zustand store. No WebSocket is needed — SSE (one-way server-push) is sufficient.

The critical architectural constraint is that the LLM only generates SQL — it never computes numbers. The backend executes the LLM-produced SQL via SQLAlchemy, formats the numeric results, and instructs the LLM to write a narrative _describing_ those results. SQL validation via `sqlglot` (parse + `isinstance(stmt, exp.Select)` check) plus a dedicated read-only PostgreSQL user enforces the read-only boundary at two independent layers.

**Primary recommendation:** Use `ollama` Python library + `sse-starlette` for streaming; `sqlglot` for SQL validation; Zustand for ephemeral chat state; build chat UI from shadcn/ui primitives (Card, Collapsible, Badge) rather than a third-party chat library.

---

## Standard Stack

### Core (Backend)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ollama` | 0.6.1 | Ollama Python client — AsyncClient for streaming chat | Official library; AsyncClient integrates directly with FastAPI async |
| `sse-starlette` | 3.3.2 | `EventSourceResponse` for SSE streaming from FastAPI | Production-ready, W3C compliant, handles client disconnect, released 2026-02-28 |
| `sqlglot` | latest | SQL parsing and statement-type validation | Pure Python, no dependencies, parses PostgreSQL dialect, `isinstance(stmt, exp.Select)` check |
| SQLAlchemy `text()` | 2.0 (already installed) | Execute validated SQL against DB | Already in stack; `text()` prevents string interpolation injection |

### Core (Frontend)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `zustand` | 5.0.11 (already installed) | Ephemeral chat session state | Already in stack; simpler than React state for cross-component message list |
| Fetch API + `ReadableStream` | Browser native | Consume SSE stream token by token | No library needed; `response.body.getReader()` is standard across all modern browsers |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `Intl.NumberFormat` | Browser native | Format financial numbers as `$1,234.56` | Already used in `HomeTab.tsx`; use same pattern for query results |
| shadcn/ui `Collapsible` | Already installed | Collapsible data table and SQL disclosure | Already in the component library |
| shadcn/ui `Card`, `Badge`, `Button`, `Skeleton` | Already installed | Chat bubble layout, loading state | Already in the component library |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sse-starlette` | `fastapi.responses.StreamingResponse` directly | StreamingResponse works but lacks client-disconnect handling; sse-starlette adds that for free |
| Custom chat UI | `shadcn-chat` (jakobhoeg) | `shadcn-chat` is unmaintained; build from primitives using existing shadcn/ui components |
| `sqlglot` parse check | Regex keyword blocking | `sqlglot` catches edge cases regex misses (e.g., CTEs, subqueries with DELETE); sqlglot is the right tool |
| Python `ollama` library | Raw `httpx` to Ollama API | `ollama` library is the official client; raw httpx adds no benefit here |

**Installation (new packages only):**
```bash
# Backend — add to pyproject.toml
uv add ollama sse-starlette sqlglot

# Frontend — no new packages needed
```

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── api/
│   └── query.py          # POST /api/query/ask  (new router)
├── query/
│   ├── __init__.py
│   ├── prompt.py         # build_system_prompt(), build_messages()
│   ├── sql_validator.py  # validate_sql() — sqlglot SELECT-only check
│   └── ollama_client.py  # get_ollama_client(), stream_chat()

frontend/src/
├── components/
│   └── query/
│       ├── QueryTab.tsx          # Top-level tab content
│       ├── ChatWindow.tsx        # Message list + auto-scroll
│       ├── ChatMessage.tsx       # Single message bubble with SQL/table disclosure
│       ├── StarterPrompts.tsx    # 3-4 clickable starter questions
│       ├── ChatInput.tsx         # Textarea + Send button
│       └── ResultTable.tsx       # Collapsible data table
├── hooks/
│   └── useChatStream.ts          # fetch streaming logic, appends tokens to store
└── store/
    └── useChatStore.ts           # Zustand store for ephemeral message list
```

### Pattern 1: Schema-Aware System Prompt

**What:** Inject the database schema as DDL-style table descriptions into the system message. Keep schema minimal — only the tables the LLM needs (bookings, journal_entries, journal_lines, accounts, expenses, properties).

**When to use:** Every request. Schema is small enough (6 tables, ~30 columns total) to fit in a single system message without RAG.

**Prompt structure:**
```python
SYSTEM_PROMPT = """You are a PostgreSQL SQL generator for a vacation rental management system.

TASK: Convert the user's natural language question into a single valid PostgreSQL SELECT query.

RULES:
- Generate ONLY a SELECT statement. Never INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER.
- Never perform arithmetic. SQL aggregations (SUM, AVG, COUNT) compute all numbers.
- If the question is ambiguous (missing property name, time period), ask ONE clarifying question instead of guessing.
- If the question is outside financial/booking scope, respond: "I can answer questions about revenue, expenses, bookings, and occupancy."
- Always output the SQL in a ```sql ... ``` code fence. Nothing else.

DATABASE SCHEMA:

Table: properties
  id INTEGER PRIMARY KEY
  slug VARCHAR(64)          -- short identifier e.g. 'jay', 'minnie'
  display_name VARCHAR(255) -- human-readable e.g. 'Jay', 'Minnie'

Table: bookings
  id INTEGER PRIMARY KEY
  platform VARCHAR(32)           -- 'airbnb', 'vrbo', 'rvshare'
  guest_name VARCHAR(255)
  check_in_date DATE
  check_out_date DATE
  net_amount NUMERIC(10,2)       -- net payout after platform fees (USD)
  property_id INTEGER REFERENCES properties(id)

Table: journal_entries
  id INTEGER PRIMARY KEY
  entry_date DATE
  description VARCHAR(512)
  source_type VARCHAR(64)        -- 'booking_payout', 'expense', 'loan_payment', etc.
  property_id INTEGER REFERENCES properties(id)

Table: journal_lines
  id INTEGER PRIMARY KEY
  entry_id INTEGER REFERENCES journal_entries(id)
  account_id INTEGER REFERENCES accounts(id)
  amount NUMERIC(12,2)           -- positive=debit, negative=credit

Table: accounts
  id INTEGER PRIMARY KEY
  number INTEGER                 -- chart of accounts number 1000-9999
  name VARCHAR(128)
  account_type VARCHAR(32)       -- 'asset', 'liability', 'equity', 'revenue', 'expense'

Table: expenses
  id INTEGER PRIMARY KEY
  expense_date DATE
  amount NUMERIC(12,2)           -- always positive (USD)
  category VARCHAR(64)
  description VARCHAR(512)
  vendor VARCHAR(255)
  attribution VARCHAR(32)        -- 'jay', 'minnie', 'shared'
  property_id INTEGER REFERENCES properties(id)

SIGN CONVENTION: Revenue account journal_lines have NEGATIVE amounts (credits).
To get positive revenue: SUM(journal_lines.amount) * -1 for revenue accounts.
"""
```

**Source:** Mistral AI text-to-SQL cookbook (docs.mistral.ai), Arize AI prompt guide

### Pattern 2: Two-Phase LLM Call

**What:** The pipeline makes two Ollama calls per user question:
1. **Phase A — SQL generation:** Ask the LLM to produce SQL given the schema + user question + conversation history.
2. **Phase B — Narrative generation:** Execute the SQL, then ask the LLM to describe the results in plain English.

**Why two phases:** Separates "generate SQL" from "describe results." The LLM sees real numbers from SQL execution — never guesses them.

```python
# Phase A: SQL generation (non-streaming, expect structured output)
sql_messages = build_sql_messages(user_question, conversation_history)
sql_response = await ollama_client.chat(
    model="mistral:7b-instruct",
    messages=sql_messages,
    stream=False,
    options={"temperature": 0.1}  # low temperature for deterministic SQL
)
raw_sql = extract_sql_from_response(sql_response.message.content)

# Validate (sqlglot) → execute (SQLAlchemy) → get rows

# Phase B: Narrative generation (streaming)
narrative_messages = build_narrative_messages(user_question, raw_sql, query_results)
async for chunk in await ollama_client.chat(
    model="mistral:7b-instruct",
    messages=narrative_messages,
    stream=True,
    options={"temperature": 0.3}
):
    yield chunk.message.content
```

**Source:** Training data pattern; verified against Mistral cookbook structure.

### Pattern 3: FastAPI SSE Endpoint

**What:** A single `POST /api/query/ask` endpoint that accepts the user message + conversation history and streams back an SSE response.

**Stream protocol:**
- `event: token` — individual LLM narrative tokens
- `event: sql` — the validated SQL (sent once, after Phase A)
- `event: results` — JSON-encoded table rows (sent once, after SQL execution)
- `event: error` — JSON error payload if SQL generation/execution fails
- `event: done` — signals stream end

```python
# Source: sse-starlette docs + ollama Python library docs
from sse_starlette import EventSourceResponse
from fastapi import APIRouter
from ollama import AsyncClient

router = APIRouter(prefix="/api/query", tags=["query"])

@router.post("/ask")
async def ask_query(request: QueryRequest):
    async def generate():
        try:
            # Phase A: SQL generation
            sql = await generate_sql(request.message, request.history)
            yield {"event": "sql", "data": sql}

            # Validate + execute
            rows, columns = await execute_validated_sql(sql)
            yield {"event": "results", "data": json.dumps({"columns": columns, "rows": rows})}

            # Phase B: Narrative streaming
            async for chunk in stream_narrative(request.message, sql, rows):
                yield {"event": "token", "data": chunk}

            yield {"event": "done", "data": ""}

        except SQLValidationError as e:
            yield {"event": "error", "data": json.dumps({"type": "validation", "message": str(e)})}
        except OllamaUnavailableError as e:
            yield {"event": "error", "data": json.dumps({"type": "ollama_down", "message": str(e)})}

    return EventSourceResponse(generate())
```

### Pattern 4: Ollama AsyncClient Initialization

**What:** Reuse a single `AsyncClient` instance configured with the Ollama URL from app config.

```python
# app/query/ollama_client.py
from ollama import AsyncClient
from app.config import get_config

_client: AsyncClient | None = None

def get_ollama_client() -> AsyncClient:
    global _client
    if _client is None:
        config = get_config()
        _client = AsyncClient(host=config.ollama_url)
    return _client
```

**Source:** ollama-python GitHub README (github.com/ollama/ollama-python)

### Pattern 5: SQL Validation (Two Layers)

**Layer 1 — sqlglot parse check (application layer):**
```python
# app/query/sql_validator.py
import sqlglot
from sqlglot import expressions as exp

class SQLValidationError(Exception):
    pass

def validate_sql(sql: str) -> str:
    """Parse SQL and reject anything that is not a single SELECT statement."""
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except Exception as e:
        raise SQLValidationError(f"SQL parse error: {e}")

    if len(statements) != 1:
        raise SQLValidationError(f"Expected 1 statement, got {len(statements)}")

    stmt = statements[0]
    if not isinstance(stmt, exp.Select):
        raise SQLValidationError(
            f"Only SELECT statements are allowed. Got: {type(stmt).__name__}"
        )

    return sql.strip()
```

**Layer 2 — PostgreSQL read-only user (database layer):**

Create a dedicated read-only database user for LLM query execution:
```sql
-- Run once as superuser (PostgreSQL 14+)
CREATE ROLE llm_reader LOGIN PASSWORD 'changeme';
GRANT CONNECT ON DATABASE rental_management TO llm_reader;
GRANT USAGE ON SCHEMA public TO llm_reader;
GRANT pg_read_all_data TO llm_reader;  -- PostgreSQL 14+

-- Add to .env as LLM_DATABASE_URL
-- postgresql+psycopg://llm_reader:changeme@host/rental_management
```

Even if sqlglot validation is bypassed, the DB user cannot write. Defense in depth.

**Source:** Crunchy Data blog (crunchydata.com); sqlglot GitHub README

### Pattern 6: Frontend SSE Consumer

**What:** Use `fetch` with `response.body.getReader()` to consume the SSE stream token by token. No `EventSource` (which requires GET) — use `fetch` with POST body.

```typescript
// hooks/useChatStream.ts
export function useChatStream() {
  const { appendToken, setSql, setResults, setError, setDone } = useChatStore()

  async function sendMessage(message: string, history: ChatMessage[]) {
    const response = await fetch('/api/query/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''  // keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('event: ')) continue  // event type line
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          // parse event from previous event: line — handle event routing
          handleSSEData(data)
        }
      }
    }
  }

  return { sendMessage }
}
```

**Source:** MDN ReadableStream docs (developer.mozilla.org)

### Pattern 7: Zustand Chat Store (Ephemeral)

```typescript
// store/useChatStore.ts
import { create } from 'zustand'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string       // final/streaming text
  sql?: string          // the SQL that produced this answer
  results?: QueryResult // table data
  error?: ChatError     // error details if failed
  isStreaming: boolean
}

interface ChatStore {
  messages: ChatMessage[]
  isOllamaAvailable: boolean
  addUserMessage: (content: string) => string     // returns id
  addAssistantMessage: () => string               // returns id, starts streaming
  appendToken: (id: string, token: string) => void
  setSql: (id: string, sql: string) => void
  setResults: (id: string, results: QueryResult) => void
  setError: (id: string, error: ChatError) => void
  setDone: (id: string) => void
  setOllamaAvailable: (available: boolean) => void
  // NOTE: No persist() — session-only, clears on reload
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isOllamaAvailable: true,
  addUserMessage: (content) => {
    const id = crypto.randomUUID()
    set((s) => ({ messages: [...s.messages, { id, role: 'user', content, isStreaming: false }] }))
    return id
  },
  addAssistantMessage: () => {
    const id = crypto.randomUUID()
    set((s) => ({ messages: [...s.messages, { id, role: 'assistant', content: '', isStreaming: true }] }))
    return id
  },
  appendToken: (id, token) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m
      ),
    })),
  // ... setSql, setResults, setError, setDone follow same pattern
}))
```

**Key: no `persist()` middleware** — this intentionally clears on page reload.

**Source:** zustand docs + reliasoftware.com chat tutorial pattern

### Pattern 8: Conversational Context Window

Include prior messages in the Ollama chat history. Recommended context: **last 10 messages** (5 user + 5 assistant turns). This keeps the context window manageable for Mistral 7B (32K tokens) while supporting follow-up questions like "what about VRBO?".

```python
def build_sql_messages(
    user_question: str,
    history: list[dict],  # [{"role": "user"|"assistant", "content": str}]
) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Include last 10 history messages (5 turns)
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_question})
    return messages
```

### Pattern 9: Ollama Availability Gate

The health endpoint already checks Ollama (`/health` returns `"ollama": "available"|"unavailable"`). The QueryTab must:
1. Poll `/health` or react to Ollama status from the store.
2. Render the tab trigger grayed/disabled when `ollama === "unavailable"`.
3. Re-enable automatically when health check returns available.

```typescript
// In AppShell.tsx — extend health polling
const { data: healthData } = useQuery({
  queryKey: ['health'],
  queryFn: () => apiFetch<HealthResponse>('/health'),
  refetchInterval: 30_000,  // poll every 30s
})
const ollamaAvailable = healthData?.ollama === 'available'
```

### Anti-Patterns to Avoid

- **LLM arithmetic:** Never ask the LLM to sum or compute. Always execute SQL and pass rows to the narrative prompt.
- **String interpolating user input into SQL:** Always use `sqlglot` parse validation. Never `f"SELECT {user_input}"`.
- **Streaming SQL generation:** Set `stream=False` for Phase A (SQL gen). Streaming an incomplete SQL string makes extraction unreliable. Stream only Phase B (narrative).
- **Using EventSource API for POST:** Browser `EventSource` only supports GET. Use `fetch` + `ReadableStream` for POST requests to `/api/query/ask`.
- **Storing chat history in DB:** Explicitly decided as out of scope. Session-only Zustand store, no `persist()`.
- **Including all tables in schema prompt:** Only include the 6 relevant tables. Smaller schema = better SQL generation accuracy.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQL statement type checking | Regex keyword blocklist | `sqlglot` | Regex misses CTEs (`WITH ... DELETE`), subqueries, dialect variations; sqlglot parses the full AST |
| SSE streaming from FastAPI | Manual `yield "data: ...\n\n"` headers | `sse-starlette` EventSourceResponse | Handles client disconnect, proper headers, graceful shutdown |
| Ollama HTTP calls | Raw `httpx` async requests | `ollama` Python library | Official client; handles streaming protocol, error types, connection management |
| Chat message state | Local `useState` in component | Zustand store | Messages must be shared between ChatWindow, ChatInput, and useChatStream hook |
| Number formatting | Manual string manipulation | `Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'})` | Handles commas, decimal places, locale correctly; already used in `HomeTab.tsx` |

**Key insight:** The dangerous-looking parts (SQL safety, streaming protocol) already have mature solutions. The custom work is prompt engineering and UI composition.

---

## Common Pitfalls

### Pitfall 1: LLM Outputs SQL Wrapped in Markdown Fence

**What goes wrong:** Mistral 7B (and most instruction-tuned models) outputs SQL inside ```sql ... ``` code fences. Naive string extraction misses edge cases.

**Why it happens:** Model follows common Markdown conventions. The system prompt instructs it to use a code fence, so this is expected.

**How to avoid:** Use a robust extractor:
```python
import re

def extract_sql_from_response(text: str) -> str:
    # Try ```sql ... ``` fence first
    match = re.search(r'```(?:sql)?\s*(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: look for SELECT keyword
    match = re.search(r'(SELECT\s+.+)', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    raise SQLValidationError("No SQL found in LLM response")
```

**Warning signs:** `sqlglot.parse()` raises on non-SQL text — catch `ParseError`.

### Pitfall 2: Streaming SSE with POST via Browser EventSource

**What goes wrong:** Browser native `EventSource` API only supports GET requests. Using it for the chat endpoint (which needs a POST body for message + history) silently fails or requires awkward workarounds.

**Why it happens:** W3C SSE spec defines `EventSource` for GET only.

**How to avoid:** Use `fetch` + `response.body.getReader()` for POST SSE. This works in all modern browsers and is the standard pattern for LLM chat frontends.

**Warning signs:** `EventSource` constructor URL doesn't accept request body; the endpoint never receives the message.

### Pitfall 3: Appending to Wrong Message on Fast Token Arrival

**What goes wrong:** Multiple concurrent `appendToken` calls update the message list before React re-renders. If message IDs are mismatched, tokens appear on the wrong message.

**Why it happens:** Zustand `set()` is synchronous but React batches renders; async token arrival interleaves with state updates.

**How to avoid:** Always identify the assistant message by the ID returned from `addAssistantMessage()`. Capture the ID in the hook closure at stream start, use it throughout the stream:
```typescript
const assistantId = useChatStore.getState().addAssistantMessage()
// ... use assistantId in every appendToken call
```

**Warning signs:** Tokens appear in the wrong message bubble, or messages merge unexpectedly.

### Pitfall 4: Revenue Sign Convention in SQL Results

**What goes wrong:** The database stores revenue journal_lines as negative credits. A query like `SELECT SUM(amount)` on revenue lines returns negative numbers. The LLM narrative says "you lost $5,000" when actually there was $5,000 revenue.

**Why it happens:** Double-entry accounting convention: revenue is a credit (negative in this schema). Documented in `dashboard.py` and `journal_line.py`.

**How to avoid:** Include the sign convention explicitly in the system prompt (already included in Pattern 1 above). Also include a note in the narrative prompt:
```
IMPORTANT: Revenue journal_lines have NEGATIVE amounts. SUM(amount) for revenue accounts
will be negative. The SQL should negate for display: -SUM(journal_lines.amount)
```

**Warning signs:** LLM describes revenue as a loss, or numbers in narrative don't match the table data.

### Pitfall 5: Mistral 7B Temperature Too High for SQL Generation

**What goes wrong:** At temperature > 0.3, Mistral produces syntactically varied SQL that sometimes introduces errors (wrong table aliases, missing JOINs). At temperature 0, it's too rigid and may fail on novel question phrasings.

**Why it happens:** SQL generation requires precision; temperature controls randomness.

**How to avoid:** Use `temperature: 0.1` for Phase A (SQL generation). Use `temperature: 0.3` for Phase B (narrative — needs some variety).

**Warning signs:** High rate of sqlglot parse failures or PostgreSQL execution errors.

### Pitfall 6: Context Window Overflow with Long History

**What goes wrong:** With 32K context and each SQL generation turn consuming ~2K tokens (schema ~800 tokens + history + question), a long session can overflow, causing Mistral to truncate the schema or history.

**Why it happens:** Mistral 7B-instruct has 32K context but the schema prompt is large.

**How to avoid:** Cap conversation history at 10 messages (5 turns). The schema is ~800 tokens; 10 history messages at ~200 tokens each = ~2000 tokens; total stays well under 5K even for complex questions.

**Warning signs:** SQL quality degrades mid-session; LLM ignores schema constraints.

### Pitfall 7: Ollama Unavailable During Request (Mid-Stream)

**What goes wrong:** Ollama process dies after the SSE connection opens but before streaming completes. The `ollama` client raises `ConnectionError` mid-async-generator.

**Why it happens:** Ollama is a local process that can crash or be restarted.

**How to avoid:** Wrap the entire `generate()` async generator in try/except and emit an `event: error` SSE event before closing:
```python
except Exception as e:
    yield {"event": "error", "data": json.dumps({"type": "ollama_down", "message": "Ollama connection lost"})}
```

The frontend shows the friendly error and "Show details" expander.

---

## Code Examples

Verified patterns from official sources:

### Ollama AsyncClient Streaming with FastAPI (sse-starlette)

```python
# Source: ollama-python GitHub README + sse-starlette PyPI docs
from ollama import AsyncClient
from sse_starlette import EventSourceResponse
from fastapi import APIRouter
import json

router = APIRouter(prefix="/api/query", tags=["query"])

@router.post("/ask")
async def ask(request: QueryRequest, db: Session = Depends(get_db)):
    client = get_ollama_client()

    async def generate():
        try:
            # Phase A: SQL generation (non-streaming for reliable extraction)
            sql_response = await client.chat(
                model="mistral:7b-instruct",
                messages=build_sql_messages(request.message, request.history),
                stream=False,
                options={"temperature": 0.1},
            )
            raw_sql = extract_sql_from_response(sql_response.message.content)

            # Validate
            validated_sql = validate_sql(raw_sql)  # raises SQLValidationError if not SELECT
            yield {"event": "sql", "data": validated_sql}

            # Execute against read-only connection
            rows, columns = execute_query(validated_sql, db)
            yield {"event": "results", "data": json.dumps({"columns": columns, "rows": rows})}

            # Phase B: Narrative (streaming)
            async for chunk in await client.chat(
                model="mistral:7b-instruct",
                messages=build_narrative_messages(request.message, validated_sql, rows, columns),
                stream=True,
                options={"temperature": 0.3},
            ):
                if chunk.message.content:
                    yield {"event": "token", "data": chunk.message.content}

            yield {"event": "done", "data": ""}

        except SQLValidationError as e:
            yield {"event": "error", "data": json.dumps({"type": "sql_invalid", "detail": str(e)})}

    return EventSourceResponse(generate())
```

### sqlglot SELECT-only Validation

```python
# Source: sqlglot GitHub README
import sqlglot
from sqlglot import expressions as exp

def validate_sql(sql: str) -> str:
    try:
        statements = sqlglot.parse(sql.strip(), read="postgres")
    except Exception as e:
        raise SQLValidationError(f"Parse failed: {e}")

    if not statements or statements[0] is None:
        raise SQLValidationError("Empty SQL")
    if len(statements) > 1:
        raise SQLValidationError("Multiple statements not allowed")

    stmt = statements[0]
    if not isinstance(stmt, exp.Select):
        raise SQLValidationError(
            f"Only SELECT is allowed. Statement type: {type(stmt).__name__}"
        )
    return sql.strip()
```

### SQLAlchemy Raw SQL Execution (read-only connection)

```python
# Source: SQLAlchemy 2.0 docs
from sqlalchemy import text
from sqlalchemy.orm import Session

def execute_query(sql: str, db: Session) -> tuple[list[dict], list[str]]:
    """Execute validated SQL and return (rows, column_names).

    Uses the existing SQLAlchemy session. The DB user should be read-only.
    No parameterization needed since we validated it's a pure SELECT.
    """
    try:
        result = db.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return rows, columns
    except Exception as e:
        raise QueryExecutionError(f"SQL execution failed: {e}")
```

### React Fetch SSE Consumer

```typescript
// Source: MDN ReadableStream docs
async function streamQuery(
  message: string,
  history: ChatMessage[],
  handlers: SSEHandlers
): Promise<void> {
  const response = await fetch('/api/query/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history: history.slice(-10) }),
  })

  if (!response.ok) throw new Error(`HTTP ${response.status}`)

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = 'message'

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        const data = line.slice(6)
        switch (currentEvent) {
          case 'token':   handlers.onToken(data); break
          case 'sql':     handlers.onSql(data); break
          case 'results': handlers.onResults(JSON.parse(data)); break
          case 'error':   handlers.onError(JSON.parse(data)); break
          case 'done':    handlers.onDone(); break
        }
        currentEvent = 'message'  // reset after data line
      }
    }
  }
}
```

### Starter Prompt Suggestions

Recommended starter prompts for the empty chat state:

```typescript
const STARTER_PROMPTS = [
  "How much did Jay make this month?",
  "Show me all Airbnb bookings in January 2026",
  "What were the top expenses last quarter?",
  "What is the occupancy rate for Minnie in 2025?",
]
```

These cover the four primary query categories: revenue by property, bookings by platform, expenses, occupancy.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WebSocket for chat streaming | SSE (Server-Sent Events) | ~2023 | SSE is simpler for one-way LLM token streaming; WebSocket adds bidirectional complexity not needed here |
| LangChain text-to-SQL agents | Direct Ollama API + custom prompt | ~2024 | LangChain adds significant overhead and abstraction; direct Ollama is simpler for a single-model, fixed-schema use case |
| OpenAI format JSON for SQL extraction | Markdown code fence extraction | — | Mistral 7B-instruct is reliable with code fence conventions; `format: "json"` adds complexity |
| Polling-based chat (ajax refresh) | SSE streaming tokens | — | Streaming is now standard UX expectation for LLM interfaces |

**Deprecated/outdated:**
- `EventSource` API for POST requests: Cannot send request body; use `fetch` + `ReadableStream` instead.
- `stream: false` for long LLM responses: Users wait with no feedback; always stream Phase B (narrative).
- Sharing the app's main PostgreSQL user with the LLM query executor: Use a dedicated `llm_reader` role with `pg_read_all_data`.

---

## Open Questions

1. **Mistral 7B model tag: `mistral` vs `mistral:7b-instruct`**
   - What we know: Ollama library has both `mistral:latest` and `mistral:7b-instruct` tags. The user said "Mistral 7B is already deployed and running."
   - What's unclear: Which exact tag is currently pulled on the local Ollama instance.
   - Recommendation: Check with `ollama list` at task start. If `mistral` is present but not `mistral:7b-instruct`, use `mistral` (latest = 7B instruct v0.3). Document the model name in `config/base.yaml` as `ollama_model`.

2. **Read-only DB user: create new or reuse existing**
   - What we know: The existing `DATABASE_URL` uses a user with full privileges. A dedicated read-only user is best practice.
   - What's unclear: Whether creating a second DB user in Docker Compose / Alembic is within scope for this phase.
   - Recommendation: Add `LLM_DATABASE_URL` to `.env` using a new `llm_reader` role. Create via an Alembic migration or a `manage.py` command. The `sqlglot` validation provides defense even if the same user is used temporarily.

3. **SQL execution timeout enforcement**
   - What we know: 30-second tolerance for total response time. If generated SQL runs a full table scan, it could timeout PostgreSQL session.
   - What's unclear: Whether PostgreSQL `statement_timeout` is set on the existing connection.
   - Recommendation: Set `statement_timeout` on the read-only connection: `db.execute(text("SET statement_timeout = '15s'"))` before executing the LLM-generated query.

4. **Ambiguity detection: LLM or rule-based?**
   - What we know: Ambiguous questions should trigger a clarifying follow-up, not a guess.
   - What's unclear: Whether to detect ambiguity via LLM output (LLM says "I need clarification") or via a rules-based pre-check (detect "which property?" patterns).
   - Recommendation: Let the LLM detect ambiguity. The system prompt already instructs it to ask ONE clarifying question instead of guessing. If `extract_sql_from_response()` finds no SQL code fence, treat the entire LLM output as a clarification request and return it as an `event: clarification` SSE event.

---

## Sources

### Primary (HIGH confidence)

- `github.com/ollama/ollama-python` README — AsyncClient chat streaming API, `stream=True` behavior, `ChatResponse` structure, `ResponseError` exception
- `pypi.org/project/ollama/` — current version 0.6.1, installation
- `pypi.org/project/sse-starlette/` — current version 3.3.2 (released 2026-02-28), `EventSourceResponse` usage
- `github.com/tobymao/sqlglot` README — `parse_one()`, `parse()`, `exp.Select` isinstance check
- `developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams` — `fetch` + `getReader()` + `TextDecoder` pattern
- Project source code (`app/models/`, `app/api/dashboard.py`, `frontend/src/`) — existing patterns, schema, DB conventions

### Secondary (MEDIUM confidence)

- `docs.mistral.ai/cookbooks/third_party-neon-neon_text_to_sql` — schema injection format with XML tags, DDL-based schema representation, two-phase SQL + narrative approach
- `crunchydata.com/blog/creating-a-read-only-postgres-user` — PostgreSQL `pg_read_all_data` role (PG14+), `GRANT CONNECT`, `GRANT USAGE` commands
- `ollama.com/library/mistral:7b-instruct` — mistral 7B-instruct v0.3 as current recommended tag, Q4_K_M default quantization, 32K context window

### Tertiary (LOW confidence)

- `reliasoftware.com/blog/react-chatbot-ui` — Zustand chat store pattern (verified against Zustand docs that this is the correct API shape)
- Arize AI blog on text-to-SQL prompting — temperature recommendations (0.1 for SQL, 0.3 for narrative) — community consensus, not benchmarked for Mistral 7B specifically
- `medium.com` articles on FastAPI SSE patterns — consistent with official FastAPI and sse-starlette docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — ollama library, sse-starlette, sqlglot all verified via official PyPI pages and GitHub READMEs
- Architecture (two-phase LLM + streaming): HIGH — pattern verified against Mistral cookbook and FastAPI SSE docs
- SQL validation approach: HIGH — sqlglot parse + isinstance pattern verified against official README
- Prompt engineering: MEDIUM — schema structure verified against Mistral cookbook; temperature recommendations are LOW (community consensus only)
- Frontend streaming (fetch + ReadableStream): HIGH — MDN official docs
- Chat UI component approach (shadcn primitives): HIGH — verified against existing project component library

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (30 days for stable libraries; Ollama moves fast but API is stable)
