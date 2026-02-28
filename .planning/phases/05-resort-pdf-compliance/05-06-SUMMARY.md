---
phase: 05-resort-pdf-compliance
plan: 06
subsystem: api
tags: [fastapi, sqlalchemy, compliance, pdf, webhook, n8n, resort]

# Dependency graph
requires:
  - phase: 05-resort-pdf-compliance
    provides: process_booking_submission() orchestrator and should_auto_submit() threshold check (05-04)
  - phase: 05-resort-pdf-compliance
    provides: ResortSubmission ORM model (05-01)
  - phase: 05-resort-pdf-compliance
    provides: APScheduler urgency scheduler wired into main.py lifespan (05-05)
provides:
  - GET /compliance/submissions — paginated list with status/urgency filters and full booking details
  - POST /compliance/submit/{booking_id} — manual submission trigger (operator override)
  - POST /compliance/confirm/{booking_id} — idempotent n8n webhook for Campspot confirmation emails
  - POST /compliance/approve/{submission_id} — approve preview-mode pending submissions
  - POST /compliance/process-pending — batch process all eligible pending submissions
  - compliance_router registered in main.py — all /compliance/* routes accessible via FastAPI
affects: [06-dashboard, 07-frontend, phase 7]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fixed-path routes before path-param routes: /process-pending registered before /submit/{id}, /confirm/{id}, /approve/{id}"
    - "Sync endpoints for DB-only work (list, confirm); async endpoints for pipeline work (submit, approve, process-pending)"
    - "Idempotent webhook: confirm endpoint returns already_confirmed for repeated calls without error"

key-files:
  created:
    - app/api/compliance.py
  modified:
    - app/main.py

key-decisions:
  - "process-pending registered before /{param} routes — prevents FastAPI route conflict where 'process-pending' would be parsed as a booking_id integer"
  - "confirm endpoint queries by booking_id (not submission_id) — n8n knows booking context, not internal submission IDs"
  - "submit and approve are async def — they call async process_booking_submission(); confirm and list are sync (no async work)"
  - "process-pending respects preview mode: returns preview_mode_active if threshold not yet reached"
  - "approve endpoint checks status == 'pending' before triggering send — returns HTTP 409 for already-submitted/confirmed"

patterns-established:
  - "Compliance router pattern: prefix=/compliance, tags=['compliance'], follows ingestion.py structure"
  - "API commit responsibility: compliance endpoints rely on process_booking_submission() to call db.commit(); list/confirm endpoints commit directly"

# Metrics
duration: 4min
completed: 2026-02-28
---

# Phase 5 Plan 06: Compliance API Router Summary

**FastAPI compliance router with 5 endpoints exposing submission management, n8n webhook confirmation, preview approval, and batch processing — completing the Phase 5 resort PDF compliance feature set**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-28T04:26:20Z
- **Completed:** 2026-02-28T04:29:59Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `app/api/compliance.py` with all 5 compliance endpoints following existing router patterns
- Registered `compliance_router` in `app/main.py` — all `/compliance/*` routes now accessible
- Route ordering enforced: `/process-pending` before path-param routes to prevent FastAPI route conflicts
- `confirm` endpoint is fully idempotent — n8n can call repeatedly without side effects
- `process-pending` respects preview mode threshold via `should_auto_submit()`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create compliance API router with all endpoints** - `f27af98` (feat)
2. **Task 2: Register compliance router in main.py** - `7280663` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `app/api/compliance.py` — Full compliance router: submissions list, submit, confirm, approve, process-pending
- `app/main.py` — Added `compliance_router` import and `app.include_router(compliance_router)`

## Decisions Made

- `process-pending` registered before `/{param}` routes: FastAPI route matching is order-sensitive; a fixed path `/process-pending` must be declared before `/{booking_id}` or `/{submission_id}` patterns or the literal string would be treated as a parameter value. Same pattern as 04-04 bank transaction routes.
- `confirm` endpoint queries by `booking_id` (not `submission_id`): n8n's automation sees the booking confirmation email containing booking identifiers, not internal submission IDs.
- `submit` and `approve` are `async def`: they call `await process_booking_submission()` which is async. `confirm` and `list` are sync — pure DB operations.
- `process-pending` returns `preview_mode_active` (not error) when below threshold: the operator may legitimately call this endpoint before preview period ends; it should explain why nothing was processed.
- `approve` returns HTTP 409 for non-pending submissions: prevents accidental double-sends on already-submitted or confirmed submissions.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Full Phase 5 resort PDF compliance feature set is now complete and accessible via HTTP API
- Phase 7 dashboard can use `GET /compliance/submissions` for submission status display (includes `is_urgent`, `confirmation_attached`, `status`, booking details)
- n8n automation can call `POST /compliance/confirm/{booking_id}` to mark submissions confirmed
- Operator has full manual control: trigger individual submissions, approve preview-mode submissions, batch-process pending queue
- 05-02 checkpoint still pending (PDF form type verification — AcroForm vs XFA) but does not block dashboard work in Phase 7

---
*Phase: 05-resort-pdf-compliance*
*Completed: 2026-02-28*
