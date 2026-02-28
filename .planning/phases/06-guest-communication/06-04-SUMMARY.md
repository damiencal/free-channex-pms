---
phase: 06-guest-communication
plan: "04"
subsystem: api
tags: [fastapi, sqlalchemy, apscheduler, communication, background-tasks, ingestion]

requires:
  - phase: 06-01
    provides: CommunicationLog model, message template rendering
  - phase: 06-02
    provides: prepare_welcome_message(), send_pre_arrival_message()
  - phase: 06-03
    provides: schedule_pre_arrival_job(), compute_pre_arrival_send_time()
  - phase: 02-ingestion
    provides: normalizer ingest_csv(), create_manual_booking() pipeline

provides:
  - _create_communication_logs() hook wired into normalizer pipeline
  - Automatic CommunicationLog creation on every new booking import
  - APScheduler pre-arrival job registration on booking import
  - BackgroundTasks welcome email dispatch for VRBO/RVshare in upload API
  - welcome_async_ids in normalizer return dict for API layer coordination

affects: [06-05, communication-api-plan]

tech-stack:
  added: []
  patterns:
    - "Communication log creation in normalizer pipeline (same session as booking upsert)"
    - "welcome_async_ids return value pattern: normalizer signals API layer which bookings need async email"
    - "VRBO/RVshare welcome deferred to prepare_welcome_message() to keep create + notify atomic"

key-files:
  created: []
  modified:
    - app/ingestion/normalizer.py
    - app/api/ingestion.py

key-decisions:
  - "_create_communication_logs() does NOT pre-create VRBO/RVshare welcome logs — deferred to prepare_welcome_message() so create+notify remain atomic and idempotency check in prepare_welcome_message() does not block the email"
  - "welcome_needs_async returns DB IDs (not platform booking IDs) — API layer needs DB IDs to call prepare_welcome_message(booking_id)"
  - "Idempotency check uses count of ALL CommunicationLog rows for booking_id — if any exist, skip entirely; prevents partial re-import duplication"
  - "schedule_pre_arrival_job() called for all platforms from normalizer — sync-safe APScheduler 3.x add_job() is thread-safe"

patterns-established:
  - "Normalizer signals async work needed via result dict keys (welcome_async_ids, inserted_db_ids) — API layer decides whether/how to fire BackgroundTasks"
  - "BackgroundTask helpers per concern: _fire_background_submissions for compliance, _fire_background_welcome_messages for communication"

duration: 2min
completed: 2026-02-28
---

# Phase 06 Plan 04: Ingestion Pipeline Communication Wiring Summary

**Communication pipeline integrated into booking ingestion: every new booking auto-creates CommunicationLog entries, registers APScheduler pre-arrival jobs, and fires VRBO/RVshare welcome operator emails via BackgroundTasks**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T19:49:07Z
- **Completed:** 2026-02-28T19:51:11Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `_create_communication_logs()` to normalizer — creates `native_configured` welcome for Airbnb and `pending` pre-arrival for all platforms, registers APScheduler jobs, returns VRBO/RVshare booking IDs for async email processing
- Wired `_create_communication_logs()` into both `ingest_csv()` and `create_manual_booking()`, adding `welcome_async_ids` to both return dicts
- Added `_fire_background_welcome_messages()` to ingestion API and wired it into VRBO and RVshare upload endpoints; Airbnb and Mercury endpoints correctly unaffected

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _create_communication_logs() to normalizer and wire into ingestion** - `d096830` (feat)
2. **Task 2: Wire background welcome tasks into upload API endpoints** - `a959acc` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `app/ingestion/normalizer.py` - Added `_create_communication_logs()` private helper; wired into `ingest_csv()` and `create_manual_booking()`; imports `CommunicationLog`, `compute_pre_arrival_send_time`, `schedule_pre_arrival_job`
- `app/api/ingestion.py` - Added `prepare_welcome_message` import, `_fire_background_welcome_messages()` helper, welcome BackgroundTasks in VRBO upload and RVshare entry endpoints

## Decisions Made

**VRBO/RVshare welcome log deferred to prepare_welcome_message():**
`_create_communication_logs()` does NOT pre-create the welcome CommunicationLog for VRBO/RVshare. If it did, `prepare_welcome_message()` would hit its idempotency check (`existing is not None → return`) and skip the operator notification email entirely. By deferring to `prepare_welcome_message()`, the log creation and email dispatch remain atomic, and the idempotency guard works correctly on genuine re-imports.

**welcome_needs_async returns DB IDs:**
The normalizer returns DB booking IDs (not platform booking IDs) for VRBO/RVshare welcome processing. `prepare_welcome_message(booking_id, platform, db)` takes the DB ID. Returning DB IDs avoids a second lookup in the API layer.

**Idempotency: count-based check on booking_id:**
`_create_communication_logs()` skips a booking entirely if ANY `CommunicationLog` rows exist for it (`count > 0`). This matches the intent: if prior import created logs, re-import should not create partial duplicates. The unique constraint on `(booking_id, message_type)` provides DB-level enforcement as a backstop.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected VRBO/RVshare welcome log creation to avoid blocking operator email**

- **Found during:** Task 1 (designing _create_communication_logs())
- **Issue:** The plan spec said to create welcome logs for all platforms in `_create_communication_logs()`, including VRBO/RVshare with `status='pending'`. However, `prepare_welcome_message()` has an idempotency check (`existing is not None → return`) that would bail out before sending the operator email if the log already exists. The result: welcome email never sent for VRBO/RVshare.
- **Fix:** `_create_communication_logs()` creates welcome logs for Airbnb only (`native_configured`). For VRBO/RVshare, it skips welcome log creation and adds the booking ID to `welcome_needs_async`. `prepare_welcome_message()` creates the log AND sends the email in one atomic operation.
- **Files modified:** app/ingestion/normalizer.py
- **Verification:** Import chain verified OK; `prepare_welcome_message()` idempotency guard now correctly blocks only genuine re-runs, not first-time processing
- **Committed in:** d096830 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — logic bug in plan spec)
**Impact on plan:** Fix is essential for correctness — without it, VRBO/RVshare operators would never receive welcome message notifications. No scope creep.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full communication pipeline wired: bookings imported → logs created → pre-arrival jobs scheduled → VRBO/RVshare welcome emails dispatched
- Plan 05 (communication API) can now expose endpoints for operators to confirm VRBO/RVshare message sends, query communication log status, and trigger manual pre-arrival sends
- No blockers

---
*Phase: 06-guest-communication*
*Completed: 2026-02-28*
