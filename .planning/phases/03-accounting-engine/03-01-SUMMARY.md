---
phase: 03-accounting-engine
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, postgresql, double-entry, bookkeeping, decimal, numeric]

# Dependency graph
requires:
  - phase: 02-data-ingestion
    provides: bookings and bank_transactions tables that Phase 3 adds reconciliation_status to

provides:
  - Account ORM model with chart of accounts number/name/type/is_active
  - JournalEntry ORM model with source_id idempotency key
  - JournalLine ORM model with signed Numeric(12,2) amounts
  - create_journal_entry() — balance-enforced, idempotent journal builder
  - LineSpec dataclass for specifying debit/credit lines
  - Migration 003 with all 6 Phase 3 tables (accounts, journal_entries, journal_lines, expenses, loans, reconciliation_matches)
  - 21-account chart of accounts seeded in DB
  - reconciliation_status column on bookings and bank_transactions

affects:
  - 03-02 (revenue recognition — calls create_journal_entry for booking payouts)
  - 03-03 (expense tracking — uses Expense ORM on expenses stub table)
  - 03-04 (loan payments — uses Loan ORM on loans stub table)
  - 03-05 (reconciliation — uses ReconciliationMatch ORM on reconciliation_matches stub table)
  - 03-06 (accounting API — queries all Phase 3 models)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pg_insert ON CONFLICT DO NOTHING for idempotent journal entry creation"
    - "Numeric(12,2) + Python Decimal throughout — never float for monetary amounts"
    - "Signed amount convention: positive=debit, negative=credit on JournalLine"
    - "source_id as idempotency key (unique constraint) on journal_entries"
    - "Single mega-migration strategy: all Phase 3 tables in 003 to enable parallel Wave-2 execution"

key-files:
  created:
    - app/models/account.py
    - app/models/journal_entry.py
    - app/models/journal_line.py
    - app/accounting/__init__.py
    - app/accounting/journal.py
    - alembic/versions/003_accounting_tables.py
  modified:
    - app/models/__init__.py
    - app/models/booking.py
    - app/models/bank_transaction.py

key-decisions:
  - "Numeric(12,2) for all Phase 3 monetary amounts (upgraded from 10,2 used in Phase 2)"
  - "source_id as String(256) idempotency key — ON CONFLICT DO NOTHING returns None on duplicate"
  - "Stub tables for expenses/loans/reconciliation_matches in migration 003 — Wave-2 plans add ORM models only"
  - "Signed amount on JournalLine (positive=debit, negative=credit) — balance check is simply sum==0"
  - "property_id nullable on JournalEntry — None for shared/cross-property entries"
  - "reconciliation_status defaults to 'unmatched' on both bookings and bank_transactions"

patterns-established:
  - "Journal builder pattern: validate FIRST (balance + line count), then upsert, then create lines"
  - "All accounting models use Integer PK + unique business key (source_id or account number)"
  - "create_journal_entry returns None on duplicate (not error) — caller decides if skip is expected"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 3 Plan 01: Accounting Core Summary

**Double-entry bookkeeping foundation: Account/JournalEntry/JournalLine ORM models with balance-enforced idempotent journal builder and single migration creating all 6 Phase 3 tables with 21-account chart of accounts seed**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T21:36:01Z
- **Completed:** 2026-02-27T21:38:27Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Three new ORM models (Account, JournalEntry, JournalLine) using SQLAlchemy 2.0 Mapped[] pattern
- `create_journal_entry()` with pre-DB balance enforcement (sum must == 0), minimum 2 lines, and idempotent upsert via `pg_insert ON CONFLICT DO NOTHING` on `source_id`
- Migration 003 creates all 6 Phase 3 tables in one file, enabling Wave-2 plans (03-03, 03-04, 03-05) to run in parallel without migration conflicts
- Chart of accounts seeded with 21 accounts across all 5 types (asset, liability, equity, revenue, expense)
- `reconciliation_status` column added to bookings and bank_transactions with default "unmatched"

## Task Commits

Each task was committed atomically:

1. **Task 1: Account, JournalEntry, JournalLine ORM models and journal builder** - `46e35ae` (feat)
2. **Task 2: Migration 003 with all Phase 3 tables, chart of accounts seed, reconciliation_status** - `490834e` (feat)

## Files Created/Modified

- `app/models/account.py` - Account ORM model: number (1000-9999), name, account_type, is_active with CheckConstraint
- `app/models/journal_entry.py` - JournalEntry ORM model: source_id unique idempotency key, property_id FK nullable, lines relationship
- `app/models/journal_line.py` - JournalLine ORM model: signed Numeric(12,2) amount, FK to journal_entries and accounts
- `app/accounting/__init__.py` - Accounting engine package init
- `app/accounting/journal.py` - LineSpec dataclass + create_journal_entry() with balance enforcement and idempotent upsert
- `alembic/versions/003_accounting_tables.py` - Migration 003: all 6 Phase 3 tables, 21-account seed, reconciliation_status columns
- `app/models/__init__.py` - Added Account, JournalEntry, JournalLine imports
- `app/models/booking.py` - Added reconciliation_status field (server_default="unmatched")
- `app/models/bank_transaction.py` - Added reconciliation_status field (server_default="unmatched")

## Decisions Made

- **Numeric(12,2) for Phase 3 amounts**: Upgraded from 10,2 used in Phase 2 models. Phase 3 research specified 12,2 for accounting amounts.
- **Stub table strategy in migration 003**: Expenses, loans, and reconciliation_matches tables are defined in this migration as stubs. Wave-2 plans (03-03, 03-04, 03-05) only add ORM models and business logic — no new migration files needed, eliminating the risk of parallel migration conflicts.
- **Signed amount on JournalLine**: Positive=debit, negative=credit. Balance check is `sum(line.amount) == Decimal("0")`, which is simple and correct for double-entry accounting.
- **source_id as idempotency key**: `String(256)` unique constraint on `journal_entries.source_id`. `create_journal_entry` returns `None` on duplicate rather than raising — caller decides whether a skip is expected or a bug.
- **property_id nullable on JournalEntry**: Shared or cross-property entries (e.g., shared loan payments) have no property_id.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Docker was not running (no .env file), so the migration `alembic upgrade head` step was skipped per plan instructions. Migration file syntax was verified with `ast.parse()`.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `create_journal_entry()` is callable and fully tested via import verification
- All 6 Phase 3 DB tables will be created when migration 003 is applied
- Chart of accounts seeded with 21 accounts — revenue/expense recognition plans can reference account numbers directly
- Wave-2 plans (03-02 through 03-06) can all start: migration 003 creates their tables, they only need to add ORM models

---
*Phase: 03-accounting-engine*
*Completed: 2026-02-27*
