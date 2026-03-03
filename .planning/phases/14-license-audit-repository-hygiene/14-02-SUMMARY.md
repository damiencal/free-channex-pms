---
phase: 14-license-audit-repository-hygiene
plan: 02
subsystem: infra
tags: [apache2, license, notice, attribution, open-source]

# Dependency graph
requires:
  - phase: 14-01
    provides: license audit results confirming pypdf replaces pymupdf and listing all direct deps
provides:
  - Apache 2.0 LICENSE file at repo root (200 lines, full canonical text)
  - NOTICE file at repo root listing all direct Python and npm dependencies with license types
affects: [17-public-release, README, contributors]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Apache 2.0 copyright header format: 'Copyright YYYY Name' before license body"
    - "NOTICE file structure: project name, copyright, then Python and JS dependency sections"

key-files:
  created:
    - LICENSE
    - NOTICE
  modified: []

key-decisions:
  - "Copyright holder: CHANGE_ME, year 2026"
  - "NOTICE lists direct dependencies only (not transitive) per Apache 2.0 common practice"
  - "psycopg listed as LGPL-3.0-only in NOTICE (per license audit decision from Plan 01)"
  - "structlog listed as MIT or Apache-2.0 dual-licensed in NOTICE"

patterns-established:
  - "NOTICE format: package - license - URL, alphabetical within each section"

# Metrics
duration: 2min
completed: 2026-03-03
---

# Phase 14 Plan 02: License Files Summary

**Apache 2.0 LICENSE (200 lines, full canonical text) and NOTICE file (63 lines, 34 direct dependencies) created at repo root for open source release**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-03T07:01:56Z
- **Completed:** 2026-03-03T07:04:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created full Apache License Version 2.0 text (200 lines) with "Copyright 2026 CHANGE_ME"
- Created NOTICE file listing all 20 direct Python dependencies with accurate license types
- Created NOTICE file listing all 14 production + 10 dev npm dependencies
- Confirmed pypdf (BSD-3-Clause) listed; no reference to old pymupdf (AGPL-3.0) dependency

## Task Commits

Each task was committed atomically:

1. **Task 1: Create LICENSE file with Apache 2.0 text** - `c57c0c5` (feat)
2. **Task 2: Create NOTICE file with third-party attribution** - `52ec489` (feat)

**Plan metadata:** `[pending]` (docs: complete plan)

## Files Created/Modified

- `LICENSE` - Full Apache License Version 2.0 text, 200 lines, copyright CHANGE_ME 2026
- `NOTICE` - Third-party attribution listing 34 direct dependencies (20 Python, 14 npm production + 10 npm dev)

## Decisions Made

- NOTICE lists direct dependencies only (not transitive) — common practice for Apache 2.0 NOTICE files; transitive deps are covered by their own license files
- psycopg listed with its actual LGPL-3.0-only license in the NOTICE (acceptable per Plan 01 audit decision)
- structlog listed as "MIT or Apache-2.0 (dual-licensed)" since it ships under both licenses

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

pip-licenses tool was not available in the uv project environment (tool mode returned empty output). Resolved by using `importlib.metadata` via `uv run python3` to query installed package metadata directly, cross-referencing well-known package licenses from PyPI for packages that report UNKNOWN in their metadata fields.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LICENSE and NOTICE files are complete and ready for public exposure
- All direct dependencies attributed correctly with accurate license types
- Ready for Phase 14-04 (final hygiene tasks) and eventual public repository release

---
*Phase: 14-license-audit-repository-hygiene*
*Completed: 2026-03-03*
