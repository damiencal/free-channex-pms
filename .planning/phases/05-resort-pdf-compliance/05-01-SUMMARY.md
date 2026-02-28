---
phase: 05-resort-pdf-compliance
plan: 01
subsystem: database
tags: [pymupdf, aiosmtplib, apscheduler, tenacity, smtp, alembic, sqlalchemy, pydantic-settings]

# Dependency graph
requires:
  - phase: 04-financial-reports
    provides: migration 004 (down_revision chain), AppConfig pattern, ORM model conventions
provides:
  - pymupdf, aiosmtplib, apscheduler, tenacity dependencies installed
  - AppConfig SMTP credentials (smtp_host, smtp_port, smtp_user, smtp_password, smtp_from_email)
  - AppConfig compliance settings (confirmations_dir, pdf_template_path, pdf_mapping_path, auto_submit_threshold, resort_contact_name)
  - PropertyConfig host_name and host_phone required fields
  - ResortSubmission ORM model (resort_submissions table)
  - Alembic migration 005 creating resort_submissions with FK to bookings and unique constraint
  - docker-compose confirmations/ volume mount (read-only)
  - .env.example SMTP documentation
affects:
  - 05-02 (pdf-filler)
  - 05-03 (email-sender)
  - 05-04 (scheduler)
  - 05-05 (submission-api)

# Tech tracking
tech-stack:
  added:
    - pymupdf==1.27.1 (PDF form filling)
    - aiosmtplib==5.1.0 (async SMTP email)
    - apscheduler==3.11.2 (in-process scheduling, 3.x not 4.0 alpha)
    - tenacity==9.1.4 (retry logic)
    - tzlocal==5.3.1 (installed as apscheduler dependency)
  patterns:
    - SMTP credentials in .env (secrets), compliance settings in base.yaml (non-secrets) — consistent with existing pattern
    - Required PropertyConfig fields with no default — forces operator to provide at config time
    - Hand-written migration with explicit down_revision chain

key-files:
  created:
    - app/models/resort_submission.py
    - alembic/versions/005_compliance_tables.py
  modified:
    - pyproject.toml
    - uv.lock
    - .env.example
    - config/base.yaml
    - config/config.example.yaml
    - config/jay.yaml
    - config/minnie.yaml
    - app/config.py
    - app/models/__init__.py
    - docker-compose.yml

key-decisions:
  - "SMTP credentials in .env only (secrets pattern); compliance settings in base.yaml (non-secrets)"
  - "host_name and host_phone are required fields (no default) — same pattern as resort_checkin_instructions"
  - "confirmations/ mounted read-only in container — app reads PDFs written by n8n/mail rules on host"
  - "ResortSubmission unique constraint on booking_id ensures one submission per booking"

patterns-established:
  - "Secrets-vs-config separation: credentials in .env, non-secret settings in base.yaml — enforced for SMTP"
  - "PropertyConfig required fields: host info follows same no-default pattern as resort_checkin_instructions"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 5 Plan 01: Foundation Summary

**ResortSubmission ORM model with migration 005, SMTP+compliance AppConfig fields, PropertyConfig host info, and four Phase 5 dependencies (pymupdf, aiosmtplib, apscheduler, tenacity) installed**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T02:03:21Z
- **Completed:** 2026-02-28T02:05:36Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Installed all four Phase 5 dependencies (pymupdf, aiosmtplib, apscheduler 3.x, tenacity)
- Extended AppConfig with SMTP credentials (from .env) and compliance settings (from base.yaml)
- Added host_name and host_phone required fields to PropertyConfig; updated all property YAMLs
- Created ResortSubmission model with full lifecycle tracking and migration 005 down_revision=004

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dependencies, update config schema, and docker-compose** - `6a7e71a` (feat)
2. **Task 2: Create ResortSubmission model and Alembic migration 005** - `d25f63d` (feat)

**Plan metadata:** `[see final commit]` (docs: complete plan)

## Files Created/Modified
- `app/models/resort_submission.py` - ResortSubmission ORM model tracking form submission lifecycle
- `alembic/versions/005_compliance_tables.py` - Migration creating resort_submissions table with FK+unique constraint
- `app/config.py` - AppConfig extended with SMTP fields and compliance settings; PropertyConfig extended with host_name/host_phone
- `pyproject.toml` - Added pymupdf, aiosmtplib, apscheduler, tenacity
- `config/base.yaml` - Added compliance settings (confirmations_dir, pdf paths, threshold, contact name)
- `.env.example` - Added SMTP env vars documentation
- `config/jay.yaml` - Added host_name/host_phone placeholders
- `config/minnie.yaml` - Added host_name/host_phone placeholders
- `config/config.example.yaml` - Added host_name/host_phone example values
- `docker-compose.yml` - Added confirmations/ read-only volume mount
- `app/models/__init__.py` - Imported ResortSubmission

## Decisions Made
- SMTP credentials stay in .env (secrets pattern) — consistent with DATABASE_URL handling
- Compliance settings (non-secret) go in base.yaml — consistent with ollama_url, archive_dir
- host_name and host_phone are required (no default) — forces operator to supply host info at config time; same pattern as resort_checkin_instructions
- confirmations/ volume mounted read-only (`:ro`) — container only reads confirmation PDFs; n8n/mail rules write them on the host
- APScheduler 3.x (not 4.0 alpha) per roadmap decision

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

**External services require manual configuration.** SMTP credentials must be set in `.env` before Phase 5 email features are used:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

For Gmail: create an App Password at Google Account > Security > App passwords (requires 2FA enabled).

Property YAMLs also need `host_name` and `host_phone` changed from `CHANGE_ME` to real values before Phase 5 plans run.

## Next Phase Readiness
- All four dependencies installed and importable
- AppConfig SMTP + compliance fields ready for Plans 02-05 to consume
- PropertyConfig host info fields ready for PDF pre-population in Plan 02
- ResortSubmission model ready for Plans 04/05 (scheduler, API)
- Migration 005 ready to apply when database is next migrated

Blockers: None for Wave-2 execution. Property YAMLs need CHANGE_ME values updated before production use.

---
*Phase: 05-resort-pdf-compliance*
*Completed: 2026-02-28*
