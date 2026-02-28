# Phase 5: Resort PDF Compliance - Research

**Researched:** 2026-02-27
**Domain:** PDF form filling, SMTP email delivery, background scheduling, webhook confirmation
**Confidence:** HIGH (core libraries verified via official docs and PyPI)

## Summary

This phase builds an automated pipeline that: (1) fills an AcroForm PDF on booking import, (2) emails it with the booking confirmation PDF attachment, (3) tracks status through a webhook-triggered confirmation flow, and (4) runs a daily urgency check. All four areas have well-established Python solutions — no hand-rolling required.

The critical pre-planning blocker (AcroForm vs. XFA) has a definitive resolution path: PyMuPDF can detect XFA via low-level dict inspection, and the correct cross-viewer rendering strategy is `field.update()` + `doc.bake()` — NOT `doc.need_appearances()` alone, which fails on macOS Preview and iOS Mail. The `bake()` method embeds appearance streams permanently into the PDF, guaranteeing consistent display across all viewers.

For email delivery, use `aiosmtplib` (async SMTP, v5.1.0) with Python's stdlib `EmailMessage` for attachment handling. For scheduling, use `APScheduler` 3.x `AsyncIOScheduler` integrated into the existing FastAPI lifespan. For retry logic, use `tenacity` (v9.1.4) with exponential backoff.

**Primary recommendation:** Fill AcroForm fields with PyMuPDF, call `field.update()` on each widget, then `doc.bake()` before saving — this is the only approach that works reliably in macOS Preview and iOS Mail.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (pymupdf) | 1.27.1 | AcroForm PDF filling | Already decided in STATE.md; only library that regenerates appearance streams correctly |
| aiosmtplib | 5.1.0 | Async SMTP email delivery | Native asyncio, works with FastAPI event loop, simple API |
| APScheduler | 3.11.2 | Daily urgency check scheduling | Already chosen in STATE.md; 3.x is stable, 4.0 is alpha |
| tenacity | 9.1.4 | Email retry with exponential backoff | Standard Python retry library, async-native |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `email` | (stdlib) | EmailMessage + add_attachment | Building MIME messages with PDF attachments |
| Python stdlib `smtplib` | (stdlib) | Sync SMTP (fallback) | Only if aiosmtplib causes issues; prefer aiosmtplib |
| SQLAlchemy 2.0 | (existing) | `ResortSubmission` model + queries | All DB operations use existing ORM pattern |
| Alembic | (existing) | Migration for new table | New `resort_submissions` table |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aiosmtplib | fastapi-mail | fastapi-mail is heavier, adds Jinja2 templating; overkill for fixed template |
| aiosmtplib | smtplib in thread pool | Works but blocking; aiosmtplib is cleaner in async context |
| tenacity | manual retry loop | Tenacity handles backoff, logging hooks, exception filtering without boilerplate |
| APScheduler 3.x | Celery beat | Celery requires broker (Redis/RabbitMQ); APScheduler runs in-process with no infra |

**Installation:**
```bash
uv add pymupdf aiosmtplib apscheduler tenacity
```

## Architecture Patterns

### Recommended Project Structure

```
app/
├── compliance/
│   ├── __init__.py
│   ├── pdf_filler.py        # PyMuPDF form filling logic
│   ├── emailer.py           # aiosmtplib send + tenacity retry
│   ├── submission.py        # Orchestrator: fill PDF → send email → update DB
│   └── urgency.py           # Daily check: find pending within 3 days
├── api/
│   └── compliance.py        # Router: POST /compliance/confirm/{booking_id}
├── models/
│   └── resort_submission.py # ResortSubmission ORM model
alembic/versions/
└── 005_compliance_tables.py # resort_submissions table migration
```

### Pattern 1: AcroForm Detection (Pre-Phase Blocker Resolution)

**What:** Before building the PDF pipeline, verify the Sun Retreats form is AcroForm (not XFA). PyMuPDF cannot fill XFA forms.

**When to use:** One-time verification before implementation.

**Example:**
```python
# Source: PyMuPDF low-level interface docs
import pymupdf

def detect_form_type(pdf_path: str) -> str:
    """Returns 'acroform', 'xfa', or 'none'."""
    doc = pymupdf.open(pdf_path)
    if not doc.is_pdf:
        return "none"

    cat = doc.pdf_catalog()
    what, value = doc.xref_get_key(cat, "AcroForm")

    if what == "null":
        return "none"

    # AcroForm exists — check for XFA sub-key
    if what == "xref":
        acroform_xref = int(value.replace("0 R", "").strip())
        xfa_what, _ = doc.xref_get_key(acroform_xref, "XFA")
        if xfa_what != "null":
            return "xfa"  # REQUIRES different approach (Playwright HTML-to-PDF)

    return "acroform"  # PyMuPDF can fill this
```

**If XFA:** The planned approach (PyMuPDF form filling) will not work. Escalate before building.

### Pattern 2: AcroForm Filling with Cross-Viewer Compatibility

**What:** Fill all AcroForm fields from the JSON mapping, update appearance streams, then bake to embed appearances permanently.

**When to use:** Every time a PDF needs to be filled for email submission.

**Critical:** `field.update()` alone is NOT sufficient for macOS Preview and iOS Mail. Must call `doc.bake()` before saving.

**Example:**
```python
# Sources: Artifex blog (official PyMuPDF publisher), DeepWiki PyMuPDF form-fields
import pymupdf
import json
from pathlib import Path
from datetime import date

def fill_resort_form(
    template_pdf_path: str,
    mapping_json_path: str,
    booking_data: dict,
    property_data: dict,
) -> bytes:
    """
    Fill an AcroForm PDF from a JSON field mapping.
    Returns the filled PDF as bytes.

    Raises ValueError if template is not an AcroForm PDF.
    """
    # Load mapping
    mapping = json.loads(Path(mapping_json_path).read_text())
    field_map = mapping["fields"]

    # Build field values from three source types
    field_values: dict[str, str] = {}
    for pdf_field_name, spec in field_map.items():
        source = spec["source"]
        if source == "static":
            field_values[pdf_field_name] = spec["value"]
        elif source == "booking":
            raw = booking_data.get(spec["field"], "")
            # Format dates if needed
            if "format" in spec and isinstance(raw, date):
                raw = raw.strftime(spec["format"].replace("MM", "%m").replace("DD", "%d").replace("YYYY", "%Y"))
            field_values[pdf_field_name] = str(raw) if raw is not None else ""
        elif source == "property":
            field_values[pdf_field_name] = str(property_data.get(spec["field"], ""))

    # Open and fill the PDF
    doc = pymupdf.open(template_pdf_path)

    for page in doc:
        for widget in page.widgets():
            if widget.field_name in field_values:
                widget.field_value = field_values[widget.field_name]
                widget.update()  # Regenerates appearance stream for this field

    # Bake: embeds appearance streams permanently — required for macOS Preview + iOS Mail
    doc.bake()

    # Return as bytes (caller saves or attaches to email)
    return doc.tobytes()
```

**Note:** `doc.tobytes()` returns the filled PDF as bytes without touching the filesystem — use this for in-memory email attachment.

### Pattern 3: Enumerate PDF Form Fields (Validation Helper)

**What:** Inspect what fields exist in the actual PDF form. Run once against the real Sun Retreats form to confirm field names match the JSON mapping.

**Example:**
```python
# Source: PyMuPDF official docs - widget enumeration
import pymupdf

def list_form_fields(pdf_path: str) -> list[dict]:
    """List all form field names and types in a PDF."""
    doc = pymupdf.open(pdf_path)
    fields = []
    for page_num, page in enumerate(doc):
        for widget in page.widgets():
            fields.append({
                "page": page_num,
                "name": widget.field_name,
                "type": widget.field_type_string,
                "current_value": widget.field_value,
            })
    return fields
```

### Pattern 4: Email Delivery with Multiple PDF Attachments

**What:** Compose and send an email with two PDF attachments (filled form + booking confirmation).

**Example:**
```python
# Sources: Python stdlib email.examples docs, aiosmtplib PyPI docs
from email.message import EmailMessage
import aiosmtplib

async def send_resort_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_addr: str,
    to_addr: str,
    subject: str,
    body: str,
    filled_form_bytes: bytes,
    filled_form_filename: str,
    confirmation_bytes: bytes,
    confirmation_filename: str,
) -> None:
    """
    Send email with two PDF attachments.
    Raises aiosmtplib.SMTPException on failure (caller handles retry).
    """
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    # Attach filled booking form
    msg.add_attachment(
        filled_form_bytes,
        maintype="application",
        subtype="pdf",
        filename=filled_form_filename,
    )

    # Attach platform booking confirmation
    msg.add_attachment(
        confirmation_bytes,
        maintype="application",
        subtype="pdf",
        filename=confirmation_filename,
    )

    await aiosmtplib.send(
        msg,
        hostname=smtp_host,
        port=smtp_port,
        username=smtp_user,
        password=smtp_password,
        use_tls=(smtp_port == 465),   # Direct TLS for port 465
        start_tls=(smtp_port == 587), # STARTTLS for port 587
    )
```

### Pattern 5: Email Retry with Tenacity

**What:** Wrap email send with exponential backoff retry. Surface only after all retries exhausted.

**Example:**
```python
# Source: Tenacity official docs
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
import logging

log = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(4),          # 4 total attempts (1 + 3 retries)
    wait=wait_exponential(multiplier=2, min=10, max=120),  # 10s, 20s, 40s (capped at 120s)
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,  # Re-raise the final exception so caller knows all retries failed
)
async def send_with_retry(...) -> None:
    await send_resort_email(...)
```

**Rationale for 4 attempts / 10-120s backoff:** SMTP failures are often transient (server busy, connection drop). 4 attempts over ~90 seconds is enough to handle brief outages without blocking indefinitely. If all fail, the system surfaces the error (logs + status stays pending).

### Pattern 6: APScheduler Daily Urgency Check (AsyncIOScheduler)

**What:** Run urgency check once per day. Integrates with existing FastAPI lifespan pattern.

**Example:**
```python
# Source: APScheduler 3.x official docs, Sentry FastAPI guide
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager
from fastapi import FastAPI

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    scheduler.add_job(
        run_urgency_check,        # async def or sync def
        trigger=CronTrigger(hour=8, minute=0),  # 08:00 daily
        id="urgency_check",
        replace_existing=True,
    )
    scheduler.start()

    yield  # App running

    # --- Shutdown ---
    scheduler.shutdown()
```

**Use `AsyncIOScheduler` (not `BackgroundScheduler`)** because the app is async. `AsyncIOScheduler` runs jobs on the same asyncio event loop as FastAPI/uvicorn, allowing jobs to be `async def` coroutines.

### Pattern 7: n8n Webhook Confirmation Endpoint

**What:** FastAPI endpoint that n8n calls when it detects a Campspot confirmation email.

**Example:**
```python
# Pattern follows existing router style in app/api/
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.resort_submission import ResortSubmission

router = APIRouter(prefix="/compliance", tags=["compliance"])

@router.post("/confirm/{booking_id}")
def mark_confirmed(booking_id: int, db: Session = Depends(get_db)) -> dict:
    """Called by n8n when Campspot automated confirmation email is received."""
    submission = db.get(ResortSubmission, booking_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status == "confirmed":
        return {"status": "already_confirmed"}  # Idempotent
    submission.status = "confirmed"
    db.commit()
    return {"status": "confirmed", "booking_id": booking_id}
```

### Pattern 8: Confirmation File Matching

**What:** Match a booking to its platform confirmation PDF by looking for the booking's `platform_booking_id` in the `confirmations/` directory filenames.

**Example:**
```python
# Source: project decision — filename contains confirmation code (e.g., HMAB1234.pdf)
from pathlib import Path

def find_confirmation_file(
    confirmation_code: str,
    confirmations_dir: str,
) -> Path | None:
    """
    Find confirmation PDF by scanning filenames for the confirmation code.

    Matching: case-insensitive containment check.
    Example: confirmation_code="HMAB1234" matches "HMAB1234.pdf", "booking_HMAB1234_conf.pdf"

    Returns None if no file found (submission proceeds without confirmation attachment,
    or is queued until file appears).
    """
    base = Path(confirmations_dir)
    if not base.exists():
        return None

    code_lower = confirmation_code.lower()
    for pdf_file in base.glob("*.pdf"):
        if code_lower in pdf_file.name.lower():
            return pdf_file

    return None
```

**Decision needed by planner:** What happens when confirmation file is not found at submission time? Options: (a) submit without it and attach when found, (b) wait up to N minutes polling. Given the architecture, option (a) is simpler and matches the "auto-submit immediately" decision.

### Pattern 9: Preview Mode (Count-Based)

**What:** Track how many submissions have been auto-sent. First N require manual approval.

**DB-side:** Store `auto_submit_count` in a config or settings table, or count confirmed auto-submissions in `resort_submissions`. Simpler: query `COUNT(*) WHERE submitted_automatically=true`.

**Recommended threshold:** 3. First 3 submissions require operator to review filled PDF before sending. After 3 successful submissions, full auto-submit activates. Store threshold in `base.yaml` (non-secret).

**Why 3:** Enough to verify field mapping correctness across at least 2 properties (Jay and Minnie) without delaying real operations.

### Anti-Patterns to Avoid

- **Using `doc.need_appearances(True)` alone:** Delegates appearance rendering to the PDF viewer. macOS Preview and iOS Mail do NOT honor this flag — fields display blank. Always follow with `doc.bake()`.
- **Saving filled PDF to disk before emailing:** Use `doc.tobytes()` to keep it in memory. Avoids temp file cleanup and race conditions.
- **Using `BackgroundScheduler` in async app:** Runs jobs in a thread pool. Use `AsyncIOScheduler` so jobs share the event loop and can be `async def`.
- **Hardcoding SMTP credentials in YAML:** SMTP credentials are secrets. They go in `.env` only, following the established pattern.
- **Querying all bookings in urgency check:** Filter by `status='pending'` and `check_in_date <= today + 3 days` at the DB level. Do not load all bookings.
- **Firing urgency email per-booking on every check:** De-duplicate — only send urgency alerts for bookings that crossed the threshold since the last check, OR send a daily digest. Avoid alert storms.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom loop with `time.sleep` | `tenacity` | Edge cases: exception filtering, jitter, before-sleep hooks, proper async sleep |
| Scheduled daily job | `threading.Timer` or `asyncio.sleep` loop | `APScheduler` AsyncIOScheduler | Handles app restart, missed job detection, proper lifecycle management |
| PDF appearance stream generation | Custom AP dict injection | `pymupdf.bake()` | MuPDF internals handle font encoding, glyph lookup, correct PDF structure |
| SMTP MIME construction | String-building multipart body | `email.EmailMessage.add_attachment()` | Correct Content-Disposition headers, boundary encoding, charset handling |
| XFA form detection | String search in raw PDF bytes | `pymupdf.xref_get_key()` | Structured dict traversal, correct xref resolution |

**Key insight:** PDF appearance stream generation and SMTP MIME encoding both have subtle standards-compliance requirements. Both are solved by established libraries; hand-rolled solutions inevitably break on specific viewers or email clients.

## Common Pitfalls

### Pitfall 1: Blank Fields in macOS Preview and iOS Mail

**What goes wrong:** Form is filled with `field.field_value = "..."` and `field.update()`, saved with `doc.save()`. PDF looks correct in Adobe Reader but shows empty fields in macOS Preview and iOS Mail.

**Why it happens:** `field.update()` regenerates the appearance stream, but `doc.save()` without `doc.bake()` preserves the form structure. macOS Preview and iOS Mail do not regenerate appearance streams on open — they require them to be pre-embedded.

**How to avoid:** Always call `doc.bake()` after setting all field values and before `doc.tobytes()` or `doc.save()`. Order: set values → `field.update()` per field → `doc.bake()` once → serialize.

**Warning signs:** Test the filled PDF by opening in macOS Preview AND forwarding to an iOS device before deploying.

### Pitfall 2: XFA Form Instead of AcroForm

**What goes wrong:** The Sun Retreats form is XFA — PyMuPDF iterates zero widgets, the filled PDF is identical to the template.

**Why it happens:** XFA forms store their structure in an XML packet, not in AcroForm field dictionaries. PyMuPDF's `page.widgets()` returns nothing for XFA forms.

**How to avoid:** Run `detect_form_type()` against the actual resort PDF before building the pipeline. If XFA, an entirely different approach is needed (Playwright HTML-to-PDF).

**Warning signs:** `len(list(page.widgets())) == 0` on every page when you know the form has fields.

### Pitfall 3: Confirmation File Not Yet Present at Submission Time

**What goes wrong:** Booking is imported, PDF is filled, but the confirmation PDF hasn't arrived in `confirmations/` yet (n8n or mail rule hasn't processed it). Email is sent without the second attachment.

**Why it happens:** The system auto-submits immediately on import; confirmation files arrive asynchronously from a separate automation.

**How to avoid:** Design the submission flow to handle missing confirmation gracefully. Two options:
1. Send with only the filled form, and emit a warning log.
2. Store the submission in "pending_confirmation_file" status and retry once the file appears (polling or webhook trigger).

**Recommendation (discretion area):** Use option 1 for simplicity. Log the missing confirmation at WARNING level. The resort contact receives the filled form immediately; the confirmation PDF can be forwarded separately if needed.

**Warning signs:** `find_confirmation_file()` returning `None` for most bookings in early operation.

### Pitfall 4: Preview Mode Race Condition

**What goes wrong:** Two bookings are imported simultaneously. Both read the auto-submit count as 2 (below threshold of 3). Both proceed to full auto-submit, bypassing preview for the third verification.

**Why it happens:** Non-atomic read-then-write of the submission counter.

**How to avoid:** Use the count of existing `resort_submissions` rows with `submitted_automatically=true` as the atomic check — a DB `SELECT COUNT(*)` in the same transaction as the insert. Alternatively, use a DB-level counter with `SELECT ... FOR UPDATE` semantics.

**Warning signs:** Preview mode completing after only 1-2 manual approvals.

### Pitfall 5: APScheduler Not Stopped on Shutdown

**What goes wrong:** `scheduler.start()` in lifespan startup but no `scheduler.shutdown()` in teardown. On app restart (especially in Docker), the scheduler thread/task leaks.

**Why it happens:** Forgetting the shutdown call in the `finally` or post-yield block of lifespan.

**How to avoid:** Always call `scheduler.shutdown()` in the post-yield portion of the lifespan context manager. `AsyncIOScheduler.shutdown()` waits for running jobs to complete.

### Pitfall 6: SMTP Credentials in YAML Config

**What goes wrong:** SMTP host/user/password added to `base.yaml` and committed to git.

**Why it happens:** Following the pattern for non-secret config, forgetting SMTP credentials are secrets.

**How to avoid:** SMTP credentials (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`) go in `.env` only. Non-secret SMTP settings (like the `from` display name) can go in `base.yaml`. This matches the existing `database_url` pattern.

### Pitfall 7: docker-compose Missing `confirmations/` Volume

**What goes wrong:** `confirmations/` directory exists on the host but is not mounted into the container. `find_confirmation_file()` always returns `None`.

**Why it happens:** New directory requirement not added to `docker-compose.yml` volumes.

**How to avoid:** Add `./confirmations:/app/confirmations:ro` to the app service volumes in `docker-compose.yml`. The `confirmations_dir` config key in `base.yaml` should default to `./confirmations`.

## Code Examples

### Inspecting Real PDF Fields (Run Against Actual Sun Retreats Form)

```python
# Run this once against the actual form to get real field names
# Source: PyMuPDF official docs widget enumeration
import pymupdf

doc = pymupdf.open("sun_retreats_booking_form.pdf")
print(f"Is form PDF: {doc.is_form_pdf}")
print(f"Form type: {detect_form_type('sun_retreats_booking_form.pdf')}")
for page_num, page in enumerate(doc):
    for widget in page.widgets():
        print(f"Page {page_num}: {widget.field_name!r} ({widget.field_type_string}) = {widget.field_value!r}")
```

### ResortSubmission Model

```python
# Source: follows existing SQLAlchemy 2.0 mapped_column pattern in codebase
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db import Base

class ResortSubmission(Base):
    __tablename__ = "resort_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    # Status values: "pending" | "submitted" | "confirmed"

    submitted_automatically: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    # True = auto-submitted; False = manual approval required (preview mode)

    is_urgent: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    # True = check-in within 3 days and not yet submitted

    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### Subject Line Formatting

```python
# Source: locked decision from CONTEXT.md
def format_email_subject(guest_name: str, lot_number: str, check_in: date, check_out: date) -> str:
    """
    Example: "Booking Form - John Smith - Lot 110 - Mar 5-8"
    Same-month: "Mar 5-8"; cross-month: "Mar 31 - Apr 2"
    """
    if check_in.month == check_out.month:
        dates_str = f"{check_in.strftime('%b')} {check_in.day}-{check_out.day}"
    else:
        dates_str = f"{check_in.strftime('%b')} {check_in.day} - {check_out.strftime('%b')} {check_out.day}"
    return f"Booking Form - {guest_name} - Lot {lot_number} - {dates_str}"
```

### Urgency Check Query (SQLAlchemy 2.0)

```python
# Source: follows existing SQLAlchemy 2.0 select() pattern in codebase
from datetime import date, timedelta
from sqlalchemy import select, and_
from app.models.resort_submission import ResortSubmission
from app.models.booking import Booking

def get_urgent_pending_submissions(db: Session) -> list[tuple[ResortSubmission, Booking]]:
    """Find pending submissions where check-in is within 3 days."""
    deadline = date.today() + timedelta(days=3)
    stmt = (
        select(ResortSubmission, Booking)
        .join(Booking, ResortSubmission.booking_id == Booking.id)
        .where(
            and_(
                ResortSubmission.status == "pending",
                Booking.check_in_date <= deadline,
            )
        )
    )
    return db.execute(stmt).all()
```

### Config Extensions (AppConfig additions)

```python
# Add to AppConfig in app/config.py — secrets in .env, non-secrets in base.yaml

# In AppConfig (from .env — secrets):
smtp_host: str = "smtp.gmail.com"       # SMTP_HOST env var
smtp_port: int = 587                     # SMTP_PORT env var
smtp_user: str = ""                      # SMTP_USER env var
smtp_password: str = ""                  # SMTP_PASSWORD env var

# In base.yaml (non-secret):
# smtp_from_name: "Thomas"              — display name for From header
# confirmations_dir: "./confirmations"  — path to booking confirmation PDFs
# pdf_template_path: "pdf_mappings/sun_retreats_booking.pdf"
# pdf_mapping_path: "pdf_mappings/sun_retreats_booking.json"
# auto_submit_threshold: 3             — preview mode: first N require manual approval
```

### Preview Mode Check (Auto-Submit Decision)

```python
from sqlalchemy import select, func
from app.models.resort_submission import ResortSubmission

def should_auto_submit(db: Session, threshold: int = 3) -> bool:
    """True if we've passed the preview-mode threshold."""
    count = db.execute(
        select(func.count()).where(ResortSubmission.submitted_automatically == True)
    ).scalar_one()
    return count >= threshold
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pypdf form filling | PyMuPDF (already decided) | STATE.md decision | pypdf doesn't regenerate appearance streams; PyMuPDF does |
| `doc.need_appearances(True)` only | `field.update()` + `doc.bake()` | Consistent pattern since PyMuPDF 1.18+ | `bake()` required for macOS Preview + iOS Mail |
| APScheduler 4.0 (alpha) | APScheduler 3.x (stable, 3.11.2) | Already decided in STATE.md | 4.0 API is completely different, not production-ready |
| Celery beat for scheduling | APScheduler in-process | N/A for this scale | No external broker dependency |

**Deprecated/outdated:**
- `doc.need_appearances()` as sole fix: Bug in 1.24.10 (fixed in 1.24.11), but more importantly, it only works if the viewer honors the flag. macOS Preview does NOT. Use `bake()`.
- `page.first_widget` / `widget.next` iteration: Still works but `page.widgets()` generator is cleaner and current.

## Open Questions

1. **AcroForm vs XFA (CRITICAL BLOCKER)**
   - What we know: PyMuPDF cannot fill XFA forms. Detection is possible via `xref_get_key`. If XFA, entirely different approach needed.
   - What's unclear: The actual Sun Retreats form type — this has never been verified.
   - Recommendation: **First task of Phase 5** must be to run `detect_form_type()` against the actual resort PDF and confirm it's AcroForm. If XFA, stop and escalate before any further implementation.

2. **Missing Confirmation File Handling**
   - What we know: Confirmations arrive asynchronously; booking import triggers immediately.
   - What's unclear: How often will confirmations be missing at the moment of import? If always delayed by minutes/hours, option (a) "send without confirmation" may be inadequate.
   - Recommendation: Implement option (a) first (send without, log warning). Add a retry mechanism in a later iteration if the operator reports this as a problem.

3. **SMTP Provider**
   - What we know: Credentials go in `.env`, configuration goes in `base.yaml`.
   - What's unclear: Which SMTP provider (Gmail, SMTP2GO, SendGrid, etc.) the operator uses — affects TLS port (465 vs 587) and auth method.
   - Recommendation: Config must support both `use_tls=True` (port 465) and `start_tls=True` (port 587). Default to 587/STARTTLS.

4. **Cross-Month Date Formatting in Subject Line**
   - What we know: Format is "Booking Form - John Smith - Lot 110 - Mar 5-8".
   - What's unclear: Exact format when check-in and check-out span two months (e.g., Mar 31 - Apr 2).
   - Recommendation: Use "Mar 31 - Apr 2" (month + day for both). Confirmed decisions don't cover this edge case explicitly.

5. **Urgency Alert: Digest vs Per-Booking Email**
   - What we know: Urgent submissions flagged via email alert to operator.
   - What's unclear: One email per urgent booking, or a single daily digest listing all urgent ones.
   - Recommendation: Daily digest (one email per day listing all urgent bookings). Avoids alert storms if multiple bookings are simultaneously urgent.

## Sources

### Primary (HIGH confidence)
- PyMuPDF 1.27.1 PyPI page — version, Python requirements, installation
- PyMuPDF official docs (pymupdf.readthedocs.io) — Widget API, `bake()`, `need_appearances()`, `page.widgets()`, xref low-level interface
- Artifex blog (official PyMuPDF publisher) — complete form-filling code example with `field.update()` and flattening options
- DeepWiki PyMuPDF form-fields — definitive `bake()` vs `need_appearances()` compatibility analysis, recommended 4-step workflow
- APScheduler 3.x official docs (apscheduler.readthedocs.io) — CronTrigger API, AsyncIOScheduler, add_job() API, version 3.11.2
- aiosmtplib 5.1.0 PyPI page and docs (aiosmtplib.readthedocs.io) — send() coroutine, TLS/STARTTLS options, current version
- Python stdlib email.examples docs (docs.python.org) — `EmailMessage.add_attachment()` pattern for binary attachments
- Tenacity docs (tenacity.readthedocs.io) — `@retry`, `stop_after_attempt`, `wait_exponential`, async support, version 9.1.4

### Secondary (MEDIUM confidence)
- GitHub issue #3859 (PyMuPDF) — `need_appearances()` bug in 1.24.10, fixed in 1.24.11 (verified via GitHub)
- GitHub issue #563 (PyMuPDF) — `widget.update()` regenerates appearance streams, documented by maintainer
- GitHub discussion #3664 (PyMuPDF) — XFA form support: explicitly "No, and no plans" from maintainer
- Sentry FastAPI scheduling guide — APScheduler lifespan integration pattern (consistent with official docs)

### Tertiary (LOW confidence)
- WebSearch results on SMTP credentials pattern — confirmed consistent with existing project pattern (`.env` for secrets)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all library versions verified via PyPI and official docs
- Architecture: HIGH — patterns derived from official documentation and existing codebase conventions
- PDF cross-viewer compatibility: HIGH — DeepWiki + GitHub issues confirm `bake()` is required; multiple sources agree
- APScheduler integration: HIGH — official docs + sentry guide consistent
- Pitfalls: HIGH for known issues (XFA, blank fields, SMTP credentials) / MEDIUM for operational pitfalls (missing confirmation file handling)

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (libraries are stable; PyMuPDF releases frequently but API is stable)
