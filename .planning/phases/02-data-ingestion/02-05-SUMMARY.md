---
phase: 02-data-ingestion
plan: "05"
subsystem: ingestion
tags: [polars, mercury, csv, bank-transactions, deduplication, composite-key, sha256]

# Dependency graph
requires:
  - phase: 02-data-ingestion/02-01
    provides: BankTransactionRecord Pydantic schema, polars installed, ingestion package structure

provides:
  - app/ingestion/adapters/mercury.py with validate_headers() and parse() functions
  - Composite-key deduplication strategy for Mercury bank transactions ("mercury-" + sha256[:16])
  - tests/fixtures/mercury_sample.csv — 7-row synthetic sample for testing
  - tests/fixtures/MERCURY_CSV_NOTES.md — format documentation and verification checklist

affects:
  - 02-06+ (ingestion endpoint plans will wire mercury adapter into normalizer/API)
  - 03-accounting (bank reconciliation reads bank_transactions table fed by this adapter)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Adapter pattern: validate_headers(df) + parse(df) -> (records, errors) matching all other platform adapters
    - Composite key deduplication: sha256(date|amount|description)[:16] prefixed with "mercury-" when no native ID available
    - Halt-and-report error collection: row errors accumulated; caller decides to abort or continue

key-files:
  created:
    - app/ingestion/adapters/mercury.py
    - tests/fixtures/mercury_sample.csv
    - tests/fixtures/MERCURY_CSV_NOTES.md
  modified: []

key-decisions:
  - "Mercury dedup uses composite key (Date+Amount+Description hash) — generic Mercury CSV has no native transaction ID column; COL_TRANSACTION_ID constant is commented in source for easy update when real export confirms a native ID"
  - "REQUIRED_HEADERS = {Date, Description, Amount} only — Running Balance, Category, Account, Bank Name are ignored (optional extra columns Mercury includes)"
  - "Sample CSV is synthetic (LOW confidence) — MERCURY_CSV_NOTES.md documents verification checklist for when real export is obtained"

patterns-established:
  - "Mercury adapter follows identical API surface as other adapters: validate_headers(df) + parse(df) -> tuple[list[BankTransactionRecord], list[str]]"
  - "Amount parsing strips $, commas; preserves sign convention: positive=credit, negative=debit"
  - "Date parsing tries MM/DD/YYYY, M/D/YYYY, ISO in order with graceful per-row error"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 2 Plan 05: Mercury CSV Adapter Summary

**Mercury bank CSV adapter with composite-key deduplication (sha256 of Date+Amount+Description), amount/date parsing, and row-level error collection; synthetic fixture documents format assumptions pending real export verification**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T18:50:03Z
- **Completed:** 2026-02-27T18:52:04Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created tests/fixtures/mercury_sample.csv (7 rows, mix of credits and debits with realistic descriptions)
- Created tests/fixtures/MERCURY_CSV_NOTES.md documenting synthetic source, dedup strategy, column assumptions, and verification checklist
- Implemented app/ingestion/adapters/mercury.py (211 lines) with validate_headers() and parse() matching the adapter pattern established in 02-01

## Task Commits

Each task was committed atomically:

1. **Task 1: Inspect actual Mercury CSV and create sample fixture** - `9060ef7` (chore)
2. **Task 2: Implement Mercury CSV adapter with header validation and transaction deduplication** - `aa36d38` (feat)

**Plan metadata:** _(pending final commit)_

## Files Created/Modified
- `app/ingestion/adapters/mercury.py` - Mercury CSV adapter: validate_headers(), parse(), _generate_transaction_id(), _parse_date(), _parse_amount()
- `tests/fixtures/mercury_sample.csv` - 7-row synthetic Mercury CSV (Date, Description, Amount, Running Balance, Category, Account, Bank Name)
- `tests/fixtures/MERCURY_CSV_NOTES.md` - Format documentation: source, dedup strategy, date/amount conventions, verification checklist

## Decisions Made

- **Composite key deduplication:** Mercury's generic CSV export does not include a native transaction ID column (based on research in 02-RESEARCH.md — "critical uncertainty"). The adapter generates `mercury-{sha256(date|amount|description)[:16]}`. The `COL_TRANSACTION_ID` constant is left commented in the source file so it's trivial to activate when a real Mercury export is inspected and a native ID column is confirmed.
- **REQUIRED_HEADERS is minimal:** Only `Date`, `Description`, and `Amount` are required. Extra columns Mercury may include (Running Balance, Category, Account, Bank Name) are ignored — validate_headers() does a subset check, not an equality check.
- **Synthetic fixture (LOW confidence):** No real Mercury CSV was found on disk during execution. MERCURY_CSV_NOTES.md documents this clearly and provides a verification checklist. The adapter's column name constants are isolated so updating them requires changing one line.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None for this adapter alone. When connecting to the ingestion endpoint (future plan), operators will upload their Mercury CSV. Before that:

1. Export a real Mercury CSV from the Mercury dashboard (generic format, not QuickBooks/NetSuite)
2. Compare column headers against `REQUIRED_HEADERS` in `app/ingestion/adapters/mercury.py`
3. Follow the verification checklist in `tests/fixtures/MERCURY_CSV_NOTES.md`
4. If a native transaction ID column exists, uncomment `COL_TRANSACTION_ID` and update `_generate_transaction_id()` to read from it

## Next Phase Readiness
- Mercury adapter complete; importable as `from app.ingestion.adapters.mercury import validate_headers, parse`
- Follows identical adapter API as other platform adapters — ready for normalizer integration
- Dedup strategy documented; composite key stable unless Mercury changes transaction descriptions
- Real Mercury CSV inspection still needed before production use — see MERCURY_CSV_NOTES.md

---
*Phase: 02-data-ingestion*
*Completed: 2026-02-27*
