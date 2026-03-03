# Architecture Research

**Domain:** Self-hosted vacation rental management suite
**Researched:** 2026-02-26
**Confidence:** MEDIUM-HIGH

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        INGESTION LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │  Airbnb CSV  │  │  VRBO CSV    │  │ RVshare CSV  │  │ Bank CSV │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────┬─────┘ │
│         └─────────────────┴─────────────────┴───────────────┘       │
│                                  │                                   │
│                    ┌─────────────▼─────────────┐                     │
│                    │  Parser / Normalizer       │                     │
│                    │  (per-platform adapters)   │                     │
│                    └─────────────┬─────────────┘                     │
└──────────────────────────────────┼───────────────────────────────────┘
                                   │ Normalized BookingRecord / Transaction
┌──────────────────────────────────▼───────────────────────────────────┐
│                        CORE DATA LAYER                               │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                      PostgreSQL                              │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐             │    │
│  │  │  bookings  │  │  accounts  │  │  journal   │             │    │
│  │  │            │  │  (CoA)     │  │  entries   │             │    │
│  │  └────────────┘  └────────────┘  └────────────┘             │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐             │    │
│  │  │  scheduled │  │  config    │  │  audit_log │             │    │
│  │  │  jobs      │  │  (YAML)    │  │            │             │    │
│  │  └────────────┘  └────────────┘  └────────────┘             │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼───────────────────────────────────┐
│                      APPLICATION LAYER                               │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  Accounting  │  │  Scheduler   │  │  Notifier    │               │
│  │  Engine      │  │  (APScheduler│  │  (email /    │               │
│  │              │  │  + job store)│  │   platform   │               │
│  └──────┬───────┘  └──────┬───────┘  │   messages)  │               │
│         │                 │          └──────┬───────┘               │
│  ┌──────▼───────┐  ┌──────▼───────┐         │                       │
│  │  PDF Form    │  │  LLM Query   │         │                       │
│  │  Generator   │  │  Interface   │◄────────┘                       │
│  └──────────────┘  │  (Ollama)    │                                  │
│                    └──────────────┘                                  │
└──────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼───────────────────────────────────┐
│                       PRESENTATION LAYER                             │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                   FastAPI (REST API)                         │    │
│  └──────────────────────────────┬───────────────────────────────┘    │
│                                 │                                    │
│  ┌──────────────────────────────▼───────────────────────────────┐    │
│  │              Web Dashboard (React / HTMX)                    │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Platform Adapters | Parse platform-specific CSV exports into a normalized schema | One class per platform (AirbnbAdapter, VRBOAdapter, etc.) |
| Normalizer | Validate, deduplicate, and write canonical records to DB | Python dataclasses + SQLAlchemy |
| Accounting Engine | Maintain double-entry ledger, chart of accounts, financial reports | python-accounting or custom SQLAlchemy models |
| Scheduler | Fire time-based jobs (form submissions, guest messages) | APScheduler 3.x with SQLAlchemy job store |
| PDF Generator | Fill static PDF templates with booking/property data | pypdf + pdfrw overlay, or fillpdf |
| Notifier | Send emails (resort forms) and guest messages | smtplib / SMTP + platform message APIs |
| LLM Query Interface | Accept natural language, generate SQL, return results | Ollama Python SDK + schema-aware prompt |
| Config Manager | Load property-specific YAML config; expose to all services | Pydantic Settings + YAML loader |
| FastAPI App | HTTP API for dashboard and manual triggers | FastAPI + SQLAlchemy async |
| Web Dashboard | Monitoring, financial overview, manual import | HTMX + Jinja2 (lightweight) or React |

---

## Recommended Project Structure

```
roost/
├── config/
│   ├── config.yaml              # Property-specific config (gitignored for private data)
│   └── config.example.yaml     # Template for open-source users
├── src/
│   ├── ingestion/
│   │   ├── adapters/
│   │   │   ├── airbnb.py        # AirbnbAdapter: CSV -> BookingRecord
│   │   │   ├── vrbo.py          # VRBOAdapter
│   │   │   ├── rvshare.py       # RVshareAdapter
│   │   │   └── mercury.py      # MercuryAdapter: CSV -> BankTransaction
│   │   ├── normalizer.py        # Dedup, validate, write to DB
│   │   └── models.py            # BookingRecord, BankTransaction dataclasses
│   ├── accounting/
│   │   ├── engine.py            # Journal entry creation, double-entry rules
│   │   ├── chart_of_accounts.py # Account hierarchy, account types
│   │   ├── reports.py           # P&L, balance sheet, cash flow
│   │   └── models.py            # Account, JournalEntry, Transaction SQLAlchemy models
│   ├── scheduler/
│   │   ├── jobs.py              # Job definitions (form submission, messages)
│   │   ├── triggers.py          # When jobs fire (3+ days before arrival, etc.)
│   │   └── store.py             # APScheduler setup with SQLAlchemy job store
│   ├── pdf/
│   │   ├── generator.py         # Fill PDF templates with booking data
│   │   └── templates/           # Static PDF form templates
│   ├── notifications/
│   │   ├── email.py             # SMTP email for resort forms
│   │   └── messages.py         # Platform message sending (Airbnb, VRBO APIs)
│   ├── llm/
│   │   ├── query.py             # Ollama integration, NL -> SQL pipeline
│   │   └── prompts.py           # Schema-aware prompt templates
│   ├── config/
│   │   └── settings.py          # Pydantic Settings, loads config.yaml
│   ├── api/
│   │   ├── main.py              # FastAPI app, route registration
│   │   ├── routes/
│   │   │   ├── imports.py       # POST /imports (trigger CSV ingestion)
│   │   │   ├── bookings.py      # GET /bookings
│   │   │   ├── accounting.py    # GET /reports, GET /accounts
│   │   │   ├── scheduler.py     # GET/POST /jobs
│   │   │   └── query.py         # POST /query (LLM interface)
│   │   └── dependencies.py      # DB session, config injection
│   └── db/
│       ├── session.py           # SQLAlchemy engine + async session factory
│       └── migrations/          # Alembic migrations
├── dashboard/                   # Frontend (HTMX templates or React build)
├── docker/
│   ├── Dockerfile.api
│   └── Dockerfile.scheduler     # If running scheduler as separate service
├── docker-compose.yml
├── pyproject.toml
└── tests/
    ├── ingestion/
    ├── accounting/
    └── fixtures/               # Sample CSV files from each platform
```

### Structure Rationale

- **ingestion/adapters/:** One file per platform so adding a new platform (e.g., Booking.com) is a single file addition with no changes elsewhere. Each adapter implements a common interface.
- **accounting/:** Isolated from ingestion. Accounting receives normalized records, never raw CSVs. This keeps the double-entry logic testable independently.
- **scheduler/:** Separated from the API. The scheduler runs as a persistent background process; the API exposes job status but does not own scheduling logic.
- **llm/:** Thin wrapper around Ollama. Contains only prompt engineering and schema description. Business logic stays in accounting/ and ingestion/.
- **config/:** YAML-based config loaded at startup via Pydantic Settings. All property-specific data (resort email, property name, fee structure) lives here, not in code.

---

## Architectural Patterns

### Pattern 1: Platform Adapter + Normalizer

**What:** Each CSV source has its own adapter class that knows the column names and data quirks of that platform. The adapter produces a canonical `BookingRecord` or `BankTransaction` object. The normalizer receives these objects and writes them to the database, applying deduplication.

**When to use:** Any time you ingest from multiple sources with different schemas.

**Trade-offs:**
- Pro: Adding a new platform is additive, not modifying existing code.
- Pro: Platform quirks (Airbnb's date format, VRBO's fee columns) are contained.
- Con: You must maintain a canonical schema that covers all platforms; edge cases require schema evolution.

**Example:**
```python
# src/ingestion/adapters/airbnb.py
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import csv

@dataclass
class BookingRecord:
    platform: str
    confirmation_code: str
    guest_name: str
    check_in: date
    check_out: date
    payout_amount: Decimal
    platform_fee: Decimal
    raw_data: dict  # preserve original for debugging

class AirbnbAdapter:
    COLUMN_MAP = {
        "Confirmation Code": "confirmation_code",
        "Guest Name": "guest_name",
        "Start Date": "check_in",
        "End Date": "check_out",
        "Amount": "payout_amount",
    }

    def parse(self, file_path: str) -> list[BookingRecord]:
        records = []
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(self._row_to_record(row))
        return records

    def _row_to_record(self, row: dict) -> BookingRecord:
        return BookingRecord(
            platform="airbnb",
            confirmation_code=row["Confirmation Code"],
            guest_name=row["Guest Name"],
            check_in=self._parse_date(row["Start Date"]),
            check_out=self._parse_date(row["End Date"]),
            payout_amount=Decimal(row["Amount"].replace("$", "").strip()),
            platform_fee=Decimal("0"),  # derive from gross - net
            raw_data=dict(row),
        )
```

---

### Pattern 2: Double-Entry Accounting Engine

**What:** Every financial event creates at least two journal entries that sum to zero. Bookings create revenue and accounts-receivable entries. Payouts create bank and accounts-receivable clearing entries. Expenses create expense and accounts-payable entries.

**When to use:** Any system tracking money — required here to generate P&L and balance sheet.

**Trade-offs:**
- Pro: Self-auditing; the ledger is always balanced.
- Pro: Generates real financial statements from the same data.
- Con: More complex to implement correctly than a simple income/expense table.
- Con: Vacation rental accounting has platform-specific fee structures that must be mapped correctly.

**Example:**
```python
# src/accounting/engine.py
from decimal import Decimal
from .models import Account, JournalEntry, Transaction
from sqlalchemy.ext.asyncio import AsyncSession

async def record_booking_payout(
    session: AsyncSession,
    booking_id: str,
    gross_amount: Decimal,
    platform_fee: Decimal,
    net_payout: Decimal,
    bank_account: Account,
    revenue_account: Account,
    platform_fee_account: Account,
):
    """
    Payout received from platform:
    DR  Bank                  net_payout
    DR  Platform Fee Expense  platform_fee
    CR  Rental Revenue        gross_amount
    """
    txn = Transaction(description=f"Payout for booking {booking_id}")
    session.add(txn)

    entries = [
        JournalEntry(transaction=txn, account=bank_account,
                     amount=net_payout, entry_type="debit"),
        JournalEntry(transaction=txn, account=platform_fee_account,
                     amount=platform_fee, entry_type="debit"),
        JournalEntry(transaction=txn, account=revenue_account,
                     amount=gross_amount, entry_type="credit"),
    ]
    session.add_all(entries)
    # Verify balanced: sum(debits) == sum(credits)
    assert sum(e.amount for e in entries if e.entry_type == "debit") == \
           sum(e.amount for e in entries if e.entry_type == "credit")
```

---

### Pattern 3: APScheduler with Persistent Job Store

**What:** APScheduler runs embedded in the application (or a dedicated scheduler container). Jobs are stored in the database (SQLAlchemy job store), so they survive restarts. Jobs are created when a booking is ingested and fire at calculated trigger times (e.g., 3 days before check-in).

**When to use:** Self-hosted application where you don't want the operational complexity of Celery + Redis + workers, but need persistent, time-based scheduling.

**Trade-offs:**
- Pro: No Redis or message broker required — PostgreSQL is the job store.
- Pro: Dynamic job creation at ingestion time (calculate trigger from check_in date).
- Con: Scheduler is in-process; if the container dies, no jobs run until restart.
- Con: Not distributed (fine for single-host self-hosted deployment).
- Note: For this use case (self-hosted, single machine, low-frequency jobs), APScheduler is the right choice. Celery would be overengineering.

**Example:**
```python
# src/scheduler/store.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

def create_scheduler(db_url: str) -> AsyncIOScheduler:
    jobstores = {
        "default": SQLAlchemyJobStore(url=db_url)
    }
    return AsyncIOScheduler(jobstores=jobstores)

# src/scheduler/jobs.py
from datetime import timedelta
from .store import scheduler

def schedule_arrival_form(booking: BookingRecord, trigger_days_before: int = 3):
    trigger_time = booking.check_in - timedelta(days=trigger_days_before)
    scheduler.add_job(
        func=submit_arrival_form,
        trigger="date",
        run_date=trigger_time,
        args=[booking.confirmation_code],
        id=f"arrival_form_{booking.confirmation_code}",
        replace_existing=True,  # safe to re-import same booking
    )
```

---

### Pattern 4: Schema-Aware LLM Query Interface

**What:** The Ollama integration receives a natural language question, injects the database schema as context in the system prompt, generates SQL, validates it, executes it, and returns structured results. The schema context is built once at startup and cached.

**When to use:** Natural language query over financial data — replaces need for complex report builder UI.

**Trade-offs:**
- Pro: No external API calls; fully local via Ollama.
- Pro: Works with any model Ollama supports (llama3, mistral, codellama).
- Con: LLM-generated SQL can be wrong — must validate before execution.
- Con: Complex queries (date ranges, multi-join aggregations) require good prompt engineering.
- Con: Read-only queries only — never allow LLM-generated write SQL.

**Example:**
```python
# src/llm/query.py
import ollama
from .prompts import build_system_prompt

SCHEMA_CONTEXT = None  # loaded at startup

async def query_financial_data(natural_language_question: str) -> dict:
    global SCHEMA_CONTEXT
    if SCHEMA_CONTEXT is None:
        SCHEMA_CONTEXT = build_schema_context()  # reads DB schema

    response = ollama.chat(
        model="llama3",
        messages=[
            {"role": "system", "content": build_system_prompt(SCHEMA_CONTEXT)},
            {"role": "user", "content": natural_language_question},
        ]
    )
    sql = extract_sql(response["message"]["content"])
    validate_sql(sql)  # rejects writes, validates syntax
    results = await execute_readonly_query(sql)
    return {"sql": sql, "results": results}
```

---

### Pattern 5: Config-Driven Property Settings

**What:** All property-specific data lives in `config/config.yaml`. The application reads this at startup via Pydantic Settings. Code is generic; config makes it specific.

**When to use:** Open-source tool that others will self-host with different properties.

**Trade-offs:**
- Pro: Others can clone the repo and add their own config file — code needs no changes.
- Pro: Secret values (SMTP password, API keys) can be injected via environment variables overlaying the YAML.
- Con: YAML config must be validated carefully (Pydantic catches this at startup).

**Example:**
```yaml
# config/config.yaml
property:
  name: "My Lakefront Cabin"
  resort_email: "reservations@resort.example.com"
  arrival_form_days_before: 3

platforms:
  airbnb:
    import_path: "/data/imports/airbnb"
  vrbo:
    import_path: "/data/imports/vrbo"

accounting:
  chart_of_accounts:
    rental_revenue: "4000"
    platform_fees: "6100"
    bank_account: "1010"

notifications:
  smtp_host: "${SMTP_HOST}"
  smtp_user: "${SMTP_USER}"
  smtp_password: "${SMTP_PASSWORD}"
```

---

## Data Flow

### Booking Ingestion Flow

```
User places CSV in /data/imports/airbnb/
        ↓
Import trigger (manual via API or file-watch cron)
        ↓
AirbnbAdapter.parse(file_path) → List[BookingRecord]
        ↓
Normalizer.deduplicate(records)  [check confirmation_code in DB]
        ↓
Write BookingRecord to bookings table
        ↓
AccountingEngine.record_booking_payout(booking) → JournalEntries
        ↓
Scheduler.schedule_arrival_form(booking, trigger_days=3)
        ↓
Scheduler.schedule_guest_message(booking, trigger_hours_before=24)
        ↓
Done — booking fully processed
```

### Scheduled Job Execution Flow

```
APScheduler wakes at trigger time
        ↓
job: submit_arrival_form(confirmation_code)
        ↓
Load booking from DB
        ↓
Load property config (resort email, form template)
        ↓
PDFGenerator.fill_template(template, booking_data) → bytes
        ↓
Notifier.send_email(to=resort_email, attachment=pdf)
        ↓
Mark job as completed in audit_log
```

### LLM Query Flow

```
User types: "What was my total revenue last quarter?"
        ↓
POST /api/query { "question": "..." }
        ↓
LLMQueryInterface.query(question)
        ↓
Build prompt: system=schema_context + instructions, user=question
        ↓
ollama.chat(model="llama3", messages=[...])
        ↓
Extract SQL from response
        ↓
Validate SQL (read-only check, syntax check)
        ↓
Execute against PostgreSQL
        ↓
Return { sql, results, explanation }
```

### Bank Import Flow

```
User places Mercury CSV in /data/imports/bank/
        ↓
MercuryAdapter.parse(file_path) → List[BankTransaction]
        ↓
Normalizer.match_to_bookings(transactions)
        [match by date + amount to existing BookingRecord]
        ↓
AccountingEngine.record_bank_transaction(transaction)
        ↓
If unmatched → flag for manual review in dashboard
```

---

## Docker Service Separation

### Recommended Services

```yaml
# docker-compose.yml
services:

  db:
    image: postgres:16
    # owns: all application state
    # volumes: ./data/postgres:/var/lib/postgresql/data

  api:
    build: ./docker/Dockerfile.api
    # owns: HTTP API, web dashboard
    # depends_on: db
    # ports: 8000:8000

  scheduler:
    build: ./docker/Dockerfile.api  # same image, different entrypoint
    command: python -m src.scheduler.runner
    # owns: APScheduler process, job execution
    # depends_on: db
    # NOTE: shares DB for job store — no separate broker needed

  ollama:
    image: ollama/ollama
    # owns: LLM inference
    # volumes: ollama_models:/root/.ollama
    # ports: 11434:11434 (internal only)
```

### Service Boundary Rationale

| Service | Why Separate | Why NOT Separate |
|---------|-------------|-----------------|
| `db` | Data persistence, must survive restarts independently | — |
| `api` | Web-facing, needs to scale separately from background work | — |
| `scheduler` | Long-running process with its own lifecycle; if combined with API, a scheduler crash takes down the API | Could run embedded in API for simpler setup |
| `ollama` | Resource-intensive (GPU/CPU); separate restart lifecycle | — |

**Recommendation:** Start with `scheduler` embedded in `api` (simpler). Split into its own service in a later phase if scheduler jobs interfere with API response times.

### What NOT to Add as Separate Services

- **Redis:** Not needed. APScheduler uses PostgreSQL as job store. No message broker required.
- **Celery:** Overengineering for a self-hosted single-user tool. APScheduler is sufficient.
- **Separate ingestion service:** Ingestion is triggered on-demand or by a simple file-watch cron. Not a persistent service.

---

## Scaling Considerations

This system is self-hosted for a single operator managing 1-5 properties. Scaling is not a primary concern. Document scale points for awareness only.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-5 properties, 1 operator | Monolith + APScheduler embedded. Single Docker host. |
| 5-20 properties | Split scheduler to own service. Consider Celery if job volume increases. |
| 20+ properties, multi-user | This use case exceeds the design target. Major architecture changes needed. |

### First Bottleneck

PDF generation and email sending during peak check-in periods (Friday arrivals). APScheduler's thread pool handles this without modification up to ~100 concurrent jobs.

### Second Bottleneck

Ollama inference is single-threaded by default. Multiple simultaneous LLM queries queue. Acceptable for a single-user dashboard.

---

## Anti-Patterns

### Anti-Pattern 1: Calling Ollama for Write Operations

**What people do:** Allow the LLM to generate UPDATE or INSERT SQL and execute it.

**Why it's wrong:** LLMs hallucinate. A wrong SELECT returns bad data; a wrong UPDATE destroys financial records. The accounting ledger must be append-only.

**Do this instead:** LLM interface is read-only. All writes go through typed Python functions in the accounting engine. Make this a hard constraint enforced in `validate_sql()`.

---

### Anti-Pattern 2: One Monolithic CSV Parser

**What people do:** Write a single parser that handles all platforms with a giant `if platform == "airbnb"` branch tree.

**Why it's wrong:** Every platform adds to the complexity. When Airbnb changes their export format, you risk breaking VRBO parsing. Impossible to test in isolation.

**Do this instead:** One adapter class per platform implementing a common interface. Changes to one adapter cannot break others.

---

### Anti-Pattern 3: Storing Platform-Specific Fields in the Canonical Schema

**What people do:** Add `airbnb_listing_id`, `vrbo_property_code`, `rvshare_booking_ref` columns to the bookings table.

**Why it's wrong:** Schema bloat. Every platform adds columns; most are NULL for other platforms.

**Do this instead:** Canonical schema has only shared fields. Each adapter stores the original `raw_data` as a JSONB column. Platform-specific lookups query `raw_data` when needed.

---

### Anti-Pattern 4: Hardcoding Property Data in Code

**What people do:** Define resort email addresses, property names, or fee rates as Python constants.

**Why it's wrong:** The stated goal is open-source reuse. Anyone who forks the repo must edit code, not config, to use their own property.

**Do this instead:** All property-specific data in `config/config.yaml`. Config is validated at startup by Pydantic. Secrets injected via environment variables. `config.example.yaml` ships with the repo.

---

### Anti-Pattern 5: Building a Real-Time Sync Instead of Import-Based Ingestion

**What people do:** Try to call Airbnb/VRBO APIs directly to sync bookings in real time.

**Why it's wrong:** These platforms do not offer public APIs for individual hosts (as of 2026). API access is for software partners with approval processes. CSV export is the documented, supported path.

**Do this instead:** Import-based model. User downloads CSV from platform, places in watched folder or uploads via dashboard. Reliable and platform-ToS-compliant.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Airbnb | CSV export (manual download) | No official API for individual hosts |
| VRBO | CSV export (manual download) | No official API for individual hosts |
| RVshare | CSV export (manual download) | No official API for individual hosts |
| Mercury Bank | CSV export (manual download) | Mercury does have a business API; CSV is simpler |
| Resort / HOA | Email with PDF attachment | SMTP; address in config |
| Ollama | HTTP REST API at localhost:11434 | `ollama` Python SDK wraps this |
| Guest messaging | Platform-specific (future phase) | Airbnb/VRBO messaging APIs require partner status; manual for now |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Ingestion → Accounting | Direct function call (same process) | Ingestion calls `accounting.record_booking_payout()` |
| Ingestion → Scheduler | Direct function call (same process) | Ingestion calls `scheduler.schedule_arrival_form()` |
| API → Accounting | SQLAlchemy async queries | API reads from DB, does not call engine directly for reads |
| API → Scheduler | APScheduler instance (shared) | API can trigger immediate jobs or inspect scheduled jobs |
| LLM → DB | Read-only SQL queries | Generated SQL executed against read-only DB connection |
| Scheduler → PDF | Direct function call | Scheduler job calls `pdf.generator.fill_template()` |
| Scheduler → Notifier | Direct function call | Scheduler job calls `notifications.email.send()` |

---

## Build Order Implications

Architecture has clear dependency layers. Build bottom-up:

1. **Database + Config (foundation)** — Everything else depends on this. PostgreSQL schema, Alembic migrations, Pydantic Settings loading.

2. **Ingestion adapters (no dependencies)** — Each adapter is self-contained. Build and test against fixture CSV files. Fastest path to real data.

3. **Accounting engine (depends on DB)** — Core financial logic. Must be correct before anything else builds on it. Testable with seeded data.

4. **PDF generation (no dependencies)** — Standalone. Fill template from dict. Test with hardcoded data before connecting to real bookings.

5. **Scheduler (depends on DB + Ingestion)** — Requires bookings in DB to schedule against. APScheduler job store requires DB.

6. **Notifier (depends on SMTP config)** — Email and messaging. Can be built alongside scheduler. Test with a test SMTP server (MailHog in Docker).

7. **FastAPI + Dashboard (depends on all above)** — Thin layer over the above. Build last; it's glue code.

8. **LLM Query Interface (depends on DB + running Ollama)** — Can be built at any point after DB exists. Ollama must be running locally during development.

---

## Sources

- Anvil Works: Double-Entry Accounting for Engineers — https://anvil.works/blog/double-entry-accounting-for-engineers (data model patterns, journal entry structure)
- python-accounting GitHub — https://github.com/ekmungai/python-accounting (IFRS-compliant double-entry library, ORM patterns)
- Cosmic Python: External Events — https://www.cosmicpython.com/book/chapter_11_external_events.html (event-driven data ingestion patterns)
- APScheduler vs Celery Beat — https://leapcell.io/blog/scheduling-tasks-in-python-apscheduler-vs-celery-beat (scheduler architecture comparison, MEDIUM confidence)
- Ollama Python Tutorial 2026 — https://dev.to/proflead/complete-ollama-tutorial-2026-llms-via-cli-cloud-python-3m97 (API endpoints, Python SDK)
- Ollama SQL Agent — https://markaicode.com/sql-query-generator-ollama-tutorial/ (NL-to-SQL architecture with Ollama)
- FastAPI Background Tasks — https://fastapi.tiangolo.com/reference/background/ (FastAPI task handling patterns)
- Guesty Tech Stack Guide — https://www.guesty.com/blog/how-to-build-your-ultimate-short-term-rental-tech-stack/ (vacation rental component landscape)

---

*Architecture research for: Self-hosted vacation rental management suite*
*Researched: 2026-02-26*
