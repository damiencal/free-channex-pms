---
phase: 05-resort-pdf-compliance
plan: "05"
subsystem: infra
tags: [apscheduler, smtp, aiosmtplib, scheduling, compliance, urgency]

# Dependency graph
requires:
  - phase: 05-01
    provides: ResortSubmission model with is_urgent field; AppConfig with SMTP settings
  - phase: 05-03
    provides: emailer.py SMTP/aiosmtplib patterns (aiosmtplib.send, use_tls/start_tls logic)
provides:
  - app/compliance/urgency.py: run_urgency_check() function that flags pending submissions and sends daily digest
  - app/main.py: APScheduler AsyncIOScheduler integrated into FastAPI lifespan (startup/shutdown)
affects:
  - 05-06: compliance API router can expose is_urgent flag in submission listings
  - 05-04: orchestrator triggers same urgency check logic (shared models/session pattern)

# Tech tracking
tech-stack:
  added: [apscheduler>=3.11.2 (already in pyproject.toml), AsyncIOScheduler, CronTrigger]
  patterns:
    - APScheduler module-level scheduler instance (not per-request, not per-lifespan)
    - CronTrigger with replace_existing=True for idempotent restart behavior
    - APScheduler jobs create their own SessionLocal() (outside FastAPI request context)
    - DB commit before email send (email failure must not prevent DB flagging)

key-files:
  created:
    - app/compliance/urgency.py
  modified:
    - app/main.py

key-decisions:
  - "APScheduler AsyncIOScheduler (not BackgroundScheduler) because FastAPI is fully async"
  - "scheduler is module-level variable (not inside lifespan) so it persists for app lifetime"
  - "run_urgency_check() creates SessionLocal() directly -- APScheduler runs outside request context, Depends() not available"
  - "db.commit() for urgency flagging committed BEFORE email send -- email failure is non-fatal"
  - "Digest email sent to smtp_from_email (operator), not resort contact -- this is an operator alert"
  - "is_urgent==False filter prevents duplicate alerts for already-flagged bookings"
  - "replace_existing=True on add_job -- prevents duplicate jobs on Docker restart"

patterns-established:
  - "APScheduler job pattern: create own DB session, commit before side effects, handle exceptions without raising"
  - "Lifespan startup order: FAIL-FAST checks (config, templates, DB) first, then NON-FATAL (Ollama), then scheduler"
  - "Email guard pattern: check smtp_user and smtp_from_email before sending; log warning and return on missing config"

# Metrics
duration: 102min
completed: 2026-02-28
---

# Phase 5 Plan 05: Daily Urgency Checker + APScheduler Summary

**APScheduler AsyncIOScheduler wired into FastAPI lifespan, running daily urgency check that flags pending submissions within 3 days of check-in and sends a single operator digest email**

## Performance

- **Duration:** 102 min
- **Started:** 2026-02-28T02:35:56Z
- **Completed:** 2026-02-28T04:18:45Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `app/compliance/urgency.py` with `run_urgency_check()` that queries pending non-urgent submissions with check-in within 3 days, flags them `is_urgent=True`, and sends a single digest email to the operator
- Integrated `AsyncIOScheduler` with daily `CronTrigger(hour=8, minute=0)` into the FastAPI lifespan -- starts after all FAIL-FAST checks, shuts down cleanly in teardown
- Duplicate-alert prevention via `is_urgent == False` filter -- only newly-urgent bookings are reported each day
- SMTP misconfiguration handled gracefully -- logs warning and skips email without crashing the urgency check

## Task Commits

Each task was committed atomically:

1. **Task 1: Create urgency checker with daily digest alert** - `38dfcc4` (feat)
2. **Task 2: Integrate APScheduler into FastAPI lifespan** - `57e9f60` (feat)

**Plan metadata:** `[pending docs commit]` (docs: complete plan)

## Files Created/Modified
- `app/compliance/urgency.py` - Daily urgency check: queries pending submissions within 3-day window, flags is_urgent, sends operator digest
- `app/main.py` - Added AsyncIOScheduler (module-level), CronTrigger job at 08:00, scheduler.start() in startup, scheduler.shutdown() in teardown

## Decisions Made
- Used `AsyncIOScheduler` (not `BackgroundScheduler`) -- FastAPI is fully async; AsyncIOScheduler runs on the existing event loop without spawning threads
- Module-level `scheduler = AsyncIOScheduler()` -- persists for entire app lifetime; lifespan just calls start/shutdown
- `replace_existing=True` on `add_job` -- prevents duplicate job registration if the container restarts without full process exit
- `db.commit()` for urgency flagging happens **before** `await _send_urgency_digest()` -- if email fails, DB state is already correct; retry email next day is acceptable; failing to flag is not
- Digest goes to `smtp_from_email` (operator) -- not the resort contact; this is an internal operational alert
- `SessionLocal()` created directly in `run_urgency_check()` -- APScheduler callbacks execute outside FastAPI request context where `Depends(get_db)` would not work

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. APScheduler runs in-process; SMTP settings already configured in Phase 5-01.

## Next Phase Readiness
- `run_urgency_check` is exported and ready; APScheduler fires it daily at 08:00 automatically
- `is_urgent` flag is now actively maintained on `ResortSubmission` rows -- Plan 06 (compliance API) can expose this field in listing endpoints
- Scheduler is cleanly lifecycle-managed via lifespan -- no thread/task leaks on Docker restart

---
*Phase: 05-resort-pdf-compliance*
*Completed: 2026-02-28*
