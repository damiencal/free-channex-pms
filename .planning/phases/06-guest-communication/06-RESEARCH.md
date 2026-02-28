# Phase 6: Guest Communication - Research

**Researched:** 2026-02-28
**Domain:** Scheduled messaging, Jinja2 templating, communication log tracking, operator email notification
**Confidence:** HIGH

## Summary

Phase 6 builds on existing infrastructure already in place: the Jinja2 templating system (app/templates.py), APScheduler AsyncIOScheduler (app/main.py), aiosmtplib email delivery (app/compliance/emailer.py), and the booking ingestion pipeline (app/ingestion/normalizer.py). The core pattern is already established by Phase 5 compliance work — when bookings arrive, downstream records are created and scheduled tasks are fired.

The phase has three distinct concerns: (1) render message text from templates at scheduling time or send time, (2) schedule pre-arrival messages 2 days before check-in using APScheduler DateTrigger, and (3) for VRBO/RVshare, email the operator the prepared text and track pending-until-confirmed status in a new `communication_logs` table. Airbnb welcome messages are handled entirely natively by Airbnb's built-in scheduled messaging feature — the system only needs to track that a native welcome is configured.

**Primary recommendation:** Model communication_logs like resort_submissions — a status-tracking table with clear state transitions (pending/sent/confirmed for VRBO/RVshare; native_configured for Airbnb). Use APScheduler DateTrigger for pre-arrival scheduling, and the existing aiosmtplib + tenacity pattern for operator notification emails.

---

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.6 | Template rendering | Already set up with StrictUndefined, per-property override resolution in app/templates.py |
| APScheduler (AsyncIOScheduler) | 3.11.2 | Scheduling pre-arrival jobs at specific datetime | Already used for urgency check; AsyncIOScheduler supports async job functions natively |
| aiosmtplib | 5.1.0 | SMTP email sending | Already used in app/compliance/emailer.py with TLS/STARTTLS selection |
| tenacity | 9.1.4 | Retry with exponential backoff | Already used via send_with_retry() in app/compliance/emailer.py |
| SQLAlchemy 2.0 | per uv.lock | communication_logs table model | Established pattern with Mapped/mapped_column typing |
| structlog | per project | Structured logging | Already used throughout |

### New (no new libraries needed)

No new libraries are required. All needed capabilities are already present in the project's dependency set.

### Alternatives Considered

| Instead of | Could Use | Why We Don't |
|------------|-----------|-------------|
| APScheduler DateTrigger | Celery/Redis beat | APScheduler already in-process; no external broker needed at this scale |
| aiosmtplib | smtplib (sync) | App is fully async; aiosmtplib is already installed |
| In-memory job tracking | Persistent APScheduler job store (SQLAlchemy) | Pre-arrival jobs registered at runtime from DB; no job store needed — jobs are rebuilt from DB on restart |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── communication/           # New module (parallel to app/compliance/)
│   ├── __init__.py
│   ├── messenger.py         # Core: render template + schedule/send logic
│   └── emailer.py           # Operator notification email for VRBO/RVshare
├── api/
│   └── communication.py     # New API router: GET /communication/logs, POST /communication/confirm/{id}
├── models/
│   └── communication_log.py # New ORM model
templates/
└── default/
    ├── welcome.txt          # Already exists — extend variables as needed
    └── pre_arrival.txt      # Already exists — extend variables as needed
alembic/versions/
└── 006_communication_tables.py
```

### Pattern 1: APScheduler DateTrigger for One-Time Pre-Arrival Jobs

**What:** Schedule a coroutine to run once at a specific future datetime using the `date` trigger type. The scheduler module-level variable is already set up in app/main.py and is accessible globally.

**When to use:** When a booking is ingested, compute the pre-arrival send time (check_in_date - 2 days, at 09:30 local time / UTC) and schedule the job. Each new booking gets its own date-triggered job.

**Important behavior:** If `run_date` is in the past when the job is added (e.g., a booking import where check-in is tomorrow), APScheduler's DateTrigger returns `None` from `get_next_fire_time()` — the job is never fired. The system must detect this case and skip scheduling (or handle it separately as an edge case).

**Job ID convention:** Use `f"pre_arrival_{booking_id}"` with `replace_existing=True` to be idempotent — re-importing the same booking does not create duplicate scheduler jobs.

**Source:** APScheduler 3.x docs — apscheduler.readthedocs.io/en/3.x

```python
# Source: APScheduler 3.x docs + existing app/main.py pattern
from datetime import datetime, time, timezone
from apscheduler.triggers.date import DateTrigger
from app.main import scheduler  # module-level AsyncIOScheduler

def schedule_pre_arrival(booking_id: int, check_in_date: date) -> bool:
    """Schedule pre-arrival message job. Returns False if check-in is too soon."""
    send_date = check_in_date - timedelta(days=2)
    run_at = datetime.combine(send_date, time(9, 30), tzinfo=timezone.utc)

    if run_at <= datetime.now(timezone.utc):
        # Too late to schedule — handle immediately or skip
        return False

    scheduler.add_job(
        send_pre_arrival_message,
        trigger=DateTrigger(run_date=run_at),
        id=f"pre_arrival_{booking_id}",
        args=[booking_id],
        replace_existing=True,
    )
    return True
```

### Pattern 2: Scheduler Access from Outside main.py

**What:** The module-level `scheduler = AsyncIOScheduler()` in `app/main.py` is imported directly where needed, the same way `from app.main import scheduler` works. This is the pattern already used for `urgency_check`.

**Critical constraint:** Scheduler jobs are in-memory only (MemoryJobStore default). On Docker restart, all scheduled pre-arrival jobs are lost. **The system must rebuild pre-arrival jobs at startup by querying communication_logs for pending pre-arrival entries with future send times.**

```python
# Startup rebuild pattern (in lifespan, after scheduler.start())
async def _rebuild_pre_arrival_jobs(db: Session) -> None:
    """Re-register pre-arrival scheduler jobs after restart."""
    pending = db.execute(
        select(CommunicationLog).where(
            CommunicationLog.message_type == "pre_arrival",
            CommunicationLog.status == "pending",
            CommunicationLog.scheduled_for > datetime.now(timezone.utc),
        )
    ).scalars().all()

    for log_entry in pending:
        scheduler.add_job(
            send_pre_arrival_message,
            trigger=DateTrigger(run_date=log_entry.scheduled_for),
            id=f"pre_arrival_{log_entry.booking_id}",
            args=[log_entry.booking_id],
            replace_existing=True,
        )
```

### Pattern 3: communication_logs Table (Status Tracking)

**What:** A new table tracking every message action per booking, modeled after `resort_submissions`. One row per message type per booking.

**Schema design (Claude's discretion area):**

```python
# app/models/communication_log.py
class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # "welcome" | "pre_arrival"
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    # "airbnb" | "vrbo" | "rvshare"
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    # Airbnb welcome: "native_configured"
    # VRBO/RVshare welcome/pre_arrival: "pending" -> "sent" (after operator confirms)
    # Pre_arrival (scheduled): "pending" -> "sent"
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set when APScheduler job is registered; NULL for native Airbnb welcome
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operator_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # When operator notification email was sent (VRBO/RVshare)
    rendered_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Stored rendered message text (for VRBO/RVshare copy-paste; also audit trail)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("booking_id", "message_type", name="uq_comm_log_booking_type"),
    )
```

**Status state machine:**

| Platform | Message Type | Initial Status | Terminal Status |
|----------|-------------|----------------|-----------------|
| airbnb | welcome | native_configured | native_configured |
| airbnb | pre_arrival | pending | sent |
| vrbo | welcome | pending | sent |
| vrbo | pre_arrival | pending | sent |
| rvshare | welcome | pending | sent |
| rvshare | pre_arrival | pending | sent |

For VRBO/RVshare, "pending" means operator has been notified but not yet confirmed. "sent" means operator clicked the confirm endpoint.

### Pattern 4: Template Variable Expansion (Config Schema)

**What:** The existing `PropertyConfig` Pydantic model in `app/config.py` needs new fields for Phase 6 template variables. Additionally, arbitrary custom key-value pairs are needed per the CONTEXT.md decision.

**New required fields to add to `PropertyConfig`:**

```python
# In app/config.py PropertyConfig class
wifi_password: str = ""
"""WiFi password for guest pre-arrival message."""

address: str = ""
"""Full property address for guest pre-arrival message."""

check_in_time: str = "4:00 PM"
"""Check-in time shown in pre-arrival message."""

check_out_time: str = "11:00 AM"
"""Check-out time shown in pre-arrival message."""

parking_instructions: str = ""
"""Parking instructions for pre-arrival message."""

local_tips: str = ""
"""Local area tips (restaurants, grocery, emergency contacts) for pre-arrival."""

custom: dict[str, str] = {}
"""Arbitrary key-value pairs available as template variables.
Example: {"pool_code": "5678", "trash_day": "Tuesday"}
Rendered into templates as {{ custom.pool_code }}, {{ custom.trash_day }}.
"""
```

**SAMPLE_BOOKING_DATA in app/templates.py must be updated** to include all new variables or startup validation will fail (StrictUndefined raises on missing variables).

### Pattern 5: Hot Reload — New Environment Per Render

**What:** The existing `render_template()` function already calls `build_template_env()` on every invocation, which creates a fresh `Environment` with a fresh `FileSystemLoader`. Since no Environment is cached between calls, templates are re-read from disk on every render call. This is the existing behavior — no change needed.

**Verification:** Jinja2 3.x docs confirm that `auto_reload=True` (the default) causes the loader to check if source changed before using cached compiled templates. Creating a new `Environment` per call is even more direct — the in-memory cache is discarded each time.

**Source:** jinja.palletsprojects.com/en/stable/api/ — confirmed default `auto_reload=True`

The CONTEXT.md decision for hot reload is already satisfied by the existing architecture.

### Pattern 6: VRBO/RVshare Operator Notification Email

**What:** When a VRBO or RVshare pre-arrival (or welcome) message is prepared, email the operator with the full rendered message text ready to copy-paste into the platform.

**Pattern:** Follow the existing `aiosmtplib` pattern from `app/compliance/emailer.py`. Create a dedicated operator notification emailer in `app/communication/emailer.py`.

```python
# app/communication/emailer.py
# Source: app/compliance/emailer.py pattern
async def send_operator_notification(
    *,
    config: AppConfig,
    booking: Booking,
    prop_config: PropertyConfig,
    message_type: str,       # "welcome" | "pre_arrival"
    rendered_message: str,   # Full copy-pasteable text
) -> None:
    """Notify operator to manually send a VRBO/RVshare message."""
    subject = f"[Action Required] {message_type.replace('_', ' ').title()} message ready — {booking.guest_name}"
    body = _build_notification_body(booking, prop_config, rendered_message)

    msg = EmailMessage()
    msg["From"] = config.smtp_from_email
    msg["To"] = config.smtp_from_email  # Operator receives the alert
    msg["Subject"] = subject
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname=config.smtp_host,
        port=config.smtp_port,
        username=config.smtp_user,
        password=config.smtp_password,
        use_tls=(config.smtp_port == 465),
        start_tls=(config.smtp_port == 587),
    )
```

**Email body structure for copy-paste usability:**

```
[Action Required] Pre-arrival message ready to send on VRBO

Guest: Jane Smith
Reservation ID: HA-12345678 (use this to find the conversation in VRBO)
Check-in: March 15, 2026

MESSAGE TO SEND (copy everything below this line):
─────────────────────────────────────────────────
Hi Jane,

Your stay at Jay is coming up soon! ...
[full message text]
─────────────────────────────────────────────────

Once sent, confirm via: POST /communication/confirm/{log_id}
Or visit the dashboard to mark as sent.
```

### Pattern 7: Booking Ingestion Integration Hook

**What:** The existing `_create_resort_submissions()` in `normalizer.py` is the established pattern for post-ingestion side effects. Phase 6 follows the same hook point.

**Where to hook in:** After bookings are upserted in `ingest_csv()` and `create_manual_booking()`, call a new `_create_communication_logs()` function that:
1. Creates a `CommunicationLog` row for welcome message
2. Creates a `CommunicationLog` row for pre_arrival message (with `scheduled_for` computed)
3. Registers the APScheduler DateTrigger job for Airbnb pre-arrival
4. Sends the operator notification email for VRBO/RVshare welcome (or schedules it)

**For Airbnb welcome:** Mark immediately as `native_configured` — no scheduling needed, Airbnb sends it natively.

### Anti-Patterns to Avoid

- **Scheduling at startup without rebuilding from DB:** APScheduler uses in-memory job store; all jobs are lost on Docker restart. Always rebuild pending pre-arrival jobs at startup.
- **Passing `scheduler` as a parameter through layers:** It is a module-level singleton in app/main.py. Import directly where needed, same as `get_config()`.
- **Re-rendering templates at send time from stale data:** Render the message when the job fires (at send time), not at schedule time — this ensures the most current config/template is used, consistent with hot reload intent.
- **Caching the Jinja2 Environment across calls:** The current `build_template_env()` already avoids this. Don't introduce a module-level cached `Environment` for message templates.
- **Auto-marking VRBO/RVshare messages as sent:** Per CONTEXT.md, operator must explicitly confirm via endpoint. Never auto-advance status.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SMTP retry logic | Custom retry loop | Existing `send_with_retry()` in app/compliance/emailer.py (tenacity, 4 attempts, exponential backoff) | Already built and tested |
| Template rendering | Custom string interpolation | Existing `render_template()` in app/templates.py | StrictUndefined catches variable typos; per-property override resolution already handled |
| One-time future scheduling | cron jobs, threading.Timer | APScheduler DateTrigger (`'date'` trigger) | Already set up; handles async coroutines natively |
| SMTP connection/auth | Raw socket code | aiosmtplib.send() | Already in project; handles TLS/STARTTLS selection |

**Key insight:** The compliance module (Phase 5) established every pattern Phase 6 needs. Treat communication like a second compliance pipeline — same structure, different domain.

---

## Common Pitfalls

### Pitfall 1: Lost APScheduler Jobs on Docker Restart

**What goes wrong:** Pre-arrival jobs registered with the in-memory MemoryJobStore are lost when the container restarts. If a restart happens between booking import and the 9:30am send time, the message is never sent.

**Why it happens:** APScheduler's default job store is MemoryJobStore. Jobs are not persisted to disk or database.

**How to avoid:** During app lifespan startup (after `scheduler.start()`), query `communication_logs` for rows where `message_type='pre_arrival'`, `status='pending'`, and `scheduled_for > now()`. Re-register each as a DateTrigger job.

**Warning signs:** Guests don't receive pre-arrival messages for bookings imported before a system restart.

### Pitfall 2: DateTrigger with Past run_date Silently No-Ops

**What goes wrong:** If `run_date` is in the past when `add_job()` is called (e.g., a booking imported with check-in tomorrow), APScheduler's DateTrigger `get_next_fire_time()` returns `None` — the job is never added to the schedule and never fires.

**Why it happens:** DateTrigger is a one-shot trigger that only fires if the time is in the future.

**How to avoid:** Before calling `scheduler.add_job()`, check `run_at > datetime.now(timezone.utc)`. If the window has passed, log a warning and mark the communication_log row with an appropriate status/error rather than silently dropping it.

**Warning signs:** No APScheduler job registered, but also no error logged.

### Pitfall 3: Template Variable Mismatch After Adding New Fields

**What goes wrong:** Adding new variables to templates (e.g., `{{ wifi_password }}`) without updating `SAMPLE_BOOKING_DATA` in `app/templates.py` causes startup validation to fail with `UndefinedError`.

**Why it happens:** `validate_all_templates()` renders every template with `SAMPLE_BOOKING_DATA` using StrictUndefined.

**How to avoid:** Whenever a new variable is added to any template, add a corresponding key to `SAMPLE_BOOKING_DATA` in the same commit. This is an existing project convention.

**Warning signs:** App fails to start with `UndefinedError: 'wifi_password' is undefined`.

### Pitfall 4: Airbnb Welcome Native Config Confusion

**What goes wrong:** System attempts to send a welcome message to Airbnb guests programmatically, conflicting with or duplicating Airbnb's native scheduled messaging.

**Why it happens:** Airbnb's native scheduled messages run automatically after a booking is confirmed. If code also sends a welcome, guests receive two messages.

**How to avoid:** For Airbnb bookings, the welcome `CommunicationLog` row should be created with `status='native_configured'` immediately. No message text is rendered, no email is sent, no scheduler job is registered. The row exists purely for audit/tracking.

**Warning signs:** Airbnb guests report receiving duplicate welcome messages.

### Pitfall 5: Session Lifecycle in Scheduler Jobs

**What goes wrong:** APScheduler jobs run outside of FastAPI request context. Using `get_db()` (a FastAPI dependency) inside a scheduler job fails.

**Why it happens:** FastAPI's `get_db()` is a generator-based dependency injection mechanism tied to request lifecycle.

**How to avoid:** Use `SessionLocal()` directly inside scheduler job functions, identical to the pattern in `app/compliance/urgency.py`:

```python
async def send_pre_arrival_message(booking_id: int) -> None:
    db: Session = SessionLocal()
    try:
        # ... do work ...
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Pre-arrival send failed", booking_id=booking_id)
    finally:
        db.close()
```

**Warning signs:** `RuntimeError: No generator dependency` or similar FastAPI injection errors in scheduler logs.

### Pitfall 6: Timezone Handling for 9:30am Send Time

**What goes wrong:** Scheduling pre-arrival at "9:30am" without specifying a timezone sends at the wrong time for guests.

**Why it happens:** APScheduler DateTrigger with a naive datetime uses the local server timezone, which may be UTC in Docker.

**How to avoid:** The decision is "9-10am" without specifying the property's local timezone. For simplicity given the property is in the Eastern US (Fort Myers Beach), hardcode the send time to a UTC equivalent (e.g., 14:00 UTC = 9:00 AM EST / 10:00 AM EDT — or 13:30 UTC as a compromise). Document this assumption clearly. Alternatively, add a `timezone` field to `PropertyConfig` for future extensibility. Use timezone-aware datetimes throughout.

---

## Code Examples

### Scheduling a Pre-Arrival Job

```python
# Source: APScheduler 3.x docs + existing app/main.py pattern
from datetime import date, datetime, time, timedelta, timezone
from apscheduler.triggers.date import DateTrigger
from app.main import scheduler

def schedule_pre_arrival_job(booking_id: int, check_in_date: date) -> datetime | None:
    """Schedule pre-arrival message. Returns scheduled_for or None if too late."""
    send_date = check_in_date - timedelta(days=2)
    # 14:00 UTC = 9:00 AM EST / 10:00 AM EDT — covers Eastern US properties
    run_at = datetime(send_date.year, send_date.month, send_date.day,
                      14, 0, 0, tzinfo=timezone.utc)

    if run_at <= datetime.now(timezone.utc):
        log.warning("Pre-arrival send time already passed", booking_id=booking_id)
        return None

    scheduler.add_job(
        send_pre_arrival_message,
        trigger=DateTrigger(run_date=run_at),
        id=f"pre_arrival_{booking_id}",
        args=[booking_id],
        replace_existing=True,
    )
    return run_at
```

### Rendering a Message Template

```python
# Source: Existing app/templates.py render_template() — no changes needed
from app.templates import render_template

rendered = render_template(
    property_slug=prop.slug,
    template_name="pre_arrival.txt",
    data={
        "guest_name": booking.guest_name,
        "property_name": prop_config.display_name,
        "checkin_date": booking.check_in_date.strftime("%B %d, %Y"),
        "checkout_date": booking.check_out_date.strftime("%B %d, %Y"),
        "lock_code": prop_config.lock_code,
        "site_number": prop_config.site_number,
        "resort_checkin_instructions": prop_config.resort_checkin_instructions,
        "wifi_password": prop_config.wifi_password,
        "address": prop_config.address,
        "check_in_time": prop_config.check_in_time,
        "check_out_time": prop_config.check_out_time,
        "parking_instructions": prop_config.parking_instructions,
        "local_tips": prop_config.local_tips,
        **{f"custom_{k}": v for k, v in prop_config.custom.items()},
        # OR expose as dict: "custom": prop_config.custom
        # Then templates use {{ custom.pool_code }}
    },
)
```

**Recommendation for custom variables:** Expose `custom` as a dict object in the template context. Jinja2 supports `{{ custom.key }}` attribute-style access on dicts. This is cleaner than flattening to `custom_key` prefixed names.

### Creating CommunicationLog rows on booking ingestion

```python
# In app/ingestion/normalizer.py — parallel to _create_resort_submissions()
def _create_communication_logs(
    inserted_booking_ids: list[str],
    platform: str,
    db: Session,
) -> None:
    """Create pending CommunicationLog records for newly inserted bookings."""
    booking_rows = db.execute(
        select(Booking.id, Booking.check_in_date, Booking.platform_booking_id).where(
            Booking.platform == platform,
            Booking.platform_booking_id.in_(inserted_booking_ids),
        )
    ).all()

    for booking_id, check_in_date, _ in booking_rows:
        # Welcome message
        welcome_status = "native_configured" if platform == "airbnb" else "pending"
        db.add(CommunicationLog(
            booking_id=booking_id,
            message_type="welcome",
            platform=platform,
            status=welcome_status,
        ))

        # Pre-arrival message
        send_date = check_in_date - timedelta(days=2)
        run_at = datetime(send_date.year, send_date.month, send_date.day, 14, 0, 0, tzinfo=timezone.utc)
        db.add(CommunicationLog(
            booking_id=booking_id,
            message_type="pre_arrival",
            platform=platform,
            status="pending",
            scheduled_for=run_at,
        ))

    db.commit()
```

### Startup Job Rebuild

```python
# In app/main.py lifespan, after scheduler.start()
from app.communication.messenger import rebuild_pre_arrival_jobs

await rebuild_pre_arrival_jobs()  # async because it calls SessionLocal
log.info("Pre-arrival scheduler jobs rebuilt")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling for send time | APScheduler DateTrigger | Already in project | Efficient; no busy polling |
| Hard-coded message text | Jinja2 templates | Already in project | Operator-editable without code changes |
| Synchronous SMTP | aiosmtplib (async) | Already in project | Non-blocking; no thread contention |

**Key existing decision documented in STATE.md:**
- `replace_existing=True` on `scheduler.add_job` — prevents duplicate job registration on Docker restart. Must apply to pre-arrival jobs too.
- `AsyncIOScheduler` (not BackgroundScheduler) — already on existing event loop; correct for async job functions.
- `StrictUndefined` in Jinja2 — raises UndefinedError on template variable typos at render time rather than silently emitting empty string.
- `SAMPLE_BOOKING_DATA` must cover all template variables — adding a new variable to any template requires updating this dict.

---

## Open Questions

1. **Timezone for 9:30am send time**
   - What we know: Properties are in Eastern US (Fort Myers Beach); Docker container likely runs UTC.
   - What's unclear: Should the system use a hardcoded UTC offset (14:00 UTC) or add a `timezone` field to PropertyConfig?
   - Recommendation: Hardcode 14:00 UTC (conservative — always within the 9-10am window regardless of EST/EDT). Add a comment in the code. This can be made configurable in a future phase if properties span timezones.

2. **Rendered message storage**
   - What we know: CONTEXT.md says store rendered text for VRBO/RVshare operator copy-paste.
   - What's unclear: Should rendered text be stored for Airbnb pre-arrival messages too (audit trail)?
   - Recommendation: Store rendered text for all messages where the system renders a template (Airbnb pre-arrival, VRBO/RVshare both types). Skip for Airbnb welcome (native — system never renders it). Use `Text` column type (no length limit) since messages can be several paragraphs.

3. **Pre-arrival for VRBO/RVshare welcome messages**
   - What we know: VRBO/RVshare welcome is also semi-automated (prepare + email operator to send manually).
   - What's unclear: Should the VRBO/RVshare welcome operator notification be sent immediately on booking ingestion, or via a scheduler job like pre-arrival?
   - Recommendation: Send the welcome notification email immediately in the ingestion hook (no scheduling needed — it's triggered by the booking arriving). Only pre-arrival uses APScheduler.

4. **Confirm endpoint: one endpoint or per-log-id?**
   - What we know: "operator marks message as sent via button/endpoint"
   - What's unclear: Should there be `POST /communication/confirm/{log_id}` or `POST /communication/confirm/welcome/{booking_id}` style?
   - Recommendation: Use `POST /communication/confirm/{log_id}` — cleaner, avoids ambiguity with message type, consistent with the `submission_id` style in compliance API.

---

## Sources

### Primary (HIGH confidence)

- **Existing codebase** (app/templates.py, app/compliance/urgency.py, app/compliance/emailer.py, app/main.py, app/ingestion/normalizer.py) — direct reading of implemented patterns
- **APScheduler 3.x docs** (apscheduler.readthedocs.io/en/3.x/userguide.html) — DateTrigger, misfire_grace_time, MemoryJobStore behavior, add_job API
- **APScheduler 3.x DateTrigger docs** (apscheduler.readthedocs.io/en/3.x/modules/triggers/date.html) — run_date parameter, timezone parameter, past date behavior
- **APScheduler AsyncIOScheduler docs** (apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html) — async job function support confirmation
- **Jinja2 3.1.x docs** (jinja.palletsprojects.com/en/stable/api/) — auto_reload=True default, FileSystemLoader uptodate checking, Environment cache behavior

### Secondary (MEDIUM confidence)

- **Airbnb Help Center** (airbnb.com/resources/hosting-homes/a/using-scheduled-messages-to-save-time-275) — Confirmed Airbnb native scheduled messaging has 3 triggers: booking confirmed, check-in, checkout; operator sets these up via Inbox > Scheduled Messages; system sends automatically
- **WebSearch: Airbnb scheduled messaging 2026** — Confirmed API access is restricted to official partners; native scheduled messaging is the correct approach for non-partner hosts

### Tertiary (LOW confidence)

- None — all findings verified with official sources or direct codebase inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries already in project; versions verified via `uv run python -c "import importlib.metadata"`
- Architecture: HIGH — Patterns directly observed in existing Phase 5 code; APScheduler usage verified against official docs
- Pitfalls: HIGH — Most pitfalls are directly derivable from reading existing code + official APScheduler docs; timezone pitfall is MEDIUM (pragmatic recommendation, not official guidance)
- Template hot reload: HIGH — Confirmed by direct code reading: build_template_env() is called per render() invocation; no module-level Environment cache exists

**Research date:** 2026-02-28
**Valid until:** 2026-03-30 (libraries are stable; APScheduler 3.x is actively maintained)
