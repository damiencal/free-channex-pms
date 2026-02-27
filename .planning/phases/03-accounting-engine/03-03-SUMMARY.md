---
phase: 03-accounting-engine
plan: "03"
subsystem: database
tags: [sqlalchemy, postgresql, accounting, double-entry, expenses, schedule-e, decimal]

# Dependency graph
requires:
  - phase: 03-01
    provides: Account/JournalEntry/JournalLine ORM models, create_journal_entry(), migration 003 (expenses table stub)

provides:
  - Expense ORM model (app/models/expense.py) mapped to expenses table
  - record_expense() function creating both Expense record and balanced journal entry
  - bulk_import_expenses() for CSV-style batch processing with per-row error collection
  - EXPENSE_CATEGORIES list (12 Schedule E-aligned categories)
  - Category-to-account mapping covering all 12 categories including owner_reimbursable as liability

affects:
  - 03-06 (accounting API endpoints will expose record_expense and bulk_import_expenses)
  - 03-02 (revenue recording — parallel pattern to expense recording)
  - reporting phases (expense categories are the Schedule E line items for reports)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Expense recording creates both domain record (Expense) and double-entry ledger entry (JournalEntry) atomically in same flush"
    - "Category slug -> account name lookup at runtime via DB query (not hardcoded IDs) for portability"
    - "bulk_import_expenses: collect-all-errors pattern — never abort on individual row failure"
    - "source_id uses uuid4 suffix (expense:{date}:{uuid4}) for uniqueness across multiple same-date expenses"

key-files:
  created:
    - app/models/expense.py
    - app/accounting/expenses.py
  modified:
    - app/models/__init__.py

key-decisions:
  - "owner_reimbursable debits liability account 2200 (not expense) — owner paid on company behalf, company owes them back; journal: Dr Owner Reimbursable, Cr Mercury Checking"
  - "Category-to-account resolved via DB name lookup (not hardcoded account IDs) — resilient to account reseeding"
  - "UUID suffix in source_id prevents idempotency collisions for multiple expenses on same date (unlike booking payout which uses deterministic IDs)"
  - "bulk_import_expenses accepts str or float amounts and converts to Decimal internally — tolerates both CSV (str) and JSON (float) callers"

patterns-established:
  - "Domain record + journal entry created together: record_X() creates the domain object and calls create_journal_entry() in one function"
  - "Validation order: category, attribution, amount — fail fast before any DB interaction"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 3 Plan 03: Expense Model and Recording Summary

**Expense ORM model with 12 Schedule E categories, record_expense() creating balanced double-entry journal entry per expense, and bulk_import_expenses() for CSV batch processing with per-row error collection.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T21:46:22Z
- **Completed:** 2026-02-27T21:47:55Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Expense ORM model with all 10 fields matching the expenses stub table from migration 003
- 12 EXPENSE_CATEGORIES (Schedule E-aligned) with category-to-account-name mapping
- record_expense() validates inputs, resolves account IDs from chart of accounts, creates balanced journal entry (Dr expense/liability, Cr Mercury Checking), and creates linked Expense record
- owner_reimbursable correctly targets liability account 2200 (not an expense account)
- bulk_import_expenses() handles str/float amounts, collects per-row errors without aborting, returns {"imported": N, "errors": [...]}

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Expense ORM model** - `52bc215` (feat)
2. **Task 2: Implement expense recording and CSV bulk import** - `7f89279` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `app/models/expense.py` - Expense ORM model mapped to expenses table (created by migration 003)
- `app/accounting/expenses.py` - EXPENSE_CATEGORIES, record_expense(), bulk_import_expenses()
- `app/models/__init__.py` - Added Expense import for Alembic detection

## Decisions Made

- **owner_reimbursable as liability:** When an owner pays out of pocket, the company owes reimbursement — this is a liability (Dr. Owner Reimbursable 2200, Cr. Mercury Checking), not an expense debit. The plan explicitly called this out.
- **UUID suffix on source_id:** Unlike booking payouts (deterministic source IDs), multiple expenses can land on the same date. Using `expense:{date}:{uuid4()}` ensures each expense gets a unique idempotency key while still embedding the date for human readability.
- **Category-to-account resolved by name lookup at runtime:** `_get_account_id(db, name)` queries the accounts table by name each time. This avoids hardcoded account IDs that could drift if the DB is reseeded, at the cost of two extra selects per expense (acceptable for batch sizes at this scale).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Expense recording is fully functional; API endpoints (plan 03-06) can expose record_expense and bulk_import_expenses directly
- Pattern established by record_expense (domain record + journal entry in one call) should be followed by 03-04 (loan payments)
- No blockers for parallel plans 03-04 (loans) and 03-05 (reconciliation)

---
*Phase: 03-accounting-engine*
*Completed: 2026-02-27*
