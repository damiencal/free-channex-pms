---
phase: 02-data-ingestion
plan: "04"
subsystem: ingestion
tags: [polars, csv, vrbo, adapter, booking, property-resolution]

# Dependency graph
requires:
  - phase: 02-data-ingestion
    provides: BookingRecord Pydantic schema, PropertyConfig.listing_slug_map, normalizer.ingest_csv pipeline

provides:
  - VRBO Payments Report CSV adapter (validate_headers + parse) in app/ingestion/adapters/vrbo.py
  - Multi-row payout grouping by Reservation ID with net amount accumulation
  - Check In/Check Out date range parsing ("MM/DD/YYYY - MM/DD/YYYY" format)
  - VRBO Property ID resolution to property_slug via listing_slug_map
  - Synthetic VRBO sample CSV fixture with 29 MEDIUM-confidence columns (from official VRBO docs)
  - VRBO_CSV_NOTES.md documenting header source, confidence, and verification protocol

affects:
  - 02-05 (Mercury adapter follows same adapter pattern established here)
  - 02-06 (API endpoints will wire vrbo adapter into normalizer.ingest_csv)
  - 03-accounting (reads bookings table populated by VRBO imports)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - VRBO multi-row payout grouping: _ReservationGroup accumulator class sums Payable To You across rows sharing a Reservation ID
    - Check In/Check Out single-column range parsing: split on " - " separator, parse each half independently
    - Listing lookup built lazily at parse time from get_config().properties (no module-level state)

key-files:
  created:
    - app/ingestion/adapters/vrbo.py
    - tests/fixtures/vrbo_sample.csv
    - tests/fixtures/VRBO_CSV_NOTES.md
  modified:
    - app/ingestion/adapters/__init__.py

key-decisions:
  - "VRBO adapter uses _ReservationGroup accumulator class (not Polars group_by) for multi-row grouping — gives clear per-row error messages with row numbers, supports field fallback (fill empty guest_name from later rows)"
  - "Check In/Check Out split on ' - ' (space-dash-space) — assumed from VRBO docs; must verify against real export before production"
  - "REQUIRED_HEADERS is a 5-column frozenset (subset of all 29 VRBO columns) — only fields needed to build BookingRecord are required; extras ignored"
  - "Error messages include 'VRBO Payments Report CSV' in validate_headers — same fail-fast pattern as Airbnb adapter"

patterns-established:
  - "VRBO adapter pattern: same validate_headers/parse contract as Airbnb adapter — both return (list[BookingRecord], list[str])"
  - "Row-level error collection: errors accumulated across all rows before returning — halt-and-report, not fail-fast on first bad row"
  - "Property ID resolution at parse time: listing_lookup built by merging all PropertyConfig.listing_slug_map dicts"

# Metrics
duration: 4min
completed: 2026-02-27
---

# Phase 2 Plan 04: VRBO CSV Adapter Summary

**VRBO Payments Report CSV adapter with Reservation ID-based payout grouping, date range parsing, and VRBO Property ID-to-slug resolution — producing canonical BookingRecord objects for the normalizer**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-27T18:49:24Z
- **Completed:** 2026-02-27T18:53:04Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created VRBO Payments Report CSV adapter with validate_headers() (frozenset check, descriptive error) and parse() (multi-row grouping by Reservation ID, amount accumulation, date range parsing)
- Implemented _ReservationGroup accumulator to correctly sum "Payable To You" across multiple payment-type rows per reservation (HA-12345678: 250.00 + 50.00 = 300.00, HA-55443322: 195.00 + 75.00 = 270.00)
- Created synthetic VRBO sample CSV with 29 MEDIUM-confidence columns (from official VRBO help docs), 6 rows, 4 unique Reservation IDs, 2 property IDs
- Documented header source, confidence level, and production verification protocol in VRBO_CSV_NOTES.md

## Task Commits

Each task was committed atomically:

1. **Task 1: Inspect actual VRBO CSV and create sample fixture** - `bd3c4d7` (feat)
2. **Task 2: Implement VRBO CSV adapter with header validation and payout grouping** - `6f79588` (feat)

**Plan metadata:** _(pending final commit)_

## Files Created/Modified
- `app/ingestion/adapters/vrbo.py` - VRBO adapter (366 lines): validate_headers, parse, _ReservationGroup, _normalize_amount, _parse_date, _parse_check_in_out, _build_listing_lookup
- `app/ingestion/adapters/__init__.py` - Updated to document vrbo adapter in module docstring
- `tests/fixtures/vrbo_sample.csv` - Synthetic VRBO CSV: 6 rows, 4 reservations, 2 properties, multi-row grouping exercised
- `tests/fixtures/VRBO_CSV_NOTES.md` - Header source documentation and production verification protocol

## Decisions Made
- **_ReservationGroup class over Polars group_by**: Row-by-row accumulation gives precise row numbers in error messages and supports filling empty guest_name from later rows; Polars group_by would require materializing the full dataset before any error can be attributed to a specific row.
- **REQUIRED_HEADERS as 5-column subset**: Only the 5 columns needed to construct a BookingRecord are required. The remaining 24 VRBO columns are present in the export but not needed by the adapter.
- **Check In/Check Out split on " - "**: Single-column date range assumed from VRBO documentation. If the actual export uses a different separator, only `_parse_check_in_out()` needs updating.
- **Property resolution error message format**: "Row N: VRBO Property ID 'X' not found in any property's listing_slug_map" — matches the exact spec from the plan and gives the operator the config key they need to add.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

Operators must update `listing_slug_map` in `config/jay.yaml` and `config/minnie.yaml` with their actual VRBO Property IDs before running VRBO CSV imports:

```yaml
# config/jay.yaml
listing_slug_map:
  "87654321": "jay"  # Replace with actual VRBO Property ID from your Payments Report
```

VRBO Property IDs appear in the "Property ID" column of your Payments Report CSV. The fixture uses `87654321` and `11223344` as examples.

## Next Phase Readiness
- VRBO adapter is importable and passes all plan verification criteria
- Multi-row grouping tested: 6 CSV rows collapse to 4 BookingRecords with correct net amounts
- Adapter follows exact same contract as Airbnb adapter — drop-in compatible with normalizer.ingest_csv
- Ready for 02-06 (API endpoints) to wire VRBO adapter into the ingestion pipeline
- Check In/Check Out date format must be verified against a real VRBO export before production use

---
*Phase: 02-data-ingestion*
*Completed: 2026-02-27*
