---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [docker, uv, fastapi, sqlalchemy, alembic, postgres, pydantic-settings, python]

# Dependency graph
requires: []
provides:
  - pyproject.toml with all Phase 1 Python dependencies (uv-managed)
  - uv.lock for reproducible installs (62 packages resolved)
  - Dockerfile using python:3.12-slim + uv with cached dependency layer
  - docker-compose.yml with postgres:16-alpine (healthcheck) + app services
  - .env.example documenting all required environment variables
  - .gitignore protecting secrets (.env), caches (__pycache__, .venv)
affects:
  - 01-02 (database migrations — uses alembic, sqlalchemy from this plan)
  - 01-03 (app skeleton — uses fastapi, structlog, Dockerfile from this plan)
  - 01-04 (config system — uses pydantic-settings[yaml] from this plan)
  - 01-05 (templates/PDF — uses jinja2, manage.py scaffold from this plan)
  - all subsequent phases (Docker infrastructure established here)

# Tech tracking
tech-stack:
  added:
    - fastapi[standard]==0.133.1
    - sqlalchemy>=2.0 (resolved 2.0.47)
    - alembic==1.18.4
    - pydantic-settings[yaml]==2.13.1
    - jinja2==3.1.6
    - typer==0.24.1
    - questionary==2.1.1
    - structlog==25.5.0
    - httpx==0.28.1
    - psycopg[binary]==3.3.3
    - python-slugify==8.0.4
    - pytest==9.0.2 (dev)
    - pytest-asyncio==1.3.0 (dev)
    - uv (package manager)
    - hatchling (build backend)
  patterns:
    - uv + pyproject.toml for dependency management (no requirements.txt)
    - hatchling build-system with packages = ["app"] for application packaging
    - Dockerfile deps-first caching layer (COPY pyproject.toml uv.lock before COPY app/)
    - docker-compose.yml: alembic upgrade head before uvicorn in command
    - pg_isready healthcheck with depends_on: condition: service_healthy
    - config/templates bind-mounted read-only (not COPY'd — restart not rebuild)
    - DATABASE_URL uses postgresql+psycopg dialect (not +psycopg3)
    - OLLAMA_URL via env var with host.docker.internal default

key-files:
  created:
    - pyproject.toml
    - uv.lock
    - Dockerfile
    - docker-compose.yml
    - .env.example
    - .gitignore
  modified: []

key-decisions:
  - "hatchling build-system with packages=[app] allows uv sync without app/ existing yet"
  - "uv sync --frozen --no-install-project in Dockerfile separates dep layer from app code"
  - "config/templates/pdf_mappings bind-mounted read-only — operators edit without rebuild"
  - "extra_hosts: host.docker.internal:host-gateway for Linux Ollama connectivity"
  - "DATABASE_URL dialect is postgresql+psycopg (not postgresql+psycopg3)"

patterns-established:
  - "Dependency caching: COPY lock files first, RUN uv sync, then COPY app code"
  - "Service startup order: db healthcheck → alembic upgrade head → uvicorn"
  - "Secrets in .env only; YAML config files contain no secrets"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 1 Plan 01: Docker Scaffold & Project Setup Summary

**uv-managed pyproject.toml + python:3.12-slim Dockerfile + postgres:16-alpine compose stack with healthcheck-gated startup and bind-mounted config**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T16:22:04Z
- **Completed:** 2026-02-27T16:24:37Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Full dependency tree locked (62 packages, all imports verified)
- Dockerfile with cached dependency layer — rebuilds only when lock file changes
- Docker Compose stack with postgres healthcheck ensuring DB ready before app starts
- .env.example documents all 5 required env vars including correct SQLAlchemy dialect

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pyproject.toml with all Phase 1 dependencies** - `b6eb291` (feat)
2. **Task 2: Create Dockerfile, docker-compose.yml, .env.example, .gitignore** - `b36fa39` (feat)

**Plan metadata:** _(final docs commit — see below)_

## Files Created/Modified

- `pyproject.toml` - Project metadata, 11 core + 3 dev dependencies, manage entry point, hatchling build config
- `uv.lock` - Locked dependency tree (62 packages, reproducible installs)
- `Dockerfile` - python:3.12-slim + uv, cached deps layer, bind-mount pattern for config/templates
- `docker-compose.yml` - postgres:16-alpine with pg_isready healthcheck, app waits for healthy DB, alembic before uvicorn
- `.env.example` - Documents DATABASE_URL, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, OLLAMA_URL
- `.gitignore` - Protects .env, __pycache__, .venv, .DS_Store, db_data/

## Decisions Made

- **hatchling + packages=["app"]**: Needed a build-system for the `manage` entry point script. Hatchling configured to look in `app/` (created in plan 01-03) so build succeeds without it existing during `uv sync` (uv installs deps before building project).
- **`--no-install-project` in Dockerfile**: `uv sync --frozen --no-cache --no-install-project` installs only dependencies in the cache layer; the project itself is installed after `COPY app/`. This maximizes layer caching.
- **`extra_hosts: host.docker.internal:host-gateway`**: Added to app service for Linux compatibility. macOS/Windows get `host.docker.internal` automatically; Linux needs the explicit mapping. Enables Ollama connectivity from inside the container across all platforms.
- **`postgresql+psycopg` dialect**: Used in DATABASE_URL per RESEARCH.md pitfall #4 — SQLAlchemy's dialect name for psycopg3 is `psycopg`, not `psycopg3`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added hatchling build-system with packages = ["app"]**
- **Found during:** Task 1 (uv sync)
- **Issue:** Initial pyproject.toml had `[build-system]` with hatchling but no `packages` config. Hatchling couldn't find `rental_management/` directory and failed with `ValueError: Unable to determine which files to ship`.
- **Fix:** Added `[tool.hatch.build.targets.wheel] packages = ["app"]` telling hatchling where the application code lives.
- **Files modified:** pyproject.toml
- **Verification:** `uv sync` exits 0, package builds as `rental-management==0.1.0`
- **Committed in:** b6eb291 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 build bug)
**Impact on plan:** Essential fix — uv sync would not succeed without it. No scope creep.

## Issues Encountered

- `docker build` fails at `COPY manage.py ./` since `manage.py` doesn't exist until plan 01-03. This is expected (plan's verify step explicitly accounts for this). Dockerfile syntax is valid and `uv sync --frozen` layer succeeds.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 01-02 (database migrations): Alembic dependency installed, docker-compose.yml has postgres service ready, DATABASE_URL documented in .env.example
- Plan 01-03 (app skeleton): fastapi, uvicorn, structlog installed; Dockerfile COPY app/ prepared; manage entry point declared
- Plan 01-04 (config system): pydantic-settings[yaml], jinja2, pyyaml installed
- Plan 01-05 (templates/PDF): jinja2 installed; pdf_mappings/ bind-mount in docker-compose.yml ready

**No blockers.** All Phase 1 plans can proceed with dependencies available.

---
*Phase: 01-foundation*
*Completed: 2026-02-27*
