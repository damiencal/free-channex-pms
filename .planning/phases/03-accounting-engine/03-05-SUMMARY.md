---
phase: 03-accounting-engine
plan: 05
subsystem: database
tags: [sqlalchemy, reconciliation, bank-transactions, bookings, decimal, orm]

# Dependency graph
requires:
  - phase: 03-01
    provides: reconciliation_matches table (stub) in migration 003, reconciliation_status fields on bookings and bank_transactions, Base ORM setup
  - phase: 02-05
    provides: BankTransaction ORM model with amount and date fields
  - phase: 02-02
    provides: Booking ORM model with net_amount and check_in_date fields
provides:
  - ReconciliationMatch ORM model on reconciliation_matches table
  - run_reconciliation(): batch exact-amount + 7-day-window matching algorithm
  - confirm_match(): operator confirmation of auto-matched or needs_review pairs
  - reject_match(): operator rejection with audit trail and status reset
  - get_unreconciled(): unreconciled queue returning all three categories
affects:
  - 03-06 (reconciliation API endpoints will consume these functions)
  - future reporting phases that query reconciliation_status

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Decimal equality for monetary amount comparison (no float)"
    - "Mutable candidate pool pattern — remove matched bookings to prevent double-matching"
    - "Batch flush, caller commits — reconciliation functions call db.flush(), not db.commit()"
    - "Audit trail preservation — rejected matches keep the record with status='rejected', not deleted"

key-files:
  created:
    - app/models/reconciliation.py
    - app/accounting/reconciliation.py
  modified:
    - app/models/__init__.py

key-decisions:
  - "MATCH_WINDOW_DAYS = 7 per CONTEXT.md — Airbnb typically pays out on or near check-in day"
  - "Decimal equality for amount comparison — both Booking.net_amount and BankTransaction.amount are Numeric(10,2), no float involved"
  - "Multiple-candidate deposits flagged as needs_review with NO match record created — operator must confirm specific pairing"
  - "reject_match resets both sides to 'unmatched' but preserves the match record for audit trail"
  - "confirm_match upserts — works for both confirming auto-matched records and creating new records for needs_review deposits"

patterns-established:
  - "Reconciliation status lifecycle: unmatched -> matched (auto) -> confirmed (operator) or rejected (operator); or unmatched -> needs_review -> confirmed (operator)"
  - "Candidate pool mutation: available_bookings.remove(booking) prevents one booking matching two deposits"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 3 Plan 05: Reconciliation Match Summary

**ReconciliationMatch ORM model and batch reconciliation algorithm matching platform payouts to bank deposits by exact Decimal amount + 7-day date window**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T21:46:46Z
- **Completed:** 2026-02-27T21:48:27Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- ReconciliationMatch ORM model (booking_id FK unique, bank_transaction_id FK unique) on the pre-existing reconciliation_matches table from migration 003
- run_reconciliation() auto-matches single-candidate pairs and flags multi-candidate deposits as needs_review, with matched bookings removed from candidate pool to prevent double-matching
- confirm_match(), reject_match(), get_unreconciled() provide full operator workflow for reviewing and resolving flagged transactions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ReconciliationMatch ORM model** - `b65bc95` (feat)
2. **Task 2: Implement reconciliation algorithm and match management** - `59864b2` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `app/models/reconciliation.py` - ReconciliationMatch ORM model: id, booking_id (FK unique), bank_transaction_id (FK unique), status String(32), matched_at DateTime(tz), confirmed_by String(128) nullable
- `app/accounting/reconciliation.py` - Reconciliation module: MATCH_WINDOW_DAYS=7, run_reconciliation, confirm_match, reject_match, get_unreconciled
- `app/models/__init__.py` - Added ReconciliationMatch import for Alembic metadata registration

## Decisions Made

- MATCH_WINDOW_DAYS = 7: Airbnb typically pays out on or near check-in day; 7-day window accommodates delays and timing differences between platforms
- Decimal equality for amount comparison: both Booking.net_amount and BankTransaction.amount are Numeric(10,2); SQLAlchemy returns Python Decimal, so == comparison is exact with no float rounding risk
- Multiple-candidate deposits get needs_review status but no match record: operator must explicitly confirm the correct booking pairing
- reject_match preserves the match record with status="rejected" for audit trail rather than deleting it; both sides reset to "unmatched" to re-enter the queue
- confirm_match upserts: handles both confirming an existing auto-match record and creating a new record when an operator manually matches a needs_review deposit

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ReconciliationMatch model and all four algorithm functions are ready for API exposure in plan 03-06
- reconciliation_status lifecycle fully implemented: unmatched -> matched -> confirmed/rejected; unmatched -> needs_review -> confirmed
- Migration 003 table was already in place; no migration work needed
- Blocker from prior plans still open: confirm Airbnb fee model (host-only 15.5% vs split) before finalizing fee attribution in accounting entries

---
*Phase: 03-accounting-engine*
*Completed: 2026-02-27*
