# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration
**Current focus:** Phase 5 — Resort PDF Compliance (complete, except 05-02 at checkpoint)

## Current Position

Phase: 5 of 8 (Resort PDF Compliance) — Phase complete (05-02 awaiting checkpoint resolution)
Plan: 5 of 6 plans executed (05-01, 05-03, 05-04, 05-05, 05-06 complete; 05-02 at checkpoint:human-verify)
Status: Phase 5 plan 06 complete — compliance API router with all 5 endpoints registered in main.py. Full resort PDF compliance feature set now API-accessible.
Last activity: 2026-02-28 — Completed 05-06-PLAN.md

Progress: [██████████████████████░] 88% (22/25 plans estimated)

## Performance Metrics

**Velocity:**
- Total plans completed: 22
- Average duration: 2 min
- Total execution time: 38 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 6/6 | 12 min | 2 min |
| 02-data-ingestion | 6/6 | 12 min | 2 min |
| 03-accounting-engine | 6/6 | 12 min | 2 min |
| 04-financial-reports | 4/4 | 8 min | 2 min |
| 05-resort-pdf-compliance | 5/6 | 12 min | 2 min |

**Recent Trend:**
- Last 7 plans: 03-06 (2 min), 04-01 (1 min), 04-02 (2 min), 04-04 (2 min), 04-03 (2 min), 05-01 (2 min)
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
- [02-03]: Airbnb CSV column names VERIFIED (2026-02-27) — "Confirmation code" (lowercase c), "Start date"/"End date" (lowercase d); two export formats exist (Transaction History + Pending stays)
- [02-03]: REQUIRED_HEADERS is frozenset of 5 columns; Start date / End date not required (absent from Payout rows; adapter takes first non-None per group)
- [02-03]: Empty date cells in parse() are allowed (payout/fee rows omit dates) — adapter takes first non-None date per confirmation code group
- [02-03]: Missing listing in listing_slug_map produces an error and aborts import — operator must add listing identifier to property YAML config
- [02-04]: VRBO adapter uses _ReservationGroup accumulator class (not Polars group_by) — per-row error messages with row numbers; supports filling empty guest_name from later rows in same reservation
- [02-04]: Check In/Check Out split on " - " (space-dash-space) — assumed from VRBO docs; must verify against real export before production use
- [02-04]: VRBO REQUIRED_HEADERS is 5-column frozenset (subset of all 29 VRBO columns) — only fields needed to build BookingRecord are required; extras ignored
- [02-05]: Mercury VERIFIED (2026-02-27) — native "Tracking ID" column confirmed; dedup uses "mercury-{Tracking ID}" (composite hash removed). Date column is "Date (UTC)", format MM-DD-YYYY with dashes
- [02-05]: Mercury REQUIRED_HEADERS is {Date (UTC), Description, Amount, Tracking ID} — all confirmed present in real export; extras (Status, Source Account, etc.) ignored
- [02-06]: ValueError from normalizer caught at API layer and re-raised as HTTPException 422 — keeps normalizer pure Python (not FastAPI-aware)
- [02-06]: _require_csv_extension rejects non-.csv uploads before reading bytes — fast-fail before any I/O
- [02-06]: bookings endpoint joins Property table inline via select() — avoids lazy-load, property_slug returned in single query
- [02-06]: GET endpoints use limit/offset pagination with sane defaults (100/0 for bookings, 50 for history)
- [03-01]: Numeric(12,2) for all Phase 3 monetary amounts (upgraded from 10,2 used in Phase 2 models)
- [03-01]: source_id as String(256) idempotency key — ON CONFLICT DO NOTHING returns None on duplicate (not error)
- [03-01]: Stub tables for expenses/loans/reconciliation_matches in migration 003 — Wave-2 plans add ORM models only, no migration conflicts
- [03-01]: Signed amount on JournalLine (positive=debit, negative=credit) — balance check is sum==0
- [03-01]: property_id nullable on JournalEntry — None for shared/cross-property entries
- [03-01]: reconciliation_status defaults to 'unmatched' on bookings and bank_transactions
- [03-03]: owner_reimbursable debits liability account 2200 (not expense) — owner paid on company behalf, company owes them back; journal: Dr Owner Reimbursable, Cr Mercury Checking
- [03-03]: Category-to-account resolved by name lookup at runtime (not hardcoded IDs) — resilient to account reseeding
- [03-03]: UUID suffix in source_id for expenses — expense:{date}:{uuid4()} prevents idempotency collisions for multiple expenses on same date
- [03-03]: bulk_import_expenses accepts str/float amounts, converts to Decimal internally — tolerates both CSV (str) and JSON (float) callers
- [03-02]: Airbnb fee model default is split_fee (0.03) — account confirmed on legacy 3% host fee; host_only (15.5%) also fully implemented; both use gross = net / (1 - fee_rate)
- [03-02]: Switching fee models in config requires re-recognition of historical bookings — documented in AppConfig docstrings
- [03-02]: Unearned Revenue auto-clearing on payout — recognize_booking_revenue() checks for prior booking_unearned entry and creates clearing journal entry automatically
- [03-02]: VRBO/RVshare net = gross — no fee reconstruction without per-booking fee data in CSV exports; single-event recognition
- [03-05]: MATCH_WINDOW_DAYS = 7 — Airbnb typically pays out on or near check-in day; 7-day window accommodates payout timing variation
- [03-05]: Decimal equality for reconciliation amount comparison — Booking.net_amount and BankTransaction.amount are Numeric(10,2); SQLAlchemy returns Python Decimal, no float rounding risk
- [03-05]: Multiple-candidate deposits flagged needs_review with NO match record — operator must confirm specific booking pairing
- [03-05]: reject_match preserves match record with status="rejected" for audit trail; both sides reset to "unmatched" to re-enter queue
- [03-04]: Caller provides P&I split from lender's amortization schedule — system does not compute amortization
- [03-04]: property_id=None on loan payment journal entries — loans are shared liabilities, not property-specific
- [03-04]: source_id for loan payments: loan_payment:{loan.id}:{payment_ref} — combines entity ID with caller ref for uniqueness across loans
- [03-04]: interest_rate stored as Numeric(6,4) annual decimal (0.0650 = 6.5%) — informational field; P&I computation happens externally
- [03-05]: confirm_match upserts — handles both confirming auto-matched records and creating new records for needs_review deposits
- [03-06]: get_config() (not Depends) in accounting endpoints — AppConfig is module-level singleton loaded at lifespan; direct call avoids per-request overhead
- [03-06]: recognize-all batch commit per booking with individual rollback on error — one bad booking does not abort the entire batch
- [03-06]: POST /reconciliation/reject/{match_id} uses query param confirmed_by (not body) — simple action, match_id from path is sufficient
- [03-06]: Accounting module commit responsibility: modules use db.flush() only; API endpoints call db.commit()
- [04-01]: resolve_period() priority order: start/end > month > quarter > year > ytd > error — explicit ranges always take precedence
- [04-01]: NON_EXPENSE_CATEGORIES [owner_deposit, loan_payment, transfer, personal] — bank transaction types that don't appear on P&L
- [04-01]: property_id on loans is nullable — property-specific loans get property_id set; shared working capital loans remain NULL
- [04-01]: EXPENSE_CATEGORIES not duplicated in reports.py — imported from expenses.py to maintain single source of truth
- [04-04]: abs(txn.amount) when passing to record_expense() — bank debits stored as negative; record_expense() requires positive amounts
- [04-04]: Bulk /bank-transactions/categorize registered before /{txn_id}/category — fixed-path routes must precede path-param routes to avoid route conflict
- [04-04]: record_expense() ValueError in bulk = per-item error (continues); in single = HTTP 422 (aborts) — different error semantics for batch vs single ops
- [04-03]: Loan liability balances via get_loan_balance() not journal sums — Phase 3 never created origination entries; only payment debits exist
- [04-03]: Retained Earnings = negate(sum of all revenue+expense journal lines up to as_of_date) — simplest correct formula; revenue credits are negative, so negating the total sum yields positive RE when profitable
- [04-03]: Balance sheet combined-only, zero-balance accounts included — all active balance-sheet accounts shown even with no activity
- [04-03]: Income statement breakdown=totals|monthly — monthly mode groups by (year, month) tuple, collects union of revenue+expense months
- [05-01]: SMTP credentials in .env only (secrets pattern); compliance settings in base.yaml — consistent with existing credential handling pattern
- [05-01]: host_name and host_phone are required PropertyConfig fields (no default) — same pattern as resort_checkin_instructions; forces operator to provide at config time
- [05-01]: confirmations/ volume mounted read-only in container — app reads PDFs; n8n/mail rules write them on host
- [05-01]: ResortSubmission unique constraint on booking_id — enforces one submission per booking at DB level
- [05-03]: stdlib logging for tenacity before_sleep_log — tenacity expects stdlib Logger, not structlog BoundLogger
- [05-03]: confirmation_bytes optional (None omits second attachment) — caller decides how to handle missing confirmation file
- [05-03]: find_confirmation_file returns None when dir absent or no match — not raise; orchestrator handles gracefully
- [05-03]: port 465 → use_tls=True, other ports → start_tls=True — covers both common SMTP configurations
- [05-02]: field.update() + doc.bake() enforced — need_appearances() alone fails on macOS Preview and iOS Mail; bake() embeds appearance streams permanently
- [05-02]: fill_resort_form() accepts plain dicts not ORM models — orchestrator (Plan 04) builds dicts from ORM before calling
- [05-02]: list_form_fields() is the field discovery tool — run against actual resort PDF to get real field names for mapping JSON
- [05-05]: AsyncIOScheduler (not BackgroundScheduler) used — FastAPI is fully async; AsyncIOScheduler runs on existing event loop without spawning threads
- [05-05]: scheduler is module-level variable — persists for app lifetime; lifespan only calls start/shutdown
- [05-05]: run_urgency_check() creates SessionLocal() directly — APScheduler callbacks run outside request context where Depends(get_db) is unavailable
- [05-05]: db.commit() for urgency flagging before email send — email failure is non-fatal; DB state correct even if digest not sent
- [05-05]: is_urgent==False filter in urgency query — prevents duplicate alerts for bookings already flagged in previous runs
- [05-05]: replace_existing=True on scheduler.add_job — prevents duplicate job registration on Docker restart
- [05-04]: guest_name split on first space only (maxsplit=1) — booking.guest_name -> guest_first_name / guest_last_name for PDF Text_2/Text_3 fields
- [05-04]: BackgroundTasks.add_task() used (not asyncio.create_task) — fires after response sent, DB session valid during execution
- [05-04]: should_auto_submit() check in API layer before add_task — below threshold = no background tasks fired; normalizer already created pending records
- [05-04]: Normalizer stays sync — only creates DB records; async email sending handled by API BackgroundTasks
- [05-04]: rvshare endpoint changed from def to async def — required for BackgroundTasks with async process_booking_submission()
- [05-06]: process-pending registered before /{param} routes — prevents FastAPI route conflict where 'process-pending' would be parsed as a booking_id integer
- [05-06]: confirm endpoint queries by booking_id (not submission_id) — n8n knows booking context, not internal submission IDs
- [05-06]: submit and approve are async def; confirm and list are sync — async for pipeline calls, sync for DB-only operations
- [05-06]: process-pending returns preview_mode_active (not error) when below threshold — operator may call before preview period ends

### Pending Todos

None.

### Blockers/Concerns

- [05-02 CHECKPOINT]: Resort PDF form type still unverified — detect_form_type() is built; user must run it against actual Sun Retreats PDF and confirm AcroForm. If XFA, entire Phase 5 approach changes (Playwright HTML-to-PDF instead of form filling).
- [Pre-Phase 3]: RESOLVED — Airbnb fee model confirmed: split_fee (3% host) is current; host_only (15.5%) also implemented. Config defaults set. Re-recognition required if model changes.
- [04-02]: Revenue query filters source_type==booking_payout — non-booking adjustments excluded from platform breakdown
- [04-02]: Combined P&L uses full shared expense amounts once (not sum of per-property allocations) — no double-counting
- [04-02]: generate_pl() returns plain dict not Pydantic model — nested arbitrary-key structure (platform names, display_name as keys) doesn't map cleanly to fixed schemas
- [Pre-Phase 8]: Ollama model selection unresolved — benchmark Qwen2.5-Coder 14B vs. available models against actual schema before Phase 8 planning. Hardware VRAM constraints will determine feasibility.

## Session Continuity

Last session: 2026-02-28T04:29:59Z
Stopped at: Completed 05-06-PLAN.md — compliance API router with all 5 endpoints created and registered in main.py. Phase 5 feature set complete. 05-02 still at checkpoint:human-verify awaiting PDF form type confirmation.
Resume file: None
