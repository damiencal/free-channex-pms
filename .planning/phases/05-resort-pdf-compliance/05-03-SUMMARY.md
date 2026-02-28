---
phase: 05-resort-pdf-compliance
plan: 03
subsystem: email
tags: [aiosmtplib, tenacity, smtp, email, pdf, retry, async]

# Dependency graph
requires:
  - phase: 05-resort-pdf-compliance/05-01
    provides: aiosmtplib + tenacity dependencies installed, AppConfig SMTP fields, compliance config pattern

provides:
  - send_resort_email() — async SMTP delivery with 1-2 PDF attachments, TLS/STARTTLS selection
  - send_with_retry() — 4-attempt exponential backoff wrapper (min=10s, max=120s, reraise=True)
  - find_confirmation_file() — case-insensitive PDF scan by confirmation code, returns None on no match
  - format_email_subject() — "Booking Form - Guest - Lot N - dates" with same/cross-month handling
  - format_email_body() — casual tone email body with configurable contact and sender name

affects:
  - 05-04 (submission orchestrator — composes emailer + confirmation + pdf_filler)
  - 05-05 (submission API — triggers send_with_retry on booking import)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Async email delivery: aiosmtplib.send() with EmailMessage (stdlib MIME, not string building)"
    - "Tenacity retry with stdlib logging: before_sleep_log(logger, logging.WARNING) — tenacity requires stdlib logger, not structlog"
    - "Port-based TLS selection: port 465 → use_tls=True, all other → start_tls=True"
    - "Confirmation matching: sorted(glob('*.pdf')) for deterministic results; None on miss (not raise)"

key-files:
  created:
    - app/compliance/emailer.py
    - app/compliance/confirmation.py
  modified: []

key-decisions:
  - "stdlib logging for tenacity before_sleep_log — tenacity expects stdlib Logger, not structlog BoundLogger"
  - "confirmation_bytes optional (None omits second attachment) — allows sending without confirmation when file not found"
  - "find_confirmation_file returns None when dir absent or no match — caller decides how to handle missing confirmation"
  - "port 465 → use_tls, other → start_tls — covers both common SMTP configurations"

patterns-established:
  - "Email MIME via EmailMessage (not string): add_attachment() handles Content-Type and encoding"
  - "Tenacity reraise=True pattern: surfaces original exception after retry exhaustion, not RetryError"

# Metrics
duration: 3min
completed: 2026-02-28
---

# Phase 5 Plan 03: Email Sender Summary

**Async SMTP email delivery (aiosmtplib) with 4-attempt tenacity retry and confirmation PDF matcher plus subject/body formatters**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-28T02:09:17Z
- **Completed:** 2026-02-28T02:12:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `emailer.py` with `send_resort_email()` (async SMTP, TLS/STARTTLS, 1-2 PDF attachments) and `send_with_retry()` (4 attempts, exponential backoff min=10s/max=120s, reraise=True)
- Created `confirmation.py` with `find_confirmation_file()` (case-insensitive PDF scan, None on miss), `format_email_subject()` (same-month and cross-month date formats), and `format_email_body()` (casual tone, configurable names)
- All must_haves verified: imports clean, subject format assertions pass, None-on-miss confirmed

## Task Commits

Each task was committed atomically:

1. **Task 1: Create email delivery module with async SMTP and retry** - `a57be4c` (feat)
2. **Task 2: Create confirmation file matcher and email formatting helpers** - `270f1d1` (feat)

**Plan metadata:** `[see final commit]` (docs: complete plan)

## Files Created/Modified
- `app/compliance/emailer.py` — Async SMTP delivery via aiosmtplib + tenacity 4-attempt retry wrapper
- `app/compliance/confirmation.py` — PDF file scanner, subject formatter, casual-tone body formatter

## Decisions Made
- Used stdlib `logging` (not structlog) for tenacity's `before_sleep_log` — tenacity's type annotation expects a stdlib `Logger`; structlog's `BoundLogger` is incompatible
- `confirmation_bytes` is `Optional[bytes]` — when `find_confirmation_file()` returns `None`, the orchestrator can still send with just the form (no second attachment)
- Port-based TLS selection: `use_tls=True` only for port 465; all other ports use `start_tls=True`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required beyond what 05-01 already documented (SMTP credentials in `.env`).

## Next Phase Readiness
- All email and confirmation building blocks ready for Plan 04 (submission orchestrator)
- `send_with_retry()` is the primary integration point: orchestrator calls it with form bytes from pdf_filler + confirmation bytes from find_confirmation_file
- `format_email_subject()` and `format_email_body()` are ready to consume booking data and AppConfig fields

---
*Phase: 05-resort-pdf-compliance*
*Completed: 2026-02-28*
