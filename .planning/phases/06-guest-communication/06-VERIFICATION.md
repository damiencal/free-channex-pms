---
phase: 06-guest-communication
verified: 2026-02-28T21:30:00Z
status: gaps_found
score: 4/5 must-haves verified
gaps:
  - truth: "2-3 days before check-in, an arrival message is sent with the correct lock code and property details for the booked unit, pulled from config (for Airbnb bookings)"
    status: partial
    reason: "For Airbnb pre-arrival, the system renders the correct template (with lock code from config) and marks the CommunicationLog as 'sent', but there is no delivery mechanism: no operator notification email is sent, the status is already 'sent' so there is no pending flag to alert the operator, and the guest only receives the message if the operator manually checks /communication/logs for 'sent' Airbnb pre-arrival entries — which provides no actionable signal. VRBO/RVshare are correctly handled (operator email with copy-pasteable text). Plan 06-02 must-have line 17 stated 'handles Airbnb (sends operator email)' but the implementation contradicts this and only renders + marks sent with no notification."
    artifacts:
      - path: "app/communication/messenger.py"
        issue: "send_pre_arrival_message() for Airbnb path (lines 179-194) renders template and marks status='sent' but does not call send_operator_notification_with_retry(). The VRBO/RVshare else branch (lines 196-225) correctly emails the operator. No equivalent notification exists for Airbnb."
    missing:
      - "For Airbnb pre-arrival: either (a) operator notification email with rendered message text (same pattern as VRBO/RVshare), OR (b) change CommunicationLog status to 'pending' instead of 'sent' so operator can identify unsent messages via GET /communication/logs?status=pending"
      - "If relying on Airbnb's native check-in reminder feature: document this explicitly and change status to 'native_configured' (like welcome), and do not render a custom template for Airbnb pre-arrival"
human_verification:
  - test: "Confirm Airbnb native scheduled messaging is configured in the Airbnb host account"
    expected: "Operator has configured Airbnb Inbox > Scheduled Messages with a 'booking confirmed' trigger (welcome) and ideally a 'check-in' trigger (pre-arrival reminder) using Airbnb's built-in message templates"
    why_human: "This is an external platform configuration, not verifiable from code. Success criterion 1 ('no manual action required per booking') depends on this one-time operator setup being complete."
  - test: "Trigger a test Airbnb booking import and verify the pre-arrival job fires 2 days before check-in"
    expected: "APScheduler DateTrigger fires send_pre_arrival_message(), rendered message stored in communication_logs.rendered_message, status becomes 'sent', but verify whether operator is notified to actually send the message via Airbnb app"
    why_human: "The pre-arrival job runs async and requires a real or simulated booking with a check-in date 2+ days in the future to test the scheduler path end-to-end."
  - test: "Trigger a VRBO booking import and verify operator receives notification email"
    expected: "Background task fires prepare_welcome_message() for VRBO booking; operator receives email at smtp_from_email with '=' delimited copy-paste section containing rendered welcome text"
    why_human: "SMTP delivery requires live SMTP credentials — cannot be verified from code structure alone."
---

# Phase 6: Guest Communication Verification Report

**Phase Goal:** Guests receive a welcome message upon booking and arrival details 2-3 days before check-in, driven entirely by config-editable templates
**Verified:** 2026-02-28T21:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | New Airbnb booking triggers welcome message via Airbnb's native scheduled messaging (no manual action per booking) | ? HUMAN | System marks `status='native_configured'` in CommunicationLog when Airbnb booking ingested. Requires operator one-time setup of Airbnb Scheduled Messages — not verifiable from code alone. |
| 2 | 2-3 days before check-in, arrival message sent with correct lock code and property details from config | PARTIAL | Scheduler job fires `send_pre_arrival_message()` at `check_in_date - 2 days, 14:00 UTC`. Template renders lock code, address, wifi, etc. from `PropertyConfig`. For VRBO/RVshare: operator email sent with copy-pasteable text. For **Airbnb**: message rendered but status immediately marked `'sent'` with **no operator notification** — no delivery mechanism exists to ensure the guest receives the message. |
| 3 | Templates use variable substitution (guest name, check-in date, property name, lock code) | VERIFIED | `render_guest_message()` builds a 15-key data dict from `Booking` ORM + `PropertyConfig`. Template `pre_arrival.j2` uses `{{ guest_name }}`, `{{ checkin_date }}`, `{{ property_name }}`, `{{ lock_code }}`, `{{ address }}`, `{{ check_in_time }}`, `{{ check_out_time }}`, `{{ wifi_password }}`, `{{ site_number }}`, `{{ resort_checkin_instructions }}`, plus conditional blocks for `parking_instructions`, `wifi_password`, `local_tips`. `StrictUndefined` ensures missing variables raise at render time. Startup validation via `validate_all_templates()` catches template errors before serving requests. |
| 4 | VRBO bookings: system prepares complete message text and notifies operator to send manually | VERIFIED | `_fire_background_welcome_messages()` fires for VRBO/RVshare uploads. `prepare_welcome_message()` renders template and calls `send_operator_notification_with_retry()`. Email body has `'=' * 60` separator line with complete copy-pasteable text. `send_pre_arrival_message()` for VRBO/RVshare path emails operator and keeps `status='pending'` until `POST /communication/confirm/{log_id}` is called. All confirmed in `app/communication/messenger.py` and `app/communication/emailer.py`. |
| 5 | Message templates editable in config files without code changes or system restart | VERIFIED | `render_message_template()` creates a **new** `jinja2.Environment` with `FileSystemLoader` on **every call**, reading template files from disk each time. Editing `templates/messages/welcome.j2` or `templates/messages/pre_arrival.j2` takes effect on the next message render. No restart required. Hot-reload documented in `app/templates.py` lines 57-58 and 216-217. |

**Score:** 4/5 truths verified (1 human-needed, 1 partial/failed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/communication_log.py` | CommunicationLog ORM model with lifecycle columns | VERIFIED | 75 lines. All required columns: `booking_id` FK, `message_type`, `platform`, `status`, `scheduled_for`, `sent_at`, `operator_notified_at`, `rendered_message` (Text), `error_message`. `UniqueConstraint("booking_id", "message_type", name="uq_comm_log_booking_type")`. Imported in `app/models/__init__.py`. |
| `alembic/versions/006_communication_tables.py` | Migration creating communication_logs table | VERIFIED | 37 lines. `down_revision = "005"`, `revision = "006"`. Creates all columns including FK to `bookings.id`. UniqueConstraint on `(booking_id, message_type)`. |
| `app/config.py` (PropertyConfig) | Extended with 7 guest communication fields | VERIFIED | `wifi_password`, `address`, `check_in_time` (default "4:00 PM"), `check_out_time` (default "11:00 AM"), `parking_instructions`, `local_tips`, `custom: dict[str, str]` all present with defaults. Non-breaking — existing configs without these fields continue to work. |
| `app/templates.py` | render_message_template(), REQUIRED_MESSAGE_TEMPLATES, updated SAMPLE_BOOKING_DATA, updated validate_all_templates() | VERIFIED | `render_message_template()` at line 205, `REQUIRED_MESSAGE_TEMPLATES = ["welcome.j2", "pre_arrival.j2"]` at line 46, `SAMPLE_BOOKING_DATA` includes all 15 template variables at lines 24-40. `validate_all_templates()` validates both compliance templates (`templates/default/`) and message templates (`templates/messages/`) before serving. |
| `templates/messages/welcome.j2` | Professional welcome message template | VERIFIED | Uses `guest_name`, `property_name`, `checkin_date`, `checkout_date`. Professional tone. Informs guest that arrival details will follow. |
| `templates/messages/pre_arrival.j2` | Comprehensive pre-arrival template with lock code and conditional blocks | VERIFIED | Uses all required variables: `guest_name`, `property_name`, `checkin_date`, `check_in_time`, `checkout_date`, `check_out_time`, `address`, `site_number`, `lock_code`, `resort_checkin_instructions`. Conditional blocks for `parking_instructions`, `wifi_password`, `local_tips`. |
| `app/communication/__init__.py` | Package marker | VERIFIED | File exists (empty package marker). |
| `app/communication/messenger.py` | render_guest_message(), send_pre_arrival_message(), prepare_welcome_message() | VERIFIED (partial gap) | 365 lines. All three functions exist and are substantive. `render_guest_message()` correctly uses `render_message_template()` (not compliance `render_template()`). Gap: Airbnb pre-arrival path in `send_pre_arrival_message()` does not notify operator. |
| `app/communication/emailer.py` | Operator notification email with copy-paste section | VERIFIED | 191 lines. `send_operator_notification()` with `'=' * 60` separator delimiters. `send_operator_notification_with_retry()` with tenacity (4 attempts, exponential backoff 10s-120s). |
| `app/communication/scheduler.py` | schedule_pre_arrival_job(), rebuild_pre_arrival_jobs() | VERIFIED | 166 lines. `PRE_ARRIVAL_DAYS_BEFORE = 2`, `PRE_ARRIVAL_SEND_HOUR_UTC = 14`. Past-send-time guard before `add_job()`. `replace_existing=True`. `rebuild_pre_arrival_jobs()` queries `CommunicationLog` for pending pre-arrival entries with future `scheduled_for`. Circular imports avoided via lazy imports inside function bodies. |
| `app/ingestion/normalizer.py` | _create_communication_logs() wired into ingest_csv() and create_manual_booking() | VERIFIED | `_create_communication_logs()` at line 168. Called in both `ingest_csv()` (line 375) and `create_manual_booking()` (line 581). Both return dicts include `welcome_async_ids`. Airbnb welcome = `native_configured`. VRBO/RVshare welcome deferred to `prepare_welcome_message()` (correct — prevents idempotency bug). |
| `app/api/ingestion.py` | _fire_background_welcome_messages() wired for VRBO and RVshare; not wired for Airbnb or Mercury | VERIFIED | `_fire_background_welcome_messages()` at line 67. Wired in `upload_vrbo_csv()` (lines 173-177) and `create_rvshare_booking()` (lines 244-248). NOT wired in `upload_airbnb_csv()` or `upload_mercury_csv()` (correct by design). |
| `app/api/communication.py` | GET /communication/logs, POST /communication/confirm/{log_id} | VERIFIED | 156 lines. `GET /communication/logs` with status, message_type, platform query filters. Joins Booking and Property for full context including guest_name, check_in_date, property_slug. Returns rendered_message. `POST /communication/confirm/{log_id}` transitions pending→sent, idempotent for already-sent, 409 for native_configured. |
| `app/main.py` | communication_router registered, rebuild_pre_arrival_jobs() in lifespan | VERIFIED | `communication_router` imported at line 26, registered at line 118. `rebuild_pre_arrival_jobs` imported at line 31, awaited at line 94 after `scheduler.start()`. Startup log at line 95. |
| `config/jay.yaml`, `config/minnie.yaml` | Updated with 7 guest communication fields | VERIFIED | Both files have `wifi_password`, `address`, `check_in_time`, `check_out_time`, `parking_instructions`, `local_tips`, `custom` at lines 14-20. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/models/communication_log.py` | `app/models/booking.py` | ForeignKey on booking_id | VERIFIED | `mapped_column(ForeignKey("bookings.id"), nullable=False)` line 25 |
| `alembic/versions/006_communication_tables.py` | `alembic/versions/005_compliance_tables.py` | down_revision chain | VERIFIED | `down_revision = "005"` line 12 |
| `app/communication/messenger.py` | `app/templates.py` | render_message_template() call | VERIFIED | `from app.templates import render_message_template` line 36; called in `render_guest_message()` line 87 |
| `app/communication/messenger.py` | `app/models/communication_log.py` | Updates CommunicationLog status, rendered_message, sent_at | VERIFIED | CommunicationLog imported line 34; updated in `send_pre_arrival_message()` and `prepare_welcome_message()` |
| `app/communication/emailer.py` | aiosmtplib | SMTP sending | VERIFIED | `import aiosmtplib` line 13; called in `send_operator_notification()` |
| `app/communication/messenger.py` | `app/communication/emailer.py` | Calls send_operator_notification_with_retry for VRBO/RVshare | VERIFIED | Imported line 30; called in VRBO/RVshare branches of both `send_pre_arrival_message()` and `prepare_welcome_message()` |
| `app/communication/scheduler.py` | `app/main.py` | scheduler instance (lazy import) | VERIFIED | `from app.main import scheduler` inside function bodies (lazy import to avoid circular dependency) |
| `app/communication/scheduler.py` | `app/communication/messenger.py` | DateTrigger job calls send_pre_arrival_message | VERIFIED | `from app.communication.messenger import send_pre_arrival_message` lazy imported in both `schedule_pre_arrival_job()` and `rebuild_pre_arrival_jobs()` |
| `app/ingestion/normalizer.py` | `app/models/communication_log.py` | Creates CommunicationLog records | VERIFIED | `from app.models.communication_log import CommunicationLog` line 30; records created in `_create_communication_logs()` |
| `app/ingestion/normalizer.py` | `app/communication/scheduler.py` | schedule_pre_arrival_job() for all platforms | VERIFIED | `from app.communication.scheduler import compute_pre_arrival_send_time, schedule_pre_arrival_job` line 25; called in `_create_communication_logs()` line 246 |
| `app/api/ingestion.py` | `app/communication/messenger.py` | BackgroundTasks fires prepare_welcome_message() for VRBO/RVshare | VERIFIED | `from app.communication.messenger import prepare_welcome_message` line 23; used in `_fire_background_welcome_messages()` line 90 |
| `app/main.py` | `app/api/communication.py` | app.include_router(communication_router) | VERIFIED | `app.include_router(communication_router)` line 118 |
| `app/main.py` | `app/communication/scheduler.py` | rebuild_pre_arrival_jobs() in lifespan startup | VERIFIED | `from app.communication.scheduler import rebuild_pre_arrival_jobs` line 31; `await rebuild_pre_arrival_jobs()` line 94 |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| COMM-01: System sends a welcome message via platform messaging upon booking confirmation | PARTIAL | Airbnb: `native_configured` status recorded — depends on operator's one-time Airbnb native messaging setup. VRBO/RVshare: operator email sent. Functionally satisfied if Airbnb native messaging is pre-configured. |
| COMM-02: System sends an arrival message via platform messaging 2-3 days before check-in | PARTIAL | APScheduler job fires correctly at check_in - 2 days, 14:00 UTC. VRBO/RVshare: operator notified with copy-pasteable text. Airbnb: message rendered and marked 'sent' but **operator not notified** — no reliable delivery path for Airbnb pre-arrival. |
| COMM-03: Arrival message includes property details and lock codes from config | VERIFIED | `render_guest_message()` reads `lock_code`, `address`, `check_in_time`, `check_out_time`, `wifi_password`, `parking_instructions`, `local_tips` from `PropertyConfig`. Template uses `{{ lock_code }}` and all property fields. |
| COMM-04: System uses Airbnb's native scheduled messaging triggers where available | PARTIAL | Airbnb welcome: correctly tracked as `native_configured`. Airbnb pre-arrival: NOT using native scheduling — system renders its own template. ROADMAP plan 06-02 described "configure welcome AND pre-arrival triggers" but implementation only covers welcome. |
| COMM-05: System composes VRBO messages for manual sending (no VRBO messaging API available) | VERIFIED | VRBO welcome: `prepare_welcome_message()` renders template + emails operator via `send_operator_notification_with_retry()`. VRBO pre-arrival: `send_pre_arrival_message()` renders template + emails operator. Both have `'=' * 60` copy-paste delimiters. |
| COMM-06: Message templates are user-editable and stored in configuration files | VERIFIED | Templates at `templates/messages/welcome.j2` and `templates/messages/pre_arrival.j2`. Hot-reload via new `jinja2.Environment` per call — edits take effect immediately. |
| COMM-07: Templates support variable substitution (guest name, dates, property name, lock code, etc.) | VERIFIED | 15 template variables, all substituted from `Booking` ORM + `PropertyConfig`. `StrictUndefined` catches missing variables at render time. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/communication/messenger.py` | 179-194 | Airbnb pre-arrival: marks `status='sent'` before message is actually sent to guest; no operator notification emitted | Blocker | Operator has no signal that Airbnb pre-arrival message needs to be manually sent via Airbnb app. Guest may not receive the config-driven pre-arrival message. |

### Human Verification Required

#### 1. Airbnb Native Scheduled Messages (One-Time Setup)
**Test:** Verify in the Airbnb host account that Scheduled Messages are configured under Inbox > Scheduled Messages with a "booking confirmed" trigger
**Expected:** A template exists that fires automatically on each new booking confirmation, sending a welcome message to the guest
**Why human:** External platform configuration — not verifiable from the codebase. Success criterion 1 ("no manual action required") only holds if this one-time setup was done.

#### 2. VRBO/RVshare Operator Email Delivery
**Test:** Import a VRBO CSV with a new booking; confirm the operator receives a notification email containing the rendered welcome message text
**Expected:** Email arrives at the configured `smtp_from_email` address with subject `[Action Required] Welcome message ready - <guest_name> (VRBO)` and a copy-paste section between `====` separator lines
**Why human:** SMTP delivery requires live credentials and cannot be tested structurally.

#### 3. APScheduler Pre-Arrival Job Fire
**Test:** Import a booking with check-in date 2 days in the future; wait until 14:00 UTC 2 days before check-in
**Expected:** `send_pre_arrival_message()` fires, `CommunicationLog.rendered_message` is populated, VRBO/RVshare operator receives email
**Why human:** Time-dependent behavior — requires waiting or mocking the scheduler clock.

### Gaps Summary

The phase implementation is structurally complete and well-wired across 15 files. Templates render correctly with variable substitution, the communication log tracks message lifecycle, the scheduler registers DateTrigger jobs, and VRBO/RVshare operator notifications work end-to-end.

One gap blocks full goal achievement: **Airbnb pre-arrival message delivery is incomplete.** The system renders the correct pre-arrival template (with lock code, address, and all config-driven fields) and marks it `sent` in the database — but sends no operator notification email and provides no actionable signal. The operator has no mechanism to discover that a rendered Airbnb pre-arrival message is waiting to be sent via the Airbnb app. This contradicts both success criterion 2 ("an arrival message is sent") and COMM-02 ("system sends an arrival message"). The VRBO/RVshare path correctly handles this with an operator notification email; the Airbnb path is missing the equivalent mechanism.

The intended behavior per the CONTEXT doc ("Airbnb uses native scheduled messaging") and ROADMAP plan description ("configure welcome AND pre-arrival triggers") suggests Airbnb pre-arrival should either use Airbnb's native check-in reminder trigger (same as welcome) or send an operator notification email. The current implementation does neither.

Additionally, success criterion 1 and COMM-04 require human verification — the Airbnb native welcome depends on a one-time operator setup in the Airbnb platform that cannot be verified from the codebase.

---

_Verified: 2026-02-28T21:30:00Z_
_Verifier: Claude (gsd-verifier)_
