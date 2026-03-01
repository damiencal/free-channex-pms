---
phase: 09-integration-wiring-fixes
plan: 02
subsystem: api
tags: [fastapi, background-tasks, revenue-recognition, accounting, ingestion]

# Dependency graph
requires:
  - phase: 03-accounting-engine
    provides: recognize_booking_revenue() and create_journal_entry() with idempotent source_id
  - phase: 05-resort-pdf-compliance
    provides: BackgroundTask pattern (_fire_background_submissions) that this mirrors

provides:
  - Automatic revenue recognition on every Airbnb, VRBO, and RVshare booking import
  - _fire_background_revenue_recognition() helper in app/api/ingestion.py

affects:
  - 09-03 (calendar integration)
  - dashboard phase (revenue metrics now auto-populated after import)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "BackgroundTask revenue recognition wired after each CSV upload response"
    - "Lazy import inside background helper to avoid circular imports"

key-files:
  created: []
  modified:
    - app/api/ingestion.py

key-decisions:
  - "Lazy import of recognize_booking_revenue() inside function body avoids circular import (revenue.py imports from models, which ingestion.py also imports)"
  - "Revenue recognition is NOT gated by should_auto_submit — runs unconditionally for all inserted bookings with no preview threshold"
  - "Separate if inserted_db_ids: block for revenue recognition — does not nest inside should_auto_submit check"
  - "Mercury upload endpoint excluded — bank transactions, not bookings; no revenue to recognize"
  - "Per-booking db.commit() and db.rollback() on exception — mirrors _fire_background_welcome_messages pattern"

patterns-established:
  - "Background revenue recognition: unconditional, per-booking, isolated commit/rollback"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 09 Plan 02: Revenue Recognition Auto-Wiring Summary

**BackgroundTask revenue recognition wired into all three booking upload endpoints (Airbnb, VRBO, RVshare) eliminating the manual POST /api/accounting/revenue/recognize-all step after CSV imports**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-01T02:20:16Z
- **Completed:** 2026-03-01T02:22:01Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `_fire_background_revenue_recognition()` async helper following the established `_fire_background_submissions` / `_fire_background_welcome_messages` BackgroundTask pattern
- Wired revenue recognition unconditionally into `upload_airbnb_csv`, `upload_vrbo_csv`, and `create_rvshare_booking` — all three booking upload endpoints
- Excluded `upload_mercury_csv` (bank transaction import, not booking import)
- Revenue recognition is idempotent via `create_journal_entry()` source_id uniqueness — manual recognize-all calls remain safe after auto-recognition

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _fire_background_revenue_recognition helper** - `a76a3d6` (feat)
2. **Task 2: Wire revenue recognition into all three upload endpoints** - `4fefb42` (feat)

## Files Created/Modified

- `app/api/ingestion.py` - Added `_fire_background_revenue_recognition()` helper and wired it into 3 upload endpoints

## Decisions Made

- **Lazy import:** `from app.accounting.revenue import recognize_booking_revenue` placed inside function body to avoid circular import (revenue.py imports from models, ingestion.py imports same models)
- **No gate:** Revenue recognition is unconditional — no `should_auto_submit` threshold. The operator sees financial metrics immediately after import without configuring a threshold
- **Separate block:** Each endpoint has its own `if inserted_db_ids:` block for revenue recognition, independent of the auto-submit check's gating logic
- **Mercury excluded:** Bank transaction imports have no bookings; wiring revenue recognition there would be a logic error

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Revenue recognition now fires automatically after every booking import
- Dashboard financial metrics (revenue, platform breakdown, income statement) will reflect new bookings immediately without operator intervention
- Ready for plan 09-03

---
*Phase: 09-integration-wiring-fixes*
*Completed: 2026-02-28*
