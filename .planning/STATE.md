# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration
**Current focus:** Phase 2 — Data Ingestion (in progress)

## Current Position

Phase: 2 of 8 (Data Ingestion)
Plan: 1 of ~5 in current phase
Status: In progress — 02-01 complete (data layer foundation)
Last activity: 2026-02-27 — Completed 02-01-PLAN.md (ORM models, schemas, migration 002, config additions)

Progress: [███████░░░] 28% (7/25 plans estimated)

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 2 min
- Total execution time: 12 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 6/6 | 12 min | 2 min |
| 02-data-ingestion | 1/5 | 2 min | 2 min |

**Recent Trend:**
- Last 7 plans: 01-01 (2 min), 01-03 (1 min), 01-02 (3 min), 01-04 (2 min), 01-05 (3 min), 01-06 (1 min), 02-01 (2 min)
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
- [01-04]: ConsoleRenderer chosen for structlog — self-hosted tool, logs read by operator directly; JSON logging unnecessary at this scale
- [01-04]: Ollama check in lifespan is non-fatal — Ollama is Phase 8 feature; app must start without it
- [01-04]: /health always returns HTTP 200 — Docker HEALTHCHECK needs reliable HTTP 200; JSON status field communicates degraded state
- [01-05]: StrictUndefined in Jinja2 — raises UndefinedError on template variable typos at render time rather than silently emitting empty string
- [01-05]: SAMPLE_BOOKING_DATA must cover all template variables — adding a new variable to any template requires updating this dict or startup validation fails
- [01-05]: python-slugify for CLI wizard — avoids hand-rolling slug validation; handles spaces, uppercase, special chars
- [01-05]: Config files as source of truth (Phase 1) — CLI wizard reads slugs from YAML files for collision detection; DB sync deferred to future plan
- [01-05]: PDF mapping schema has three source types — booking (from booking data), property (from config), static (hardcoded, e.g., N/A for guest phone per resort policy)
- [01-06]: resort_checkin_instructions is required (no default) — forces operator to provide property-specific text at config time, not at template-edit time
- [01-06]: New template variable protocol — adding any variable requires updating SAMPLE_BOOKING_DATA + all property YAMLs + config.example.yaml
- [02-01]: listing_slug_map is dict[str, str] on PropertyConfig — each property maps platform identifiers to its own slug; normalizer builds unified lookup at import time
- [02-01]: BookingRecord.property_slug resolved by normalizer (not adapter) — keeps adapters stateless and DB-free
- [02-01]: check_in_date and check_out_date use sa.Date() (calendar dates only) — DateTime would risk time-zone confusion
- [02-01]: archive_dir defaults to "./archive" and mounted read-write in Docker — app writes archived CSVs here

### Pending Todos

None.

### Blockers/Concerns

- [Pre-Phase 5]: Resort PDF form type unverified — must confirm AcroForm vs. XFA before building PDF pipeline. XFA requires HTML-to-PDF (Playwright) instead of form filling. Verify against actual Sun Retreats form before Phase 5 planning.
- [Pre-Phase 3]: Airbnb fee model change (October 2025, host-only fee at 15.5%) — confirm which model applies to this account before finalizing accounting engine fee attribution logic.
- [Pre-Phase 8]: Ollama model selection unresolved — benchmark Qwen2.5-Coder 14B vs. available models against actual schema before Phase 8 planning. Hardware VRAM constraints will determine feasibility.

## Session Continuity

Last session: 2026-02-27T18:44:11Z
Stopped at: Completed 02-01-PLAN.md — data layer foundation (ORM models, schemas, migration 002, config additions). Ready for 02-02 (CSV ingestion adapters).
Resume file: None
