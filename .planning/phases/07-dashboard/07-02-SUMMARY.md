---
phase: 07-dashboard
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, dashboard, occupancy, financial-metrics, actions]

# Dependency graph
requires:
  - phase: 03-accounting-engine
    provides: JournalLine/JournalEntry/Account models with signed amount convention
  - phase: 05-resort-pdf-compliance
    provides: ResortSubmission model with status/is_urgent fields
  - phase: 06-guest-communication
    provides: CommunicationLog model with status/message_type/scheduled_for fields
  - phase: 02-data-ingestion
    provides: Booking model with reconciliation_status and net_amount
provides:
  - Dashboard API router with 5 purpose-built GET endpoints
  - GET /api/dashboard/properties — property list for UI selectors
  - GET /api/dashboard/metrics — YTD financials with YoY comparison and actions badge count
  - GET /api/dashboard/bookings — bookings with property info for calendar view (overlap filter, limit 500)
  - GET /api/dashboard/occupancy — per-property 12-month occupancy rates (Python-computed)
  - GET /api/dashboard/actions — sorted pending actions from 3 sources with total count
affects:
  - 07-dashboard/07-03 and beyond (frontend consumes these endpoints)
  - Phase 08 (LLM query interface may reference these aggregations)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Dashboard endpoints aggregate multiple models in a single query response
    - Occupancy computed in Python (not SQL) for clarity with partial-month overlap logic
    - Actions sorted by urgency using internal _group/_sort_key fields stripped before return
    - Monetary amounts formatted as strings with 2 decimal places (f"{amount:.2f}")
    - YoY percentage: null if no prior-year data (avoids division by zero)

key-files:
  created:
    - app/api/dashboard.py
  modified:
    - app/main.py

key-decisions:
  - "Occupancy computed in Python over 12-month booking window rather than in SQL — partial-month overlap logic is cleaner in Python; avoids complex SQL date arithmetic"
  - "Actions endpoint uses internal _group/_sort_key fields stripped at return boundary — preserves sort semantics across heterogeneous action types without API leakage"
  - "Metrics endpoint computes actions_count inline via _count_pending_actions helper — avoids a second HTTP round-trip from dashboard frontend for badge display"
  - "Bookings endpoint uses overlap semantics (check_in <= range_end AND check_out >= range_start) — standard interval overlap condition for calendar views"
  - "YoY change returns null (not '0%' or 'N/A') when prior year data is zero — null signals missing data cleanly to frontend; allows conditional rendering"

patterns-established:
  - "Dashboard endpoints: join Property inline rather than lazy-load — all responses return property_slug/display_name without N+1 queries"
  - "_sum_journal_lines helper: reusable signed-amount aggregation function extracted for use across YTD/prior-year/monthly metric computations"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 07 Plan 02: Dashboard Backend API Summary

**Five FastAPI dashboard endpoints aggregating bookings, journal lines, occupancy, and pending actions from multiple Phase 3-6 models into purpose-built JSON responses for the frontend.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T22:09:29Z
- **Completed:** 2026-02-28T22:11:24Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `app/api/dashboard.py` with 5 GET endpoints prefixed at `/api/dashboard` (566 lines)
- Registered `dashboard_router` in `app/main.py` with proper placement (after all other routers, before any future SPA mount)
- Implemented occupancy calculation with correct partial-month overlap logic in Python for the last 12 calendar months
- Built actions endpoint pulling from 3 heterogeneous sources (resort forms, communication logs, unreconciled bookings) with urgency-based sort ordering

## Task Commits

Each task was committed atomically:

1. **Task 1: Create dashboard API router with properties and metrics endpoints** - `8034eba` (feat)
2. **Task 2: Register dashboard router in FastAPI app** - `f6aa289` (feat)

**Plan metadata:** (included in final docs commit)

## Files Created/Modified
- `app/api/dashboard.py` — New dashboard API router with 5 endpoints (properties, metrics, bookings, occupancy, actions)
- `app/main.py` — Added `dashboard_router` import and `app.include_router(dashboard_router)` registration

## Decisions Made
- **Occupancy in Python, not SQL:** Partial-month overlap (e.g. booking spanning Feb/Mar contributes to both months) is significantly cleaner to compute in Python with `max(check_in, month_start)` / `min(check_out, month_end)` than in SQL date arithmetic
- **Actions `_group`/`_sort_key` fields:** Heterogeneous action types (resort forms sort by days-to-checkin ASC, messages by scheduled_for ASC, unreconciled by check_in DESC) require different sort semantics per type; internal fields carry sort state and are stripped before return
- **`_count_pending_actions` helper:** Metrics endpoint needs actions count for badge display; extracted as shared helper to avoid duplicating query logic between `/metrics` and `/actions`
- **YoY returns `null` not `"0%"`:** `null` cleanly signals "no prior-year data" to the frontend; `"0%"` would falsely imply zero change rather than missing baseline
- **Bookings overlap filter:** Standard calendar interval overlap — `check_in <= range_end AND check_out >= range_start` — handles bookings that span the query boundary in either direction

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The Task 2 commit picked up frontend files created in parallel by Plan 07-01. This is expected given the parallel execution mode and does not affect correctness — all dashboard routes were verified before commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 5 `/api/dashboard/*` endpoints are registered and importable
- Frontend (Plan 07-03+) can immediately consume these endpoints
- Endpoints support optional `property_id` filter parameter throughout
- No migrations required — reads from existing tables only

---
*Phase: 07-dashboard*
*Completed: 2026-02-28*
