# Phase 4: Financial Reports - Research

**Researched:** 2026-02-27
**Domain:** Financial report generation from double-entry ledger, bank transaction categorization, FastAPI, SQLAlchemy 2.0, Polars 1.38
**Confidence:** HIGH (SQLAlchemy query patterns, sign conventions, schema gaps), MEDIUM (shared expense allocation approach, JSON response shapes)

---

## Summary

Phase 4 generates financial reports (P&L, balance sheet, income statement) by querying the double-entry ledger built in Phase 3. No new framework dependencies are required — the existing stack (FastAPI 0.133, SQLAlchemy 2.0.47, PostgreSQL, Polars 1.38) handles everything. The primary work is writing correct aggregate queries against `journal_lines`/`journal_entries`/`expenses` tables and assembling structured JSON responses.

The most important technical finding is that **three schema gaps in Phase 3 must be addressed by a Phase 4 migration**: (1) `bank_transactions` lacks `category` and `journal_entry_id` columns needed for categorization; (2) the `Loan` model lacks a `property_id` column required to attribute property-specific loan interest in per-property P&L; and (3) loan liability balances cannot be derived from `journal_lines` alone (no origination journal entry was created in Phase 3) and must use `loans.original_balance` combined with payment sums.

The report generation pattern is: SQLAlchemy queries with `GROUP BY` for aggregation, Python dicts for result assembly, and Pydantic response models for serialization. Polars is NOT needed for the report aggregation layer — SQL `GROUP BY` is fully sufficient for the data volumes involved. Polars remains used in the ingestion layer (CSV parsing) but adding it to reports would be unnecessary complexity.

**Primary recommendation:** Write report generators as pure functions in `app/accounting/reports.py` that accept a `Session` and parameters, return plain Python dicts/dataclasses, and are exposed through a new `app/api/reports.py` FastAPI router. Bank transaction categorization endpoints extend `app/api/accounting.py` (keeping categorization alongside existing accounting endpoints).

---

## Standard Stack

No new libraries are needed. Everything is already in `pyproject.toml`.

### Core (Already Installed)
| Library | Version | Purpose | Role in Phase 4 |
|---------|---------|---------|-----------------|
| FastAPI | 0.133.1 | HTTP framework | New report router, PATCH endpoints |
| SQLAlchemy | 2.0.47 | ORM + query builder | Aggregate queries for reports |
| Pydantic | (via FastAPI) | Schema validation | Request/response models |
| PostgreSQL | (via psycopg3) | Database | Stores journal entries, expenses |
| Polars | 1.38.1 | Data processing | Not needed for reports; already used in ingestion |

### No New Dependencies Required
Phase 4 adds no new packages. All aggregation is done in SQL/Python.

**Installation:** No `uv add` commands needed.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── accounting/
│   ├── reports.py          # NEW: P&L, balance sheet, income statement generators
│   ├── journal.py          # EXISTING (Phase 3)
│   ├── revenue.py          # EXISTING (Phase 3)
│   ├── expenses.py         # EXISTING (Phase 3) — reused for bank tx categorization
│   ├── loans.py            # EXISTING (Phase 3)
│   └── reconciliation.py   # EXISTING (Phase 3)
├── api/
│   ├── accounting.py       # EXTENDED: add bank transaction categorization endpoints
│   ├── reports.py          # NEW: report endpoints (P&L, balance sheet, income statement)
│   ├── health.py           # EXISTING
│   └── ingestion.py        # EXISTING
├── models/
│   ├── bank_transaction.py # EXTENDED: add category, journal_entry_id columns
│   └── loan.py             # EXTENDED: add property_id column
└── main.py                 # EXTENDED: include reports router
alembic/versions/
└── 004_financial_reports.py  # NEW migration
```

### Pattern 1: Report Generator Functions

Each report is a pure function in `app/accounting/reports.py`. Functions accept a `Session` and parameters, execute SQLAlchemy queries, and return plain Python dicts. The API layer calls them and wraps results in Pydantic response models.

```python
# Source: project patterns from app/accounting/expenses.py, loans.py
def generate_pl(
    db: Session,
    start_date: date,
    end_date: date,
    property_id: int | None = None,   # None = combined (all properties)
    breakdown: str = "combined",       # "combined" or "property"
) -> dict:
    """Return P&L report as plain dict."""
    ...
```

### Pattern 2: Period Resolution Helper

All report endpoints accept shorthand period params that resolve to `start_date`/`end_date`. A single helper handles all period types:

```python
from datetime import date

def resolve_period(
    start_date: date | None,
    end_date: date | None,
    month: str | None,       # "YYYY-MM"
    quarter: str | None,     # "Q1" | "Q2" | "Q3" | "Q4"
    year: int | None,        # calendar year
    ytd: bool = False,
) -> tuple[date, date]:
    """Resolve period parameters to (start_date, end_date).

    Priority: raw start/end > month > quarter+year > year > ytd
    Raises HTTPException 422 if no valid period can be determined.
    """
    if start_date and end_date:
        return start_date, end_date
    if month:
        # "2026-01" -> Jan 1 to Jan 31
        ...
    if quarter and year:
        # Q1 -> Jan 1 to Mar 31
        quarter_starts = {1: (1,1), 2: (4,1), 3: (7,1), 4: (10,1)}
        quarter_ends   = {1: (3,31), 2: (6,30), 3: (9,30), 4: (12,31)}
        ...
    if year:
        return date(year, 1, 1), date(year, 12, 31)
    if ytd:
        today = date.today()
        return date(today.year, 1, 1), today
    raise HTTPException(422, "Provide at least one period parameter")
```

### Pattern 3: SQLAlchemy Aggregate Queries for Reports

Use `select()` with `func.sum()` and `group_by()`, not full ORM object loading. This is the correct pattern for aggregate report queries:

```python
# Source: SQLAlchemy 2.0 docs — aggregate queries
from sqlalchemy import func, select, case

# P&L revenue query: journal lines for Rental Income account
stmt = (
    select(
        JournalEntry.property_id,
        JournalEntry.source_id,
        JournalEntry.entry_date,
        func.sum(JournalLine.amount).label("total_amount"),
    )
    .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
    .join(Account, Account.id == JournalLine.account_id)
    .where(
        Account.name == "Rental Income",
        JournalEntry.source_type == "booking_payout",
        JournalEntry.entry_date >= start_date,
        JournalEntry.entry_date <= end_date,
    )
    .group_by(
        JournalEntry.property_id,
        JournalEntry.source_id,
        JournalEntry.entry_date,
    )
)
rows = db.execute(stmt).all()
```

### Pattern 4: Sign Convention for Report Presentation

The journal stores amounts as signed values (positive = debit, negative = credit). Financial report presentation requires sign flipping for display:

| Account Type | Journal Convention | Display Convention |
|---|---|---|
| Asset | Positive = debit (cash in) | Show as-is (positive = we have it) |
| Liability | Negative = credit (we owe) | Negate for display (show positive = owed) |
| Revenue | Negative = credit (income) | Negate for display (show positive = earned) |
| Expense | Positive = debit (cost) | Show as-is (positive = we spent it) |

**Exception: Loan accounts.** Loan origination journal entries were NEVER created in Phase 3 — only payment entries exist. Loan display balance cannot be derived from journal lines alone. Use:
```python
loan_balance = loan.original_balance - sum_of_principal_payments_in_journal_lines
```
This is exactly what `get_loan_balance()` in `app/accounting/loans.py` already computes. The balance sheet generator MUST use this function (or equivalent query) for loan accounts.

### Pattern 5: Shared Expense Allocation

Shared expenses (`property_id IS NULL`) split evenly across ALL active properties. Active property count is queried dynamically from the `properties` table — never hardcoded:

```python
from app.models.property import Property

active_properties = db.query(Property).all()
num_properties = len(active_properties)
property_ids = [p.id for p in active_properties]

# Each property gets: shared_expense_amount / num_properties
allocated_share = expense.amount / num_properties
```

### Pattern 6: Platform Extraction from source_id

Booking payout journal entries encode the platform in their `source_id`. Extract without joining to bookings:

```python
# source_id format: "booking_payout:{platform}:{platform_booking_id}"
# e.g., "booking_payout:airbnb:HM123ABC"
# Python extraction:
platform = source_id.split(":")[1]   # "airbnb", "vrbo", or "rvshare"
```

This is confirmed by the source_id patterns in `app/accounting/revenue.py`:
- `f"booking_payout:airbnb:{booking.platform_booking_id}"`
- `f"booking_payout:vrbo:{booking.platform_booking_id}"`
- `f"booking_payout:rvshare:{booking.platform_booking_id}"`

### Pattern 7: Bank Transaction Categorization

When a bank transaction is categorized as an expense category (one of the 12 Schedule E categories), call `record_expense()` to create both an `Expense` record and its journal entry. This keeps all expenses in one table for consistent P&L queries:

```python
# PATCH /api/accounting/bank-transactions/{id}/category
from app.accounting.expenses import record_expense, EXPENSE_CATEGORIES

NON_EXPENSE_CATEGORIES = frozenset({
    "owner_deposit", "loan_payment", "transfer", "revenue", "personal"
})

def categorize_bank_transaction(db, txn, category, property_id, attribution):
    txn.category = category
    if category in EXPENSE_CATEGORIES:
        expense = record_expense(
            db=db,
            expense_date=txn.date,
            amount=abs(txn.amount),   # bank amounts may be negative (debits)
            category=category,
            description=txn.description or f"Bank transaction {txn.transaction_id}",
            attribution=attribution,
            property_id=property_id,
        )
        txn.journal_entry_id = expense.journal_entry_id
    # Non-expense categories: just set category, no journal entry
    db.flush()
```

### Anti-Patterns to Avoid

- **Querying bookings.net_amount for P&L revenue:** Use journal_lines instead. bookings.net_amount misses gross reconstruction (Airbnb fees already deducted) and includes unrecognized bookings.
- **Hardcoding property count:** Always query the properties table for active property count. Never write `/ 2` for shared expense splits.
- **Using float for amounts in Pydantic response fields:** Use `float` with `round(x, 2)` at output conversion, or define response fields as `Decimal` (serialized as strings). **Do not pass raw float64 Polars sums directly into Pydantic models** without rounding.
- **Deriving loan balances from journal lines alone:** Phase 3 never created loan origination entries. Always use `get_loan_balance(db, loan)` or the equivalent inline calculation for balance sheet loan figures.
- **Adding Polars for report aggregation:** SQL GROUP BY handles all aggregation needed. Polars in this layer adds complexity for no benefit at these data volumes.

---

## Required Schema Changes (Migration 004)

Phase 4 requires a new Alembic migration with three additions:

### 1. `bank_transactions` new columns
```sql
ALTER TABLE bank_transactions
  ADD COLUMN category VARCHAR(64) NULL,
  ADD COLUMN journal_entry_id INTEGER REFERENCES journal_entries(id) NULL;
```
The `category` column stores the assigned category slug (e.g., `"utilities"`, `"owner_deposit"`).
The `journal_entry_id` column links to the expense journal entry created during categorization (NULL for non-expense categories).

### 2. `loans` new column
```sql
ALTER TABLE loans
  ADD COLUMN property_id INTEGER REFERENCES properties.id NULL;
```
`NULL` = shared loan (Working Capital Loan Payable); set to property ID for property-specific loans (RV Purchase Loan Payable). The P&L generator uses this to attribute loan interest expense to the correct property.

### ORM Model Updates
- `BankTransaction`: add `category: Mapped[str | None]` and `journal_entry_id: Mapped[int | None]`
- `Loan`: add `property_id: Mapped[int | None]`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Loan balance calculation | Custom running total from journal lines | `get_loan_balance(db, loan)` from `loans.py` | Phase 3 already handles; no origination entry in ledger |
| Expense + journal entry creation for categorized transactions | Direct journal entry construction | `record_expense()` from `expenses.py` | Validates category, creates both Expense record and JournalEntry atomically |
| Period date resolution | Multiple if/else blocks per endpoint | Single `resolve_period()` helper | Shared across all 3 report endpoints; prevents inconsistency |
| Multi-property aggregation | Hardcoded property list | Query `properties` table | Must scale beyond 2 properties per requirements |
| Sign flipping | Per-field manual negation | Single sign convention documented and applied centrally | Consistent across all reports |

---

## Common Pitfalls

### Pitfall 1: Loan Balance on Balance Sheet
**What goes wrong:** Developer queries `SUM(journal_lines.amount)` for loan accounts (2100, 2110) and gets the total principal paid, not the current outstanding balance.
**Why it happens:** Phase 3 never created loan origination journal entries. Only payment entries (debit to loan account) exist. SUM of debit lines = principal paid, not current balance.
**How to avoid:** For each loan account, compute: `original_balance - SUM(positive_lines_to_loan_account)`. Use `get_loan_balance()` from `loans.py` or join to `loans` table and compute inline.
**Warning signs:** Balance sheet shows decreasing liability that starts at zero instead of at `original_balance`.

### Pitfall 2: Revenue Sign Inversion
**What goes wrong:** Revenue lines in journal appear as negative (credits), so summing them gives a negative total revenue figure.
**Why it happens:** Double-entry convention: income credits decrease the account balance. In this codebase, credit = negative amount stored in `journal_lines.amount`.
**How to avoid:** Always negate revenue account sums for display: `revenue_display = -sum(line.amount for line in revenue_lines)`.
**Warning signs:** P&L shows negative revenue, or net income = expenses + |revenue| instead of revenue - expenses.

### Pitfall 3: Shared Expense Over-counting
**What goes wrong:** When generating combined P&L (all properties together), shared expenses get counted once. When generating per-property P&L, if you simply sum shared expenses per property they get double-counted on the combined total.
**Why it happens:** The per-property P&L allocates 1/N of shared expenses to each property. Summing per-property results gives correct combined total ONLY if allocation was done before summing (not after).
**How to avoid:** For combined P&L, sum shared expenses once (not allocated). For per-property P&L, allocate first then sum. These are separate code paths.
**Warning signs:** Combined P&L expenses don't equal sum of per-property expenses.

### Pitfall 4: Platform Fees in Wrong Section
**What goes wrong:** Platform fees (account 5010, `source_type="booking_payout"`) appear in the revenue section because their journal entries have `source_type="booking_payout"`.
**Why it happens:** Booking payout entries have multiple lines: one for Rental Income (revenue) and one for Platform Fees (expense). Both lines share the same entry's `source_type`.
**How to avoid:** Filter by `account.account_type = 'revenue'` AND `account.name = 'Rental Income'` for revenue section. Filter by `account.account_type = 'expense'` for expense section. Never rely solely on `source_type` to determine revenue vs expense.

### Pitfall 5: Loan Interest Attribution in Per-Property P&L
**What goes wrong:** All loan interest (Non-Mortgage Interest account) appears with `journal_entry.property_id = NULL` because `record_loan_payment()` hardcodes `property_id=None`.
**Why it happens:** Phase 3 loans.py design: loan payments always post with `property_id=None`.
**How to avoid:** In Phase 4, add `property_id` to the `Loan` model/table. When generating per-property P&L, query loan payment journal entries via `source_id` pattern `"loan_payment:{loan_id}:*"`, look up the loan's `property_id`, and attribute interest expense accordingly.
**Warning signs:** Per-property P&L shows zero loan interest for all properties; it's all in the "shared" bucket.

### Pitfall 6: Bank Transaction Amount Sign
**What goes wrong:** Bank transactions have negative amounts for debits (money out). Calling `record_expense(amount=txn.amount)` with a negative value raises a `ValueError` (amount must be positive).
**Why it happens:** Bank CSV convention: positive = deposit, negative = debit.
**How to avoid:** Always use `abs(txn.amount)` when creating expenses from bank transactions. Validate that the transaction IS a debit (negative) before categorizing as an expense.

---

## Code Examples

### Balance Sheet Query (Verified against schema)
```python
# Source: app/accounting/loans.py (get_loan_balance pattern) + app/api/accounting.py (balances endpoint)
from sqlalchemy import func, select
from app.models.account import Account
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.models.loan import Loan

def _query_account_balances_as_of(db: Session, as_of: date) -> list[Row]:
    """Sum journal lines per account up to as_of date."""
    return db.execute(
        select(
            Account.number,
            Account.name,
            Account.account_type,
            func.coalesce(func.sum(JournalLine.amount), Decimal("0")).label("raw_balance"),
        )
        .outerjoin(JournalLine, JournalLine.account_id == Account.id)
        .outerjoin(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            Account.is_active == True,
            Account.account_type.in_(["asset", "liability", "equity"]),
            # Include lines with no entry (outerjoin produces NULL) or entry_date <= as_of
            (JournalEntry.entry_date == None) | (JournalEntry.entry_date <= as_of),
        )
        .group_by(Account.id, Account.number, Account.name, Account.account_type)
        .order_by(Account.number)
    ).all()

def _get_loan_balances(db: Session, as_of: date) -> dict[int, Decimal]:
    """Return {account_id: current_balance} for all loan accounts."""
    loans = db.query(Loan).all()
    result = {}
    for loan in loans:
        # Principal paid up to as_of
        principal_paid = db.execute(
            select(func.coalesce(func.sum(JournalLine.amount), Decimal("0")))
            .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
            .where(
                JournalLine.account_id == loan.account_id,
                JournalEntry.entry_date <= as_of,
            )
        ).scalar_one()
        result[loan.account_id] = loan.original_balance - principal_paid
    return result
```

### P&L Revenue Query
```python
# Source: Derived from app/accounting/revenue.py source_id patterns
from sqlalchemy import func, select

def _query_revenue_lines(db: Session, start_date: date, end_date: date) -> list[Row]:
    """Revenue lines from Rental Income account for recognized bookings."""
    return db.execute(
        select(
            JournalEntry.property_id,
            JournalEntry.source_id,     # platform extracted with split(":")[1]
            JournalEntry.entry_date,
            func.sum(JournalLine.amount).label("total"),
        )
        .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(
            Account.name == "Rental Income",
            JournalEntry.source_type == "booking_payout",
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
        .group_by(
            JournalEntry.property_id,
            JournalEntry.source_id,
            JournalEntry.entry_date,
        )
    ).all()
    # Note: total is negative (credit). Display as -total.
```

### P&L Expense Query
```python
# Source: Derived from app/models/expense.py schema
from sqlalchemy import select

def _query_expenses(db: Session, start_date: date, end_date: date) -> list[Row]:
    """All expenses in the period from expenses table."""
    return db.execute(
        select(
            Expense.property_id,
            Expense.category,
            Expense.attribution,
            Expense.amount,
        )
        .where(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
        )
    ).all()
    # Caller allocates shared (property_id=None) expenses evenly across properties
```

### Period Resolution
```python
# Source: Python stdlib datetime
from datetime import date
from fastapi import HTTPException

def resolve_period(
    start_date: date | None = None,
    end_date: date | None = None,
    month: str | None = None,
    quarter: str | None = None,
    year: int | None = None,
    ytd: bool = False,
) -> tuple[date, date]:
    if start_date and end_date:
        return start_date, end_date
    if month:
        # "YYYY-MM"
        y, m = int(month[:4]), int(month[5:7])
        import calendar
        last_day = calendar.monthrange(y, m)[1]
        return date(y, m, 1), date(y, m, last_day)
    if quarter and year:
        q = int(quarter[1])  # "Q1" -> 1
        starts = {1: (1,1), 2: (4,1), 3: (7,1), 4: (10,1)}
        ends   = {1: (3,31), 2: (6,30), 3: (9,30), 4: (12,31)}
        return date(year, *starts[q]), date(year, *ends[q])
    if year:
        return date(year, 1, 1), date(year, 12, 31)
    if ytd:
        today = date.today()
        return date(today.year, 1, 1), today
    raise HTTPException(status_code=422, detail="Provide at least one period parameter")
```

### Bank Transaction Categorization Endpoint Pattern
```python
# Source: Derived from app/accounting/expenses.py (record_expense pattern)
# and app/api/accounting.py (endpoint structure)

NON_EXPENSE_CATEGORIES = frozenset({
    "owner_deposit", "loan_payment", "transfer", "personal"
})
ALL_CATEGORIES = set(EXPENSE_CATEGORIES) | NON_EXPENSE_CATEGORIES

class CategoryRequest(BaseModel):
    category: str
    property_id: int | None = None    # required if expense & property-specific
    attribution: str = "shared"        # "jay", "minnie", "shared"

@router.patch("/bank-transactions/{txn_id}/category")
def categorize_transaction(
    txn_id: int,
    body: CategoryRequest,
    db: Session = Depends(get_db),
) -> BankTransactionResponse:
    txn = db.get(BankTransaction, txn_id)
    if txn is None:
        raise HTTPException(404, f"Bank transaction {txn_id} not found")
    if body.category not in ALL_CATEGORIES:
        raise HTTPException(422, f"Invalid category: {body.category!r}")

    txn.category = body.category

    if body.category in EXPENSE_CATEGORIES:
        expense = record_expense(
            db=db,
            expense_date=txn.date,
            amount=abs(txn.amount),
            category=body.category,
            description=txn.description or f"Bank transaction {txn.transaction_id}",
            attribution=body.attribution,
            property_id=body.property_id,
        )
        txn.journal_entry_id = expense.journal_entry_id

    db.commit()
    return _build_bank_transaction_response(txn)
```

---

## Recommended JSON Response Shapes

These are in the "Claude's Discretion" area. Recommendations are designed for dashboard consumption (Phase 7).

### P&L Response
```json
{
  "property": "Jay",
  "property_id": 1,
  "period": {"start": "2026-01-01", "end": "2026-12-31", "label": "2026"},
  "revenue": {
    "airbnb": {"total": 12500.00, "months": [{"month": "2026-01", "amount": 1000.00}]},
    "vrbo":   {"total": 5000.00, "months": [{"month": "2026-01", "amount": 500.00}]},
    "rvshare": {"total": 0.00, "months": []},
    "total": 17500.00
  },
  "expenses": {
    "repairs_maintenance": 500.00,
    "supplies": 200.00,
    "utilities": 150.00,
    "platform_fees": 800.00,
    "total": 1650.00
  },
  "net_income": 15850.00
}
```
For `?breakdown=property`: returns list of per-property objects plus a "combined" object.

### Balance Sheet Response
```json
{
  "as_of": "2026-12-31",
  "assets": {
    "mercury_checking": 25000.00,
    "accounts_receivable": 1500.00,
    "total": 26500.00
  },
  "liabilities": {
    "unearned_revenue": 0.00,
    "rv_purchase_loan_payable": 45000.00,
    "working_capital_loan_payable": 10000.00,
    "owner_reimbursable": 500.00,
    "total": 55500.00
  },
  "equity": {
    "owner_equity": 3000.00,
    "retained_earnings": -32000.00,
    "total": -29000.00
  },
  "total_liabilities_and_equity": 26500.00,
  "balanced": true
}
```
`balanced = (total assets == total liabilities + equity)`. Include as sanity-check field.

### Income Statement Response
```json
{
  "period": {"start": "2026-01-01", "end": "2026-12-31", "label": "2026"},
  "revenue": {
    "rental_income": 22500.00,
    "promotional_discounts": -300.00,
    "total": 22200.00
  },
  "expenses": {
    "platform_fees": 1200.00,
    "repairs_maintenance": 800.00,
    "supplies": 300.00,
    "utilities": 1200.00,
    "non_mortgage_interest": 2400.00,
    "advertising": 100.00,
    "travel_transportation": 50.00,
    "professional_services": 500.00,
    "legal": 0.00,
    "insurance": 600.00,
    "resort_lot_rental": 3600.00,
    "cleaning_service": 1200.00,
    "total": 11950.00
  },
  "net_income": 10250.00
}
```
With `?breakdown=monthly`: wrap in `{"months": [...], "totals": {...}}`.

### Bank Transaction List Response
```json
{
  "items": [
    {
      "id": 1,
      "transaction_id": "abc123",
      "date": "2026-01-15",
      "description": "Cleaning supplies",
      "amount": -85.50,
      "category": null,
      "journal_entry_id": null,
      "reconciliation_status": "unmatched"
    }
  ],
  "total": 150,
  "uncategorized_count": 42
}
```

---

## Endpoint Structure

```
GET  /api/reports/pl
     ?start_date&end_date&month&quarter&year&ytd
     ?breakdown=combined|property
     → PL report for all properties or single

GET  /api/reports/balance-sheet
     ?as_of=YYYY-MM-DD  (required)
     → Combined balance sheet only (no per-property)

GET  /api/reports/income-statement
     ?start_date&end_date&month&quarter&year&ytd
     ?breakdown=totals|monthly
     → Combined income statement

GET  /api/accounting/bank-transactions
     ?categorized=true|false|all  (default all)
     ?start_date&end_date
     ?limit&offset
     → List bank transactions with category

PATCH /api/accounting/bank-transactions/{id}/category
     Body: {category, property_id?, attribution?}
     → Categorize single transaction, auto-create expense entry if applicable

PATCH /api/accounting/bank-transactions/categorize
     Body: [{id, category, property_id?, attribution?}, ...]
     → Bulk categorize, same auto-create logic
```

**Router registration in `main.py`:**
```python
from app.api.reports import router as reports_router
app.include_router(reports_router)
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|---|---|---|
| Query `bookings.net_amount` for revenue | Query `journal_lines` for Rental Income credits | Reports only show RECOGNIZED revenue (correct) |
| Polars for all data processing | SQLAlchemy GROUP BY for report aggregation | No unnecessary memory loading; SQL is the right tool |
| Hardcode 50/50 property split | Dynamic property count from DB | Scales beyond 2 properties |

---

## Open Questions

1. **Retained Earnings in Balance Sheet**
   - What we know: retained earnings = cumulative net income (revenue - expenses) up to as_of date
   - What's unclear: Should it be labeled "Retained Earnings" or "Current Period Net Income" (they mean the same thing for a cash-basis operation, but traditional balance sheets distinguish between prior retained earnings and current year net income)?
   - Recommendation: Label as "Retained Earnings" and compute as `-SUM(revenue_lines) - SUM(expense_lines)` up to as_of. Simplest and correct for this use case.

2. **Loan Interest Attribution Method**
   - What we know: `journal_entry.property_id = NULL` for all loan payments (Phase 3 hardcoded)
   - What's unclear: Should Phase 4 (a) add `property_id` to the `Loan` model and use it during P&L generation, or (b) instead update `record_loan_payment()` to use `loan.property_id` for future entries (leaving historical entries as NULL)?
   - Recommendation: Option (a) — add `property_id` to `Loan` model via migration, use it only in the report generator for interest attribution. Do NOT change how journal entries are created (avoids disrupting Phase 3 logic and historical entries).

3. **Non-Expense Bank Transaction Categories**
   - What we know: Categories like `owner_deposit`, `loan_payment`, `transfer` should NOT create expense journal entries
   - What's unclear: What exactly is the complete list of non-expense categories? CONTEXT mentions "owner deposit, loan payment, transfer, etc."
   - Recommendation: Define `NON_EXPENSE_CATEGORIES = {"owner_deposit", "loan_payment", "transfer", "personal"}`. Keep this enum-adjacent (string constants) rather than a DB table — the list is small and unlikely to change.

---

## Sources

### Primary (HIGH confidence)
- `/Users/tunderhill/development/airbnb-tools/app/accounting/expenses.py` — EXPENSE_CATEGORIES list, record_expense() pattern
- `/Users/tunderhill/development/airbnb-tools/app/accounting/loans.py` — get_loan_balance() confirming no origination entries
- `/Users/tunderhill/development/airbnb-tools/app/accounting/revenue.py` — source_id patterns for platform extraction
- `/Users/tunderhill/development/airbnb-tools/alembic/versions/003_accounting_tables.py` — CHART_OF_ACCOUNTS confirming all account names/numbers
- `/Users/tunderhill/development/airbnb-tools/app/models/bank_transaction.py` — confirmed missing category/journal_entry_id
- `/Users/tunderhill/development/airbnb-tools/app/models/loan.py` — confirmed missing property_id
- Live Python tests of Polars 1.38.1, SQLAlchemy 2.0.47, FastAPI 0.133.1

### Secondary (MEDIUM confidence)
- Double-entry accounting sign conventions (standard accounting domain knowledge, verified against existing code patterns in Phase 3)
- JSON response shapes (designed by research, not verified against existing dashboard spec — Phase 7 is not yet built)

---

## Metadata

**Confidence breakdown:**
- Schema gaps identified: HIGH — verified against actual model files
- Query patterns: HIGH — verified against existing Phase 3 query patterns and live test runs
- Sign conventions: HIGH — verified against Phase 3 revenue.py (credits as negatives confirmed)
- Loan balance sheet special case: HIGH — verified by reading loans.py (no origination entry)
- JSON response shapes: MEDIUM — designed for Phase 7 dashboard; shapes are recommendations, not locked
- Non-expense category list: MEDIUM — extrapolated from CONTEXT description

**Research date:** 2026-02-27
**Valid until:** 2026-03-30 (stable domain — library versions won't change; schema verified against live code)
