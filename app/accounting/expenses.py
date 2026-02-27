"""Expense recording and CSV bulk import.

Expenses are categorized using Schedule E-aligned categories. Each recorded expense
produces a balanced journal entry (debit expense/liability account, credit Mercury
Checking).

CSV bulk import format:

    expense_date,amount,category,description,attribution,vendor
    2026-01-15,125.50,supplies,"Paper towels and cleaning supplies",jay,Costco
    2026-01-20,89.00,utilities,"Internet bill January",shared,Spectrum

Required columns: expense_date, amount, category, description, attribution
Optional columns: vendor, property_id
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounting.journal import LineSpec, create_journal_entry
from app.models.account import Account
from app.models.expense import Expense

# Schedule E-aligned expense categories. Exactly 12 categories.
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

# Maps each category slug to its chart-of-accounts name.
# owner_reimbursable maps to a LIABILITY account (2200), not an expense account.
_CATEGORY_ACCOUNT_NAME: dict[str, str] = {
    "repairs_maintenance":    "Repairs & Maintenance",
    "supplies":               "Supplies",
    "utilities":              "Utilities",
    "non_mortgage_interest":  "Non-Mortgage Interest",
    "owner_reimbursable":     "Owner Reimbursable",
    "advertising":            "Advertising",
    "travel_transportation":  "Travel & Transportation",
    "professional_services":  "Professional Services",
    "legal":                  "Legal",
    "insurance":              "Insurance",
    "resort_lot_rental":      "Resort Lot Rental Fees",
    "cleaning_service":       "Cleaning Service Fees",
}

_VALID_ATTRIBUTIONS = frozenset({"jay", "minnie", "shared"})

_MERCURY_CHECKING_NAME = "Mercury Checking"


def _get_account_id(db: Session, name: str) -> int:
    """Fetch an account id by name, raising ValueError if not found."""
    row = db.execute(select(Account.id).where(Account.name == name)).one_or_none()
    if row is None:
        raise ValueError(f"Account not found in chart of accounts: {name!r}")
    return row[0]


def record_expense(
    db: Session,
    expense_date: date,
    amount: Decimal,
    category: str,
    description: str,
    attribution: str,
    property_id: int | None = None,
    vendor: str | None = None,
) -> Expense:
    """Record a single expense and create its corresponding journal entry.

    Creates both an Expense row and a balanced JournalEntry (debit expense/liability
    account, credit Mercury Checking).

    Args:
        db: SQLAlchemy session. Caller is responsible for commit.
        expense_date: Date the expense was incurred.
        amount: Positive Decimal amount in USD.
        category: One of EXPENSE_CATEGORIES.
        description: Human-readable description.
        attribution: One of 'jay', 'minnie', 'shared'.
        property_id: Optional FK to properties.id; None for shared expenses.
        vendor: Optional vendor or payee name.

    Returns:
        The created Expense record.

    Raises:
        ValueError: If category, attribution, or amount is invalid.
    """
    if category not in EXPENSE_CATEGORIES:
        raise ValueError(
            f"Invalid category {category!r}. Must be one of: {EXPENSE_CATEGORIES}"
        )
    if attribution not in _VALID_ATTRIBUTIONS:
        raise ValueError(
            f"Invalid attribution {attribution!r}. Must be one of: {sorted(_VALID_ATTRIBUTIONS)}"
        )
    if amount <= Decimal("0"):
        raise ValueError(f"Expense amount must be positive, got {amount}.")

    # Resolve account IDs from chart of accounts
    debit_account_name = _CATEGORY_ACCOUNT_NAME[category]
    debit_account_id = _get_account_id(db, debit_account_name)
    cash_account_id = _get_account_id(db, _MERCURY_CHECKING_NAME)

    # Build a unique source_id (uuid ensures uniqueness for multiple expenses on same date)
    source_id = f"expense:{expense_date.isoformat()}:{uuid4()}"

    # Create the balanced journal entry
    # Debit: expense or liability account (+amount increases it)
    # Credit: Mercury Checking (-amount decreases cash)
    journal_entry = create_journal_entry(
        db=db,
        entry_date=expense_date,
        description=description,
        source_type="expense",
        source_id=source_id,
        lines=[
            LineSpec(account_id=debit_account_id, amount=amount, description=description),
            LineSpec(account_id=cash_account_id, amount=-amount, description=description),
        ],
        property_id=property_id,
    )

    # journal_entry should never be None here (source_id is fresh uuid-based)
    journal_entry_id = journal_entry.id if journal_entry is not None else None

    expense = Expense(
        expense_date=expense_date,
        property_id=property_id,
        attribution=attribution,
        category=category,
        amount=amount,
        description=description,
        vendor=vendor,
        journal_entry_id=journal_entry_id,
    )
    db.add(expense)
    db.flush()
    return expense


def bulk_import_expenses(db: Session, rows: list[dict]) -> dict:
    """Import multiple expenses from a list of row dicts.

    Each row dict should have the following keys:
        expense_date (str, YYYY-MM-DD): Date of the expense.
        amount (str or float): Amount in USD. Converted to Decimal.
        category (str): One of EXPENSE_CATEGORIES.
        description (str): Human-readable description.
        attribution (str): One of 'jay', 'minnie', 'shared'.
        property_id (int | None, optional): FK to properties.id.
        vendor (str | None, optional): Vendor or payee name.

    Processes all rows regardless of individual errors. Errors are collected
    and returned without aborting the import.

    Args:
        db: SQLAlchemy session. Caller is responsible for commit.
        rows: List of row dicts (e.g. parsed from CSV).

    Returns:
        A dict with keys:
            "imported" (int): Count of successfully recorded expenses.
            "errors" (list[dict]): Each entry has "row" (1-based) and "error" (str).
    """
    imported = 0
    errors: list[dict] = []

    for i, row in enumerate(rows, start=1):
        try:
            # Parse expense_date
            raw_date = row.get("expense_date", "")
            if not raw_date:
                raise ValueError("expense_date is required")
            parsed_date = date.fromisoformat(str(raw_date).strip())

            # Parse amount as Decimal (never float)
            raw_amount = row.get("amount", "")
            if raw_amount == "" or raw_amount is None:
                raise ValueError("amount is required")
            try:
                parsed_amount = Decimal(str(raw_amount).strip())
            except InvalidOperation:
                raise ValueError(f"Invalid amount value: {raw_amount!r}")

            category = str(row.get("category", "")).strip()
            description = str(row.get("description", "")).strip()
            attribution = str(row.get("attribution", "")).strip()

            # Optional fields
            raw_property_id = row.get("property_id")
            property_id: int | None = int(raw_property_id) if raw_property_id else None
            vendor: str | None = row.get("vendor") or None

            record_expense(
                db=db,
                expense_date=parsed_date,
                amount=parsed_amount,
                category=category,
                description=description,
                attribution=attribution,
                property_id=property_id,
                vendor=vendor,
            )
            imported += 1

        except Exception as exc:
            errors.append({"row": i, "error": str(exc)})

    return {"imported": imported, "errors": errors}
