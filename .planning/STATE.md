# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 1 of 8 (Foundation)
Plan: 3 of 5 in current phase
Status: In progress
Last activity: 2026-02-27 — Completed 01-02-PLAN.md (Pydantic Settings config schema)

Progress: [███░░░░░░░] 12% (3/25 plans estimated)

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 2 min
- Total execution time: 6 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 3/5 | 6 min | 2 min |

**Recent Trend:**
- Last 5 plans: 01-01 (2 min), 01-03 (1 min), 01-02 (3 min)
- Trend: Steady

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: PyMuPDF chosen over pypdf for PDF form filling — pypdf does not regenerate appearance streams, causing blank forms in macOS Preview and iOS Mail
- [Roadmap]: APScheduler 3.x (not 4.0 alpha) for in-process scheduling — no external broker needed at this scale
- [Roadmap]: Polars (not pandas) for CSV ingestion — 5-25x faster, less memory
- [Roadmap]: LLM never performs arithmetic — text-to-SQL only; SQL computes, LLM describes result
- [Roadmap]: VRBO messaging is semi-automated in v1 — no public API for non-partners; system prepares text, operator sends manually
- [01-01]: hatchling build-system with packages=["app"] — allows uv sync without app/ existing; hatchling finds package when app/ is created in 01-03
- [01-01]: uv sync --no-install-project in Dockerfile — separates dep cache layer from project install; maximizes Docker layer caching
- [01-01]: extra_hosts: host.docker.internal:host-gateway — Linux compatibility for Ollama connectivity from inside Docker container
- [01-01]: DATABASE_URL uses postgresql+psycopg dialect (not +psycopg3) — SQLAlchemy dialect name for psycopg3 is psycopg
- [01-03]: alembic.ini sqlalchemy.url is empty — credentials only from DATABASE_URL env var, never committed
- [01-03]: disable_existing_loggers=False in Alembic fileConfig() — prevents Alembic from silencing app logs after migrations run
- [01-03]: Integer PK + slug unique business key on Property — int for fast FK joins, slug for human-readable config/URL identity
- [01-03]: Hand-written initial migration 001 (not autogenerate) — cleaner and more explicit for foundational table
- [01-02]: PropertyConfig as BaseModel (not BaseSettings) — per-property YAMLs loaded manually via glob, not by pydantic-settings source system
- [01-02]: Collect-all-errors fail-fast — load_all_properties() accumulates all ValidationErrors before SystemExit; operator sees every problem in one run
- [01-02]: config.example.yaml excluded by name from property discovery — coexists permanently in config/ for operator reference

### Pending Todos

None.

### Blockers/Concerns

- [Pre-Phase 5]: Resort PDF form type unverified — must confirm AcroForm vs. XFA before building PDF pipeline. XFA requires HTML-to-PDF (Playwright) instead of form filling. Verify against actual Sun Retreats form before Phase 5 planning.
- [Pre-Phase 3]: Airbnb fee model change (October 2025, host-only fee at 15.5%) — confirm which model applies to this account before finalizing accounting engine fee attribution logic.
- [Pre-Phase 8]: Ollama model selection unresolved — benchmark Qwen2.5-Coder 14B vs. available models against actual schema before Phase 8 planning. Hardware VRAM constraints will determine feasibility.

## Session Continuity

Last session: 2026-02-27T16:29:01Z
Stopped at: Completed 01-02-PLAN.md — Pydantic Settings config schema. Ready for 01-04 or 01-05 (remaining foundation plans).
Resume file: None
