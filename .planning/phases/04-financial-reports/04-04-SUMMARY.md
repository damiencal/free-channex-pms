---
phase: 04-financial-reports
plan: 04
subsystem: api
tags: [fastapi, sqlalchemy, bank-transactions, categorization, journal-entries, expenses]

# Dependency graph
requires:
  - phase: 04-01
    provides: ALL_CATEGORIES, NON_EXPENSE_CATEGORIES constants in reports.py; category/journal_entry_id columns on bank_transactions
  - phase: 03-03
    provides: record_expense() function and EXPENSE_CATEGORIES constant in expenses.py
  - phase: 03-06
    provides: accounting router pattern; commit responsibility at API layer; BankTransaction model imported via reconciliation module
affects:
  - phase: 05-pdf-pipeline
  - phase: 08-nlp-query

provides:
  - "GET /api/accounting/bank-transactions with categorized (true/false/all), date, and pagination filters"
  - "PATCH /api/accounting/bank-transactions/categorize bulk endpoint with per-item error collection"
  - "PATCH /api/accounting/bank-transactions/{txn_id}/category single categorization with auto-expense journal entry"
  - "BankTransactionResponse, CategoryAssignment, SingleCategoryRequest, BulkCategoryRequest Pydantic schemas"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bulk endpoint registered before parameterized single endpoint to avoid route conflict"
    - "abs(txn.amount) normalization: bank debits are negative, record_expense() requires positive amounts"
    - "Bulk endpoints collect errors without aborting: process all, commit once at end, return {categorized, errors}"
    - "Re-categorization guard: check journal_entry_id is not None before allowing re-assignment"

key-files:
  created: []
  modified:
    - "app/api/accounting.py"

key-decisions:
  - "BankTransaction import added to accounting.py: was absent despite plan note saying it may exist"
  - "Bulk /bank-transactions/categorize endpoint registered before /{txn_id}/category to prevent route ambiguity"
  - "abs(txn.amount) when calling record_expense(): bank debits are stored as negative amounts, record_expense() requires positive"
  - "record_expense() ValueError re-raised in bulk as per-item error (continues), in single as HTTP 422 (aborts)"

patterns-established:
  - "Bulk-then-single route ordering: always register fixed-path bulk endpoints before path-parameterized endpoints"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 4 Plan 04: Bank Transaction Categorization Endpoints Summary

**Three FastAPI endpoints for bank transaction categorization: GET list with filters, PATCH single with auto-expense journal entry creation, PATCH bulk with per-item error collection**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T00:27:37Z
- **Completed:** 2026-02-28T00:29:32Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- GET /api/accounting/bank-transactions with categorized filter (true/false/all), date range, and pagination
- PATCH /api/accounting/bank-transactions/{txn_id}/category assigns category, auto-creates expense journal entry for expense categories, prevents re-categorization when journal_entry_id exists
- PATCH /api/accounting/bank-transactions/categorize processes bulk assignments with per-item error collection (commit once after all processed)
- Four new Pydantic schemas: BankTransactionResponse, CategoryAssignment, SingleCategoryRequest, BulkCategoryRequest
- Imported ALL_CATEGORIES, NON_EXPENSE_CATEGORIES from reports.py and EXPENSE_CATEGORIES from expenses.py for category validation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Pydantic schemas for bank transaction categorization** - `177b31f` (feat)
2. **Task 2: Add bank transaction list, single categorization, and bulk categorization endpoints** - `2f116dc` (feat)

## Files Created/Modified
- `app/api/accounting.py` - Added 4 Pydantic schemas, 3 endpoints (GET list, PATCH bulk categorize, PATCH single categorize), and 4 new imports

## Decisions Made
- **BankTransaction not pre-imported:** Plan noted BankTransaction may already be imported, but it was absent. Added all four required imports (BankTransaction, ALL_CATEGORIES, NON_EXPENSE_CATEGORIES, EXPENSE_CATEGORIES).
- **Bulk before single route order:** PATCH /bank-transactions/categorize registered before PATCH /bank-transactions/{txn_id}/category to prevent "categorize" being captured as a txn_id path param.
- **abs(txn.amount) for record_expense():** Bank transaction amounts for debits are stored as negative values; record_expense() validates amount > 0, so abs() normalization is applied at the API layer.
- **Per-item error handling in bulk:** record_expense() ValueError is caught and appended to errors list (continues to next item) rather than aborting the entire bulk request.

## Deviations from Plan

None - plan executed exactly as written. The note about BankTransaction possibly being pre-imported was correctly caveated; its absence was expected and handled per plan instructions ("Only add the ALL_CATEGORIES, NON_EXPENSE_CATEGORIES, and EXPENSE_CATEGORIES imports... Check existing imports first").

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Bank transaction categorization complete (DASH-08)
- Expense categories now flow from bank transactions to P&L reports via auto-created journal entries
- Phase 4 Wave-2 is fully parallel: 04-02, 04-03, and 04-04 are all independent; 04-04 now complete
- Phase 5 (PDF pipeline) and Phase 6 onward are unblocked by 04-04

---
*Phase: 04-financial-reports*
*Completed: 2026-02-28*
