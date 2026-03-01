---
phase: 08-llm-natural-language-interface
plan: 01
subsystem: api
tags: [ollama, sqlglot, sse-starlette, llm, text-to-sql, postgresql, python]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: AppConfig singleton (get_config/load_app_config), pyproject.toml dependency management
provides:
  - app/query package with schema-aware LLM prompt, SQL validator, Ollama client
  - SYSTEM_PROMPT with all 6 DB tables, sign convention, and example queries
  - NARRATIVE_SYSTEM_PROMPT for plain-English result narration
  - SQLValidationError + validate_sql() enforcing SELECT-only via sqlglot AST
  - get_ollama_client() lazy-initialized singleton AsyncClient
  - ollama, sse-starlette, sqlglot dependencies installed
  - AppConfig.ollama_model field (default: 'mistral')
affects:
  - 08-02-plan (streaming API endpoint — composes all three modules)
  - 08-03-plan (frontend query UI — depends on SSE endpoint built on top of these)
  - 08-04-plan (conversation history — builds on build_sql_messages history param)

# Tech tracking
tech-stack:
  added: [ollama==0.6.1, sqlglot==29.0.1, sse-starlette==3.3.2]
  patterns:
    - Schema hardcoded in SYSTEM_PROMPT (not dynamic introspection) — controlled and minimal
    - Deferred get_config() import in ollama_client.py — allows import before config loaded
    - Singleton pattern for AsyncClient — reuse across requests
    - sqlglot AST isinstance check for SELECT enforcement — more reliable than string matching

key-files:
  created:
    - app/query/__init__.py
    - app/query/prompt.py
    - app/query/sql_validator.py
    - app/query/ollama_client.py
  modified:
    - pyproject.toml
    - app/config.py

key-decisions:
  - "Schema hardcoded in SYSTEM_PROMPT string (not imported from app.models) — keeps prompt controlled and minimal; schema changes require explicit prompt update"
  - "sqlglot isinstance(statements[0], exp.Select) check — AST-level enforcement is more reliable than regex/string matching; catches EXPLAIN SELECT, CTEs parsed as non-Select, etc."
  - "get_config() called inside get_ollama_client() function body (not at module level) — allows ollama_client.py to be imported before load_app_config() runs at lifespan"
  - "extract_sql_from_response does NOT raise on missing SQL — absence of SQL signals LLM clarification question; caller decides how to handle"
  - "10-message history cap in build_sql_messages — bounded context window; prevents token overflow on long conversations"
  - "ollama_model field defaults to 'mistral' — matches pre-existing Ollama check in lifespan (Phase 1 decision); operator overrides via OLLAMA_MODEL env var or base.yaml"

patterns-established:
  - "Query module pattern: each module has one responsibility (prompt, validation, client) with explicit exports list in module docstring"
  - "Deferred config import: import get_config inside function body (not module top) when module used before config is loaded"

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 8 Plan 1: LLM Query Foundation Summary

**Schema-aware text-to-SQL prompt, sqlglot SELECT-only validator, and lazy Ollama AsyncClient — the three building blocks for Plan 02's streaming query endpoint**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-01T01:01:45Z
- **Completed:** 2026-03-01T01:04:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Created `app/query/` package with three focused modules: prompt builders, SQL validator, Ollama client
- SYSTEM_PROMPT covers all 6 tables (properties, bookings, journal_entries, journal_lines, accounts, expenses) with column types, sign convention, property name guidance, and 3 example queries
- SQL validator enforces SELECT-only policy via sqlglot AST parsing — rejects DELETE, INSERT, DROP, CREATE, ALTER, and multi-statement batches
- Ollama AsyncClient singleton lazy-initialized from `get_config().ollama_url` on first call
- Three new packages (ollama 0.6.1, sqlglot 29.0.1, sse-starlette 3.3.2) installed
- `AppConfig.ollama_model` field added (default: `'mistral'`)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dependencies and config** - `8c1d709` (chore)
2. **Task 2: Create prompt.py — schema-aware prompt and message builders** - `5b807dd` (feat)
3. **Task 3: Create sql_validator.py and ollama_client.py** - `eda6b6e` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `pyproject.toml` — Added ollama, sse-starlette, sqlglot dependencies
- `app/config.py` — Added `AppConfig.ollama_model: str = "mistral"` after `ollama_url`
- `app/query/__init__.py` — Package marker
- `app/query/prompt.py` — SYSTEM_PROMPT, NARRATIVE_SYSTEM_PROMPT, build_sql_messages, build_narrative_messages, extract_sql_from_response
- `app/query/sql_validator.py` — SQLValidationError, validate_sql()
- `app/query/ollama_client.py` — get_ollama_client() singleton factory

## Decisions Made

- **Schema hardcoded in SYSTEM_PROMPT** (not dynamically read from app.models) — keeps prompt controlled; schema changes require intentional prompt update rather than automatic drift.
- **sqlglot AST isinstance check** for SELECT enforcement — more reliable than regex; handles edge cases like EXPLAIN, parsing oddities.
- **Deferred `get_config()` import** inside `get_ollama_client()` function body — allows importing the module before `load_app_config()` is called at FastAPI lifespan startup.
- **`extract_sql_from_response` does not raise** on missing SQL — absence of a code fence means the LLM is clarifying or declining; caller in Plan 02 handles this case.
- **10-message history cap** in `build_sql_messages` — prevents token overflow on extended conversations.
- **`ollama_model` defaults to `"mistral"`** — consistent with Phase 1 lifespan Ollama connectivity check; operator overrides via `OLLAMA_MODEL` env var.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required beyond Ollama being available (already documented in Phase 1).

## Next Phase Readiness

- `app/query/` package fully ready for Plan 02 to compose into streaming SSE endpoint
- `ollama_client.get_ollama_client()` + `prompt.build_sql_messages()` + `sql_validator.validate_sql()` form complete pipeline
- `sse-starlette` installed and ready for `EventSourceResponse` in Plan 02
- `NARRATIVE_SYSTEM_PROMPT` + `build_narrative_messages()` ready for Phase B narration in Plan 02/03

---
*Phase: 08-llm-natural-language-interface*
*Completed: 2026-03-01*
