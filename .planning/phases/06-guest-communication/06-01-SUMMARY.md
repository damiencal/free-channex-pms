---
phase: 06-guest-communication
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, jinja2, pydantic, communication, templates]

# Dependency graph
requires:
  - phase: 05-resort-pdf-compliance
    provides: resort_submissions model and migration 005 as chain predecessor
  - phase: 01-foundation
    provides: PropertyConfig base, Jinja2 template infrastructure, Base ORM class
provides:
  - CommunicationLog ORM model with full message lifecycle columns
  - Migration 006 creating communication_logs table (FK to bookings, unique on booking_id+message_type)
  - Extended PropertyConfig with 7 guest communication fields (wifi_password, address, check_in_time, check_out_time, parking_instructions, local_tips, custom)
  - render_message_template() for shared message templates in templates/messages/
  - templates/messages/welcome.j2 and templates/messages/pre_arrival.j2
  - Updated SAMPLE_BOOKING_DATA covering all new variables
  - validate_all_templates() now validates both compliance and message templates
affects:
  - 06-02 (messenger service uses CommunicationLog and render_message_template)
  - 06-03 (scheduler queries CommunicationLog.scheduled_for)
  - 06-04 (VRBO/RVshare operator notification reads CommunicationLog)
  - 06-05 (API endpoints read/write CommunicationLog records)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Message templates in templates/messages/ (separate from per-property compliance templates in templates/default/)"
    - "render_message_template() creates new Jinja2 Environment per call for hot-reload"
    - "PropertyConfig guest fields all have defaults — additive to existing required fields"
    - "CommunicationLog UniqueConstraint on (booking_id, message_type) enforces one row per booking per message type"

key-files:
  created:
    - app/models/communication_log.py
    - alembic/versions/006_communication_tables.py
    - templates/messages/welcome.j2
    - templates/messages/pre_arrival.j2
  modified:
    - app/config.py
    - app/models/__init__.py
    - app/templates.py
    - config/jay.yaml
    - config/minnie.yaml
    - config/config.example.yaml

key-decisions:
  - "render_message_template() is separate from render_template() — message templates use templates/messages/ with shared (not per-property-override) resolution"
  - "All new PropertyConfig guest fields have defaults (not required) — Phase 6 is additive; existing configs must not break"
  - "CommunicationLog.status server_default='pending' — all new entries start pending unless explicitly set to native_configured"
  - "SAMPLE_BOOKING_DATA extended rather than duplicated — single dict covers both compliance and message template validation"

patterns-established:
  - "Message template hot-reload: new Environment created per render_message_template() call"
  - "validate_all_templates() validates both template directories in sequence before raising SystemExit"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 6 Plan 01: Guest Communication Foundation Summary

**CommunicationLog table with lifecycle tracking (pending/sent/native_configured), extended PropertyConfig with 7 guest communication fields, shared Jinja2 message templates at templates/messages/, and updated startup validation covering both template directories**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T19:39:55Z
- **Completed:** 2026-02-28T19:42:54Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- CommunicationLog ORM model created with booking_id FK, message_type, platform, status, scheduled_for, sent_at, operator_notified_at, rendered_message (Text), error_message, and UniqueConstraint on (booking_id, message_type)
- Migration 006 created in correct chain (down_revision=005), creates communication_logs table with FK to bookings
- PropertyConfig extended with wifi_password, address, check_in_time, check_out_time, parking_instructions, local_tips, and custom dict — all with defaults for backwards compatibility
- templates/messages/welcome.j2 and templates/messages/pre_arrival.j2 created; pre_arrival.j2 uses conditional blocks for optional fields
- render_message_template() added to app/templates.py with separate message template environment
- SAMPLE_BOOKING_DATA updated to cover all new variables; validate_all_templates() validates both compliance and message templates

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend PropertyConfig and update config files** - `59fd25a` (feat)
2. **Task 2: CommunicationLog model, migration 006, message templates, templates.py** - `e998273` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `app/models/communication_log.py` - CommunicationLog ORM model with full message lifecycle columns
- `alembic/versions/006_communication_tables.py` - Migration creating communication_logs table (down_revision=005)
- `app/config.py` - PropertyConfig extended with 7 guest communication fields
- `app/models/__init__.py` - CommunicationLog registered for Alembic detection
- `app/templates.py` - SAMPLE_BOOKING_DATA, REQUIRED_MESSAGE_TEMPLATES, build_message_template_env(), render_message_template(), validate_all_templates() updated
- `templates/messages/welcome.j2` - Professional welcome message template
- `templates/messages/pre_arrival.j2` - Comprehensive pre-arrival message with conditional blocks
- `config/jay.yaml` - Guest communication fields added (Lot 110)
- `config/minnie.yaml` - Guest communication fields added (Lot 170)
- `config/config.example.yaml` - Guest communication fields documented with examples

## Decisions Made

- render_message_template() uses a separate Jinja2 Environment from render_template() — message templates live in templates/messages/ (shared, no per-property overrides), while compliance templates use templates/{slug}/ -> templates/default/ resolution
- All new PropertyConfig guest communication fields have defaults (not required) so existing configs continue working without update
- SAMPLE_BOOKING_DATA extended in-place rather than creating a separate dict — single source of truth covers both compliance and message template validation at startup
- CommunicationLog.status has server_default="pending" matching the ResortSubmission pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Guest communication fields in property YAMLs have placeholder values (CHANGE_ME) that operators fill in before using Phase 6 messaging features.

## Next Phase Readiness

- CommunicationLog table is the core state machine for all Phase 6 plans
- render_message_template() is ready for Plan 02 (messenger service) to call directly
- PropertyConfig guest fields are available for template variable injection
- Migration 006 must be applied before Phase 6 API endpoints are live (`alembic upgrade head`)
- Plan 02 (Airbnb messenger) and Plan 03 (scheduler) can now build in parallel on this foundation

---
*Phase: 06-guest-communication*
*Completed: 2026-02-28*
