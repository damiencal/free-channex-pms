---
phase: 06-guest-communication
plan: "05"
subsystem: api
tags: [fastapi, sqlalchemy, apscheduler, communication, guest-messaging]

# Dependency graph
requires:
  - phase: 06-04
    provides: CommunicationLog entries created by ingestion hooks and _create_communication_logs()
  - phase: 06-03
    provides: rebuild_pre_arrival_jobs() and schedule_pre_arrival_job() in app/communication/scheduler.py
  - phase: 06-01
    provides: CommunicationLog model and communication_logs table
provides:
  - "GET /communication/logs endpoint: filterable by status, message_type, platform"
  - "POST /communication/confirm/{log_id}: operator confirms VRBO/RVshare message as sent"
  - "communication_router registered in main.py"
  - "Pre-arrival scheduler jobs rebuilt from DB at every app startup"
affects: [07-dashboard, 08-llm-chat]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fixed-path routes before path-param routes (no route conflict)"
    - "Same join pattern as compliance: select(Model, Booking, Property.slug.label('prop_slug'))"
    - "Idempotent confirm: already-sent returns success dict, native_configured returns 409"
    - "await rebuild_pre_arrival_jobs() in lifespan after scheduler.start() — APScheduler must be running first"

key-files:
  created:
    - app/api/communication.py
  modified:
    - app/main.py

key-decisions:
  - "confirm endpoint uses log_id (not booking_id) — cleaner, avoids ambiguity across message types per booking"
  - "native_configured entries return 409 (not idempotent) — Airbnb welcome is tracked but never sent via API; operator confusion guard"
  - "already-sent returns success dict (not 409) — idempotent confirm prevents operator frustration on double-click"
  - "rebuild_pre_arrival_jobs() awaited after scheduler.start() — jobs must be added to running scheduler"

patterns-established:
  - "Communication API follows compliance API pattern: list with joins + path-param action endpoints"
  - "Startup lifespan sequence: config > templates > DB > Ollama > scheduler > job-rebuild > ready"

# Metrics
duration: 1min
completed: 2026-02-28
---

# Phase 6 Plan 05: Communication API and Startup Wiring Summary

**FastAPI communication router (GET /logs, POST /confirm/{log_id}) plus APScheduler pre-arrival job rebuild at startup, completing the Phase 6 end-to-end guest messaging system**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-28T19:53:24Z
- **Completed:** 2026-02-28T19:54:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- GET /communication/logs returns all communication log entries joined with Booking and Property, filterable by status, message_type, and platform
- POST /communication/confirm/{log_id} transitions pending->sent with idempotent behavior and 409 guard for native_configured Airbnb entries
- communication_router registered in main.py alongside compliance, ingestion, accounting, and reports routers
- Pre-arrival scheduler jobs rebuilt from communication_logs table at startup (step 6 in lifespan), surviving Docker restarts

## Task Commits

Each task was committed atomically:

1. **Task 1: Create communication API router** - `3520d82` (feat)
2. **Task 2: Register communication router and add pre-arrival job rebuild to main.py** - `ca5185d` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `app/api/communication.py` - Communication router: GET /communication/logs (filterable list with booking joins), POST /communication/confirm/{log_id} (idempotent operator confirm)
- `app/main.py` - Added communication_router import and include_router; added rebuild_pre_arrival_jobs() import and await call in lifespan step 6; updated module docstring

## Decisions Made
- confirm uses log_id (not booking_id): log_id is unambiguous — a booking can have multiple communication logs (welcome + pre_arrival); booking_id would require a message_type parameter
- native_configured entries return 409: these are Airbnb welcome logs the system tracks but never sends; preventing confirm via API guards against operator confusion
- already-sent returns success dict (not 409): idempotent pattern matches compliance confirm behavior; operators clicking twice should not see an error
- rebuild_pre_arrival_jobs() awaited after scheduler.start(): APScheduler must be running before jobs can be registered (DateTrigger add_job requires active scheduler)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 6 (Guest Communication) is now complete: CommunicationLog model, messenger service (welcome + pre-arrival), scheduler (job registration + rebuild), ingestion hooks, operator emailer, and API endpoints all operational
- Phase 7 (Dashboard) can use GET /communication/logs to display pending VRBO/RVshare messages for operator action and POST /communication/confirm/{log_id} for one-click confirmation
- Pre-arrival jobs survive Docker restarts via rebuild_pre_arrival_jobs() — no missed messages on deployment
- No blockers for Phase 7

---
*Phase: 06-guest-communication*
*Completed: 2026-02-28*
