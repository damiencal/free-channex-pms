---
phase: 12-reports-ui
plan: 03
subsystem: ui
tags: [react, typescript, tanstack-query, tailwind, reports, pl, monthly-table]

# Dependency graph
requires:
  - phase: 12-01
    provides: API layer (fetchPL, PLCombinedResponse), hooks (usePL), shared components (ReportFilters, ReportSection, EmptyState, ErrorAlert)
provides:
  - MonthlyTable: reusable horizontal-scroll monthly breakdown table (sticky labels, Total column, % column)
  - PLTab: complete P&L viewer with Totals and Monthly sub-views
affects: [12-04-income-statement, 12-05-balance-sheet]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MonthlyTable as shared reusable component: both P&L and Income Statement use same horizontal-scroll table"
    - "Sub-view toggle pattern: useState<'totals'|'monthly'> with Button secondary/ghost variants"
    - "IIFE in JSX for derived display values: avoids intermediate variables cluttering component scope"
    - "Always breakdown=combined: no per-property breakdown in Phase 12 P&L"

key-files:
  created:
    - frontend/src/components/reports/MonthlyTable.tsx
    - (PLTab.tsx overwritten — see modified)
  modified:
    - frontend/src/components/reports/PLTab.tsx

key-decisions:
  - "Monthly sub-view: expenses shown as totals only — P&L API has no monthly breakdown for expenses (by design)"
  - "Grand total row per-month computed client-side from per-platform month arrays — avoids extra API endpoint"
  - "AmountCell defined locally in PLTab — not shared component; avoids over-generalizing before patterns settle"
  - "formatDateLabel uses new Date(y, m-1, d) — avoids UTC midnight shift (consistent with [07-04] pattern)"

patterns-established:
  - "MonthlyTable props: months[], rows[]{label,values,total,isSubtotal?,isGrandTotal?}, showPercentage?, percentageBase?"
  - "formatAmount returns {display, isNegative, isZero} — callers decide how to apply red class"
  - "computePercent / formatPercent: both return em-dash for zero/NaN/zero-base cases"

# Metrics
duration: 2min
completed: 2026-03-02
---

# Phase 12 Plan 03: P&L Tab Summary

**P&L viewer with per-platform revenue breakdown, by-category expenses, percentage columns, and Totals/Monthly sub-view toggle using shared MonthlyTable component**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-02T21:19:52Z
- **Completed:** 2026-03-02T21:21:38Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `MonthlyTable` reusable horizontal-scroll table (sticky first column, month columns, Total, optional % column) to be shared with Income Statement (Plan 04)
- Replaced PLTab stub with full P&L viewer: Revenue section (per-platform subtotals + %), Expenses section (by-category + %), Net Income grand total row
- Totals/Monthly sub-view toggle — Monthly view uses MonthlyTable for revenue with grand totals computed client-side; expenses shown as period totals (API limitation)

## Task Commits

1. **Task 1: Create MonthlyTable component** - `bc81c04` (feat)
2. **Task 2: Implement PLTab with Totals/Monthly sub-views** - `5a2210e` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `frontend/src/components/reports/MonthlyTable.tsx` - Reusable horizontal-scroll monthly breakdown table; exports MonthlyTable
- `frontend/src/components/reports/PLTab.tsx` - Full P&L viewer replacing stub; exports PLTab

## Decisions Made

- **Expenses in Monthly sub-view shown as period totals**: The P&L API (`/reports/pl`) returns `expenses.by_category` as a flat dict of total amounts — no per-month breakdown. Rather than add a new endpoint, expenses are shown as totals in the monthly sub-view with a note. This is the correct tradeoff for Phase 12 scope.
- **Grand total row month values computed client-side**: The API returns per-platform month arrays. Total Revenue per month is summed across platforms in the component. No extra endpoint needed.
- **`breakdown: 'combined'` always hardcoded**: Per plan spec and [12-01] decision — no per-property breakdown in Phase 12.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `MonthlyTable` exported and ready for Income Statement (Plan 04) to import
- PLTab complete with all required features
- Build passes (zero errors, zero type errors)
- Plans 04 (Income Statement) and 05 (Balance Sheet) can proceed

---
*Phase: 12-reports-ui*
*Completed: 2026-03-02*
