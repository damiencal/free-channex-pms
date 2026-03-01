---
phase: 08-llm-natural-language-interface
plan: "02"
subsystem: api
tags: [fastapi, sse, ollama, sqlalchemy, sqlglot, sse-starlette, text-to-sql, streaming]

requires:
  - phase: 08-01
    provides: app/query package — prompt.py, sql_validator.py, ollama_client.py, dependencies installed

provides:
  - POST /api/query/ask SSE streaming endpoint (app/api/query.py)
  - Two-phase LLM pipeline: SQL generation (non-streaming) + narrative streaming
  - Query router registered in main.py

affects:
  - 08-03 (chat UI — frontend calls this endpoint)
  - 08-04 (integration tests will test this endpoint)

tech-stack:
  added: []
  patterns:
    - "SSE streaming via EventSourceResponse wrapping async generator"
    - "Two-phase LLM pipeline: Phase A non-streaming SQL gen, Phase B streaming narrative"
    - "statement_timeout guard on SQL execution (15s)"
    - "Decimal/date → JSON-safe conversion in SQL result rows"

key-files:
  created:
    - app/api/query.py
  modified:
    - app/main.py

key-decisions:
  - "clarification detection: raw_sql == raw_text AND not starts with SELECT — absence of SQL signals LLM is asking for clarification, not a bug"
  - "Phase A non-streaming (stream=False, temp 0.1) for reliable SQL extraction via regex; Phase B streaming (stream=True, temp 0.3) for narrative tokens"
  - "statement_timeout = 15000ms set per-connection before executing user-generated SQL — prevents runaway queries"
  - "Decimal/date/datetime converted to float/isoformat before json.dumps — SQLAlchemy Numeric returns Python Decimal which is not JSON-serializable"
  - "error_type detection via 'connect' in str(e).lower() for ollama_down vs unknown — simple heuristic, sufficient for operational visibility"

patterns-established:
  - "SSE generator pattern: async def generate() yields dicts with event/data keys, wrapped in EventSourceResponse"
  - "Per-phase LLM options dict: {'temperature': N} passed to client.chat options parameter"

duration: 2min
completed: 2026-02-28
---

# Phase 8 Plan 02: Query API Endpoint Summary

**POST /api/query/ask SSE endpoint composing two-phase Ollama pipeline: non-streaming SQL generation with sqlglot validation and SQLAlchemy execution, followed by streaming narrative description**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-01T01:07:05Z
- **Completed:** 2026-03-01T01:09:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `app/api/query.py` with POST /api/query/ask SSE streaming endpoint
- Implemented two-phase pipeline: Phase A SQL gen (non-streaming, temp 0.1) → validate → execute → Phase B narrative streaming (temp 0.3)
- Registered query_router in main.py after dashboard_router, before SPA mount
- All 17 implementation criteria verified via source inspection and import checks

## Task Commits

Each task was committed atomically:

1. **Task 1: Create query API endpoint with SSE streaming** - `65e416e` (feat)
2. **Task 2: Register query router in main.py** - `05aab7c` (feat)

**Plan metadata:** (docs commit — follows this summary)

## Files Created/Modified

- `app/api/query.py` - POST /api/query/ask SSE endpoint with two-phase LLM pipeline, SQL validation, execution, clarification detection, and structured error events
- `app/main.py` - Added query_router import and include_router registration

## Decisions Made

- **Clarification detection via `raw_sql == raw_text AND not startswith SELECT`**: When `extract_sql_from_response` returns the original text unchanged (no code fence or SELECT found), and that text doesn't look like SQL, the LLM is asking for clarification. The response is streamed as tokens without sql/results events.
- **Phase A non-streaming, Phase B streaming**: SQL generation uses `stream=False` for reliable single-response extraction. Narrative uses `stream=True` for progressive token delivery to the UI.
- **statement_timeout = '15000' (ms)**: Protects the database from user-generated SQL that might cause full-table scans or long-running aggregations.
- **Decimal/date serialization**: SQLAlchemy returns Python `Decimal` for `NUMERIC` columns and `date`/`datetime` for `DATE`/`TIMESTAMP` columns — both non-JSON-serializable. Converted to `float` and `isoformat()` respectively before `json.dumps`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The plan verification note says `router.routes` should show `['/ask']` but FastAPI's APIRouter stores the combined prefix + path (`/api/query/ask`) on route objects when a prefix is set. The actual endpoint is accessible at the correct full path `/api/query/ask` — verified via `app.routes` after include_router. This is correct behavior.

## User Setup Required

None - no external service configuration required. Ollama connectivity was already validated in Phase 1 and Phase 8 Plan 01.

## Next Phase Readiness

- `POST /api/query/ask` is live and registered — ready for 08-03 (chat UI frontend) to consume
- SSE event schema is fixed: `sql`, `results`, `token`, `error`, `done`
- Error types are enumerated: `sql_invalid`, `sql_execution`, `ollama_down`, `unknown`
- No blockers for parallel 08-03 execution

---
*Phase: 08-llm-natural-language-interface*
*Completed: 2026-02-28*
