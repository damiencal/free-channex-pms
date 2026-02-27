---
phase: 01-foundation
plan: 04
subsystem: api
tags: [fastapi, structlog, lifespan, health-endpoint, httpx, sqlalchemy]

# Dependency graph
requires:
  - phase: 01-02
    provides: app/config.py with load_app_config(), get_config(), AppConfig.ollama_url
  - phase: 01-03
    provides: app/db.py with engine for DB connectivity check
provides:
  - app/logging.py with structlog ConsoleRenderer configuration
  - app/main.py with FastAPI app, lifespan startup checks, and router inclusion
  - app/api/__init__.py package init
  - app/api/health.py with GET /health diagnostic endpoint
affects:
  - 01-05 (manage.py CLI — can import app/config.py and app/db.py alongside the app)
  - all subsequent phases (all API routes registered via include_router on this app)
  - phase 8 (LLM/Ollama features — health endpoint already surfaces ollama status)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - FastAPI lifespan context manager (not deprecated on_event handlers)
    - structlog ConsoleRenderer for self-hosted human-readable output
    - Fail-fast for config and DB in lifespan; non-fatal warning for Ollama
    - /health always returns HTTP 200 — safe Docker HEALTHCHECK target
    - datetime.now(timezone.utc) not deprecated datetime.utcnow()

key-files:
  created:
    - app/logging.py
    - app/main.py
    - app/api/__init__.py
    - app/api/health.py
  modified: []

key-decisions:
  - "ConsoleRenderer chosen over JSONRenderer — self-hosted tool, logs read by operator directly"
  - "Ollama check is non-fatal: log.warning and continue — Ollama is Phase 8 feature, app must start without it"
  - "DB check is fatal: re-raise exception — cannot serve any requests without database"
  - "/health always returns HTTP 200 even when status=degraded — Docker HEALTHCHECK needs reliable HTTP 200"
  - "configure_logging() called at module import level to capture all log calls"

patterns-established:
  - "Lifespan pattern: asynccontextmanager + yield separates startup and shutdown cleanly"
  - "Health endpoint pattern: check each subsystem independently, set status=degraded on DB failure only"
  - "Logging integration: structlog.configure() once at startup; structlog.get_logger() per module"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 1 Plan 04: FastAPI App with Lifespan, Logging, and /health Endpoint Summary

**FastAPI app with asynccontextmanager lifespan (fail-fast config/DB checks, non-fatal Ollama check) and structlog ConsoleRenderer + GET /health returning DB, Ollama, and property diagnostics**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T16:31:07Z
- **Completed:** 2026-02-27T16:32:35Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- FastAPI application wired with lifespan startup: config loaded fail-fast, DB verified fail-fast, Ollama checked non-fatally with 3-second timeout
- structlog configured with ConsoleRenderer for human-readable operator logs; stdlib logging integrated so uvicorn output flows through same format
- GET /health endpoint returns full system diagnostics — status, timestamp, version, all loaded properties, DB status, Ollama status — always HTTP 200 for Docker HEALTHCHECK compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Create structlog logging config and FastAPI app with lifespan startup checks** - `fec1830` (feat)
2. **Task 2: Create GET /health endpoint with DB, Ollama, and config diagnostics** - `118b5d0` (feat)

**Plan metadata:** _(docs commit — see below)_

## Files Created/Modified

- `app/logging.py` - structlog configuration: ConsoleRenderer + stdlib basicConfig integration
- `app/main.py` - FastAPI app with lifespan (config load, SELECT 1 DB check, Ollama GET check); imports health router
- `app/api/__init__.py` - API package init
- `app/api/health.py` - GET /health: status/timestamp/version/properties/database/ollama JSON response

## Decisions Made

- **ConsoleRenderer over JSONRenderer:** Self-hosted tool with operator reading logs directly in terminal or Docker logs. JSON output adds noise without benefit at this scale. JSON logging would be appropriate if logs were shipped to Loki/Datadog.
- **Ollama check is non-fatal:** Ollama is a Phase 8 feature. The app must start and serve booking/accounting routes even when Ollama is unavailable (e.g., first-run, macOS sleep, model not loaded). A `log.warning` is sufficient — the health endpoint surfaces the status.
- **DB check re-raises:** Without the database, no routes can function. Raising during lifespan prevents the app from accepting requests in a broken state. Operator sees the error in logs immediately.
- **/health always returns HTTP 200:** Docker HEALTHCHECK checks for non-2xx to mark a container unhealthy. If /health returned 503 when Ollama was down, Docker would restart healthy containers unnecessarily. The JSON `status` field communicates degraded state to monitoring without triggering restarts.
- **configure_logging() at module import:** Calling it at module level (before `log = structlog.get_logger()`) ensures no log call is made before structlog is configured, even during module-level initialization.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required for this plan. The app starts cleanly with existing config/ YAML files and .env DATABASE_URL from prior plans.

## Next Phase Readiness

- Plan 01-05 (manage.py CLI): `app/main.py` provides the `app` object; `app/config.py` and `app/db.py` are importable alongside the FastAPI app without starting the server
- Phase 2+ (all API features): New routes added to `app/api/` and registered via `app.include_router()` in `app/main.py`
- Docker health check: `curl http://localhost:8000/health` works as HEALTHCHECK target (always HTTP 200)
- Running `uvicorn app.main:app` with a live PostgreSQL and config/ directory starts cleanly with full diagnostic logging

**No blockers.** Foundation plan 01-05 can proceed immediately.

---
*Phase: 01-foundation*
*Completed: 2026-02-27*
