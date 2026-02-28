---
phase: 06-guest-communication
plan: 03
subsystem: scheduling
tags: [apscheduler, datetrigger, sqlalchemy, asyncio, communication, scheduler]

# Dependency graph
requires:
  - phase: 06-01
    provides: CommunicationLog ORM model with scheduled_for field and pending status
  - phase: 05-resort-pdf-compliance
    provides: APScheduler AsyncIOScheduler in main.py (scheduler module-level variable)
affects:
  - 06-02 (messenger.py exports send_pre_arrival_message called by scheduler jobs)
  - 06-04 (ingestion hook calls schedule_pre_arrival_job after creating CommunicationLog)
  - 06-05 (lifespan calls rebuild_pre_arrival_jobs after scheduler.start())
provides:
  - schedule_pre_arrival_job() — registers one-time DateTrigger job at check_in - 2 days, 14:00 UTC
  - rebuild_pre_arrival_jobs() — re-registers all pending pre-arrival jobs from DB on startup
  - compute_pre_arrival_send_time() — public helper computing UTC send datetime from check-in date
  - PRE_ARRIVAL_DAYS_BEFORE=2 and PRE_ARRIVAL_SEND_HOUR_UTC=14 constants

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy imports inside function bodies to avoid circular dependency chain (scheduler.py -> main.py -> scheduler.py)"
    - "Past send time detection before add_job() prevents APScheduler silent no-op (DateTrigger with past run_date never fires)"
    - "rebuild_pre_arrival_jobs() creates SessionLocal() directly — same pattern as run_urgency_check() for non-request contexts"
    - "replace_existing=True on all add_job() calls — idempotent for re-import and multi-restart scenarios"

key-files:
  created:
    - app/communication/scheduler.py
  modified: []

key-decisions:
  - "14:00 UTC hardcoded as PRE_ARRIVAL_SEND_HOUR_UTC — maps to 9am EST / 10am EDT, always within 9-10am window; can be made configurable if properties span timezones"
  - "schedule_pre_arrival_job() explicitly checks run_at <= datetime.now(timezone.utc) before add_job() — APScheduler DateTrigger silently no-ops when run_date is in the past"
  - "compute_pre_arrival_send_time() extracted as public function — reused by Plan 04 ingestion hook when setting CommunicationLog.scheduled_for"
  - "Circular imports avoided via lazy function-body imports — all three cross-module imports (scheduler, messenger) deferred until call time"

patterns-established:
  - "APScheduler job rebuild pattern: query DB for pending entries with future scheduled_for, re-register each with replace_existing=True"
  - "Job ID convention: pre_arrival_{booking_id} — unique, deterministic, enables replace_existing to deduplicate"

# Metrics
duration: 1min
completed: 2026-02-28
---

# Phase 6 Plan 03: Pre-Arrival Scheduler Summary

**APScheduler DateTrigger pre-arrival scheduling with past-time detection, startup rebuild from CommunicationLog, and circular-import-safe lazy imports — fires 2 days before check-in at 14:00 UTC (9am EST / 10am EDT)**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-28T19:44:53Z
- **Completed:** 2026-02-28T19:45:49Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- `app/communication/scheduler.py` created with `schedule_pre_arrival_job()`, `rebuild_pre_arrival_jobs()`, and `compute_pre_arrival_send_time()` — full pre-arrival scheduling and startup recovery
- Past send time detection implemented before `scheduler.add_job()` — prevents APScheduler silent no-op where DateTrigger with past `run_date` is registered but never fires
- Startup rebuild queries `CommunicationLog` for `status='pending'`, `message_type='pre_arrival'`, `scheduled_for > now` and re-registers all with `replace_existing=True` — Docker restart safety
- All circular imports (main.py scheduler, messenger.py `send_pre_arrival_message`) deferred to function body lazy imports — module loads cleanly without circular dependency errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pre-arrival scheduler module** - `441b93b` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `app/communication/scheduler.py` - Pre-arrival scheduling module: `schedule_pre_arrival_job()`, `rebuild_pre_arrival_jobs()`, `compute_pre_arrival_send_time()`, and send-time constants

## Decisions Made

- `14:00 UTC` hardcoded as `PRE_ARRIVAL_SEND_HOUR_UTC` constant — this maps to 9:00 AM EST or 10:00 AM EDT, always within the 9-10am morning window for Eastern US properties. Documented in module docstring and constants. Can be made configurable in a future phase if properties span timezones.
- `schedule_pre_arrival_job()` explicitly checks `run_at <= datetime.now(timezone.utc)` BEFORE calling `add_job()` — APScheduler's `DateTrigger` silently produces a job that never fires when `run_date` is in the past (it returns `None` from `get_next_fire_time`). The guard prevents this and emits a warning log.
- `compute_pre_arrival_send_time()` extracted as a standalone public function — Plan 04 (booking ingestion hook) needs to compute the same datetime when creating `CommunicationLog` entries with `scheduled_for` set.
- All three cross-module imports kept inside function bodies to avoid circular import chain: `scheduler.py` imports from `main.py` (for the scheduler instance) and `messenger.py` (for the job function), while `main.py` will eventually import from `scheduler.py` — deferring to call time avoids the cycle.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. `rebuild_pre_arrival_jobs()` and `schedule_pre_arrival_job()` are called by Plan 04 (ingestion) and Plan 05 (lifespan). No operator action needed for this module.

## Next Phase Readiness

- `schedule_pre_arrival_job(booking_id, check_in_date)` is ready for Plan 04 (ingestion hook) to call after creating a `CommunicationLog` entry
- `rebuild_pre_arrival_jobs()` is ready for Plan 05 (lifespan update) to call after `scheduler.start()`
- `compute_pre_arrival_send_time()` is ready for Plan 04 to use when setting `CommunicationLog.scheduled_for`
- Plan 02 (messenger.py) must exist before `send_pre_arrival_message` can be resolved at runtime — lazy imports defer this resolution safely

---
*Phase: 06-guest-communication*
*Completed: 2026-02-28*
