# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration
**Current focus:** Phase 2 — Data Ingestion (in progress)

## Current Position

Phase: 2 of 8 (Data Ingestion)
Plan: 4 of ~6 in current phase (02-04 complete)
Status: In progress — 02-04 complete (VRBO CSV adapter)
Last activity: 2026-02-27 — Completed 02-04-PLAN.md (VRBO adapter: validate_headers, parse, Reservation ID grouping, Check In/Check Out date range parsing)

Progress: [█████████░] 36% (9/25 plans estimated)

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: 2 min
- Total execution time: 18 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 6/6 | 12 min | 2 min |
| 02-data-ingestion | 4/6 | 8 min | 2 min |

**Recent Trend:**
- Last 7 plans: 01-05 (3 min), 01-06 (1 min), 02-01 (2 min), 02-02 (2 min), 02-03 (2 min), 02-04 (4 min), 02-05 (2 min)
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
- [02-02]: archive_file() uses Path.write_bytes() not shutil.copy2() — source is in-memory bytes from upload, not a file path
- [02-02]: resolve_property_id() uses module-level dict cache — only 2 properties; avoids repeated SELECT per record in batch imports
- [02-02]: All pg_insert on_conflict_do_update set_ dicts must explicitly include updated_at=func.now() — ORM onupdate hooks are not triggered by core INSERT statements
- [02-02]: create_manual_booking() records archive_path="N/A" in ImportRun — no file involved; ImportRun always recorded for audit consistency
- [02-03]: Airbnb CSV column names are UNVERIFIED (synthetic fixture) — real export must be inspected before production; Start Date / End Date most likely to differ
- [02-03]: REQUIRED_HEADERS is frozenset of 5 columns; Start Date / End Date not required (may be absent or renamed in real export)
- [02-03]: Empty date cells in parse() are allowed (payout/fee rows omit dates) — adapter takes first non-None date per confirmation code group
- [02-03]: Missing listing in listing_slug_map produces an error and aborts import — operator must add listing identifier to property YAML config
- [02-04]: VRBO adapter uses _ReservationGroup accumulator class (not Polars group_by) — per-row error messages with row numbers; supports filling empty guest_name from later rows in same reservation
- [02-04]: Check In/Check Out split on " - " (space-dash-space) — assumed from VRBO docs; must verify against real export before production use
- [02-04]: VRBO REQUIRED_HEADERS is 5-column frozenset (subset of all 29 VRBO columns) — only fields needed to build BookingRecord are required; extras ignored
- [02-05]: Mercury dedup uses composite key (Date+Amount+Description sha256[:16]) — generic Mercury CSV has no native transaction ID; COL_TRANSACTION_ID is commented in source for easy activation when real export is verified
- [02-05]: Mercury REQUIRED_HEADERS is minimal subset {Date, Description, Amount} — extra columns (Running Balance, Category, etc.) ignored; validate_headers() uses subset check, not equality

### Pending Todos

None.

### Blockers/Concerns

- [Pre-Phase 5]: Resort PDF form type unverified — must confirm AcroForm vs. XFA before building PDF pipeline. XFA requires HTML-to-PDF (Playwright) instead of form filling. Verify against actual Sun Retreats form before Phase 5 planning.
- [Pre-Phase 3]: Airbnb fee model change (October 2025, host-only fee at 15.5%) — confirm which model applies to this account before finalizing accounting engine fee attribution logic.
- [Pre-Phase 8]: Ollama model selection unresolved — benchmark Qwen2.5-Coder 14B vs. available models against actual schema before Phase 8 planning. Hardware VRAM constraints will determine feasibility.

## Session Continuity

Last session: 2026-02-27T18:53:04Z
Stopped at: Completed 02-04-PLAN.md — VRBO CSV adapter (validate_headers, Reservation ID grouping, Check In/Check Out date range parsing, VRBO Property ID resolution). Ready for remaining Phase 2 plans.
Resume file: None
