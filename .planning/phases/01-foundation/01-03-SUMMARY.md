---
phase: 01-foundation
plan: 03
subsystem: database
tags: [sqlalchemy, alembic, postgres, psycopg, orm, migrations, python]

# Dependency graph
requires:
  - phase: 01-01
    provides: pyproject.toml with sqlalchemy, alembic, psycopg[binary] already installed
provides:
  - app/db.py with SQLAlchemy 2.0 engine, SessionLocal, Base (DeclarativeBase), get_db()
  - app/models/property.py with Property ORM model (int PK + slug unique business key)
  - app/models/__init__.py registering all models with Base.metadata
  - alembic/ directory with configured env.py (reads DATABASE_URL from environment)
  - alembic/versions/001_initial_properties.py creating properties table with unique slug index
affects:
  - 01-04 (config system — writes to properties table via upsert in CLI wizard)
  - 01-05 (manage.py CLI — uses Property model and db session)
  - 02 (bookings — FK to properties.id)
  - 03 (accounting — FK to properties.id)
  - all subsequent phases (all models extend Base; all migrations chain from 001)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SQLAlchemy 2.0 Mapped[] typed column style (DeclarativeBase not declarative_base())
    - app/models/__init__.py imports all models to register with Base.metadata before alembic
    - alembic.ini sqlalchemy.url left empty — overridden by env.py via os.environ DATABASE_URL
    - disable_existing_loggers=False in fileConfig() prevents Alembic logging hijack
    - Hand-written initial migration (not autogenerate) for clean first-migration readability
    - Separate op.create_index() for slug uniqueness (cleaner than inline in create_table)

key-files:
  created:
    - app/__init__.py
    - app/db.py
    - app/models/__init__.py
    - app/models/property.py
    - alembic.ini
    - alembic/env.py
    - alembic/script.py.mako
    - alembic/versions/001_initial_properties.py
  modified: []

key-decisions:
  - "alembic.ini sqlalchemy.url is empty — credentials only from DATABASE_URL environment variable, never committed"
  - "disable_existing_loggers=False in fileConfig() prevents Alembic from silencing app logs after migration"
  - "Integer PK + slug unique business key on Property — int for fast FK joins, slug for human-readable config/URL identity"
  - "Hand-written migration 001 (not autogenerate) — cleaner and more explicit for the foundational table"
  - "app/models/__init__.py imports all models to ensure Base.metadata is populated before alembic runs"

patterns-established:
  - "Model registration: all ORM models imported in app/models/__init__.py for Alembic autogenerate"
  - "Migration credentialing: env.py reads DATABASE_URL from os.environ, overrides empty alembic.ini url"
  - "Logging safety: fileConfig(..., disable_existing_loggers=False) in every Alembic env.py"

# Metrics
duration: 1min
completed: 2026-02-27
---

# Phase 1 Plan 03: SQLAlchemy Models + Alembic Migrations Summary

**SQLAlchemy 2.0 Mapped[] Property model + Alembic migration infrastructure with env-var-driven credentials and logging-safe configuration**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-27T16:26:34Z
- **Completed:** 2026-02-27T16:27:56Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Property ORM model using SQLAlchemy 2.0 Mapped[] style with integer PK and unique slug business key
- Alembic configured to read DATABASE_URL from environment (no credentials in committed files)
- Initial migration creates properties table with separate unique index on slug (clean, explicit migration)
- Logging hijack prevention: `disable_existing_loggers=False` applied per RESEARCH.md pitfall 1

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SQLAlchemy 2.0 database layer with engine, session, and Property model** - `9e516d7` (feat)
2. **Task 2: Initialize Alembic and create initial migration for properties table** - `fc5ec0f` (feat)

**Plan metadata:** _(docs commit — see below)_

## Files Created/Modified

- `app/__init__.py` - Empty package init (required for Python package resolution)
- `app/db.py` - SQLAlchemy engine, SessionLocal, Base (DeclarativeBase), get_db() FastAPI dependency; reads DATABASE_URL from environment
- `app/models/__init__.py` - Imports Property to register it with Base.metadata; critical for Alembic autogenerate
- `app/models/property.py` - Property ORM model: int PK, slug (String(64) unique index), display_name, created_at/updated_at with timezone-aware server defaults
- `alembic.ini` - Alembic config with empty sqlalchemy.url (overridden by env.py at runtime)
- `alembic/env.py` - Migration environment: imports Base + app.models, reads DATABASE_URL from os.environ, disable_existing_loggers=False, compare_type=True
- `alembic/script.py.mako` - Alembic revision script template (default, unmodified)
- `alembic/versions/001_initial_properties.py` - Hand-written migration: creates properties table + ix_properties_slug unique index

## Decisions Made

- **Empty sqlalchemy.url in alembic.ini**: Credentials belong in environment variables only. The env.py overrides with `os.environ.get("DATABASE_URL", ...)` so no password is ever in a committed file.
- **`disable_existing_loggers=False`**: Applied to prevent Alembic from silencing application logs after running migrations — a known pitfall documented in RESEARCH.md.
- **Hand-written migration over autogenerate**: The first migration is written explicitly rather than auto-generated. This is cleaner, more readable, and ensures the exact schema we intend is specified rather than inferred.
- **Separate `op.create_index()` for slug uniqueness**: Creating the index separately from `create_table` makes the migration more readable and the intent clearer than inline `unique=True`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Database connection runs via Docker Compose (postgres service with healthcheck).

## Next Phase Readiness

- Plan 01-04 (config system): Property model ready; CLI wizard can upsert to `properties` table via `get_db()`
- Plan 01-05 (app skeleton + FastAPI): `app/` package created; `app/db.py` provides `engine` for health check DB connectivity test
- Phase 2 (bookings): `properties` table is the FK target; `alembic_version` table will track all future migrations chained from `001`
- Running `alembic upgrade head` against a live PostgreSQL creates the properties table correctly (verified via `alembic history` showing `<base> -> 001 (head)`)

**No blockers.** Phase 1 plans 04 and 05 can proceed immediately.

---
*Phase: 01-foundation*
*Completed: 2026-02-27*
