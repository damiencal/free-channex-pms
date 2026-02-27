---
phase: 02-data-ingestion
plan: "03"
subsystem: ingestion
tags: [polars, csv, airbnb, adapter, decimal, booking-record, listing-slug-map]

# Dependency graph
requires:
  - phase: 02-data-ingestion
    plan: "01"
    provides: BookingRecord Pydantic schema, listing_slug_map on PropertyConfig, get_config() singleton

provides:
  - app/ingestion/adapters/__init__.py: adapters package with documented public protocol
  - app/ingestion/adapters/airbnb.py: validate_headers() + parse() for Airbnb Transaction History CSV
  - tests/fixtures/airbnb_sample.csv: 10-row synthetic CSV with 4 confirmation codes, 2 listings
  - tests/fixtures/AIRBNB_CSV_NOTES.md: header verification status and real-export instructions

affects:
  - 02-04 (normalizer pipeline calls adapter.parse(); contract is (list[BookingRecord], list[str]))
  - 02-05 (same adapter pattern used for VRBO and Mercury — see vrbo.py and mercury.py)
  - Testing phase — fixture is the test data for Airbnb adapter unit tests

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Adapter pattern with frozenset REQUIRED_HEADERS constants for fail-fast header validation"
    - "Halt-and-report error collection: all row errors accumulated before returning ([], errors)"
    - "Multi-row grouping by confirmation code: net amount = sum of all row amounts; first non-empty guest/dates used"
    - "Apostrophe/dollar/comma amount normalization: strip with regex, preserve sign, parse as Decimal"
    - "listing_slug_map resolution inside adapter via get_config() — adapters stateless and DB-free"

key-files:
  created:
    - app/ingestion/adapters/__init__.py
    - app/ingestion/adapters/airbnb.py
    - tests/fixtures/airbnb_sample.csv
    - tests/fixtures/AIRBNB_CSV_NOTES.md
  modified:
    - tests/fixtures/airbnb_sample.csv (updated with Start Date/End Date columns)

key-decisions:
  - "Airbnb CSV column names are UNVERIFIED (synthetic fixture) — real export must be inspected before production"
  - "Start Date / End Date column names are best-guess — most likely to differ from real export"
  - "Empty date cells are allowed (payout/fee rows often omit dates) — adapter takes first non-None date per group"
  - "Missing listing in listing_slug_map produces an error (not silent skip) — operator must fix YAML config"
  - "REQUIRED_HEADERS is a frozenset of 5 columns; Start Date / End Date are not required (may be absent)"

patterns-established:
  - "adapter.validate_headers(df) must be called before adapter.parse(df) — this is normalizer's responsibility"
  - "COL_* constants at top of each adapter module — single place to update when platform renames columns"
  - "All adapter parse() functions return tuple[list[Record], list[str]] — (records, errors) contract"

# Metrics
duration: 4min
completed: 2026-02-27
---

# Phase 2 Plan 03: Airbnb CSV Adapter Summary

**Airbnb Transaction History CSV adapter with validate_headers(), apostrophe/dollar amount normalization, MM/DD/YYYY date parsing, and multi-row Confirmation Code grouping into net-amount BookingRecords**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-27T18:48:14Z
- **Completed:** 2026-02-27T18:52:00Z
- **Tasks:** 2
- **Files modified:** 4 created, 1 updated

## Accomplishments

- Created `app/ingestion/adapters/airbnb.py` (365 lines) with `validate_headers()` and `parse()` implementing the full adapter contract
- `validate_headers()` fails immediately with a descriptive message listing expected vs. actual vs. missing headers when any of the 5 required columns are absent
- `parse()` groups 10 fixture rows (4 confirmation codes, 3 rows per some bookings) into 4 BookingRecords, correctly summing net amounts (e.g., HM2468013: $310.00 + -$15.50 + $254.50 = $549.00)
- Amount normalization handles all Airbnb quirks: `'$180.00` → 180.00, `'-$15.50` → -15.50, `-$50.00` → -50.00, `$1,234.56` → 1234.56
- Synthetic CSV fixture created at `tests/fixtures/airbnb_sample.csv` with 10 rows across 4 bookings and 2 listings; documented as UNVERIFIED in `AIRBNB_CSV_NOTES.md`

## Task Commits

Each task was committed atomically:

1. **Task 1: Inspect actual Airbnb CSV and create sample fixture** - `67ab055` (chore)
2. **Task 2: Implement Airbnb CSV adapter with header validation and multi-row grouping** - `6f79588` (feat)

**Plan metadata:** _(pending final commit)_

## Files Created/Modified

- `app/ingestion/adapters/__init__.py` - Adapters package init with protocol documentation
- `app/ingestion/adapters/airbnb.py` - Airbnb adapter: validate_headers, parse, _normalize_amount, _parse_date
- `tests/fixtures/airbnb_sample.csv` - 10-row synthetic Airbnb CSV with 4 confirmation codes, 2 listings, apostrophe amounts, US dates
- `tests/fixtures/AIRBNB_CSV_NOTES.md` - Header verification status, real-export instructions, update protocol

## Decisions Made

- **Airbnb column names are UNVERIFIED**: No real Airbnb Transaction History CSV was found on this machine. The fixture and column constants (`COL_DATE`, `COL_GUEST`, `COL_START_DATE`, etc.) are synthetic guesses documented with "UNVERIFIED" comments. The `Start Date` / `End Date` column names are the most likely to differ from a real export.
- **Empty date cells are not errors**: Payout and fee rows in Airbnb CSVs typically omit check-in/out dates. The adapter silently skips empty date cells and takes the first non-None date from the group. If no row in the group has a start or end date, that produces an error.
- **REQUIRED_HEADERS is 5 columns only**: `Start Date` and `End Date` are not required for `validate_headers()` to pass because they may be absent or named differently in real exports. This keeps header validation from failing valid CSVs that store dates differently.
- **listing_slug_map errors abort the group**: If a listing name has no entry in any property's `listing_slug_map`, that confirmation code group produces an error and the entire import aborts (halt-and-report). Operator must add the listing identifier to the YAML config.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated fixture to include Start Date / End Date columns**

- **Found during:** Task 2 verification
- **Issue:** Initial fixture (Task 1) did not include `Start Date` / `End Date` columns, causing all 4 groups to produce "no valid Start Date" errors when tested with the adapter
- **Fix:** Re-created `tests/fixtures/airbnb_sample.csv` with `Start Date` and `End Date` columns; Reservation rows have dates, Payout/Fee rows have empty date cells
- **Files modified:** `tests/fixtures/airbnb_sample.csv`
- **Verification:** `parse()` produced 4 BookingRecords with correct dates from updated fixture
- **Committed in:** `6f79588` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fixture needed Start/End date columns for the adapter to function. No scope creep.

## Issues Encountered

- Initial fixture CSV had no `Start Date` / `End Date` columns, discovered during adapter verification. Fixture was updated to include them. This exposed that the column names are unverified — real Airbnb exports may name these columns differently.

## User Setup Required

Before running Airbnb CSV imports in production:
1. Export a real Airbnb Transaction History CSV from the host account
2. Compare actual column headers against the `COL_*` constants in `app/ingestion/adapters/airbnb.py`
3. If column names differ, update the constants
4. Replace `tests/fixtures/airbnb_sample.csv` with real data (redact guest PII)
5. Update `AIRBNB_CSV_NOTES.md` source line to "Real export" with date
6. Add actual listing names to `listing_slug_map` in `config/jay.yaml` and `config/minnie.yaml`

## Next Phase Readiness

- Adapter is importable: `from app.ingestion.adapters.airbnb import validate_headers, parse`
- Adapter implements the `(validate_headers, parse)` contract expected by `normalizer.ingest_csv()`
- `parse()` returns `(list[BookingRecord], list[str])` — normalizer can call it directly
- Column names are **UNVERIFIED** — production use requires real CSV inspection
- `listing_slug_map` entries in `jay.yaml` / `minnie.yaml` still have `CHANGE_ME` placeholders (from 02-01)

---
*Phase: 02-data-ingestion*
*Completed: 2026-02-27*
