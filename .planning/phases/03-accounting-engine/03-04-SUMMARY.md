---
phase: 03-accounting-engine
plan: 04
subsystem: database
tags: [sqlalchemy, postgresql, double-entry, loans, amortization, journal]

# Dependency graph
requires:
  - phase: 03-01
    provides: JournalEntry/JournalLine ORM models, create_journal_entry() builder, migration 003 with loans table stub
provides:
  - Loan ORM model with account FK, original_balance, interest_rate, start_date
  - record_loan_payment() with 3-line balanced journal entry (principal Dr, interest Dr, cash Cr)
  - get_loan_balance() computing outstanding balance from original_balance minus principal payments
affects:
  - 03-05-reporting (loan balances and interest expense appear in reports)
  - 03-06-reconciliation (loan payments create journal entries to reconcile)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Caller-provided P&I split (system does not compute amortization)
    - Module-level account cache for avoiding repeated DB lookups per payment
    - source_id format: {source_type}:{entity_id}:{caller_ref} for unique idempotency keys

key-files:
  created:
    - app/models/loan.py
    - app/accounting/loans.py
  modified:
    - app/models/__init__.py

key-decisions:
  - "Caller provides P&I split from lender's amortization schedule — system does not compute amortization"
  - "property_id=None on loan payment journal entries — loans are shared liabilities, not property-specific"
  - "source_id format: loan_payment:{loan.id}:{payment_ref} — combines entity ID with caller ref for uniqueness across loans"
  - "interest_rate stored as Numeric(6,4) annual decimal (0.0650 = 6.5%) — precision sufficient for 4 decimal places"

patterns-established:
  - "Module-level _account_cache dict for lazily caching Account.id lookups by name (same pattern as revenue.py)"
  - "3-line loan payment pattern: Dr liability + Dr expense + Cr asset = 0"
  - "get_loan_balance uses func.coalesce(func.sum(...), 0) to handle no-payments case"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 3 Plan 04: Loan Tracking Summary

**Loan ORM model and payment recording with caller-provided P&I split into principal (Dr liability) and interest (Dr Non-Mortgage Interest) as balanced double-entry journal entries**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-27T21:46:40Z
- **Completed:** 2026-02-27T21:48:03Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Loan model on pre-existing `loans` table (stub from migration 003) with name, account_id FK, original_balance, interest_rate, start_date
- `record_loan_payment()` creates balanced 3-line entry: Dr loan liability (principal), Dr Non-Mortgage Interest (interest), Cr Mercury Checking (total)
- `get_loan_balance()` computes outstanding balance as original_balance minus sum of all principal payments posted to the loan's liability account
- Idempotency via `source_id = loan_payment:{loan.id}:{payment_ref}` — ON CONFLICT DO NOTHING returns None on duplicate

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Loan ORM model** - `8a1bccf` (feat)
2. **Task 2: Implement loan payment recording with P&I split** - `3410ea1` (feat)

**Plan metadata:** committed with SUMMARY.md (docs)

## Files Created/Modified

- `app/models/loan.py` - Loan ORM model: name, account_id FK to accounts, original_balance, interest_rate, start_date, account relationship
- `app/accounting/loans.py` - record_loan_payment() and get_loan_balance() with module-level account cache
- `app/models/__init__.py` - Added `from app.models.loan import Loan  # noqa: F401`

## Decisions Made

- **Caller-provided P&I split:** System does NOT compute amortization. The operator/caller reads the split from their lender's schedule and passes principal and interest separately. This keeps the accounting engine simple and accurate regardless of amortization method.
- **property_id=None:** Loan payments are shared liabilities not tied to a specific property. Consistent with CONTEXT.md guidance.
- **source_id pattern:** `loan_payment:{loan.id}:{payment_ref}` — combining the loan's database ID with a caller-supplied reference (e.g., "2026-01") ensures uniqueness across multiple loans with the same monthly payment references.
- **interest_rate as Numeric(6,4):** Stores the annual rate as a decimal (e.g., 0.0650 for 6.5%). The field is informational for display/reporting; actual P&I computation happens externally.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Loan payment recording is ready for use in the API layer
- `get_loan_balance()` available for reporting (Plan 03-05)
- The module-level cache pattern is established for revenue.py and expense.py to follow when implemented
- No blockers for remaining Phase 3 plans

---
*Phase: 03-accounting-engine*
*Completed: 2026-02-27*
