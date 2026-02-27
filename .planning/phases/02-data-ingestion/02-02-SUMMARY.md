---
phase: 02-data-ingestion
plan: "02"
subsystem: ingestion
tags: [polars, sqlalchemy, postgresql, upsert, archival, import-run, normalizer]

# Dependency graph
requires:
  - phase: 02-data-ingestion/02-01
    provides: Booking, BankTransaction, ImportRun ORM models; BookingRecord, BankTransactionRecord, RVshareEntryRequest Pydantic schemas; archive_dir AppConfig field; listing_slug_map PropertyConfig field
  - phase: 01-foundation
    provides: Base ORM declarative base, get_db(), get_config(), Property model

provides:
  - app/ingestion/normalizer.py with ingest_csv(), ingest_bank_csv(), create_manual_booking()
  - Archive pipeline: raw bytes written to {archive_dir}/{platform}/YYYY-MM-DD_HH-MM-SS_{filename} before any DB writes
  - Upsert pipeline: pg_insert ON CONFLICT DO UPDATE with RETURNING xmax for insert/update detection
  - ImportRun recording for every successful import (CSV and manual)
  - Property slug resolution with module-level cache and clear error on missing slug
  - Listing lookup helper: builds flat identifier->slug map from all PropertyConfig.listing_slug_map dicts

affects:
  - 02-03 (bank transaction adapter calls ingest_bank_csv)
  - 02-04 (API endpoints call ingest_csv, ingest_bank_csv, create_manual_booking)
  - All future Phase 2 adapters use this pipeline

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Normalizer pattern: adapters produce canonical Pydantic records; normalizer resolves IDs, archives, upserts, records ImportRun
    - xmax trick for insert/update detection: RETURNING xmax — xmax == 0 is insert, xmax > 0 is update
    - Archive-first ordering: raw bytes archived before any DB writes so failed imports still leave a trace
    - Halt-and-report validation: all slug resolution errors collected before any DB write

key-files:
  created:
    - app/ingestion/normalizer.py
  modified: []

key-decisions:
  - "archive_file() uses Path.write_bytes() not shutil.copy2() — source is in-memory bytes from upload, not a file path"
  - "resolve_property_id() uses module-level dict cache — only 2 properties exist; avoids repeated SELECT per record"
  - "All on_conflict_do_update set_ dicts explicitly include updated_at=func.now() — ORM onupdate hooks are not triggered by pg_insert statements"
  - "build_listing_lookup() is a standalone helper — not called by ingest_csv directly, available for adapter use when resolving listing identifiers to property slugs"
  - "create_manual_booking() uses archive_path='N/A' — no file involved; ImportRun still recorded for audit consistency"

patterns-established:
  - "Single pipeline entry point: all CSV ingestion flows through ingest_csv or ingest_bank_csv; adapters never write to DB"
  - "Validation before archive before write: headers -> rows -> slug resolution -> archive -> upsert"
  - "Explicit updated_at in set_ dict is mandatory for all upserts — not optional"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 2 Plan 02: Normalizer Summary

**Polars CSV-to-PostgreSQL ingestion pipeline with pre-write archival, xmax-based insert/update detection, and per-import ImportRun recording via SQLAlchemy pg_insert ON CONFLICT DO UPDATE**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-27T18:47:16Z
- **Completed:** 2026-02-27T18:49:19Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `app/ingestion/normalizer.py` implementing the full CSV ingestion pipeline as a single orchestration module — adapters produce records, normalizer writes to the database
- `ingest_csv()`: reads CSV with Polars (all columns as Utf8, no auto-date parsing), delegates validation to adapter, archives raw bytes before any DB write, upserts Booking records with pg_insert and RETURNING xmax for insert/update counts, commits, records ImportRun
- `ingest_bank_csv()`: same pipeline for Mercury bank transactions targeting BankTransaction with `transaction_id` as single-column conflict key
- `create_manual_booking()`: resolves property slug, upserts Booking for RVshare manual entries, records ImportRun with `archive_path="N/A"`
- Private helpers: `archive_file()` (timestamped path, platform subdir), `resolve_property_id()` (module-level cache, raises ValueError on missing), `build_listing_lookup()` (flat identifier->slug map from all PropertyConfig listing maps)

## Task Commits

Each task was committed atomically:

1. **Task 1: Build normalizer with archive, upsert, and ImportRun recording** - `f05a903` (feat)

**Plan metadata:** _(pending final commit)_

## Files Created/Modified
- `app/ingestion/normalizer.py` - Core ingestion pipeline: archive, validate, upsert Booking/BankTransaction, record ImportRun; exports ingest_csv, ingest_bank_csv, create_manual_booking

## Decisions Made
- `archive_file()` uses `Path.write_bytes()` not `shutil.copy2()` — source is already in-memory bytes from the upload, not a path on disk.
- `resolve_property_id()` uses a module-level `dict` cache — there are only 2 properties; caching avoids one `SELECT` per record during batch imports.
- All `on_conflict_do_update` `set_` dicts explicitly include `updated_at: func.now()` — SQLAlchemy ORM `onupdate` hooks are bypassed by core `pg_insert` statements (documented pitfall from RESEARCH.md).
- `create_manual_booking()` records `archive_path="N/A"` in the ImportRun — no file is involved in manual entry, but ImportRun is always created for audit consistency.
- `build_listing_lookup()` is a standalone helper exported from the module — not called internally by `ingest_csv` (adapters receive the resolved `property_slug` already), but available for adapters that need to resolve a listing identifier from a CSV row.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required. Adapters that call these functions will be built in 02-03 and 02-04.

## Next Phase Readiness
- `ingest_csv()`, `ingest_bank_csv()`, and `create_manual_booking()` are ready for use by CSV adapters and API endpoints
- All three functions importable from `app.ingestion.normalizer`
- Property slug resolution raises `ValueError` with a clear message — API endpoints should convert to HTTP 422
- Archive directory is created lazily on first import — no manual setup needed
- Ready for 02-03 (Airbnb/VRBO/Mercury CSV adapters that call these functions)

---
*Phase: 02-data-ingestion*
*Completed: 2026-02-27*
