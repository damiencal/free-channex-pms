---
phase: 04-financial-reports
plan: 03
subsystem: api
tags: [sqlalchemy, fastapi, accounting, balance-sheet, income-statement, double-entry]

# Dependency graph
requires:
  - phase: 04-01
    provides: resolve_period(), category constants, reports.py module skeleton
  - phase: 04-02
    provides: generate_pl(), existing reports router with /pl endpoint
  - phase: 03-04
    provides: get_loan_balance(), Loan model, loan_payment journal entries
  - phase: 03-01
    provides: JournalLine signed amounts (positive=debit, negative=credit)
provides:
  - generate_balance_sheet(): point-in-time assets/liabilities/equity snapshot
  - generate_income_statement(): revenue/expense breakdown with totals and monthly modes
  - GET /api/reports/balance-sheet endpoint (requires as_of date)
  - GET /api/reports/income-statement endpoint (period params + breakdown=totals|monthly)
affects: [phase-05, phase-06, phase-07, phase-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Loan balance override: get_loan_balance() replaces journal line sum for loan liability accounts (no origination entries)"
    - "Retained Earnings computed from journal data: negate sum of all revenue+expense lines up to as_of_date"
    - "Monthly grouping via GROUP BY extract(year), extract(month) with Python dict accumulation"

key-files:
  created: []
  modified:
    - app/accounting/reports.py
    - app/api/reports.py

key-decisions:
  - "Loan liability balances via get_loan_balance() not journal sums -- Phase 3 never created origination entries"
  - "Retained Earnings = negate(sum of all revenue+expense journal lines up to as_of_date) -- simplest correct formula"
  - "Balance sheet combined-only, no per-property breakdown -- financial position is entity-level, not property-level"
  - "Income statement breakdown=totals|monthly -- two modes, monthly adds GROUP BY year/month with period totals section"
  - "all_bs_accounts query includes zero-balance accounts -- balance sheet should show all active accounts even with no activity"

patterns-established:
  - "Sign convention display: liability/equity/revenue accounts negated (credit-normal -> positive display)"
  - "Monthly breakdown: accumulate into defaultdict keyed by (year, month) tuple, collect all_months as sorted union of revenue+expense months"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 4 Plan 03: Balance Sheet and Income Statement Summary

**Balance sheet with loan override via get_loan_balance() and income statement with totals/monthly breakdown, completing the financial reporting triad**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T00:32:54Z
- **Completed:** 2026-02-28T00:34:54Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `generate_balance_sheet()`: queries account balances via journal lines up to as_of_date, overrides loan liability accounts with `get_loan_balance()`, computes Retained Earnings by negating cumulative revenue+expense sum, negates all credit-normal accounts for display
- `generate_income_statement()`: two modes — totals aggregates the full period by account name; monthly groups by year+month returning per-month sections plus period totals
- Two new API endpoints: GET /api/reports/balance-sheet (requires as_of) and GET /api/reports/income-statement (full period params + breakdown)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement generate_balance_sheet() and generate_income_statement()** - `774300f` (feat)
2. **Task 2: Add balance sheet and income statement endpoints to reports router** - `105e3ba` (feat)

**Plan metadata:** (included in final docs commit)

## Files Created/Modified

- `app/accounting/reports.py` - Added generate_balance_sheet() and generate_income_statement(); added imports for get_loan_balance and Loan
- `app/api/reports.py` - Added GET /balance-sheet and GET /income-statement endpoints; updated module docstring and imports

## Decisions Made

- **Loan balance override:** `get_loan_balance()` used for all loan liability accounts instead of journal line sums. Phase 3 never created loan origination journal entries — only payment debit entries exist. Using journal line sums alone would undercount (show only reduction amount, not original balance).
- **Retained Earnings formula:** Negate the sum of all revenue+expense journal lines up to as_of_date. Revenue lines are negative (credits), expense lines are positive (debits). Negating the sum yields positive retained earnings when revenues exceed expenses.
- **Zero-balance accounts included:** Balance sheet queries all active balance-sheet accounts and merges with the journal balance map, so accounts with no activity still appear with $0. This is standard balance sheet presentation.
- **Monthly breakdown design:** Collects all (year, month) keys from both revenue and expense row sets, sorts them, and iterates — ensuring months with only expenses or only revenue are still included.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Financial reporting triad complete: P&L (04-02), Balance Sheet, Income Statement (04-03)
- Phase 4 is now fully complete — all 4 plans done (04-01 through 04-04)
- Ready for Phase 5 (PDF form filling / resort check-in pipeline)
- Pre-Phase 5 blocker remains: resort PDF form type (AcroForm vs XFA) unverified

---
*Phase: 04-financial-reports*
*Completed: 2026-02-28*
