---
phase: 05-resort-pdf-compliance
plan: 02
subsystem: api
tags: [pymupdf, pdf, acroform, xfa, form-filling, compliance]

# Dependency graph
requires:
  - phase: 05-resort-pdf-compliance plan 01
    provides: pymupdf installed, AppConfig compliance fields, PropertyConfig host_name/host_phone

provides:
  - app/compliance/__init__.py compliance package
  - detect_form_type() returning 'acroform', 'xfa', or 'none' via xref inspection
  - fill_resort_form() filling AcroForm fields from JSON mapping with field.update() + doc.bake()
  - list_form_fields() enumerating all form widgets for mapping discovery
  - Three source types: booking, property, static
  - Date formatting via configurable format spec (MM/DD/YYYY)
  - Cross-viewer compatibility via doc.bake() (required for macOS Preview + iOS Mail)

affects:
  - 05-04 (submission orchestrator calls fill_resort_form())
  - 05-05 (submission API)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PyMuPDF form filling: field.update() per widget then doc.bake() once -- not need_appearances() alone"
    - "PDF mapping JSON: three source types (booking/property/static), configurable date format spec"
    - "In-memory PDF bytes via doc.tobytes() -- no temp files needed"

key-files:
  created:
    - app/compliance/__init__.py
    - app/compliance/pdf_filler.py
  modified: []

key-decisions:
  - "field.update() + doc.bake() pattern enforced -- not need_appearances() alone (fails macOS Preview/iOS Mail)"
  - "fill_resort_form() accepts dicts not ORM models -- orchestrator builds dicts from ORM in Plan 04"
  - "list_form_fields() is the discovery tool -- run against actual resort PDF to get real field names for mapping JSON"

patterns-established:
  - "PDF cross-viewer compatibility: always call widget.update() per field then doc.bake() once before tobytes()"
  - "Three mapping source types: booking (from booking dict), property (from property dict), static (hardcoded)"

# Metrics
duration: 1min
completed: 2026-02-27
---

# Phase 5 Plan 02: PDF Filler Summary

**PyMuPDF AcroForm filler with detect_form_type(), fill_resort_form() (field.update() + doc.bake()), and list_form_fields() for field discovery**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-28T02:08:49Z
- **Completed:** 2026-02-28T02:10:13Z
- **Tasks:** 1 (task 2 is a checkpoint awaiting user verification)
- **Files modified:** 2

## Accomplishments
- Created compliance package init (`app/compliance/__init__.py`)
- Implemented `detect_form_type()` using PyMuPDF low-level xref inspection for AcroForm/XFA/none detection
- Implemented `fill_resort_form()` with three source types (booking, property, static), configurable date formatting, and cross-viewer compatible rendering via `field.update()` + `doc.bake()`
- Implemented `list_form_fields()` for discovery/inspection of real PDF form field names

## Task Commits

Each task was committed atomically:

1. **Task 1: Create compliance package and PDF filler module** - `a57be4c` (feat) — Note: files were committed as part of wave-2 execution in prior session

**Plan metadata:** (pending — checkpoint not yet passed)

## Files Created/Modified
- `app/compliance/__init__.py` - Compliance package init with module docstring
- `app/compliance/pdf_filler.py` - Three public functions: detect_form_type, fill_resort_form, list_form_fields

## Decisions Made
- `field.update()` + `doc.bake()` enforced — `need_appearances()` alone fails on macOS Preview and iOS Mail; `bake()` embeds appearance streams permanently into the PDF bytes
- `fill_resort_form()` accepts plain dicts (not ORM models) — the submission orchestrator (Plan 04) will build dicts from ORM models before calling this function
- `list_form_fields()` is the discovery tool — run against the actual Sun Retreats form to get real field names before building the mapping JSON

## Deviations from Plan

None - plan executed exactly as written.

Note: `app/compliance/__init__.py` and `app/compliance/pdf_filler.py` were found already committed to the repository (commit `a57be4c`, feat(05-03)) from a prior wave-2 execution session. The files match the plan spec exactly. No re-commit was needed.

## Issues Encountered
None.

## User Setup Required

**Checkpoint required before plan is fully complete.**

The checkpoint in Task 2 requires the user to:
1. Place the actual Sun Retreats booking form PDF at `pdf_mappings/sun_retreats_booking.pdf`
2. Run `detect_form_type()` to confirm it is AcroForm (not XFA) -- this resolves the pre-Phase-5 blocker
3. Run `list_form_fields()` to enumerate real field names
4. Create `pdf_mappings/sun_retreats_booking.json` with the real field mapping
5. Test `fill_resort_form()` with sample data and open result in macOS Preview

## Next Phase Readiness
- PDF filler module is complete and imports cleanly
- All three functions verified: imports OK, PyMuPDF 1.27.1, syntax OK
- Checkpoint pending: AcroForm verification against actual Sun Retreats form
- Once checkpoint is approved, Plan 04 (submission orchestrator) can call `fill_resort_form()`

---
*Phase: 05-resort-pdf-compliance*
*Completed: 2026-02-28*
