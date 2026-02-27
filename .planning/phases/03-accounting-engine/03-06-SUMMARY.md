---
phase: 03-accounting-engine
plan: 06
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, accounting, revenue-recognition, reconciliation, expenses, loans]

# Dependency graph
requires:
  - phase: 03-01
    provides: JournalEntry/JournalLine/Account models, create_journal_entry(), migration 003
  - phase: 03-02
    provides: recognize_booking_revenue, create_unearned_revenue_entry, reverse_journal_entry
  - phase: 03-03
    provides: record_expense, bulk_import_expenses, EXPENSE_CATEGORIES
  - phase: 03-04
    provides: record_loan_payment, get_loan_balance, Loan model
  - phase: 03-05
    provides: run_reconciliation, confirm_match, reject_match, get_unreconciled
provides:
  - 14 HTTP endpoints for all Phase 3 accounting operations via FastAPI router
  - Operator-triggered revenue recognition (POST /api/accounting/revenue/recognize and /recognize-all)
  - Journal entry query with date/source_type/property_id filters
  - Account balance ledger view
  - Expense recording (single POST + CSV bulk import)
  - Loan payment recording with P&I split
  - Reconciliation workflow (trigger, unreconciled queue, confirm, reject)
affects: [07-dashboard, future-reporting, future-cli]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "APIRouter with prefix=/api/accounting, tags=[accounting] — consistent with ingestion router"
    - "Pydantic schemas defined in endpoint file (not separate schemas module) — co-located for API"
    - "get_config() FastAPI dependency-free call — config loaded at lifespan, get_config() returns cached singleton"
    - "Operator-triggered recognition pattern — imports create Booking, explicit POST creates JournalEntry"
    - "db.commit() in endpoint, not in accounting module — modules use db.flush() only"

key-files:
  created:
    - app/api/accounting.py
  modified:
    - app/main.py

key-decisions:
  - "get_config() (not Depends) for config in endpoints — config is a module-level singleton loaded at lifespan; no per-request overhead"
  - "recognize-all queries by source_type='booking_payout' to detect existing entries efficiently"
  - "Commit in each recognize-all loop iteration with individual rollback on error — avoids one bad booking failing the batch"
  - "POST /reconciliation/reject/{match_id} takes confirmed_by as query param (not body) — reject is a simple action, not a rich request"
  - "LoanPaymentRequest returns dict (not JournalEntryResponse) — idempotent skip returns None entry; simpler to return status/id dict"

patterns-established:
  - "Commit responsibility: accounting modules call db.flush() only; API endpoints call db.commit()"
  - "ValueError from any accounting module caught as HTTPException(422) at API boundary"
  - "CSV upload: file.file.read() (sync) for non-async endpoints, UploadFile + File(...) parameter"
  - "Simplified dicts in UnreconciledResponse — ORM objects serialized to minimal JSON, not full models"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 3 Plan 6: Accounting API Summary

**14-endpoint FastAPI router exposing all Phase 3 accounting operations via /api/accounting, with operator-triggered revenue recognition as the explicit bridge between booking ingestion and the ledger**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T21:52:07Z
- **Completed:** 2026-02-27T21:54:06Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `app/api/accounting.py` with 14 endpoints covering journal entries, balances, revenue recognition, expenses, loans, and reconciliation — verified at 14 routes
- Revenue recognition is strictly operator-triggered: POST /api/accounting/revenue/recognize (single) and /recognize-all (batch) are the ONLY paths from Booking to JournalEntry
- Registered accounting router in `app/main.py` alongside health and ingestion routers; all `/api/accounting/*` routes accessible

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Pydantic schemas and all accounting endpoints** - `d83510a` (feat)
2. **Task 2: Register accounting router in FastAPI app** - `cc4a8ca` (feat)

**Plan metadata:** (committed with SUMMARY/STATE update)

## Files Created/Modified

- `app/api/accounting.py` - FastAPI router with all 14 accounting endpoints and Pydantic schemas
- `app/main.py` - Added accounting_router import and app.include_router(accounting_router)

## Decisions Made

- **get_config() not Depends for config:** AppConfig is a module-level singleton loaded at lifespan startup. Calling `get_config()` directly (not via FastAPI dependency injection) avoids per-request overhead and is consistent with how the rest of the app accesses config.
- **recognize-all batch commit strategy:** Each booking's recognition is committed individually with rollback on error. This ensures one malformed booking does not abort the entire batch — partial progress is preserved.
- **POST reject/{match_id} with query param confirmed_by:** Rejection is a simple action (match_id from path is sufficient). A request body would be overengineered for a two-field interaction.
- **Loans endpoint returns dict not JournalEntryResponse:** `record_loan_payment` can return None (idempotent skip). Returning a status/journal_entry_id dict is cleaner than trying to serialize None as JournalEntryResponse.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. All endpoints are immediately usable once the database has migration 003 applied and the app is running.

## Next Phase Readiness

- All Phase 3 accounting operations are now HTTP-accessible — ready for Phase 7 dashboard integration
- Revenue recognition workflow complete: operator imports via Phase 2 endpoints, then POSTs to /api/accounting/revenue/recognize-all to post the batch to the ledger
- Phase 3 (Accounting Engine) is now fully complete (plans 03-01 through 03-06 all done)
- Next phase: Phase 4 (Notifications/Messaging) or Phase 5 (PDF generation) per ROADMAP

---
*Phase: 03-accounting-engine*
*Completed: 2026-02-27*
