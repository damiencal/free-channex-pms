---
phase: 02-data-ingestion
verified: 2026-02-27T00:00:00Z
status: human_needed
score: 6/6 must-haves verified (automated), 3 human verification items pending
---

# Phase 2: Data Ingestion Verification Report

**Phase Goal:** Real booking and transaction data flows from all three platforms into a unified ledger
**Verified:** 2026-02-27
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can upload an Airbnb Transaction History CSV and see bookings appear with correct guest details and amounts | VERIFIED | `app/ingestion/adapters/airbnb.py` (365 lines): `validate_headers()` + `parse()` with multi-row grouping by Confirmation Code, apostrophe/dollar amount stripping, MM/DD/YYYY date parsing. `POST /ingestion/airbnb/upload` wired to `normalizer.ingest_csv(..., airbnb_adapter, db)`. Upsert writes to `bookings` table. `GET /ingestion/bookings` returns results. |
| 2 | User can upload a VRBO Payments Report CSV and see VRBO reservations normalized to the same BookingRecord schema as Airbnb bookings | VERIFIED | `app/ingestion/adapters/vrbo.py` (366 lines): `validate_headers()` + `parse()` with Reservation ID grouping, `Check In/Check Out` range splitting, `Payable To You` amount parsing. `POST /ingestion/vrbo/upload` wired to `normalizer.ingest_csv(..., vrbo_adapter, db)`. Both Airbnb and VRBO adapters produce `BookingRecord` from `app.ingestion.schemas`. |
| 3 | User can upload a Mercury bank transaction CSV and see bank transactions appear with correct amounts and dates | VERIFIED | `app/ingestion/adapters/mercury.py` (211 lines): `validate_headers()` + `parse()` producing `BankTransactionRecord`. Composite SHA-256 dedup key (`mercury-{hash[:16]}`). `POST /ingestion/mercury/upload` wired to `normalizer.ingest_bank_csv(..., mercury_adapter, db)`. `GET /ingestion/bank-transactions` returns results. |
| 4 | User can manually enter an RVshare booking with all required fields and see it in the unified booking list alongside Airbnb and VRBO bookings | VERIFIED | `POST /ingestion/rvshare/entry` accepts `RVshareEntryRequest` (all required fields: confirmation_code, guest_name, check_in_date, check_out_date, net_amount, property_slug). `normalizer.create_manual_booking()` upserts to the same `bookings` table with `platform="rvshare"`. `GET /ingestion/bookings` returns all platforms together. |
| 5 | Re-importing the same CSV does not create duplicate records | VERIFIED | `normalizer.ingest_csv()` uses PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` (via `sqlalchemy.dialects.postgresql.insert`) on unique constraint `uq_booking_platform_id (platform, platform_booking_id)`. `ingest_bank_csv()` uses same pattern on `unique=True` `transaction_id`. xmax detection distinguishes insert vs. update. |
| 6 | Raw CSV files are archived with timestamp before processing so every import is auditable | VERIFIED | `normalizer.archive_file()` writes to `{archive_dir}/{platform}/YYYY-MM-DD_HH-MM-SS_{filename}` (line 54-58). Archive call at line 182 occurs **before** any `db.execute()` calls (first upsert loop begins at line 188). Same ordering in `ingest_bank_csv()`: archive at line 292, upsert loop starts at line 298. `ImportRun.archive_path` records the path. |

**Score:** 6/6 truths verified (automated structural checks)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/booking.py` | Booking ORM model | VERIFIED | 29 lines. `platform`, `platform_booking_id`, `property_id` (FK), `guest_name`, `check_in_date`, `check_out_date`, `net_amount`, `raw_platform_data`. `UniqueConstraint("platform", "platform_booking_id", name="uq_booking_platform_id")`. |
| `app/models/bank_transaction.py` | BankTransaction ORM model | VERIFIED | 23 lines. `transaction_id` (unique), `date`, `description`, `amount`, `raw_platform_data`. |
| `app/models/import_run.py` | ImportRun ORM model | VERIFIED | 24 lines. `platform`, `filename`, `archive_path`, `inserted_count`, `updated_count`, `skipped_count`, `imported_at`. |
| `app/models/__init__.py` | All models registered for Alembic | VERIFIED | Imports all 4 models (`Property`, `Booking`, `BankTransaction`, `ImportRun`) with `noqa: F401`. |
| `alembic/versions/002_ingestion_tables.py` | Migration creates 3 tables | VERIFIED | 71 lines. Creates `bookings`, `bank_transactions`, `import_runs` with all columns and constraints. `down_revision = "001"` chains correctly. Downgrade drops all 3 tables. |
| `app/ingestion/schemas.py` | Pydantic canonical schemas | VERIFIED | 68 lines. `BookingRecord`, `BankTransactionRecord`, `RVshareEntryRequest` — all fields present and typed. |
| `app/ingestion/normalizer.py` | Core pipeline: archive, upsert, ImportRun | VERIFIED | 424 lines. `ingest_csv()`, `ingest_bank_csv()`, `create_manual_booking()`, `archive_file()`, `resolve_property_id()`, `build_listing_lookup()`. Full implementations, no stubs. |
| `app/ingestion/adapters/airbnb.py` | Airbnb CSV adapter | VERIFIED | 365 lines. `validate_headers()` + `parse()` with multi-row grouping, apostrophe/dollar stripping, MM/DD/YYYY parsing. Imports from `app.ingestion.schemas`. |
| `app/ingestion/adapters/vrbo.py` | VRBO CSV adapter | VERIFIED | 366 lines. `validate_headers()` + `parse()` with Reservation ID grouping, Check In/Check Out range parsing, Payable To You amount parsing. Imports from `app.ingestion.schemas`. |
| `app/ingestion/adapters/mercury.py` | Mercury bank CSV adapter | VERIFIED | 211 lines. `validate_headers()` + `parse()` with composite SHA-256 dedup key. Imports from `app.ingestion.schemas`. |
| `app/api/ingestion.py` | All 7 API endpoints | VERIFIED | 282 lines. All 7 routes present and wired: `POST /ingestion/airbnb/upload`, `POST /ingestion/vrbo/upload`, `POST /ingestion/mercury/upload`, `POST /ingestion/rvshare/entry`, `GET /ingestion/history`, `GET /ingestion/bookings`, `GET /ingestion/bank-transactions`. |
| `app/main.py` | Ingestion router registered | VERIFIED | `from app.api.ingestion import router as ingestion_router` at line 22, `app.include_router(ingestion_router)` at line 87. |
| `app/config.py` | `archive_dir` + `listing_slug_map` in config schema | VERIFIED | `archive_dir: str = "./archive"` (default in `AppConfig`). `listing_slug_map: dict[str, str] = {}` in `PropertyConfig`. |
| `config/base.yaml` | `archive_dir` set in config file | VERIFIED | `archive_dir: "./archive"` present. |
| `config/jay.yaml`, `config/minnie.yaml` | `listing_slug_map` keys present | PARTIAL | Keys present with placeholder values `CHANGE_ME_AIRBNB_LISTING_TITLE` / `CHANGE_ME_VRBO_PROPERTY_ID`. Structure is correct; operator must populate real listing identifiers before first production import. |
| `pyproject.toml` | `polars` and `python-multipart` dependencies | VERIFIED | Both present in dependencies list. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `POST /ingestion/airbnb/upload` | `normalizer.ingest_csv()` | Direct call with `airbnb_adapter` | WIRED | `api/ingestion.py:60` calls `normalizer.ingest_csv(raw_bytes, file.filename, "airbnb", airbnb_adapter, db)` |
| `POST /ingestion/vrbo/upload` | `normalizer.ingest_csv()` | Direct call with `vrbo_adapter` | WIRED | `api/ingestion.py:85` calls `normalizer.ingest_csv(raw_bytes, file.filename, "vrbo", vrbo_adapter, db)` |
| `POST /ingestion/mercury/upload` | `normalizer.ingest_bank_csv()` | Direct call with `mercury_adapter` | WIRED | `api/ingestion.py:110` calls `normalizer.ingest_bank_csv(raw_bytes, file.filename, mercury_adapter, db)` |
| `POST /ingestion/rvshare/entry` | `normalizer.create_manual_booking()` | Direct call with `RVshareEntryRequest` | WIRED | `api/ingestion.py:138` calls `normalizer.create_manual_booking(entry, db)` |
| `normalizer.ingest_csv()` | `bookings` table | `pg_insert(Booking).on_conflict_do_update(...)` | WIRED | Lines 199-218: upsert with conflict target `["platform", "platform_booking_id"]` |
| `normalizer.ingest_bank_csv()` | `bank_transactions` table | `pg_insert(BankTransaction).on_conflict_do_update(...)` | WIRED | Lines 306-324: upsert with conflict target `["transaction_id"]` |
| `archive_file()` | timestamped file on disk | `Path.write_bytes()` before upsert loop | WIRED | Archive call at line 182 precedes first `db.execute()` at line 212 in `ingest_csv()`; archive at line 292 precedes first execute at line 318 in `ingest_bank_csv()` |
| `GET /ingestion/bookings` | `bookings` table | `select(Booking, Property.slug).join(Property)` | WIRED | Lines 204-228: joined query, returns all platforms; `platform` and `property_slug` filters available |
| `GET /ingestion/bank-transactions` | `bank_transactions` table | `select(BankTransaction).order_by(...)` | WIRED | Lines 248-260: direct query with pagination |
| `airbnb_adapter` | `app.ingestion.schemas.BookingRecord` | `from app.ingestion.schemas import BookingRecord` | WIRED | `airbnb.py:30` |
| `vrbo_adapter` | `app.ingestion.schemas.BookingRecord` | `from app.ingestion.schemas import BookingRecord` | WIRED | `vrbo.py:32` |
| `mercury_adapter` | `app.ingestion.schemas.BankTransactionRecord` | `from app.ingestion.schemas import BankTransactionRecord` | WIRED | `mercury.py:24` |

---

## Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| INGS-01: Import Airbnb CSV with schema validation | SATISFIED | `airbnb_adapter.validate_headers()` + `parse()` with halt-and-report error collection. |
| INGS-02: Import VRBO CSV with schema validation | SATISFIED | `vrbo_adapter.validate_headers()` + `parse()` with halt-and-report error collection. |
| INGS-03: Manual entry of RVshare bookings | SATISFIED | `POST /ingestion/rvshare/entry` with `RVshareEntryRequest` schema, `normalizer.create_manual_booking()`. |
| INGS-04: Import Mercury bank CSV with schema validation | SATISFIED | `mercury_adapter.validate_headers()` + `parse()` with halt-and-report error collection. |
| INGS-05: Validate CSV headers and data types on every import | SATISFIED | `validate_headers()` called first in all three upload endpoints; `parse()` validates each row with row-number error attribution. |
| INGS-06: Archive raw CSV files before processing | SATISFIED | `archive_file()` writes timestamped copy to `{archive_dir}/{platform}/YYYY-MM-DD_HH-MM-SS_{filename}` before any DB writes. `ImportRun.archive_path` records path. |
| INGS-07: Normalize all platform data into unified booking and transaction schema | SATISFIED | All adapters produce `BookingRecord` (Airbnb, VRBO, RVshare) or `BankTransactionRecord` (Mercury) from `app.ingestion.schemas`. Both write to the same `bookings` / `bank_transactions` tables. |

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `app/ingestion/adapters/airbnb.py` (lines 14-18) | `Column name verification status: SYNTHETIC — headers UNVERIFIED against a real Airbnb export` | WARNING | Adapter functional but column names (`Guest`, `Listing`, `Start Date`, `End Date`) may differ in real Airbnb exports. Code works correctly with the synthetic fixture; production import may fail header validation or silently use wrong data if columns are renamed. Documented and expected. |
| `app/ingestion/adapters/mercury.py` (lines 9-16) | `Source: Synthetic — UNVERIFIED, LOW confidence` | WARNING | Same concern as Airbnb — Mercury column names are a best-guess. `Date`, `Description`, `Amount` are the three required headers; these are common enough that risk is lower. |
| `app/ingestion/adapters/vrbo.py` (line 14) | `Confidence: MEDIUM — verified from official docs; must confirm against real export` | INFO | VRBO headers sourced from official help documentation. Medium confidence is the highest achievable without a real export. Risk is acceptable. |
| `config/jay.yaml`, `config/minnie.yaml` | `listing_slug_map` contains `CHANGE_ME_*` placeholder keys | WARNING | Placeholder listing identifiers mean any real CSV upload will fail the `listing not found in listing_slug_map` error in `parse()`. Operator must replace `CHANGE_ME_AIRBNB_LISTING_TITLE` / `CHANGE_ME_VRBO_PROPERTY_ID` with real identifiers before first production import. This is a config-data concern, not a code gap. |

No blocker anti-patterns found. No empty implementations, no `return {}` stubs, no TODO/FIXME markers in production paths.

---

## Human Verification Required

The following items cannot be verified programmatically. Automated structural checks all pass; these require a real CSV export or live system test to confirm end-to-end behavior.

### 1. Real Airbnb CSV Column Names

**Test:** Export a real Airbnb Transaction History CSV from the Airbnb host dashboard (Earnings > Transaction History > Download CSV). Compare the actual column headers against `REQUIRED_HEADERS` in `app/ingestion/adapters/airbnb.py`: `{"Date", "Type", "Confirmation Code", "Listing", "Amount"}`. Also check whether check-in/check-out columns are named `Start Date` / `End Date` or something else (e.g., `Check In` / `Check Out`).
**Expected:** Headers match exactly, OR differ and the constants in `airbnb.py` are updated to match.
**Why human:** No real Airbnb CSV was available at implementation time. The synthetic fixture was built from community forum research. Column names are the single most likely breakage point before production use.

### 2. Real Mercury Bank CSV Column Names

**Test:** Export a real Mercury bank transaction CSV (Mercury dashboard > Accounts > [Account] > Transactions > Export CSV — use the generic format, not QuickBooks/NetSuite). Compare against `REQUIRED_HEADERS = {"Date", "Description", "Amount"}`. Also check whether a native transaction ID column exists (would enable replacing the composite SHA-256 dedup key).
**Expected:** Headers `Date`, `Description`, `Amount` are present, or the constants in `mercury.py` are updated to match.
**Why human:** Mercury generic CSV format could not be confirmed without a real export. LOW confidence was assigned during research.

### 3. End-to-End Import and Bookings List

**Test:** With Docker running and properties configured (real listing identifiers in `config/jay.yaml` and `config/minnie.yaml` `listing_slug_map`): (a) upload the Airbnb sample CSV to `POST /ingestion/airbnb/upload`, (b) upload the VRBO sample CSV to `POST /ingestion/vrbo/upload`, (c) upload the Mercury sample CSV to `POST /ingestion/mercury/upload`, (d) POST a manual RVshare entry to `POST /ingestion/rvshare/entry`, (e) call `GET /ingestion/bookings` and confirm all three booking platforms appear with correct guest names, check-in dates, and net amounts, (f) call `GET /ingestion/bank-transactions` and confirm Mercury transactions appear with correct amounts and dates, (g) re-upload the same Airbnb CSV and confirm `inserted=0, updated=N` (no duplicates).
**Expected:** All platforms present in unified list, amounts correct, re-import shows updated count not inserted.
**Why human:** Requires a running PostgreSQL instance, real or valid synthetic listing identifier config, and end-to-end execution — not verifiable through static analysis alone.

---

## Summary

Phase 2 infrastructure is fully implemented with no structural gaps. All six observable truths are supported by substantive, wired artifacts:

- Three ORM models (`Booking`, `BankTransaction`, `ImportRun`) exist, are correctly defined, and are registered in `models/__init__.py` for Alembic detection.
- Alembic migration `002_ingestion_tables.py` creates all three tables with proper constraints, chains from `001`, and has a working downgrade.
- The normalizer implements the complete pipeline: archive-before-write, PostgreSQL `ON CONFLICT DO UPDATE` upsert with xmax duplicate detection, and ImportRun recording.
- All three CSV adapters (`airbnb`, `vrbo`, `mercury`) have `validate_headers()` and `parse()` with real implementations — no stubs. All import their schemas from the shared `app.ingestion.schemas` module.
- The API layer exposes all seven endpoints (`/airbnb/upload`, `/vrbo/upload`, `/mercury/upload`, `/rvshare/entry`, `/history`, `/bookings`, `/bank-transactions`) and the ingestion router is registered in `main.py`.
- Archive function writes to a timestamped path before any database writes.

The three human verification items are pre-production concerns, not code gaps: two require confirming CSV column names against real platform exports (acknowledged as unverified during implementation), and one requires a live system test with a running database.

---

_Verified: 2026-02-27_
_Verifier: Claude (gsd-verifier)_
