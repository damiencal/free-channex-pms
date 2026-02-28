---
phase: 05-resort-pdf-compliance
plan: 04
subsystem: api
tags: [fastapi, sqlalchemy, backgroundtasks, pdf, smtp, asyncio]

# Dependency graph
requires:
  - phase: 05-02
    provides: fill_resort_form() PDF filler using PyMuPDF field.update() + bake()
  - phase: 05-03
    provides: send_with_retry() async SMTP emailer, find_confirmation_file(), format_email_subject/body()
  - phase: 05-01
    provides: ResortSubmission ORM model, AppConfig compliance fields (smtp, pdf paths, auto_submit_threshold)
  - phase: 02-02
    provides: ingest_csv() / create_manual_booking() normalizer pipeline, Booking model
provides:
  - "submission.py: process_booking_submission() orchestrates full PDF fill + email send + DB status pipeline"
  - "submission.py: should_auto_submit() checks count of submitted_automatically=True records vs threshold"
  - "normalizer.py: _create_resort_submissions() creates pending ResortSubmission records for new inserts"
  - "normalizer.py: ingest_csv() and create_manual_booking() now return inserted_db_ids in result dict"
  - "ingestion.py: airbnb/vrbo/rvshare upload endpoints fire BackgroundTasks for auto-submit-eligible bookings"
affects: [05-05, 05-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "BackgroundTasks for sync-to-async handoff: normalizer stays sync, async email fires from async endpoint"
    - "Idempotent submission: skips submitted/confirmed bookings, re-processes pending"
    - "Preview mode: count-based threshold gates auto-sending before operator-verified first N submissions"
    - "Guest name splitting: booking.guest_name.split(' ', 1) -> guest_first_name / guest_last_name for PDF fields"
    - "Error isolation in background tasks: per-booking try/except, one failure never blocks others"

key-files:
  created:
    - app/compliance/submission.py
  modified:
    - app/ingestion/normalizer.py
    - app/api/ingestion.py

key-decisions:
  - "guest_name split on first space only (maxsplit=1): 'John Smith' -> ['John', 'Smith']; single-word names get empty last_name"
  - "send_with_retry() called with form_bytes/confirmation_bytes (emailer's actual param names, not plan template names)"
  - "BackgroundTasks.add_task() fires after should_auto_submit() check in API layer -- below threshold = no background tasks"
  - "Normalizer stays sync: only creates DB records; email sending is async in API BackgroundTasks"
  - "db.flush() on new ResortSubmission insert (not commit) -- stays in same transaction until success or failure"
  - "rvshare endpoint changed from def to async def to support BackgroundTasks with async process_booking_submission()"

patterns-established:
  - "Submission orchestrator is the business transaction boundary: it calls db.commit(), not callers"
  - "Three call sites for _create_resort_submissions: ingest_csv (airbnb/vrbo), create_manual_booking (rvshare)"
  - "Mercury bank CSV upload deliberately excluded from submission logic (not a booking)"

# Metrics
duration: ~15min
completed: 2026-02-28
---

# Phase 5 Plan 04: Submission Orchestrator Summary

**Submission pipeline orchestrator tying PDF fill, retry email, and DB status into one flow wired into booking import via FastAPI BackgroundTasks**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-28T02:28:31Z
- **Completed:** 2026-02-28T04:23:28Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created `process_booking_submission()` — the central coordination point that fills the PDF, finds the confirmation, formats and sends the email, and updates the DB record in one idempotent transaction
- Created `should_auto_submit()` — counts `submitted_automatically=True` records; returns True once count reaches threshold
- Preview mode implemented: below threshold, submissions created as pending without sending; above threshold, PDF filled and emailed immediately
- Wired into booking import: normalizer creates pending ResortSubmission records for new inserts; upload API endpoints fire BackgroundTasks to complete async email sending when past threshold

## Task Commits

Each task was committed atomically:

1. **Task 1: Create submission orchestrator with preview mode** - `7bf00ce` (feat)
2. **Task 2: Wire auto-submission into booking import flow** - `4caa672` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `app/compliance/submission.py` - Created — submission orchestrator with process_booking_submission() and should_auto_submit()
- `app/ingestion/normalizer.py` - Modified — added _create_resort_submissions() helper, both ingest_csv() and create_manual_booking() now create pending submission records and return inserted_db_ids
- `app/api/ingestion.py` - Modified — added BackgroundTasks to airbnb/vrbo/rvshare endpoints; added _fire_background_submissions() async helper; rvshare endpoint changed to async def

## Decisions Made

- **Guest name splitting:** `booking.guest_name.split(" ", 1)` splits on first space only. Mapping JSON requires `guest_first_name` (Text_2) and `guest_last_name` (Text_3) separately — the plan template only passed `guest_name`, but the actual mapping JSON from Plan 02 checkpoint resolution specifies the split fields.
- **Emailer parameter names:** Plan template used `from_addr`/`to_addr` and `filled_form_bytes`, but actual `send_with_retry()` signature uses `from_email`/`to_email` and `form_bytes`. Submission.py uses the correct parameter names from the actual emailer implementation.
- **BackgroundTasks vs asyncio.create_task:** Used FastAPI `BackgroundTasks` (runs after response is sent, within same request lifecycle) not raw `asyncio.create_task()`. DB session from `Depends(get_db)` remains valid during BackgroundTasks execution.
- **should_auto_submit check in API layer:** The API checks threshold once before firing background tasks. Below threshold = no background tasks fire; normalizer already created the pending records. Avoids unnecessary async work for preview-mode submissions.
- **Normalizer stays sync:** Only creates DB records. Async email sending happens in API BackgroundTasks. Clean sync/async separation maintained.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected booking_data dict to use guest_first_name/guest_last_name**
- **Found during:** Task 1 (submission orchestrator creation)
- **Issue:** Plan template built `booking_data` with `guest_name` as a whole field, but the mapping JSON (confirmed in checkpoint resolution) maps Text_2 to `guest_first_name` and Text_3 to `guest_last_name`. Passing `guest_name` would result in empty PDF fields for first/last name.
- **Fix:** Split `booking.guest_name` using `split(" ", 1)` to produce `guest_first_name` and `guest_last_name` before building `booking_data`
- **Files modified:** app/compliance/submission.py
- **Verification:** Import succeeds; booking_data dict contains guest_first_name and guest_last_name keys matching mapping JSON field names
- **Committed in:** 7bf00ce (Task 1 commit)

**2. [Rule 1 - Bug] Corrected send_with_retry() parameter names**
- **Found during:** Task 1 (submission orchestrator creation)
- **Issue:** Plan template called `send_with_retry()` with `from_addr`, `to_addr`, `filled_form_bytes`, and `filled_form_filename` — but the actual emailer.py (created in Plan 03) uses `from_email`, `to_email`, and `form_bytes`. Would have caused TypeError at runtime.
- **Fix:** Used actual parameter names from emailer.py: `from_email`, `to_email`, `form_bytes`, `confirmation_bytes`
- **Files modified:** app/compliance/submission.py
- **Verification:** Import succeeds; parameter names match send_with_retry() signature
- **Committed in:** 7bf00ce (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug — plan template had parameter/key mismatches with actual implementations from prior plans)
**Impact on plan:** Both fixes essential for correctness. No scope creep. The mapping JSON and emailer.py were the source of truth; plan template was aspirational.

## Issues Encountered
None — execution was straightforward once the guest name splitting and emailer parameter name discrepancies were identified and fixed.

## User Setup Required
None - no external service configuration required for this plan.

## Next Phase Readiness
- Full submission pipeline complete: booking import -> PDF fill -> email send -> DB status tracking
- Preview mode safety net in place for first 3 submissions
- Plan 05 (urgency checker) and Plan 06 (submission approval API) can build on this foundation
- The `should_auto_submit()` function is available for Plan 06's manual approval flow

---
*Phase: 05-resort-pdf-compliance*
*Completed: 2026-02-28*
