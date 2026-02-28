---
phase: 04-financial-reports
plan: 02
subsystem: api
tags: [sqlalchemy, fastapi, pnl, reporting, journal-lines, revenue, expenses, decimal]

# Dependency graph
requires:
  - phase: 04-01
    provides: resolve_period() helper, reports.py skeleton with category constants
  - phase: 03-01
    provides: JournalLine/JournalEntry/Account models, signed amount convention (positive=debit, negative=credit), property_id nullable on JournalEntry
  - phase: 03-02
    provides: booking_payout journal entries with source_id format booking_payout:{platform}:{booking_id}
  - phase: 03-03
    provides: expense journal entries grouped by account name (category)

provides:
  - generate_pl() function in app/accounting/reports.py — queries journal_lines for P&L data, supports combined and per-property breakdown
  - GET /api/reports/pl endpoint in app/api/reports.py — accepts all 6 period params plus breakdown param
  - Reports router registered in app/main.py alongside accounting and ingestion routers

affects:
  - 04-03 (balance sheet — can follow same pattern: reports.py function + api/reports.py endpoint)
  - 04-04 (bank transaction categorization — reports router already exists)
  - Any future reporting endpoints (GET /api/reports/*)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "P&L revenue query: join JournalLine->JournalEntry->Account, filter account_type==revenue + source_type==booking_payout, group by property_id/source_id/year/month"
    - "Platform extraction from source_id: source_id.split(':')[1] yields airbnb/vrbo/rvshare"
    - "Revenue sign flip: credits are negative in journal_lines; negate with -(row.amount) for positive display"
    - "Shared expense allocation: expense_data keyed by property_id; None key = shared; allocated = amount / property_count"
    - "Combined vs property breakdown: combined merges all property maps; property breakdown splits shared 1/N then re-totals from original data (no double-counting)"
    - "All monetary amounts serialized as str(Decimal) — avoids JSON float precision issues"

key-files:
  created:
    - app/api/reports.py
  modified:
    - app/accounting/reports.py
    - app/main.py

key-decisions:
  - "Revenue query filters source_type==booking_payout to exclude non-booking revenue adjustments from platform breakdown"
  - "Combined P&L expenses use full shared expense amounts once (not sum of per-property allocations) — avoids double-counting"
  - "Property breakdown net_income per property includes 1/N of shared expenses; combined net_income uses whole shared expense amounts"
  - "generate_pl() returns plain dict — FastAPI serializes directly, no Pydantic response model needed for nested arbitrary-key dicts"

patterns-established:
  - "Report generator functions in app/accounting/reports.py; API wiring in app/api/reports.py — keeps business logic separate from HTTP layer"
  - "Period validation: resolve_period() called in API layer, ValueError becomes HTTP 422 with detail message"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 4 Plan 2: P&L Report Generator Summary

**generate_pl() queries journal_lines for revenue-by-platform (with monthly rows) and expenses-by-category; GET /api/reports/pl endpoint supports all 6 period types plus combined/property breakdown with 1/N shared expense allocation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T00:26:54Z
- **Completed:** 2026-02-28T00:28:58Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- generate_pl() implements full P&L logic: revenue grouped by platform and month via extract(month), expenses by Account.name (category), revenue sign-flipped (credits negated for display)
- Per-property breakdown: property-specific expenses attributed directly, shared expenses (property_id=NULL) split 1/N using dynamic Property table count (never hardcoded)
- Combined totals use full shared expense amounts once — no double-counting from per-property allocations
- GET /api/reports/pl registered at /api/reports/pl supporting all 6 period params plus breakdown=combined|property

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement generate_pl() function in reports.py** - `897ad10` (feat)
2. **Task 2: Create reports API router with P&L endpoint and register in app** - `7a4d8d5` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `app/accounting/reports.py` - Added generate_pl() function with full P&L query, platform/month grouping, expense allocation logic, and both breakdown modes
- `app/api/reports.py` - Created: reports APIRouter, GET /api/reports/pl endpoint with period and breakdown params
- `app/main.py` - Added reports_router import and app.include_router(reports_router)

## Decisions Made
- Revenue query filters `source_type == "booking_payout"` to exclude non-booking adjustments from the platform breakdown — only booking revenue contributes to airbnb/vrbo/rvshare buckets
- Combined P&L uses full shared expense values once (not sum of per-property allocations) — the combined total correctly equals sum of individual property totals because 1/N × N = 1
- generate_pl() returns a plain dict rather than a Pydantic model — the nested arbitrary-key structure (platform names as keys, display_name as keys) doesn't map cleanly to fixed Pydantic schemas
- Monthly revenue rows sorted chronologically within each platform section

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- P&L endpoint ready for use; combined and property breakdown both implemented
- app/api/reports.py router exists — 04-03 (balance sheet) and 04-04 (bank transaction categorization) can add endpoints to this router
- generate_pl() pattern established for 04-03 to follow when building generate_balance_sheet()
- No blockers

---
*Phase: 04-financial-reports*
*Completed: 2026-02-28*
