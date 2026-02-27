---
phase: 02-data-ingestion
plan: "01"
subsystem: database
tags: [sqlalchemy, alembic, pydantic, polars, postgres, ingestion, bookings]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Base ORM declarative base, Alembic setup, PropertyConfig, AppConfig, db.py

provides:
  - Booking ORM model with (platform, platform_booking_id) unique constraint and Date-typed check_in/out_date
  - BankTransaction ORM model with unique transaction_id index
  - ImportRun ORM model tracking per-import statistics
  - app/ingestion/schemas.py with BookingRecord, BankTransactionRecord, RVshareEntryRequest Pydantic models
  - Alembic migration 002 creating bookings, bank_transactions, import_runs tables
  - AppConfig.archive_dir field (default "./archive") for CSV archive storage
  - PropertyConfig.listing_slug_map for resolving platform listing identifiers to property slugs
  - polars and python-multipart installed
  - Docker volume mount for archive directory persistence

affects:
  - 02-02 (CSV ingestion pipeline uses these models and schemas)
  - 02-03 (bank transaction reconciliation uses BankTransaction model)
  - 03-accounting (reads bookings and bank_transactions tables)
  - All future Phase 2 plans

# Tech tracking
tech-stack:
  added: [polars==1.38.1, python-multipart]
  patterns:
    - Canonical record schemas (BookingRecord, BankTransactionRecord) decoupled from ORM models — adapters produce schemas, normalizer writes to DB
    - listing_slug_map on PropertyConfig for cross-platform property identity resolution
    - Hand-written Alembic migrations with explicit column definitions (no autogenerate)

key-files:
  created:
    - app/models/booking.py
    - app/models/bank_transaction.py
    - app/models/import_run.py
    - app/ingestion/__init__.py
    - app/ingestion/schemas.py
    - alembic/versions/002_ingestion_tables.py
  modified:
    - app/models/__init__.py
    - app/config.py
    - config/base.yaml
    - config/config.example.yaml
    - config/jay.yaml
    - config/minnie.yaml
    - docker-compose.yml
    - pyproject.toml
    - uv.lock

key-decisions:
  - "listing_slug_map is a dict[str, str] on PropertyConfig — each key maps a platform listing identifier to this property's slug; normalizer builds unified lookup at import time"
  - "BookingRecord.property_slug resolved to property_id by normalizer — adapters don't need DB access"
  - "check_in_date and check_out_date use sa.Date() (not DateTime) — calendar dates only, no time component"
  - "archive_dir defaults to './archive' in AppConfig and is mounted as a Docker volume for persistence"

patterns-established:
  - "Adapter pattern: platform-specific parsers produce canonical Pydantic records; normalizer maps slugs to IDs and writes ORM rows"
  - "All ORM models registered in app/models/__init__.py for Alembic detection"
  - "ImportRun tracks every import with inserted/updated/skipped counts for idempotency auditing"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 2 Plan 01: Data Layer Foundation Summary

**Three PostgreSQL tables (bookings, bank_transactions, import_runs), three Pydantic ingestion schemas, and Alembic migration 002 creating the data layer foundation for all Phase 2 CSV ingestion plans**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T18:41:41Z
- **Completed:** 2026-02-27T18:44:11Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Created Booking ORM model with UniqueConstraint on (platform, platform_booking_id) and calendar Date types for check-in/out
- Created BankTransaction and ImportRun ORM models; all three registered with Base.metadata via app/models/__init__.py
- Created app/ingestion/schemas.py with BookingRecord, BankTransactionRecord, and RVshareEntryRequest Pydantic models defining canonical ingestion shapes
- Created Alembic migration 002 chaining from 001, creating all three tables with correct column types and constraints
- Added AppConfig.archive_dir and PropertyConfig.listing_slug_map; installed polars and python-multipart; mounted archive volume in Docker

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dependencies, config additions, and Docker volume mount** - `370094b` (feat)
2. **Task 2: Create ORM models, Pydantic schemas, and Alembic migration** - `674eedf` (feat)

**Plan metadata:** _(pending final commit)_

## Files Created/Modified
- `app/models/booking.py` - Booking ORM model with platform/platform_booking_id unique constraint, Date check-in/out columns
- `app/models/bank_transaction.py` - BankTransaction ORM model with unique transaction_id index
- `app/models/import_run.py` - ImportRun ORM model tracking per-import insert/update/skip counts
- `app/models/__init__.py` - Updated to import all three new models for Alembic discovery
- `app/ingestion/__init__.py` - Empty package init for ingestion module
- `app/ingestion/schemas.py` - BookingRecord, BankTransactionRecord, RVshareEntryRequest Pydantic models
- `alembic/versions/002_ingestion_tables.py` - Migration creating bookings, bank_transactions, import_runs tables
- `app/config.py` - Added AppConfig.archive_dir and PropertyConfig.listing_slug_map fields
- `config/base.yaml` - Added archive_dir default
- `config/config.example.yaml` - Added listing_slug_map example
- `config/jay.yaml` - Added listing_slug_map with CHANGE_ME placeholders
- `config/minnie.yaml` - Added listing_slug_map with CHANGE_ME placeholders
- `docker-compose.yml` - Added ./archive:/app/archive volume mount
- `pyproject.toml` - Added polars and python-multipart dependencies
- `uv.lock` - Updated by uv sync

## Decisions Made
- `listing_slug_map` is a `dict[str, str]` on `PropertyConfig` — each property maps its own platform identifiers to its slug. The normalizer builds a unified lookup from all properties at import time. This lets one property be known by different names across platforms without coupling adapters to the DB.
- `BookingRecord.property_slug` is resolved by the normalizer (not the adapter) — keeps adapters stateless and DB-free.
- `check_in_date` and `check_out_date` use `sa.Date()` (calendar dates only) — these are never timestamps; using DateTime would risk time-zone confusion.
- `archive_dir` defaults to `"./archive"` and is mounted read-write (not `:ro`) in Docker — the app writes archived CSVs here.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

Operators must update `listing_slug_map` in `config/jay.yaml` and `config/minnie.yaml` with actual platform listing identifiers before running CSV imports:

- For Airbnb: use the listing title as it appears in CSV exports
- For VRBO: use the numeric property ID as it appears in CSV exports

Files contain `CHANGE_ME_AIRBNB_LISTING_TITLE` and `CHANGE_ME_VRBO_PROPERTY_ID` placeholders.

## Next Phase Readiness
- All three database tables exist (migration 002 ready to run with `alembic upgrade head`)
- Canonical Pydantic schemas define the data contracts for all Phase 2 CSV adapters
- `polars` available for high-performance CSV parsing in subsequent plans
- `archive_dir` and `listing_slug_map` config fields available for ingestion pipeline
- Ready to build platform-specific CSV adapters (02-02: Airbnb/VRBO CSV ingestion)

---
*Phase: 02-data-ingestion*
*Completed: 2026-02-27*
