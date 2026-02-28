---
phase: 06-guest-communication
plan: 02
subsystem: api
tags: [aiosmtplib, tenacity, jinja2, sqlalchemy, structlog, communication]

# Dependency graph
requires:
  - phase: 06-01
    provides: CommunicationLog model, render_message_template(), PropertyConfig guest fields
  - phase: 05-resort-pdf-compliance
    provides: aiosmtplib + tenacity emailer pattern (compliance/emailer.py)
  - phase: 01-foundation
    provides: SessionLocal, AppConfig, structlog
provides:
  - app/communication/__init__.py: package marker
  - app/communication/emailer.py: send_operator_notification() with copy-paste delimited body, send_operator_notification_with_retry() with tenacity
  - app/communication/messenger.py: render_guest_message(), send_pre_arrival_message(), prepare_welcome_message()
affects:
  - 06-03 (scheduler calls send_pre_arrival_message(booking_id) as APScheduler job target)
  - 06-04 (ingestion hooks call prepare_welcome_message(booking_id, platform, db))
  - 06-05 (API reads CommunicationLog records written by this module)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Operator self-notification: from_email == to_email for all communication alerts (same as urgency digest in compliance/urgency.py)"
    - "APScheduler session pattern: send_pre_arrival_message creates SessionLocal() directly, not FastAPI Depends"
    - "BackgroundTask session pattern: prepare_welcome_message receives db from caller, uses flush() not commit()"
    - "Platform-split logic: Airbnb=mark sent (no email), VRBO/RVshare=notify operator (status stays pending)"

key-files:
  created:
    - app/communication/__init__.py
    - app/communication/emailer.py
    - app/communication/messenger.py
  modified: []

key-decisions:
  - "send_pre_arrival_message() creates own SessionLocal() — same pattern as run_urgency_check() in compliance/urgency.py; APScheduler runs outside FastAPI request context"
  - "prepare_welcome_message() receives db session from caller and uses flush() not commit() — caller (API endpoint) owns commit boundary"
  - "Airbnb pre-arrival marks status='sent' immediately (system renders, operator copies to Airbnb app) vs VRBO/RVshare keeps 'pending' until operator confirms via API"
  - "Airbnb welcome uses native_configured status — Airbnb handles delivery natively, system never renders or sends"
  - "_find_property_config() iterates config.properties O(n) — negligible at n=2 properties"
  - "SMTP guard in prepare_welcome_message: skips with warning if smtp_user/smtp_from_email empty — prevents crashes on unconfigured deployments"

patterns-established:
  - "render_guest_message() builds data dict from ORM + PropertyConfig then delegates to render_message_template() — separation of concern between data assembly and template rendering"
  - "Email copy-paste section delimited by '=' * 60 separator lines — trivially easy for operator to select message text"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 6 Plan 02: Guest Communication Messenger Summary

**Communication module with render_guest_message() building Jinja2 context from Booking + PropertyConfig, platform-split send logic (Airbnb marks sent, VRBO/RVshare emails operator with === delimited copy-paste text), and APScheduler-compatible SessionLocal session management**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T19:44:50Z
- **Completed:** 2026-02-28T19:46:56Z
- **Tasks:** 2
- **Files modified:** 3 (all created)

## Accomplishments

- `app/communication/emailer.py`: operator notification email with `=` * 60 separator lines for copy-paste, tenacity retry wrapper (4 attempts, exponential backoff 10s-120s), stdlib logging for tenacity compatibility
- `app/communication/messenger.py`: `render_guest_message()` assembles all 15 template variables from Booking ORM + PropertyConfig (including all 7 guest communication fields: wifi_password, address, check_in/out_time, parking_instructions, local_tips, custom)
- `send_pre_arrival_message(booking_id)`: APScheduler-safe with own `SessionLocal()`, Airbnb path marks `status='sent'` + stores `rendered_message`, VRBO/RVshare path emails operator + sets `operator_notified_at`
- `prepare_welcome_message(booking_id, platform, db)`: idempotent (skips if CommunicationLog row exists), Airbnb=`native_configured`, VRBO/RVshare=renders+emails+`status='pending'`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create communication module with operator notification emailer** - `9f7828f` (feat)
2. **Task 2: Create messenger service with template rendering and message send logic** - `333f429` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `app/communication/__init__.py` - Package marker (empty)
- `app/communication/emailer.py` - Operator notification email: `send_operator_notification()` (aiosmtplib), `send_operator_notification_with_retry()` (tenacity 4x), `_build_notification_body()` with `=` * 60 delimiters
- `app/communication/messenger.py` - Core messaging: `render_guest_message()`, `send_pre_arrival_message()`, `prepare_welcome_message()`, `_find_property_config()`

## Decisions Made

- `send_pre_arrival_message()` creates its own `SessionLocal()` — APScheduler runs outside FastAPI request context (same pattern as `run_urgency_check()` in `app/compliance/urgency.py`)
- `prepare_welcome_message()` accepts `db: Session` from caller and uses `db.flush()` — API endpoint owns the commit boundary, matching the established module commit responsibility pattern from Phase 3
- Airbnb pre-arrival: marks `status='sent'` immediately because the system has rendered the full text ready for operator to paste into the Airbnb app — the "sent" status here means "prepared for delivery" not "automatically delivered"
- Airbnb welcome: `native_configured` status, no rendering — Airbnb's native scheduled messaging handles delivery; system only tracks that it is configured
- SMTP guard added to `prepare_welcome_message()`: skips email with warning log if `smtp_user` or `smtp_from_email` is empty — prevents crashes on unconfigured deployments

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `send_pre_arrival_message(booking_id)` is ready to be registered as an APScheduler `DateTrigger` job target in Plan 03
- `prepare_welcome_message(booking_id, platform, db)` is ready to be called from ingestion endpoint `BackgroundTasks` in Plan 04
- All 11 verification criteria from the plan passed
- Platform-split logic tested by inspection: Airbnb path verified independent from VRBO/RVshare path

---
*Phase: 06-guest-communication*
*Completed: 2026-02-28*
