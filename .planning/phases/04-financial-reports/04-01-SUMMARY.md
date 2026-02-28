---
phase: 04-financial-reports
plan: 01
subsystem: database
tags: [alembic, sqlalchemy, migration, bank-transactions, loans, period-resolution, categories]

# Dependency graph
requires:
  - phase: 03-accounting-engine
    provides: journal_entries table, loans table, bank_transactions table, expenses.py with EXPENSE_CATEGORIES

provides:
  - Migration 004 adding category/journal_entry_id to bank_transactions, property_id to loans
  - BankTransaction ORM with category and journal_entry_id fields
  - Loan ORM with property_id field for per-property loan attribution
  - resolve_period() helper supporting 6 period types with full validation
  - ALL_CATEGORIES (16 total: 12 expense + 4 non-expense) in reports.py

affects:
  - 04-02 (P&L report — needs resolve_period and property_id on loans)
  - 04-03 (balance sheet — needs resolve_period)
  - 04-04 (bank transaction categorization — needs category/journal_entry_id columns and ALL_CATEGORIES)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "resolve_period() as shared period resolver — all report endpoints call this single function rather than duplicating period logic"
    - "EXPENSE_CATEGORIES imported (not duplicated) in reports.py — single source of truth preserved in expenses.py"
    - "Wave-1 migration bundles all schema changes for a phase — Wave-2 plans run in parallel without migration conflicts"

key-files:
  created:
    - alembic/versions/004_financial_reports.py
    - app/accounting/reports.py
  modified:
    - app/models/bank_transaction.py
    - app/models/loan.py

key-decisions:
  - "resolve_period() priority order: start/end > month > quarter > year > ytd > error — first match wins, explicit ranges always take precedence"
  - "NON_EXPENSE_CATEGORIES [owner_deposit, loan_payment, transfer, personal] captures bank transaction types that don't appear on P&L"
  - "property_id on loans is nullable — property-specific loans (RV) get property_id; shared loans (working capital) remain NULL"
  - "category and journal_entry_id on bank_transactions are both nullable — set only during categorization workflow in plan 04-04"

patterns-established:
  - "Quarter resolution: Q1=(1,3), Q2=(4,6), Q3=(7,9), Q4=(10,12); case-insensitive input accepted"
  - "Month last-day via calendar.monthrange(year, month)[1] — handles leap years correctly"

# Metrics
duration: 1min
completed: 2026-02-28
---

# Phase 4 Plan 1: Financial Reports Foundation Summary

**Alembic migration 004 adds category/journal_entry_id to bank_transactions and property_id to loans; reports.py establishes shared resolve_period() with 6 period types and 16-category ALL_CATEGORIES constant**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-28T00:21:11Z
- **Completed:** 2026-02-28T00:22:33Z
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- Migration 004 (down_revision=003) adds 3 nullable columns across 2 tables in a single migration so all Wave-2 plans can run in parallel
- BankTransaction and Loan ORM models updated to expose new columns immediately
- resolve_period() handles all 6 period types (start/end, month+year, quarter+year, year, ytd, error) with descriptive ValueError messages
- ALL_CATEGORIES (16 entries) built by importing EXPENSE_CATEGORIES from expenses.py — zero duplication of the 12 Schedule E categories

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Alembic migration 004 and update ORM models** - `2640d33` (feat)
2. **Task 2: Create reports.py with resolve_period() helper and report constants** - `a2d5490` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `alembic/versions/004_financial_reports.py` - Migration adding category/journal_entry_id to bank_transactions, property_id to loans
- `app/models/bank_transaction.py` - Added category (String(64), nullable) and journal_entry_id (FK journal_entries.id, nullable) fields
- `app/models/loan.py` - Added property_id (FK properties.id, nullable) field
- `app/accounting/reports.py` - resolve_period() helper + NON_EXPENSE_CATEGORIES + ALL_CATEGORIES constants

## Decisions Made
- resolve_period() priority order: start/end > month > quarter > year > ytd > error — explicit ranges always take precedence, ytd is last computed option
- NON_EXPENSE_CATEGORIES chosen as [owner_deposit, loan_payment, transfer, personal] — these 4 cover all bank transaction types that don't represent Schedule E expenses
- property_id on loans is nullable — property-specific loans (e.g., RV Purchase Loan on Jay) get property_id set; shared working capital loans remain NULL
- EXPENSE_CATEGORIES not duplicated — imported directly from app.accounting.expenses to maintain single source of truth

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All Wave-2 plans (04-02, 04-03, 04-04) have their foundation: schema columns exist in migration, ORM models expose them, resolve_period() is available
- Plans 04-02 (P&L), 04-03 (balance sheet), and 04-04 (bank transaction categorization) can run in parallel
- No blockers; migration 004 will apply cleanly after 003

---
*Phase: 04-financial-reports*
*Completed: 2026-02-28*
