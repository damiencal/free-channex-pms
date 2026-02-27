# Phase 2: Data Ingestion - Research

**Researched:** 2026-02-27
**Domain:** Polars CSV parsing, FastAPI file upload, SQLAlchemy upsert, archival patterns, platform CSV schemas
**Confidence:** HIGH (stack/patterns), MEDIUM (CSV schemas — actual files must be inspected)

---

## Summary

Phase 2 ingests CSV exports from Airbnb, VRBO, and Mercury bank into a unified booking and transaction schema stored in PostgreSQL. A fourth path accepts manual RVshare bookings via a JSON POST endpoint. The phase builds on Phase 1's FastAPI + SQLAlchemy 2.0 + Alembic foundation directly — no new framework decisions are needed.

The standard approach for this domain is: FastAPI receives multipart file uploads via `UploadFile` (requires `python-multipart`), passes bytes to Polars `read_csv()` via `io.BytesIO`, validates headers and types before writing anything, archives the raw file to `archive_dir` (from `AppConfig`), then upserts into PostgreSQL using SQLAlchemy's `insert(...).on_conflict_do_update()`. A persistent `ImportRun` table tracks every import for audit and dashboard use.

**Critical gap:** No sample CSV files exist in the repository. Actual column names for Airbnb, VRBO, and Mercury CSVs cannot be confirmed from web research or documentation — they must be inspected from real exports before the adapters can be finalized. This is the primary uncertainty going into planning.

**Primary recommendation:** Use Polars 1.38.1 for all CSV reading (already decided), `sqlalchemy.dialects.postgresql.insert` for upserts, and standard library `shutil` + `pathlib` for archival. Add `polars` and `python-multipart` as the only new dependencies.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Polars | 1.38.1 | CSV parsing and validation | Already decided; 5-25x faster than pandas; BytesIO support; schema_overrides for type enforcement |
| python-multipart | 0.0.x | FastAPI multipart/form-data parsing | Required by FastAPI for all UploadFile endpoints; without it, file uploads raise 422 |
| SQLAlchemy (postgresql dialect) | 2.0.x (already installed) | PostgreSQL upsert via INSERT...ON CONFLICT | Already in stack; dialect-specific insert() provides on_conflict_do_update |
| Python stdlib: io, shutil, pathlib | stdlib | BytesIO wrapping, archival, path ops | No new dependency needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dateutil | (if needed) | Date parsing fallback for non-ISO formats | Only if Polars try_parse_dates cannot handle Airbnb's date format |
| Pydantic BaseModel | already installed | RVshare manual entry request body schema | Reuse existing Pydantic for JSON endpoint validation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Polars | pandas | Pandas is fine but decision is locked; Polars is faster and has BytesIO support |
| Direct DB write | Stage then write | Staging adds complexity; validate-then-write in memory is sufficient at this scale |
| Custom archival | watchdog file watcher | Watchdog is a deferred idea per CONTEXT.md; simple shutil.copy2 is sufficient |

### Installation

```bash
uv add polars python-multipart
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 2 additions)

```
airbnb-tools/
├── app/
│   ├── models/
│   │   ├── property.py          # (existing)
│   │   ├── booking.py           # NEW: Booking ORM model
│   │   ├── bank_transaction.py  # NEW: BankTransaction ORM model
│   │   └── import_run.py        # NEW: ImportRun ORM model
│   ├── ingestion/               # NEW: ingestion package
│   │   ├── __init__.py
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── airbnb.py        # Airbnb CSV adapter
│   │   │   ├── vrbo.py          # VRBO CSV adapter
│   │   │   └── mercury.py       # Mercury CSV adapter
│   │   ├── normalizer.py        # Canonical schema + dedup + DB write + archival
│   │   └── schemas.py           # Pydantic models: BookingRecord, BankTransactionRecord, RVshareEntryRequest
│   └── api/
│       ├── health.py            # (existing)
│       └── ingestion.py         # NEW: upload endpoints + manual entry endpoint
├── alembic/
│   └── versions/
│       ├── 001_initial_properties.py  # (existing)
│       └── 002_ingestion_tables.py    # NEW: bookings, bank_transactions, import_runs
```

### Pattern 1: Adapter Architecture

**What:** Each platform adapter is a module with two functions: `validate_headers(df: pl.DataFrame) -> None` (raises on wrong structure) and `parse(df: pl.DataFrame) -> list[BookingRecord]` (returns canonical records). The adapter never writes to DB — it only transforms.

**When to use:** All three CSV adapters (Airbnb, VRBO, Mercury).

```python
# app/ingestion/adapters/airbnb.py
import polars as pl
from app.ingestion.schemas import BookingRecord

EXPECTED_HEADERS = frozenset(["Date", "Type", "Confirmation Code", "Guest", ...])
# NOTE: these exact names must be verified against real Airbnb exports

def validate_headers(df: pl.DataFrame) -> None:
    """Fail immediately if headers don't match expected Airbnb structure."""
    actual = frozenset(df.columns)
    if not EXPECTED_HEADERS.issubset(actual):
        missing = EXPECTED_HEADERS - actual
        raise ValueError(
            f"This doesn't look like an Airbnb Transaction History CSV. "
            f"Expected headers: {sorted(EXPECTED_HEADERS)}. "
            f"Missing: {sorted(missing)}"
        )

def parse(df: pl.DataFrame) -> list[BookingRecord]:
    """Parse and normalize Airbnb rows to canonical BookingRecords.

    Handles:
    - Apostrophe-prefixed amounts: strip leading apostrophe, parse as Decimal
    - Non-ISO dates: use Polars date parsing or explicit strptime
    - Multi-row events: group by Confirmation Code, sum amounts, take first guest/dates
    """
    ...
```

### Pattern 2: CSV Ingestion Flow

**What:** The normalizer orchestrates: read bytes → validate headers → validate rows → archive raw file → upsert to DB → record ImportRun.

**When to use:** All CSV upload endpoints.

```python
# app/ingestion/normalizer.py
import io
import shutil
from datetime import datetime, timezone
from pathlib import Path
import polars as pl

from app.config import get_config
from app.ingestion.schemas import BookingRecord

def ingest_csv(
    raw_bytes: bytes,
    filename: str,
    platform: str,       # "airbnb" | "vrbo" | "mercury"
    adapter,             # module with validate_headers() and parse()
    db,                  # SQLAlchemy Session from get_db()
) -> dict:
    """Full ingestion pipeline for a CSV upload.

    Order: read → validate headers → validate rows → archive → upsert → record.
    Nothing is written to DB if validation fails.
    """
    config = get_config()

    # 1. Read CSV with Polars
    df = pl.read_csv(
        io.BytesIO(raw_bytes),
        infer_schema_length=0,      # read all columns as strings; adapter handles types
        null_values=["", "N/A"],
        try_parse_dates=False,       # do not auto-parse; adapter handles date normalization
    )

    # 2. Validate headers (fail immediately with clear message)
    adapter.validate_headers(df)

    # 3. Validate rows (collect ALL errors before failing)
    records, errors = adapter.parse(df)
    if errors:
        raise ValueError(format_errors(errors))

    # 4. Archive raw file (archive first, always — even failed imports leave a trace)
    archive_path = archive_file(raw_bytes, filename, platform, config.archive_dir)

    # 5. Upsert records to DB
    inserted, updated = upsert_records(records, platform, db)

    # 6. Record ImportRun
    record_import_run(db, platform, filename, len(inserted), len(updated), 0, archive_path)

    return {
        "inserted": len(inserted),
        "updated": len(updated),
        "skipped": 0,
        "inserted_ids": inserted,
        "updated_ids": updated,
    }
```

### Pattern 3: Reading CSV Bytes with Polars

**What:** Polars `read_csv()` accepts `io.BytesIO` directly. Use `infer_schema_length=0` to treat all columns as strings initially — let the adapter handle type conversion with full validation control.

**When to use:** All CSV upload paths.

```python
# Source: Polars docs — read_csv accepts BytesIO and raw bytes
import io
import polars as pl

async def upload_csv(file: UploadFile, db = Depends(get_db)):
    raw_bytes = await file.read()
    df = pl.read_csv(
        io.BytesIO(raw_bytes),
        infer_schema_length=0,   # all columns as Utf8; avoids schema inference surprises
        null_values=["", "N/A"],
    )
    ...
```

**Key Polars read_csv parameters:**

| Parameter | Type | Purpose |
|-----------|------|---------|
| `source` | str, Path, bytes, BytesIO, file-like | Input — use `io.BytesIO(raw_bytes)` for uploaded files |
| `has_header` | bool (default True) | Whether first row is headers |
| `separator` | str (default ",") | Field delimiter |
| `infer_schema_length` | int or None (default 100) | Rows used for type inference; 0 = all Utf8 |
| `schema_overrides` | dict[str, PolarsDataType] | Override inferred types for specific columns |
| `null_values` | str, list[str], dict | Values to treat as null |
| `try_parse_dates` | bool (default False) | Auto-parse ISO8601-like dates |
| `ignore_errors` | bool (default False) | Skip unparseable rows (do NOT use — we want halt-and-report) |
| `columns` | list[str | int] | Select specific columns only |
| `truncate_ragged_lines` | bool (default False) | Handle rows with fewer fields than header |

**Do NOT use `ignore_errors=True`** — the halt-and-report requirement means any bad row must surface an error, not be silently skipped.

### Pattern 4: PostgreSQL Upsert

**What:** SQLAlchemy's PostgreSQL-specific `insert()` with `on_conflict_do_update()`. Uses the stable ID column (confirmation code, reservation ID, or transaction ID) as the conflict target.

**When to use:** All DB write operations for Booking and BankTransaction tables.

```python
# Source: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.booking import Booking

def upsert_bookings(records: list[BookingRecord], db) -> tuple[list, list]:
    inserted_ids, updated_ids = [], []
    for record in records:
        stmt = pg_insert(Booking).values(**record.to_dict())
        stmt = stmt.on_conflict_do_update(
            index_elements=["platform", "platform_booking_id"],  # unique constraint
            set_={
                "guest_name": stmt.excluded.guest_name,
                "check_in_date": stmt.excluded.check_in_date,
                "check_out_date": stmt.excluded.check_out_date,
                "net_amount": stmt.excluded.net_amount,
                "updated_at": stmt.excluded.updated_at,
            }
        )
        result = db.execute(stmt)
        # Distinguish insert vs update: rowcount alone doesn't distinguish,
        # use RETURNING or query before insert to check existence
        ...
    db.commit()
    return inserted_ids, updated_ids
```

**Note on insert vs update detection:** PostgreSQL `ON CONFLICT DO UPDATE` does not distinguish inserts from updates in the returned rowcount. To distinguish them for the response summary, either:
1. Query existence before upserting (SELECT WHERE platform_booking_id = ...)
2. Use `INSERT ... ON CONFLICT ... RETURNING xmax` (xmax = 0 means insert, > 0 means update) — this is PostgreSQL-specific but efficient

**Recommendation:** Use `RETURNING xmax` for efficiency. This avoids a SELECT per row.

```python
from sqlalchemy import text

# Add RETURNING xmax to distinguish insert from update
stmt = stmt.returning(text("xmax"))
result = db.execute(stmt)
for row in result:
    if row.xmax == 0:
        inserted_ids.append(record.platform_booking_id)
    else:
        updated_ids.append(record.platform_booking_id)
```

### Pattern 5: Raw File Archival

**What:** Copy raw bytes to `archive_dir/{platform}/YYYY-MM-DD_HH-MM-SS_{filename}` before processing. Archive happens before any DB writes — even failed imports leave a trace.

**When to use:** All CSV upload paths, before validation errors can abort processing.

```python
# app/ingestion/normalizer.py
import shutil
from datetime import datetime, timezone
from pathlib import Path

def archive_file(raw_bytes: bytes, filename: str, platform: str, archive_dir: str) -> Path:
    """Archive raw CSV to archive_dir/{platform}/YYYY-MM-DD_HH-MM-SS_{filename}.

    archive_dir comes from AppConfig (configurable via base.yaml or .env).
    Creates subdirectory if it doesn't exist.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    dest_dir = Path(archive_dir) / platform
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{ts}_{filename}"
    dest_path.write_bytes(raw_bytes)
    return dest_path
```

**Note:** Write bytes directly rather than `shutil.copy2()` because the source is already in memory (bytes from `await file.read()`), not a file path.

### Pattern 6: FastAPI File Upload Endpoint

**What:** POST endpoint accepting multipart file upload with `UploadFile`. Requires `python-multipart` installed. Reads bytes with `await file.read()`.

**When to use:** All three CSV upload endpoints.

```python
# app/api/ingestion.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.ingestion import normalizer
from app.ingestion.adapters import airbnb

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

@router.post("/airbnb/upload")
async def upload_airbnb_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload Airbnb Transaction History CSV."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    raw_bytes = await file.read()

    try:
        result = normalizer.ingest_csv(
            raw_bytes=raw_bytes,
            filename=file.filename,
            platform="airbnb",
            adapter=airbnb,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return result
```

### Pattern 7: RVshare Manual Entry Endpoint

**What:** POST endpoint accepting JSON body with all required booking fields. Validated by Pydantic model. No CSV involved.

**When to use:** RVshare manual entry (Phase 2 only provides this endpoint — no UI in this phase).

```python
# app/ingestion/schemas.py
from datetime import date
from decimal import Decimal
from pydantic import BaseModel

class RVshareEntryRequest(BaseModel):
    confirmation_code: str
    guest_name: str
    check_in_date: date
    check_out_date: date
    net_amount: Decimal
    property_slug: str  # references Property.slug
    notes: str | None = None

# app/api/ingestion.py
@router.post("/rvshare/entry")
def create_rvshare_booking(
    entry: RVshareEntryRequest,
    db: Session = Depends(get_db),
):
    """Manually enter an RVshare booking."""
    ...
```

### Pattern 8: ImportRun Table

**What:** Persistent record of every import attempt. Queryable via GET endpoint for dashboard use.

**When to use:** Record at end of every successful import.

```python
# app/models/import_run.py
from datetime import datetime
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db import Base

class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)   # "airbnb"|"vrbo"|"mercury"|"rvshare"
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    archive_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

### Anti-Patterns to Avoid

- **Writing to DB before validation completes:** The halt-and-report requirement means all rows must pass validation before any DB write. Never write partially-valid imports.
- **Using `pl.scan_csv()` for uploaded files:** `scan_csv()` does not support `BytesIO` (lazy mode requires a real file path). Use `pl.read_csv()`.
- **Using `ignore_errors=True` in Polars:** Silently skips bad rows; incompatible with halt-and-report behavior.
- **Inferring types with default `infer_schema_length=100`:** Can misidentify columns if first 100 rows happen to look like integers but later rows have strings. Use `infer_schema_length=0` (all Utf8) and validate types explicitly in the adapter.
- **Storing `archive_dir` path in source code:** Must come from `AppConfig` (which reads from `base.yaml` or env var). Operator controls where archives go.
- **Hardcoding platform column names as string literals in business logic:** Column name constants belong in each adapter module (e.g., `AIRBNB_CONFIRMATION_COL = "Confirmation Code"`). This makes header-change detection easy to update in one place.
- **Using `session.add()` for upserts:** `session.add()` with an existing PK raises `IntegrityError`. Use `pg_insert(...).on_conflict_do_update()` for idempotent writes.
- **Relying on ORM relationship loading during batch upserts:** For bulk imports, bypass ORM relationships and use core INSERT ... ON CONFLICT for performance.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing from bytes | Custom line splitter | `pl.read_csv(io.BytesIO(raw_bytes))` | Handles quoting, escaping, BOM, encoding edge cases |
| Header validation | String compare against known list | Polars `.columns` attribute + set comparison | Instant, no iteration needed |
| Type coercion for amounts | Custom apostrophe stripper + float() | Polars `.str.strip_chars("'").cast(pl.Decimal)` | Handles nulls and edge cases cleanly |
| Deduplication logic | Custom SELECT + INSERT loop | `pg_insert(...).on_conflict_do_update()` | Atomic — no race condition; one round-trip per record |
| Request body validation | Manual dict validation | Pydantic `BaseModel` (already in stack) | Already used for config; same pattern for API bodies |
| Archive timestamping | Custom format string | `datetime.now(timezone.utc).strftime(...)` + `Path.write_bytes()` | Simple, no library needed |
| Import history persistence | In-memory list | `ImportRun` SQLAlchemy model | Survives restarts; queryable by dashboard (Phase 7) |

**Key insight:** This domain's risks are data corruption (bad rows silently inserted) and invisible failures (import runs not recorded). The patterns above prevent both without custom code.

---

## Common Pitfalls

### Pitfall 1: Polars Type Inference Surprises

**What goes wrong:** Polars infers an "amount" column as `Int64` from the first 100 rows, then fails on row 101 which has `$1,234.56` or a leading apostrophe.

**Why it happens:** `infer_schema_length` defaults to 100 — only samples the first 100 rows. Airbnb CSVs use apostrophe-prefixed amounts (`'150.00`) which look like strings initially, then the inferred type causes a cast error mid-parse.

**How to avoid:** Always use `infer_schema_length=0` for platform CSV files. Treat all columns as `Utf8` (string) on read; the adapter explicitly casts to correct types after cleaning.

**Warning signs:** `InvalidOperationError: cannot cast Utf8 to Int64` or mismatched types mid-import.

### Pitfall 2: `scan_csv()` Rejects BytesIO

**What goes wrong:** Code uses `pl.scan_csv(io.BytesIO(raw_bytes))` for lazy evaluation, raises `OSError: Expected file path or Path object, got ...`.

**Why it happens:** Polars lazy mode (`scan_csv`) does not support in-memory sources; only `read_csv` (eager) supports BytesIO.

**How to avoid:** Always use `pl.read_csv()` for in-memory bytes. CSVs at this scale (thousands of rows) don't need lazy evaluation.

**Warning signs:** `OSError` or `TypeError` when using `scan_csv` with BytesIO.

### Pitfall 3: python-multipart Not Installed

**What goes wrong:** `POST /ingestion/airbnb/upload` returns HTTP 422 with `{"detail": "Form data requires \"python-multipart\" to be installed"}` even though the endpoint looks correct.

**Why it happens:** FastAPI's multipart/form-data parsing depends on `python-multipart`. It's not included in `fastapi[standard]`.

**How to avoid:** `uv add python-multipart`. Verify with `python -c "import multipart"`.

**Warning signs:** HTTP 422 on file upload endpoint before any application code runs.

### Pitfall 4: Airbnb Multi-Row Events Produce Duplicate Records

**What goes wrong:** Importing an Airbnb CSV creates 3 records per reservation (booking creation, payout release, fee adjustment) instead of one net record.

**Why it happens:** Airbnb CSVs emit multiple rows per confirmation code — each row is a separate financial event for the same booking.

**How to avoid:** Group by `Confirmation Code` in the adapter before building `BookingRecord`. Sum amounts, take first guest name and dates. Emit one `BookingRecord` per confirmation code.

```python
# Group Airbnb multi-row events
grouped = df.group_by("Confirmation Code").agg([
    pl.col("Amount").str.strip_chars("'").cast(pl.Float64).sum().alias("net_amount"),
    pl.col("Guest").first(),
    pl.col("Start Date").first(),
    pl.col("End Date").first(),
])
```

**Warning signs:** `inserted_count` equals 3x the actual number of reservations.

### Pitfall 5: Archive Written After DB Commit

**What goes wrong:** DB write succeeds, archive write fails (disk full, permissions) — import is in DB but no raw file for audit.

**Why it happens:** Archive step placed after DB commit in the pipeline.

**How to avoid:** Archive first, always. The decision in CONTEXT.md is explicit: "Archive first, then process — even failed imports leave a trace." Archive before calling `upsert_records()`.

**Warning signs:** ImportRun records with no corresponding archived file.

### Pitfall 6: `on_conflict_do_update` Doesn't Update `updated_at`

**What goes wrong:** Re-imported records update field values but `updated_at` remains the original insert timestamp.

**Why it happens:** SQLAlchemy's `onupdate=func.now()` on the ORM model column is not triggered by `ON CONFLICT DO UPDATE` statements — those bypass ORM lifecycle events.

**How to avoid:** Explicitly include `updated_at` in the `set_` dict of `on_conflict_do_update`:

```python
from sqlalchemy import func
set_={"updated_at": func.now(), ...other fields...}
```

**Warning signs:** `updated_at` never changes on re-imports even though other fields update correctly.

### Pitfall 7: `archive_dir` Not Mounted in Docker

**What goes wrong:** Archives write to a path inside the container that isn't mounted, losing files on container restart.

**Why it happens:** The `archive_dir` config value points to a container-internal path without a Docker volume mount.

**How to avoid:** Add `archive_dir` to `AppConfig`, document it in `config/base.yaml` with a default like `./archive`. Mount `./archive:/app/archive` in `docker-compose.yml` the same way `config/` is mounted.

**Warning signs:** Archive files disappear after `docker-compose restart`.

### Pitfall 8: CSV Column Names Change Without Detection

**What goes wrong:** Airbnb silently renames a column in a future export (e.g., "Confirmation Code" → "Booking Code"). The adapter silently produces null values for that column in all rows.

**Why it happens:** `infer_schema_length=0` + Polars silently allows column access to return nulls when the column doesn't exist (depending on how you access it).

**How to avoid:** `validate_headers()` must be called before `parse()`. Use a frozenset of required column names and fail immediately if any are missing. The CONTEXT.md decision "fail immediately with clear message" for wrong structure applies here.

---

## Code Examples

Verified patterns from official sources and confirmed capabilities:

### Polars CSV from UploadFile bytes

```python
# Source: Polars docs (BytesIO support confirmed); FastAPI docs (await file.read())
import io
import polars as pl
from fastapi import UploadFile

async def parse_csv_upload(file: UploadFile) -> pl.DataFrame:
    raw_bytes = await file.read()
    return pl.read_csv(
        io.BytesIO(raw_bytes),
        infer_schema_length=0,    # all columns as Utf8
        null_values=["", "N/A"],
        has_header=True,
    )
```

### Airbnb amount normalization (apostrophe prefix)

```python
# Airbnb quirk: amounts like 'to '$150.00 or '-$50.00 (apostrophe separator in some exports)
# Silent normalization — no warning per CONTEXT.md decision
df = df.with_columns(
    pl.col("Amount")
      .str.strip_chars("'$,")   # remove apostrophe, dollar sign, commas
      .str.replace("-", "")     # handle negatives — or preserve sign depending on schema
      .cast(pl.Decimal(scale=2))
      .alias("net_amount")
)
```

### Header validation

```python
# Fail fast with descriptive message — exact column names must be confirmed from real exports
REQUIRED_HEADERS = frozenset(["Date", "Type", "Confirmation Code", ...])  # verify from actual file

def validate_headers(df: pl.DataFrame) -> None:
    actual = frozenset(df.columns)
    missing = REQUIRED_HEADERS - actual
    if missing:
        raise ValueError(
            f"This doesn't look like an Airbnb Transaction History CSV. "
            f"Expected headers: {sorted(REQUIRED_HEADERS)}. "
            f"Got: {sorted(actual)}. "
            f"Missing: {sorted(missing)}"
        )
```

### Row-level error collection (halt-and-report)

```python
errors = []
records = []
for row_num, row in enumerate(df.iter_rows(named=True), start=2):  # start=2 because row 1 is header
    row_errors = []
    if not row.get("Confirmation Code"):
        row_errors.append(f"Row {row_num}: Confirmation Code is missing")
    if row.get("Amount") is None:
        row_errors.append(f"Row {row_num}: Amount is missing")
    try:
        amount = Decimal(str(row["Amount"]).strip("'$,"))
    except Exception:
        row_errors.append(f"Row {row_num}: amount is not a number ({row['Amount']!r})")
    errors.extend(row_errors)
    if not row_errors:
        records.append(build_booking_record(row))

if errors:
    raise ValueError("\n".join(errors))  # halt-and-report: list all errors, write nothing
```

### PostgreSQL upsert with xmax for insert/update detection

```python
# Source: SQLAlchemy docs — postgresql dialect INSERT...ON CONFLICT
# xmax trick: https://www.postgresql.org/docs/current/ddl-system-columns.html
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import text

def upsert_booking(record: BookingRecord, db) -> str:
    """Returns 'inserted' or 'updated'."""
    stmt = pg_insert(Booking).values(**record.to_dict())
    stmt = stmt.on_conflict_do_update(
        index_elements=["platform", "platform_booking_id"],
        set_={
            "guest_name": stmt.excluded.guest_name,
            "check_in_date": stmt.excluded.check_in_date,
            "check_out_date": stmt.excluded.check_out_date,
            "net_amount": stmt.excluded.net_amount,
            "updated_at": func.now(),  # must be explicit — ORM onupdate not triggered
        }
    ).returning(text("xmax"))

    row = db.execute(stmt).fetchone()
    return "inserted" if row.xmax == 0 else "updated"
```

### Archival to timestamped path

```python
from datetime import datetime, timezone
from pathlib import Path

def archive_file(raw_bytes: bytes, filename: str, platform: str, archive_dir: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    dest_dir = Path(archive_dir) / platform
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{ts}_{filename}"
    dest_path.write_bytes(raw_bytes)
    return str(dest_path)
```

---

## Database Schema Design

### New Tables Required (Phase 2)

#### `bookings` table

Stores Airbnb, VRBO, and RVshare bookings in a unified schema.

```python
class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)          # "airbnb"|"vrbo"|"rvshare"
    platform_booking_id: Mapped[str] = mapped_column(String(128), nullable=False)  # confirmation code / reservation ID
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False)
    guest_name: Mapped[str] = mapped_column(String(255), nullable=False)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # pre-grouped net payout
    raw_platform_data: Mapped[dict] = mapped_column(JSON, nullable=True)        # original CSV row(s) for audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint for dedup: platform + platform_booking_id
    __table_args__ = (UniqueConstraint("platform", "platform_booking_id"),)
```

**Note on property_id:** Bookings must be associated with a property. For multi-listing Airbnb/VRBO accounts, the CSV may include a listing name or ID. Phase 2 needs to map CSV listing info to `property_id`. If the operator has one property per platform listing (the likely case here), this can default to a known property_id from config. This mapping strategy must be confirmed during planning.

#### `bank_transactions` table

```python
class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)  # Mercury's native ID
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)    # positive = credit, negative = debit
    raw_platform_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

#### `import_runs` table

```python
class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    archive_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### AppConfig Addition

`archive_dir` must be added to `AppConfig` (in `app/config.py`) and to `config/base.yaml`:

```yaml
# config/base.yaml addition
archive_dir: "./archive"   # override in .env as ARCHIVE_DIR for Docker
```

```python
# app/config.py AppConfig addition
archive_dir: str = "./archive"
"""Directory for raw CSV archives. Mount as a Docker volume for persistence."""
```

---

## CSV Schema Investigation (Open Questions)

The exact column names for all three platforms must be confirmed from real exports. The CONTEXT.md explicitly defers these to the researcher. Since no sample files exist in the repo, these are unresolved.

### Airbnb Transaction History CSV — UNCONFIRMED

**What is known from community forums and tool integrations:**
- Contains: confirmation code, guest name, amount, dates, transaction type
- Amount column uses apostrophe prefix in some exports (quirk confirmed in CONTEXT.md)
- Date format is US/non-ISO (confirmed as known quirk in CONTEXT.md)
- Multiple rows per booking (confirmed — grouped by confirmation code per CONTEXT.md)
- Accessible via: Airbnb host dashboard > Transaction History > Download CSV

**Likely column names (LOW confidence — must verify from actual export):**
```
Date, Type, Confirmation Code, Listing, Details, Reference, Currency,
Amount, Paid Out, Host Fee, Cleaning Fee, Guest Fee, Sub Total
```

**What to do before coding 02-01:**
Export an actual Airbnb Transaction History CSV from the host account and record exact column headers in the plan. Add as a fixture to `tests/fixtures/airbnb_sample.csv`.

### VRBO Payments Report CSV — MEDIUM confidence

**Confirmed from official VRBO help documentation:**
```
RefID, Payout ID, Reservation ID, Check In/Check Out, Number of Nights,
Source, Subscription Model, Payment Date, Disbursement Date, Payment Type,
Property ID, Guest Name, Payment Method, Taxable Revenue, Non-Taxable Revenue,
Guest Payment, Your Revenue, Payable To You, Tax, Service Fee, Currency,
Commission, VAT on Commission, Payment Processing Fee, Deposit Amount,
Stay Tax We Remit, Stay Tax You Remit, Refundable Deposit, Payout
```

**Stable ID:** `Reservation ID` — confirmed from VRBO docs as "unique booking identifier (remains same across multiple payments/refunds)".

**Key fields for canonical schema:**
- `Reservation ID` → `platform_booking_id`
- `Guest Name` → `guest_name`
- `Payable To You` → `net_amount` (net payout to owner, after fees)
- `Payment Date` → useful for grouping
- `Check In/Check Out` → needs parsing (format TBD from actual export)

**What to do before coding 02-02:**
Export an actual VRBO Payments Report and confirm column headers match. Note exact date format for `Check In/Check Out` and whether it's one or two columns.

### Mercury Bank Transaction CSV — UNCONFIRMED

**What is known:**
- Mercury offers CSV download per account
- Two pre-formatted options: QuickBooks CSV and NetSuite CSV (different column names)
- Also a generic CSV download

**Mercury native CSV likely columns (LOW confidence — must confirm from actual export):**
```
Date, Description, Amount, Running Balance, Category, Account, Bank Name
```
Or in QuickBooks format:
```
Date, Description, Original Description, Amount, Transaction Type, Category, Account Name, Labels, Notes
```

**Stable ID:** The CONTEXT.md states "platform-native transaction ID as stable key" — but the Mercury CSV column name for this ID is unconfirmed. Mercury's transaction IDs may not appear in their CSV export at all; if absent, deduplication must use a composite key (Date + Amount + Description). **This is a critical uncertainty.**

**What to do before coding 02-03:**
Export an actual Mercury transaction CSV, confirm whether a transaction ID column exists, and determine the deduplication key.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pandas for CSV | Polars | 2023+ | 5-25x faster; less memory; BytesIO support |
| Session.add() for upserts | pg_insert + on_conflict_do_update | SQLAlchemy 2.0+ | Atomic; no IntegrityError risk |
| Separate SELECT + INSERT for dedup | Single INSERT...ON CONFLICT | Always PostgreSQL feature | One round-trip; race-condition free |
| Manual multipart parsing | python-multipart + FastAPI UploadFile | FastAPI 0.x | Framework handles parsing; dev only handles bytes |

**Deprecated/outdated:**
- `pl.scan_csv()` for in-memory bytes: Does not support BytesIO; use `pl.read_csv()`.
- `dtypes` parameter in Polars `read_csv()`: Renamed to `schema_overrides` in Polars 0.20.31. Use `schema_overrides`.
- `@app.on_event("startup")` FastAPI decorator: Still applies from Phase 1 — already using `lifespan`.

---

## Open Questions

### 1. Exact Airbnb CSV column names (HIGH PRIORITY — blocks 02-01)

- **What we know:** Confirmation code, amount (with apostrophe quirk), date (non-ISO), multi-row per booking
- **What's unclear:** Exact header strings — "Confirmation Code" vs "Booking Reference", "Amount" vs "Gross Earnings", etc.
- **Recommendation:** Before writing the adapter, export a real Airbnb Transaction History CSV. Add as a test fixture. Document exact headers in the 02-01 plan.

### 2. Mercury CSV transaction ID field (HIGH PRIORITY — blocks 02-03)

- **What we know:** CONTEXT.md says use "platform-native transaction ID" for Mercury dedup
- **What's unclear:** Whether Mercury's CSV export includes a unique transaction ID column at all. QuickBooks CSV and generic CSV formats may differ.
- **Recommendation:** Export a Mercury CSV before planning 02-03. If no transaction ID column exists, dedup key must be composite (Date + Amount + Description hash). Note this in the plan.

### 3. Property-to-booking mapping

- **What we know:** Bookings need `property_id` FK; this account has two properties (Jay, Minnie)
- **What's unclear:** Airbnb/VRBO CSVs likely include a listing name or ID — how does that map to the `properties` table slug/id? If the account has exactly one listing per platform, default to a single property. If multiple, need explicit mapping.
- **Recommendation:** Confirm whether Airbnb CSV includes a "Listing" or "Listing Title" column (likely). VRBO CSV has `Property ID` column (confirmed). Provide a mapping in `base.yaml` or per-property config: `airbnb_listing_title: "Jay's Place"`.

### 4. Airbnb date format exact string

- **What we know:** Date format is "American format" / non-ISO (confirmed in CONTEXT.md as known quirk)
- **What's unclear:** Exact format string — `MM/DD/YYYY`, `M/D/YYYY`, `Jan 15, 2025`, etc.
- **Recommendation:** Verify from actual export. Polars `try_parse_dates=False` + explicit `strptime` is safer than auto-parsing.

### 5. VRBO "Check In/Check Out" column format

- **What we know:** VRBO docs list a single column called "Check In/Check Out"
- **What's unclear:** Whether this is one column with a date range (e.g., "01/15/2025 - 01/20/2025") or two separate columns
- **Recommendation:** Verify from actual VRBO Payments Report export. If combined, parse with split and strptime.

---

## Sources

### Primary (HIGH confidence)

- https://pypi.org/project/polars/ — Version 1.38.1 confirmed (released 2026-02-06)
- https://docs.pola.rs/user-guide/io/csv/ — read_csv vs scan_csv, BytesIO support confirmed
- https://deepwiki.com/pola-rs/polars/7.2-csv-and-spreadsheet-io — read_csv parameter table (has_header, schema_overrides, null_values, try_parse_dates, separator, infer_schema_length)
- https://fastapi.tiangolo.com/tutorial/request-files/ — UploadFile API, await file.read() pattern, SpooledTemporaryFile behavior
- https://docs.sqlalchemy.org/en/20/dialects/postgresql.html — pg_insert, on_conflict_do_update, excluded alias
- https://help.vrbo.com/articles/How-do-I-read-my-payments-report — VRBO CSV column headers (all 29 columns confirmed)
- https://sentry.io/answers/upload-a-csv-file-in-fastapi-and-convert-it-to-json/ — FastAPI CSV upload pattern with bytes → decode → parse

### Secondary (MEDIUM confidence)

- Community Airbnb forum threads — confirm multi-row structure, apostrophe amounts, US date format; no exact column headers available
- GitHub pola-rs/polars issues #12617, #9266 — scan_csv BytesIO limitation confirmed; read_csv BytesIO confirmed
- GitHub pola-rs/polars issues #18951, #20903, #23837 — schema_overrides known bugs in some versions; use with care

### Tertiary (LOW confidence)

- WebSearch: Mercury bank CSV format — generic description only; actual column headers unconfirmed from official docs
- WebSearch: Airbnb exact column names — community posts reference fields but no authoritative header list found

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Polars 1.38.1 on PyPI, python-multipart requirement confirmed, SQLAlchemy upsert from official docs
- Architecture: HIGH — FastAPI UploadFile pattern from official docs, Polars BytesIO confirmed, upsert pattern from SQLAlchemy official docs
- VRBO CSV schema: MEDIUM — from official VRBO help documentation
- Airbnb CSV schema: LOW — column names unverified; must inspect actual export
- Mercury CSV schema: LOW — column names unverified; transaction ID existence unconfirmed
- Pitfalls: HIGH for Polars/SQLAlchemy pitfalls (multiple sources), MEDIUM for archival pitfalls (logic-derived)

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (Polars and FastAPI stable; VRBO/Airbnb CSV format could change without notice)
