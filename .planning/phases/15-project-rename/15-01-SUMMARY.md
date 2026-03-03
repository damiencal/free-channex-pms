---
phase: 15-project-rename
plan: 01
subsystem: infra
tags: [uv, docker-compose, fastapi, pyproject, rename, roost]

# Dependency graph
requires: []
provides:
  - pyproject.toml declaring package name roost-rental
  - docker-compose.yml with roost-db, roost-api services and name:roost
  - .env.example DATABASE_URL using @roost-db: hostname
  - uv.lock regenerated with roost-rental package name
  - app/main.py FastAPI title and startup log referencing Roost
  - app/logging.py docstring referencing Roost
  - manage.py CLI help and setup banner referencing Roost
  - README.md heading and docker command referencing Roost
affects: [15-02, 15-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Docker Compose project-level name: roost (top-level name key)"
    - "Service names include product prefix: roost-db, roost-api"
    - "Docker service name == DATABASE_URL hostname (roost-db)"

key-files:
  created: []
  modified:
    - pyproject.toml
    - docker-compose.yml
    - .env.example
    - uv.lock
    - app/main.py
    - app/logging.py
    - manage.py
    - README.md

key-decisions:
  - "Package distribution name: roost-rental (not roost — avoids PyPI collision risk)"
  - "Docker service renamed app → roost-api, db → roost-db for namespace clarity"
  - "image: roost added to roost-api for named image builds"
  - "POSTGRES_DB=rental_management and db_data volume unchanged — not project identity"
  - "FastAPI description changed to 'Rental Operations Platform' to preserve domain context"

patterns-established:
  - "uv sync after pyproject.toml name change to regenerate uv.lock atomically"
  - "Docker service names cascade into DATABASE_URL hostnames — change both together"

# Metrics
duration: 2min
completed: 2026-03-03
---

# Phase 15 Plan 01: Rename Python Package and Docker Services Summary

**Python package renamed to roost-rental, Docker Compose restructured with roost-db/roost-api/name:roost, and all backend identity strings updated from "Rental Management Suite" to "Roost"**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-03T19:49:52Z
- **Completed:** 2026-03-03T19:51:22Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- pyproject.toml declares `name = "roost-rental"` with updated description referencing Roost
- docker-compose.yml fully restructured: top-level `name: roost`, services renamed `db → roost-db` and `app → roost-api`, `image: roost` added
- .env.example DATABASE_URL hostname updated from `@db:` to `@roost-db:` to match new service name
- uv.lock regenerated via `uv sync` — old rental-management package removed, roost-rental installed
- app/main.py startup log and FastAPI title both reference "Roost"
- app/logging.py, manage.py, README.md all updated — zero "Rental Management Suite" strings remain

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename Python package and Docker Compose services** - `b512015` (feat)
2. **Task 2: Update backend application strings and README** - `30ff8d8` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `pyproject.toml` - name = "roost-rental", description references Roost
- `docker-compose.yml` - name: roost, roost-db, roost-api, image: roost
- `.env.example` - DATABASE_URL hostname @db: → @roost-db:
- `uv.lock` - regenerated with roost-rental package (rental-management removed)
- `app/main.py` - startup log "Starting Roost", title="Roost"
- `app/logging.py` - docstring "Structlog configuration for Roost"
- `manage.py` - docstring, typer help, and setup banner reference "Roost CLI" / "Roost"
- `README.md` - heading # Roost, restart command uses roost-api

## Decisions Made

- Package distribution name is `roost-rental` (not `roost`) to avoid potential PyPI namespace collisions and to be descriptive
- `POSTGRES_DB=rental_management`, `POSTGRES_USER=rental`, and `db_data` volume left unchanged — these are database implementation details, not project identity strings; changing them would break existing installs
- FastAPI description updated to "Rental Operations Platform — Self-hosted vacation rental management" to preserve domain context while adopting Roost brand
- `image: roost` added to roost-api service (was absent in original) to produce named Docker images on build

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The `.pyc` bytecode files in `app/__pycache__/` contained old compiled strings but are not git-tracked and auto-regenerate — not a real issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Foundation identity established: pyproject.toml and docker-compose.yml are the authoritative Roost configuration
- Plan 02 (frontend rename) can proceed — it depends on this plan's docker-compose.yml service names for any reference updates
- Plan 03 (planning docs + directory rename) can proceed after Plan 02
- No blockers

---
*Phase: 15-project-rename*
*Completed: 2026-03-03*
