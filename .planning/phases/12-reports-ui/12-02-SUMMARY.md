---
phase: 12-reports-ui
plan: "02"
subsystem: ui
tags: [react, typescript, tanstack-query, tailwind, reports, balance-sheet]

# Dependency graph
requires:
  - phase: 12-reports-ui/12-01
    provides: useBalanceSheet hook, ReportFilters, ReportSection, EmptyState, ErrorAlert, Skeleton

provides:
  - Full interactive Balance Sheet viewer replacing stub from Plan 01
  - formatAmount utility: em-dash for zero, red parentheses for negative, USD currency for positive
  - formatAsOfDate utility: local-date parsing to avoid UTC midnight shift
  - AccountTable local component: account rows with subtotal row (bg-muted/30)
  - Grand total row (bg-muted/60, border-t-2) for Total Liabilities & Equity
  - All five states: prompt, loading skeletons, error+retry, empty, report content

affects:
  - 12-03 (PLTab) and 12-04 (IncomeStatementTab) can mirror AccountTable and formatting patterns
  - Future reports can reuse formatAmount for consistent number display

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Manual-fetch pattern: hasGenerated flag for prompt state, generate() as setParams trigger"
    - "Local date parsing: new Date(y, m-1, d) avoids UTC midnight shift (per [07-04] pattern)"
    - "Balance check transparency: string comparison of assets.total vs total_liabilities_and_equity"

key-files:
  created: []
  modified:
    - frontend/src/components/reports/BalanceSheetTab.tsx

key-decisions:
  - "hasContent determined by account array length (not totals) — empty account arrays signal no data even if totals string is '0.00'"
  - "doesNotBalance uses string comparison — totals are returned as strings by API; parseFloat comparison avoided to stay consistent with API contract"
  - "AccountTable extracted as local component — shared by all three sections; keeps BalanceSheetTab readable"
  - "formatAsOfDate uses new Date(y, m-1, d) — avoids UTC midnight shift per established [07-04] pattern"

patterns-established:
  - "AccountTable pattern: accounts.map() rows + bg-muted/30 subtotal row, reusable across report tabs"
  - "Five-state render pattern: prompt / skeleton / error / empty / content — standard for all manual-fetch report tabs"

# Metrics
duration: 2min
completed: 2026-03-02
---

# Phase 12 Plan 02: Balance Sheet Tab Summary

**Full Balance Sheet viewer with collapsible Assets/Liabilities/Equity sections, formatted amounts (em-dash/red-parens/USD), grand total row, and five-state render (prompt/skeleton/error/empty/content)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-02T21:19:05Z
- **Completed:** 2026-03-02T21:20:55Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Replaced single-line stub with 200-line interactive Balance Sheet viewer
- Wired all Plan 01 foundation components: useBalanceSheet, ReportFilters(snapshot), ReportSection
- Implemented complete number formatting: em-dash for zero, red parentheses for negative, USD for positive
- Extracted AccountTable local component for clean per-section rendering with subtotal rows
- Added grand total row (Total Liabilities & Equity) and balance check warning

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement Balance Sheet viewer** - `bea1b75` (feat)
2. **Task 2: Verify Balance Sheet integration** - No code changes; verification passed, build clean

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `frontend/src/components/reports/BalanceSheetTab.tsx` - Full interactive viewer replacing stub; exports BalanceSheetTab

## Decisions Made

- **hasContent by account length:** Checking `accounts.length > 0` instead of parsing totals is more robust — totals may be "0.00" with no accounts (empty state) vs no accounts because there is genuine no data.
- **String comparison for balance check:** `data.assets.total !== data.total_liabilities_and_equity` — API returns string; avoids float precision issues from parseFloat comparison.
- **AccountTable extracted:** Three sections share identical table structure; local component avoids 60+ lines of duplication.
- **`formatAsOfDate` uses `new Date(y, m-1, d)`:** Follows the established [07-04] pattern to avoid UTC midnight shift when parsing ISO date strings.

## Deviations from Plan

None - plan executed exactly as written. The `handleGenerate` adapter function narrows the ReportFilters union type (`as_of | { start_date, end_date }`) to the snapshot variant — this is idiomatic TypeScript narrowing, not a deviation.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Balance Sheet tab complete and building cleanly
- AccountTable and formatAmount patterns established for Plans 03-05 to reuse
- Plan 03 (PLTab) and Plan 04 (IncomeStatementTab) can reference the five-state render structure
- No blockers

---
*Phase: 12-reports-ui*
*Completed: 2026-03-02*
