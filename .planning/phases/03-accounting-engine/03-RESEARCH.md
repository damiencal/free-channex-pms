# Phase 3: Accounting Engine - Research

**Researched:** 2026-02-27
**Domain:** Double-entry bookkeeping, revenue recognition, bank reconciliation, SQLAlchemy financial data patterns
**Confidence:** HIGH (SQLAlchemy/DB patterns, loan accounting, standard schema), MEDIUM (Airbnb fee model), LOW (discount CSV field availability)

---

## Summary

Phase 3 builds a double-entry bookkeeping ledger engine on top of the Phase 2 data ingestion layer. The primary technology is already in place (PostgreSQL via SQLAlchemy 2.0, FastAPI, Python 3.12) — no new framework dependencies are required. The accounting domain adds specific data models and application-layer patterns that are well-established and do not require external libraries.

The standard approach for double-entry accounting in PostgreSQL is: a `journal_entries` header table (one per transaction event) paired with a `journal_lines` table (two or more rows per entry — always balanced). Balance enforcement is handled at the application layer (sum of amounts must equal zero before committing) rather than a database CHECK constraint, because the "SUM = 0" invariant spans multiple rows in a related table — a pattern that CHECK constraints cannot enforce across rows. A `accounts` table holds the chart of accounts. Idempotent journal entry creation uses a stable `source_id` (e.g., `airbnb_HMABCDEF_payout`) with `INSERT ... ON CONFLICT DO NOTHING` at the entry level.

The critical blocker from CONTEXT.md — verifying whether the 15.5% Airbnb host-only fee applies to this account — has been resolved through research. **The fee model depends on how the account is connected.** PMS-connected hosts transitioned by October 27, 2025; individual hosts who previously used simplified pricing transitioned by December 1, 2025; individual hosts who were NOT on simplified pricing may still be on the old split-fee model (3% host). The operator must confirm which model their account is currently on before the fee calculation logic is wired in.

**Primary recommendation:** Use a two-table journal entry design (`journal_entries` + `journal_lines`) with application-layer balance enforcement, `Numeric(12, 2)` for all monetary amounts, and a stable `source_id` string for idempotency. No new pip dependencies are needed.

---

## Standard Stack

The entire Phase 3 stack is already installed. No new packages are required.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.x (installed) | ORM models, upsert, session management | Already in stack; 2.0 style with `Mapped[]` annotations is the current pattern |
| PostgreSQL NUMERIC | (DB column type) | Exact decimal storage for monetary amounts | NUMERIC avoids floating-point rounding errors; required for financial data |
| Python `decimal.Decimal` | stdlib | Python-side exact arithmetic | SQLAlchemy `Numeric` maps to `Decimal` in Python; never use `float` for money |
| Alembic | installed | Database migrations | Already in stack; new tables added via new version file |
| FastAPI | installed | API endpoints for journal query, expense entry | Already in stack |
| Pydantic | installed | Request/response schemas for accounting endpoints | Already in stack |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `enum.Enum` | stdlib | Typed constants for account types, journal line types | Debit/credit direction, account category |
| Python `dataclasses` | stdlib | Lightweight entry builder objects before DB commit | Assembling journal lines before batch insert |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Application-layer balance check | PostgreSQL CHECK constraint | CHECK constraints cannot enforce "sum of related rows = 0"; application layer is the correct location |
| Application-layer balance check | PostgreSQL trigger | Triggers work but add DB-level complexity and are harder to test; application layer is simpler and testable in pytest |
| Custom double-entry library (python-accounting, pyluca) | Hand-rolled models | These libraries target Django or generic use; adding them as dependencies creates a heavy abstraction layer over a simple schema that doesn't need it |
| Numeric(12, 2) | Storing amounts as integers (cents) | Integer storage is faster but adds conversion complexity everywhere; Decimal is cleaner for a single-currency, low-volume system |

### Installation

No new packages needed. All dependencies are already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure (Phase 3 additions)

```
app/
├── models/
│   ├── property.py              # (existing)
│   ├── booking.py               # (existing)
│   ├── bank_transaction.py      # (existing)
│   ├── import_run.py            # (existing)
│   ├── account.py               # NEW: Chart of accounts
│   ├── journal_entry.py         # NEW: Journal entry header
│   ├── journal_line.py          # NEW: Journal entry lines (debits/credits)
│   ├── expense.py               # NEW: Expense records
│   ├── loan.py                  # NEW: Loan liability accounts
│   └── reconciliation.py        # NEW: Payout-to-deposit match records
├── accounting/                  # NEW: accounting package
│   ├── __init__.py
│   ├── journal.py               # Journal entry builder + balance enforcement
│   ├── revenue.py               # Booking → journal entry logic
│   ├── expenses.py              # Expense entry logic
│   ├── loans.py                 # Loan payment split logic
│   └── reconciliation.py        # Payout-to-deposit matching algorithm
├── api/
│   ├── health.py                # (existing)
│   ├── ingestion.py             # (existing)
│   └── accounting.py            # NEW: accounting API endpoints
alembic/
└── versions/
    ├── 001_initial_properties.py   # (existing)
    ├── 002_ingestion_tables.py     # (existing)
    └── 003_accounting_tables.py    # NEW
```

### Pattern 1: Two-Table Double-Entry Journal Design

**What:** Every financial event creates one `JournalEntry` header row and two or more `JournalLine` rows. The sum of all line amounts for a single entry must be zero (debits are positive, credits are negative — or use an explicit `direction` enum). The header holds metadata (date, description, source_id for idempotency). The lines hold account references and amounts.

**When to use:** Every financial event — booking payout recognition, expense recording, loan payment, adjustment.

```python
# Source: Standard double-entry schema pattern (verified from multiple authoritative sources)
# app/models/journal_entry.py
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, Numeric, String, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    """Type of source: 'booking_payout', 'expense', 'loan_payment', 'reversal', 'adjustment'"""
    source_id: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    """Stable idempotency key. Format: '{source_type}:{platform}:{platform_id}:{event}'
    Examples: 'booking_payout:airbnb:HMABCDEF123', 'expense:2026-02-15:uuid4'
    Unique constraint ensures no duplicate journal entries for same event."""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["JournalLine"]] = relationship(back_populates="entry", cascade="all, delete-orphan")
```

```python
# app/models/journal_line.py
from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    """Signed amount. Debit = positive, Credit = negative.
    The sum of all lines in one entry must equal zero.
    Using signed amounts avoids a direction enum and makes SUM checks trivial."""
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    entry: Mapped["JournalEntry"] = relationship(back_populates="lines")
    account: Mapped["Account"] = relationship()
```

### Pattern 2: Application-Layer Balance Enforcement

**What:** Before committing a journal entry to the database, assert that the sum of all line amounts equals zero. Raise `ValueError` if not. This is enforced in the journal builder function, not as a DB constraint.

**Why application layer:** A PostgreSQL CHECK constraint can only inspect a single row at a time. Enforcing "sum of related rows = 0" requires a trigger — which is harder to unit-test and mixes business logic into the DB layer. The application layer enforcement is simpler, fully testable with pytest, and sufficient for a single-writer system.

```python
# Source: Standard pattern from authoritative accounting engineering references
# app/accounting/journal.py
from decimal import Decimal
from dataclasses import dataclass
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine


@dataclass
class LineSpec:
    account_id: int
    amount: Decimal          # positive = debit, negative = credit
    description: str | None = None


def create_journal_entry(
    db: Session,
    entry_date: date,
    description: str,
    source_type: str,
    source_id: str,
    lines: list[LineSpec],
) -> JournalEntry | None:
    """Create a balanced journal entry. Returns None if source_id already exists (idempotent).

    Raises ValueError if lines do not sum to zero.
    """
    # Balance check — application layer enforcement
    total = sum(line.amount for line in lines)
    if total != Decimal("0"):
        raise ValueError(
            f"Journal entry lines do not balance: sum={total}. "
            f"source_id={source_id!r}"
        )

    if len(lines) < 2:
        raise ValueError("A journal entry requires at least two lines.")

    # Idempotent insert — skip if source_id already exists
    stmt = pg_insert(JournalEntry).values(
        entry_date=entry_date,
        description=description,
        source_type=source_type,
        source_id=source_id,
    ).on_conflict_do_nothing(index_elements=["source_id"])

    result = db.execute(stmt)
    if result.rowcount == 0:
        # Already exists — idempotent; return None to signal skip
        return None

    # Fetch the inserted entry to get its ID for the lines
    entry = db.query(JournalEntry).filter_by(source_id=source_id).one()

    for line in lines:
        db.add(JournalLine(
            entry_id=entry.id,
            account_id=line.account_id,
            amount=line.amount,
            description=line.description,
        ))

    db.flush()  # write lines within same transaction; caller calls db.commit()
    return entry
```

### Pattern 3: Chart of Accounts Model

**What:** A `accounts` table holds all accounts referenced in journal lines. Account number ranges follow the standard convention. Each account has a type that determines normal balance direction.

```python
# app/models/account.py
from sqlalchemy import Integer, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    """Account number. Ranges: 1000-1999 Assets, 2000-2999 Liabilities,
    3000-3999 Equity, 4000-4999 Revenue, 5000-5999 Expenses."""
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    """One of: 'asset', 'liability', 'equity', 'revenue', 'expense'"""
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __table_args__ = (
        CheckConstraint("number >= 1000 AND number <= 9999", name="ck_account_number_range"),
    )
```

### Pattern 4: Airbnb Deferred-Then-Recognized Revenue

**What:** Airbnb's multi-row event model requires a two-phase journal entry pattern. Booking creation row creates an Unearned Revenue entry. Payout row converts it to Rental Income.

**When to use:** Airbnb bookings only. VRBO and RVshare use single-event recognition.

```python
# Phase 1: Booking creation (Reservation row in CSV — no Confirmation Code, has dates/amount)
# Entry: Dr. Accounts Receivable (or placeholder), Cr. Unearned Revenue
#
# Phase 2: Payout release (Payout row in CSV — grouped with Reservation by Confirmation Code)
# Entry: Dr. Unearned Revenue, Cr. Rental Income
#        Dr. Platform Fees Expense, Cr. Accounts Receivable (clears the receivable)
#
# In practice: with the current Phase 2 grouping logic (net amount per confirmation code),
# Phase 3 sees the booking record AFTER grouping. The deferred/recognized pattern must
# operate on the raw booking's group composition, not just the net amount.
# See Open Questions section for the implications of this.
```

**Important note on current Phase 2 state:** The existing `airbnb.py` adapter groups all rows by `Confirmation Code` and produces a single `BookingRecord` with the net amount. The deferred/recognized pattern requires access to individual row types within the group (Reservation vs Payout rows). The accounting engine will need to inspect `raw_platform_data["rows"]` (which stores all original CSV rows) to determine the row types and apply the correct journal entry pattern. The `Type` column in the Airbnb CSV carries the event type per row.

### Pattern 5: Expense Entry Model

**What:** Expenses are recorded both as a journal entry (for the ledger) and as a structured expense record (for categorized reporting).

```python
# app/models/expense.py
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db import Base


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), nullable=True)
    """None = Shared expense (not auto-split). Jay or Minnie = property-specific."""
    attribution: Mapped[str] = mapped_column(String(32), nullable=False)
    """One of: 'jay', 'minnie', 'shared'"""
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    """Schedule E-aligned category. See EXPENSE_CATEGORIES constant."""
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), nullable=True)
    """FK to the journal entry that records this expense in the double-entry ledger."""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

```python
# Valid expense categories (Schedule E-aligned per CONTEXT.md decisions)
EXPENSE_CATEGORIES = [
    "repairs_maintenance",
    "supplies",
    "utilities",
    "non_mortgage_interest",
    "owner_reimbursable",
    "advertising",
    "travel_transportation",
    "professional_services",
    "legal",
    "insurance",
    "resort_lot_rental",
    "cleaning_service",
]
```

### Pattern 6: Loan Model and Payment Splitting

**What:** Loan liability accounts track outstanding balance. Each payment splits into a principal component (reduces the liability account) and an interest component (expense account). The caller provides the split amounts — derived from the loan amortization schedule provided by the lender.

**Standard journal entry for a loan payment:**
```
Dr. Loan Liability Account    $157.05   (principal reduction)
Dr. Non-Mortgage Interest Expense $30.00   (interest)
    Cr. Cash / Bank Account           $187.05
```

```python
# app/models/loan.py
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db import Base


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    """Descriptive name, e.g., 'RV Purchase Loan', 'Working Capital Loan'"""
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    """The liability account in the chart of accounts."""
    original_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    """Annual interest rate as a decimal, e.g., 0.0650 for 6.5%"""
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### Pattern 7: Bank Reconciliation Algorithm

**What:** Match platform payout records against Mercury bank deposits. The CONTEXT.md decision is: exact amount + date within 7-day window. When multiple payouts match one deposit (same amount, same window), flag as "needs review". Unmatched deposits stay in the unreconciled queue.

**When to use:** After payout data and bank transactions are both ingested (Phase 2 output is the input here).

```python
# app/accounting/reconciliation.py
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.booking import Booking
from app.models.bank_transaction import BankTransaction
from app.models.reconciliation import ReconciliationMatch


MATCH_WINDOW_DAYS = 7  # per CONTEXT.md decision


def find_matches(db: Session) -> dict:
    """Run reconciliation algorithm against all unmatched payouts and deposits.

    Returns dict with:
        matched: list of (booking_id, bank_transaction_id) pairs auto-matched
        needs_review: list of bank_transaction_ids with multiple candidate payouts
        unmatched_payouts: list of booking_ids with no matching bank deposit
        unmatched_deposits: list of bank_transaction_ids with no matching payout
    """
    # Fetch all unreconciled payouts (platform payout records without a confirmed match)
    unreconciled_payouts = db.query(Booking).filter(
        Booking.reconciliation_status == "unmatched"
    ).all()

    # Fetch all unreconciled deposits (bank credits without a confirmed match)
    unreconciled_deposits = db.query(BankTransaction).filter(
        BankTransaction.amount > 0,
        BankTransaction.reconciliation_status == "unmatched",
    ).all()

    matched = []
    needs_review = []

    for deposit in unreconciled_deposits:
        # Find all payouts where amount matches exactly and date is within window
        candidates = [
            p for p in unreconciled_payouts
            if p.net_amount == deposit.amount
            and abs((deposit.date - p.check_in_date).days) <= MATCH_WINDOW_DAYS
            # Note: payout date is approximately check-in date per CONTEXT.md
        ]

        if len(candidates) == 1:
            matched.append((candidates[0].id, deposit.id))
        elif len(candidates) > 1:
            needs_review.append(deposit.id)
        # else: zero candidates — deposit stays unreconciled

    return {
        "matched": matched,
        "needs_review": needs_review,
        "unmatched_payouts": [...],  # payouts with no deposit match
        "unmatched_deposits": [...],  # deposits with no payout match
    }
```

```python
# app/models/reconciliation.py
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db import Base


class ReconciliationMatch(Base):
    __tablename__ = "reconciliation_matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=False, unique=True)
    bank_transaction_id: Mapped[int] = mapped_column(ForeignKey("bank_transactions.id"), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    """One of: 'matched' (auto), 'confirmed' (operator confirmed), 'needs_review' (ambiguous)"""
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
```

### Anti-Patterns to Avoid

- **Using `float` for monetary amounts:** Floating-point arithmetic produces rounding errors that compound over many transactions. Always use `Decimal` in Python and `NUMERIC` in PostgreSQL.
- **Storing debit/credit as separate columns with a direction flag:** Using a single signed amount (positive=debit, negative=credit) makes balance checking trivial (`sum(amounts) == 0`). Separate columns require more complex validation.
- **Enforcing journal balance with a DB trigger:** Triggers mix business logic into the database layer and are harder to unit-test. The application-layer check in `create_journal_entry()` is simpler and sufficient.
- **Auto-splitting shared expenses:** CONTEXT.md decision: shared expenses are NOT auto-split. Reports show per-property and combined views. Do not add auto-split logic.
- **Using the `money` PostgreSQL type:** The PostgreSQL `money` type has locale-dependent behavior and limited arithmetic support. Use `NUMERIC(12, 2)` instead.
- **Hard-coding the Airbnb fee percentage:** The 15.5% rate may or may not apply to this account (see Open Questions). The fee percentage must be configurable, not a hard-coded constant.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Idempotent entry creation | Custom SELECT-then-INSERT logic | `pg_insert(...).on_conflict_do_nothing()` on `source_id` | Atomic; no race condition; one round-trip |
| Loan amortization schedule | Calculate P&I split in code | Accept P and I amounts in the API request | Operator uses lender-provided schedule; code doesn't need to compute it |
| Rounding arithmetic for financial amounts | `round()` built-in | `Decimal` with explicit `ROUND_HALF_UP` | Python `round()` uses banker's rounding which surprises accountants |
| Currency conversion | Any conversion library | N/A — single currency (USD) per CONTEXT.md | System is USD-only; no conversion needed |

**Key insight:** This domain's risk is data corruption (imbalanced entries that can't be audited). The patterns above ensure every entry in the DB is balanced and idempotent.

---

## Recommended Chart of Accounts

Standard account number ranges (verified from AccountingTools, AccountingCoach, and multiple small-business accounting references):

```
1000-1999   Assets
2000-2999   Liabilities
3000-3999   Equity
4000-4999   Revenue (and contra-revenue)
5000-5999   Expenses
```

### Proposed Chart of Accounts for This System

```python
# Seed data for accounts table — created in 003_accounting_tables.py migration
CHART_OF_ACCOUNTS = [
    # ASSETS
    {"number": 1010, "name": "Mercury Checking",           "account_type": "asset"},
    {"number": 1020, "name": "Accounts Receivable",        "account_type": "asset"},

    # LIABILITIES
    {"number": 2010, "name": "Unearned Revenue",           "account_type": "liability"},
    {"number": 2100, "name": "RV Purchase Loan Payable",   "account_type": "liability"},
    {"number": 2110, "name": "Working Capital Loan Payable","account_type": "liability"},
    {"number": 2200, "name": "Owner Reimbursable",         "account_type": "liability"},
    # (one liability account per loan — exact number of loans TBD by operator)

    # EQUITY
    {"number": 3000, "name": "Owner Equity",               "account_type": "equity"},

    # REVENUE (4000s)
    {"number": 4000, "name": "Rental Income",              "account_type": "revenue"},
    {"number": 4010, "name": "Promotional Discounts",      "account_type": "revenue"},
    # Account 4010 is contra-revenue (normal balance is debit — reduces gross revenue)

    # EXPENSES (5000s — Schedule E-aligned)
    {"number": 5010, "name": "Platform Fees",              "account_type": "expense"},
    {"number": 5100, "name": "Repairs & Maintenance",      "account_type": "expense"},
    {"number": 5110, "name": "Supplies",                   "account_type": "expense"},
    {"number": 5120, "name": "Utilities",                  "account_type": "expense"},
    {"number": 5130, "name": "Non-Mortgage Interest",      "account_type": "expense"},
    {"number": 5140, "name": "Advertising",                "account_type": "expense"},
    {"number": 5150, "name": "Travel & Transportation",    "account_type": "expense"},
    {"number": 5160, "name": "Professional Services",      "account_type": "expense"},
    {"number": 5170, "name": "Legal",                      "account_type": "expense"},
    {"number": 5180, "name": "Insurance",                  "account_type": "expense"},
    {"number": 5190, "name": "Resort Lot Rental Fees",     "account_type": "expense"},
    {"number": 5200, "name": "Cleaning Service Fees",      "account_type": "expense"},
]
```

Account numbers are seeded as part of the Alembic migration `003_accounting_tables.py` — not managed by the application at runtime.

---

## Airbnb Fee Model — Blocker Resolution

**Critical context from CONTEXT.md:** "Blocker to verify before coding fee attribution: Airbnb changed fee model in October 2025 to host-only fee at 15.5% — must confirm which model applies to this account before wiring the fee calculation into revenue recognition logic."

**Research findings (MEDIUM confidence — multiple sources agree but official Airbnb page blocked JavaScript rendering):**

The October 2025 change was NOT universal for all hosts. The rollout was phased:

| Host Type | Transition Date | Fee Model After |
|-----------|----------------|-----------------|
| PMS-connected hosts (Hostaway, Guesty, etc.) | October 27, 2025 | Host-only 15.5% mandatory |
| Non-PMS hosts on simplified pricing | December 1, 2025 | Host-only 15.5% standardized |
| Non-PMS hosts NOT on simplified pricing (traditional split-fee) | No mandatory change announced | Old split-fee (3% host + 14-16% guest) may still apply |

**Sources:** rentalscaleup.com (citing official Airbnb communications), beyondpricing.com, hospitable.com support docs. All agree on this three-tier structure.

**What this means for Phase 3:** The fee percentage in the revenue recognition logic must be **configurable** rather than hard-coded. Before coding plan 03-02 (revenue recognition), the operator must check their Airbnb host dashboard to confirm whether they are on:
- Host-only fee: 15.5% applied to booking subtotal (nightly + cleaning + extra fees)
- Split-fee: 3% host fee applied to their payout amount

**The fee base also differs:** Under host-only, 15.5% applies to the full booking subtotal including cleaning fees. Under split-fee, the host pays 3% of the reservation subtotal excluding taxes. The journal entry structure differs between these models.

**Recommended approach for Phase 3 coding:**
1. Make fee percentage a config value in `AppConfig` (e.g., `airbnb_host_fee_rate: float`)
2. Make fee model a config enum (e.g., `airbnb_fee_model: 'host_only' | 'split_fee'`)
3. Revenue recognition logic reads from config — not hard-coded
4. Operator sets these values after confirming with their Airbnb dashboard

---

## Discount Field Research — Airbnb CSV

**Research question from CONTEXT.md:** "Promotional discounts tracked as contra-revenue — data availability in CSV imports to be confirmed during research."

**Findings (LOW confidence — no authoritative source found):**

The Airbnb Transaction History CSV's `Type` column contains row type values for each transaction event. Research indicates the following row types appear:
- `Payout` (the actual bank transfer)
- `Reservation` (booking creation with guest and dates)
- `Resolution` (adjustment/correction)
- `Host fee` (per-booking service fee — older split-fee model)
- `Cleaning fee` (if separately tracked)

**What is NOT confirmed:** Whether a distinct row type for "Promotional discount" (platform-funded discounts, early bird discounts, weekly/monthly discounts) appears in the CSV. Multiple searches and community forum reviews did not produce a clear answer.

**Two scenarios and their implications:**

1. **Discounts DO appear as a separate row type in the CSV:** The current Phase 2 grouping logic sums all row amounts by Confirmation Code, so a discount row's negative amount would already reduce the net_amount in the `BookingRecord`. The discount amount can be extracted from `raw_platform_data["rows"]` for contra-revenue tracking by filtering for the discount row type.

2. **Discounts do NOT appear as separate rows:** They are already reflected in the nightly rate (i.e., Airbnb adjusts the reservation amount before the CSV is generated). In this case, no separate discount journal entry is needed — the gross booking amount in the CSV is already net of discounts, and contra-revenue tracking is not possible from CSV data alone.

**Recommended approach:**
- Implement the accounting engine without discount extraction initially (discounts flow through as reduced net income)
- Inspect an actual Airbnb Transaction History CSV that includes a promotional discount booking to see if a distinct row type appears
- If it does, add extraction logic in plan 03-02 as a follow-on task
- Document this as LOW confidence and flag it for operator verification

---

## Common Pitfalls

### Pitfall 1: Using Float for Monetary Amounts

**What goes wrong:** Decimal arithmetic with floats produces subtle rounding errors. For example, `0.1 + 0.2 == 0.30000000000000004` in Python.

**Why it happens:** IEEE 754 floating-point cannot exactly represent most decimal fractions.

**How to avoid:** Always use `decimal.Decimal` in Python and `NUMERIC(12, 2)` in PostgreSQL. Never cast monetary amounts to `float` at any point in the pipeline.

**Warning signs:** Balance checks that fail by $0.01 on valid entries; rounding differences accumulating over many transactions.

### Pitfall 2: Imbalanced Journal Entry Committed to DB

**What goes wrong:** A bug in the journal builder produces an entry where debits do not equal credits. The ledger is permanently corrupted.

**Why it happens:** Missing a line in complex entries (e.g., forgetting the platform fee line in a revenue recognition entry).

**How to avoid:** The `create_journal_entry()` function must assert `sum(amounts) == Decimal("0")` before writing ANY lines. This assertion must be the first operation after assembling the line list — not a final check after partial writes.

**Warning signs:** Trial balance report shows non-zero total; ledger accounts don't foot correctly.

### Pitfall 3: Duplicate Journal Entries on Re-Ingestion

**What goes wrong:** Re-uploading an Airbnb CSV (common during troubleshooting) creates duplicate journal entries for bookings already in the system, doubling revenue figures.

**Why it happens:** The journal entry builder doesn't check if an entry already exists for a booking event.

**How to avoid:** Use `source_id` as a unique key on `journal_entries`. Format: `f"booking_payout:{platform}:{platform_booking_id}"`. Use `INSERT ... ON CONFLICT DO NOTHING` — the function returns `None` to signal the skip.

**Warning signs:** Revenue doubles after re-ingestion; duplicate entries in the ledger report.

### Pitfall 4: Reconciliation Date Window Using Wrong Payout Date

**What goes wrong:** The 7-day window match uses the wrong date field from the booking record as the payout date reference, causing valid matches to be missed or invalid matches to be made.

**Why it happens:** Airbnb typically pays out on check-in day. The `check_in_date` is the correct reference for the date window comparison, not `created_at` or `updated_at`.

**How to avoid:** Match `bank_transaction.date` against `booking.check_in_date ± 7 days` per CONTEXT.md specification.

**Warning signs:** Valid payouts not matching even though amounts match exactly.

### Pitfall 5: Missing `reconciliation_status` Column on Bookings and BankTransactions

**What goes wrong:** The reconciliation engine queries bookings and bank transactions for unreconciled records but these tables don't have a status field, requiring a full join to `reconciliation_matches` on every query.

**Why it happens:** Not adding a status/flag column to the source tables when designing the reconciliation schema.

**How to avoid:** Add `reconciliation_status` column to both `bookings` and `bank_transactions` tables (values: `'unmatched'`, `'matched'`, `'confirmed'`, `'needs_review'`). Default to `'unmatched'` on insert. Update when a match is created or confirmed. This makes the unreconciled queue query trivial.

**Warning signs:** Reconciliation queries require complex joins; performance degrades as transaction volume grows.

### Pitfall 6: Airbnb Phase 2 Grouping Obscures Row-Type Information

**What goes wrong:** The deferred/recognized revenue pattern requires distinguishing Reservation rows from Payout rows within an Airbnb multi-row booking group. The Phase 2 adapter groups these into a single `BookingRecord` with just the net amount.

**Why it happens:** Phase 2 was designed to produce one canonical booking per confirmation code — correct for ingestion but lossy for accounting purposes.

**How to avoid:** The `raw_platform_data["rows"]` field on `Booking` stores all original CSV rows. The revenue recognition logic in Phase 3 must inspect this field, filtering rows by their `Type` column value to determine what kind of event each row represents.

**Warning signs:** Revenue recognized at wrong time; unearned revenue accounts not clearing properly.

### Pitfall 7: Missing Loan Account in Chart of Accounts at Migration Time

**What goes wrong:** Loan payment journal entries reference a loan liability account that doesn't exist yet because the chart of accounts seed data didn't include all loans.

**Why it happens:** The number of loans is not known at migration authoring time, so the seed data is incomplete.

**How to avoid:** The Alembic migration seeds a generic `Loan Payable` placeholder account. The actual loan accounts (named per specific loan) are created via an admin API endpoint or directly in the DB before recording loan payments. Document this setup step in the plan.

---

## Code Examples

Verified patterns from official sources and the existing codebase:

### Journal Entry Creation (Balanced)

```python
# Source: Application pattern; balance enforcement from authoritative double-entry accounting references
from decimal import Decimal
from app.accounting.journal import create_journal_entry, LineSpec
from app.models.account import Account

def record_payout_revenue(db, booking, accounts: dict[str, Account]):
    """Record Airbnb payout as revenue recognition.

    Journal entry:
        Dr. Mercury Checking      +net_amount   (debit increases asset)
        Cr. Rental Income         -gross_amount (credit increases revenue)
        Dr. Platform Fees Expense +fee_amount   (debit increases expense)

    Note: Dr. + Dr. + Cr. must sum to zero.
    gross_amount = net_amount + fee_amount
    """
    net_amount = booking.net_amount
    fee_amount = calculate_platform_fee(gross_amount, config.airbnb_host_fee_rate)
    gross_amount = net_amount + fee_amount

    create_journal_entry(
        db=db,
        entry_date=booking.check_in_date,   # per CONTEXT.md: revenue at payout (check-in)
        description=f"Airbnb payout: {booking.platform_booking_id}",
        source_type="booking_payout",
        source_id=f"booking_payout:airbnb:{booking.platform_booking_id}",
        lines=[
            LineSpec(account_id=accounts["Mercury Checking"].id,   amount=net_amount),
            LineSpec(account_id=accounts["Rental Income"].id,      amount=-gross_amount),
            LineSpec(account_id=accounts["Platform Fees"].id,      amount=fee_amount),
        ],
    )
    # Verification: net_amount + (-gross_amount) + fee_amount
    #             = net_amount - gross_amount + fee_amount
    #             = net_amount - (net_amount + fee_amount) + fee_amount = 0 ✓
```

### Loan Payment Journal Entry

```python
# Source: double-entry-bookkeeping.com (verified journal entry structure)
def record_loan_payment(db, loan_account_id: int, principal: Decimal,
                        interest: Decimal, payment_date, payment_ref: str):
    """Record a loan payment split into principal and interest.

    Journal entry:
        Dr. Loan Payable (liability)    +principal  (debit reduces liability)
        Dr. Non-Mortgage Interest Exp   +interest   (debit increases expense)
        Cr. Mercury Checking (asset)    -(principal + interest)

    Sum: principal + interest - (principal + interest) = 0 ✓
    """
    total_payment = principal + interest
    create_journal_entry(
        db=db,
        entry_date=payment_date,
        description=f"Loan payment: {payment_ref}",
        source_type="loan_payment",
        source_id=f"loan_payment:{payment_ref}",
        lines=[
            LineSpec(account_id=loan_account_id,                   amount=principal),
            LineSpec(account_id=accounts["Non-Mortgage Interest"].id, amount=interest),
            LineSpec(account_id=accounts["Mercury Checking"].id,   amount=-total_payment),
        ],
    )
```

### Cancellation Reversal

```python
# Source: Standard accounting reversal pattern
def reverse_journal_entry(db, original_entry_id: int, reversal_date, reason: str):
    """Create a reversal entry that exactly offsets an original entry.

    Per CONTEXT.md: both entries remain visible for audit trail.
    The reversal negates every line amount in the original entry.
    """
    original = db.query(JournalEntry).filter_by(id=original_entry_id).one()
    original_lines = db.query(JournalLine).filter_by(entry_id=original_entry_id).all()

    reversal_source_id = f"reversal:{original.source_id}"

    create_journal_entry(
        db=db,
        entry_date=reversal_date,
        description=f"Reversal of: {original.description} — {reason}",
        source_type="reversal",
        source_id=reversal_source_id,
        lines=[
            LineSpec(account_id=line.account_id, amount=-line.amount)   # negate each line
            for line in original_lines
        ],
    )
```

### PostgreSQL Upsert for Idempotent Journal Entry

```python
# Source: SQLAlchemy 2.0 docs — https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.journal_entry import JournalEntry

stmt = pg_insert(JournalEntry).values(
    entry_date=entry_date,
    description=description,
    source_type=source_type,
    source_id=source_id,
).on_conflict_do_nothing(index_elements=["source_id"])

result = db.execute(stmt)
if result.rowcount == 0:
    return None  # already exists — idempotent skip
```

### Numeric Precision (Correct Pattern)

```python
# Source: PostgreSQL docs — https://www.postgresql.org/docs/current/datatype-numeric.html
# SQLAlchemy Numeric maps to Python decimal.Decimal (asdecimal=True by default)
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

# In ORM model:
amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
# Numeric(12, 2) = up to 9,999,999,999.99 — sufficient for rental income

# In application code:
fee = (gross_amount * Decimal("0.155")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
# Never: fee = gross_amount * 0.155  (float — wrong)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Airbnb split-fee (3% host + 14-16% guest) | Host-only fee (15.5% from host payout) | Oct-Dec 2025 (phased) | Fee calculation logic and journal entry structure differ |
| Separate debit/credit columns | Single signed amount column | Standard pattern for this scale | Simpler balance check: `sum(amounts) == 0` |
| DB trigger for balance enforcement | Application-layer assertion | Current best practice for this architecture | Testable with pytest; no DB-level complexity |

**Deprecated/outdated:**
- PostgreSQL `money` type: Do not use. Locale-dependent behavior, limited arithmetic. Use `NUMERIC(12, 2)`.
- Python `float` for monetary calculations: Do not use. Use `decimal.Decimal`.

---

## Open Questions

### 1. Airbnb Fee Model for This Account (HIGH PRIORITY — blocks 03-02)

- **What we know:** The 15.5% host-only fee applies to PMS-connected hosts (since Oct 27, 2025) and to non-PMS hosts who were on simplified pricing (since Dec 1, 2025). Hosts NOT on simplified pricing may still be on the old 3% split-fee.
- **What's unclear:** Which model is active on this specific Airbnb account.
- **Recommendation:** Operator checks Airbnb host dashboard > Earnings > Payout Details for any recent booking to see whether the fee line shows "3% Host Fee" or "15.5% Host Fee". Make the fee rate and model configurable in `AppConfig` regardless of which model applies.

### 2. Discount Row Type in Airbnb CSV (MEDIUM PRIORITY — affects 03-02)

- **What we know:** Promotional discounts are a desired contra-revenue tracking feature per CONTEXT.md. Multiple research sources did not confirm a distinct discount row type in the Airbnb Transaction History CSV.
- **What's unclear:** Whether Airbnb emits a separate `Type: "Promotional discount"` row for discounted bookings, or whether the discount is silently baked into the nightly rate.
- **Recommendation:** Inspect an actual Airbnb Transaction History CSV that includes a booking with a promotional/early-bird discount. Look for any row with a discount-related `Type` value. If present, extract it in 03-02. If absent, document that discount tracking is not possible from CSV data and flag as a limitation.

### 3. Number of Loans (MEDIUM PRIORITY — affects 03-01 chart of accounts seed)

- **What we know:** "One or more loans exist" per CONTEXT.md. Two example names given: RV Purchase Loan, Working Capital Loan.
- **What's unclear:** Exact number of loan accounts to seed, their names, and whether they are property-specific or shared.
- **Recommendation:** Operator provides loan names and initial balances before 03-04 is implemented. Seed with two placeholder accounts and document that additional accounts can be added via admin API or direct SQL.

### 4. Booking `reconciliation_status` Column Migration

- **What we know:** The reconciliation engine needs to query for unmatched payouts. Both `bookings` and `bank_transactions` tables (created in Phase 2) need a `reconciliation_status` column.
- **What's unclear:** Whether to add this in Phase 2's existing migration (retroactive change) or in the Phase 3 migration (Alembic `op.add_column`).
- **Recommendation:** Add as a new `op.add_column` in the Phase 3 migration (`003_accounting_tables.py`). This preserves Phase 2 migration integrity. Default to `'unmatched'` for all existing rows using `server_default`.

### 5. Gross Amount Reconstruction for Host-Only Fee Model

- **What we know:** Under the host-only fee model, the Airbnb CSV shows only the net payout amount (after 15.5% deduction). Gross revenue = net_payout / (1 - 0.155).
- **What's unclear:** Whether this formula is correct for all fee scenarios (e.g., if a cleaning fee is in the subtotal, the math is slightly more complex).
- **Recommendation:** Confirm with the actual Airbnb Transaction History CSV for a completed booking under the current fee model: check whether a separate "Host Fee" row appears in the CSV (making gross reconstruction trivial) or whether only the net payout row appears (requiring formula-based reconstruction). The existing Phase 2 adapter already stores `raw_platform_data["rows"]` which will contain the answer.

---

## Sources

### Primary (HIGH confidence)

- https://docs.sqlalchemy.org/en/20/dialects/postgresql.html — `INSERT ... ON CONFLICT` syntax, `on_conflict_do_nothing()`, `on_conflict_do_update()`, `excluded` alias
- https://docs.sqlalchemy.org/en/20/core/constraints.html — `CheckConstraint` in ORM declarative style with `__table_args__`
- https://www.postgresql.org/docs/current/datatype-numeric.html — `NUMERIC` vs `FLOAT` for monetary storage; recommendation for exact decimal arithmetic
- https://www.double-entry-bookkeeping.com/other-long-term-debt/loan-repayment-principal-and-interest/ — Standard journal entry structure for loan P&I split
- Existing codebase: `app/models/booking.py`, `app/models/bank_transaction.py` — confirmed `Numeric(10, 2)` pattern already in use; `Mapped[]` annotation style confirmed
- Existing codebase: `app/ingestion/adapters/airbnb.py` — confirmed `raw_platform_data["rows"]` stores all CSV rows for a booking group; `Type` column exists in Airbnb CSV

### Secondary (MEDIUM confidence)

- https://www.rentalscaleup.com/airbnb-host-only-fee/ — Airbnb fee rollout timeline confirmed; PMS vs non-PMS distinction
- https://www.beyondpricing.com/blog/airbnb-service-fee-changes-2025 — Cross-reference for fee rollout phases; confirms December 1, 2025 for non-PMS hosts on simplified pricing
- https://www.balanced.software/double-entry-bookkeeping-for-programmers/ — Journal/entry/line table design confirmed as standard approach
- https://gist.github.com/NYKevin/9433376 — PostgreSQL double-entry schema with `NUMERIC(20,2)` on amounts; materialized balance view pattern
- https://www.accountingtools.com/articles/chart-of-accounts-numbering.html — Standard 1000/2000/3000/4000/5000 numbering ranges confirmed as de facto standard
- https://anvil.works/blog/double-entry-accounting-for-engineers — Application-layer balance enforcement vs DB trigger; two-table (entry + lines) design

### Tertiary (LOW confidence)

- WebSearch: Airbnb Transaction History CSV discount row types — no authoritative source found; discount availability in CSV is unresolved
- WebSearch: Airbnb individual host fee model post-December 2025 — partial clarity; official Airbnb page blocked by JavaScript rendering

---

## Metadata

**Confidence breakdown:**
- Standard stack (SQLAlchemy, Numeric, Decimal): HIGH — verified from official docs
- Double-entry schema design: HIGH — multiple authoritative sources agree on two-table pattern
- Balance enforcement pattern: HIGH — application layer is the correct approach; confirmed from multiple engineering references
- Chart of accounts numbering: HIGH — universally accepted convention
- Loan P&I journal entry: HIGH — verified from authoritative accounting source
- Airbnb fee model (15.5% applicable to this account): LOW — model confirmed as fee type but which applies to THIS account is unverified without operator confirmation
- Airbnb discount CSV availability: LOW — no authoritative source found; needs operator verification with real CSV
- Reconciliation algorithm: HIGH — exact match + date window is a standard technique; 7-day window is per CONTEXT.md decision

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (SQLAlchemy/PostgreSQL patterns stable for 30+ days; Airbnb fee model stable but policy-dependent)
