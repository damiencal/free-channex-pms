---
phase: 02-data-ingestion
plan: "06"
subsystem: api
tags: [fastapi, sqlalchemy, csv, UploadFile, APIRouter, airbnb, vrbo, mercury, rvshare]

# Dependency graph
requires:
  - phase: 02-02
    provides: normalizer with ingest_csv, ingest_bank_csv, create_manual_booking
  - phase: 02-03
    provides: airbnb adapter (validate_headers, parse)
  - phase: 02-04
    provides: vrbo adapter (validate_headers, parse)
  - phase: 02-05
    provides: mercury adapter (validate_headers, parse)
provides:
  - POST /ingestion/airbnb/upload — Airbnb CSV upload endpoint
  - POST /ingestion/vrbo/upload — VRBO CSV upload endpoint
  - POST /ingestion/mercury/upload — Mercury bank CSV upload endpoint
  - POST /ingestion/rvshare/entry — RVshare manual booking entry endpoint
  - GET /ingestion/history — Import run history query endpoint
  - GET /ingestion/bookings — Unified bookings list endpoint
  - GET /ingestion/bank-transactions — Bank transactions list endpoint
affects: [03-accounting-engine, 04-notifications, 05-pdf-generation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - APIRouter with prefix and tags for endpoint grouping
    - _require_csv_extension helper for uniform file type validation across upload endpoints
    - ValueError-to-HTTPException 422 pattern for normalizer error surfacing
    - Optional query param filters with typed Query() defaults

key-files:
  created:
    - app/api/ingestion.py
  modified:
    - app/main.py

key-decisions:
  - "ValueError from normalizer caught at API layer and re-raised as HTTPException 422 — keeps normalizer pure Python (not FastAPI-aware)"
  - "_require_csv_extension rejects non-.csv uploads before reading bytes — fast-fail before any I/O"
  - "bookings endpoint joins Property table inline via select() — avoids lazy-load, property_slug returned in single query"
  - "GET endpoints use limit/offset pagination with sane defaults (100/0 for bookings, 50 for history)"

patterns-established:
  - "Upload pattern: _require_csv_extension -> await file.read() -> normalizer call -> ValueError -> 422"
  - "Query pattern: select().order_by(desc()).limit().offset() with optional .where() filters"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 2 Plan 6: Ingestion API Endpoints Summary

**Seven HTTP endpoints wiring the ingestion pipeline to the outside world: 3 CSV uploads (Airbnb/VRBO/Mercury), 1 manual entry (RVshare), and 3 query endpoints (history, bookings, bank-transactions)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T18:58:01Z
- **Completed:** 2026-02-27T18:59:19Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `app/api/ingestion.py` with all 7 endpoints under `/ingestion` prefix
- Registered ingestion router in `app/main.py` alongside the existing health router
- All upload endpoints validate .csv extension, read bytes, delegate to normalizer, and convert ValueError to HTTP 422
- GET endpoints support optional platform/property_slug filters and limit/offset pagination

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ingestion API endpoints** - `5b4dc36` (feat)
2. **Task 2: Register ingestion router in FastAPI app** - `5564376` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `app/api/ingestion.py` - APIRouter with all 7 ingestion endpoints; 282 lines
- `app/main.py` - Added ingestion_router import and app.include_router(ingestion_router)

## Decisions Made

- **ValueError-to-422 at API layer:** normalizer raises ValueError on bad data; API layer catches and re-raises as HTTPException 422. Keeps normalizer pure Python (no FastAPI dependency).
- **`_require_csv_extension` helper:** Shared validation across all 3 upload endpoints. Rejects non-.csv files before reading bytes — avoids unnecessary I/O.
- **Bookings join in query:** `select(Booking, Property.slug)` with explicit join avoids lazy-loading; property_slug returned in the same query without N+1.
- **Pagination defaults:** bookings default limit=100 (wide default for batch consumers), history default limit=50 (smaller — runs accumulate quickly).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 2 (Data Ingestion) is fully complete:
- ORM models and Alembic migration (02-01)
- Normalizer pipeline with archive/upsert/ImportRun (02-02)
- Airbnb, VRBO, Mercury adapters (02-03, 02-04, 02-05)
- HTTP API exposing all ingestion operations (02-06)

Ready for Phase 3 (Accounting Engine): booking and bank transaction data is now importable and queryable via REST.

---
*Phase: 02-data-ingestion*
*Completed: 2026-02-27*
