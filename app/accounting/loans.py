"""Loan payment recording with principal/interest split as double-entry journal entries.

The caller (operator or API) provides the principal/interest split from the lender's
amortization schedule. This module does NOT compute amortization.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounting.journal import LineSpec, create_journal_entry
from app.models.account import Account
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.models.loan import Loan

# Module-level account cache: name -> Account.id
# Populated lazily on first use and reused for all subsequent calls.
_account_cache: dict[str, int] = {}

_NON_MORTGAGE_INTEREST = "Non-Mortgage Interest"
_MERCURY_CHECKING = "Mercury Checking"


def _get_account_id(db: Session, name: str) -> int:
    """Look up an account id by name, using a module-level cache."""
    if name not in _account_cache:
        account = db.query(Account).filter_by(name=name).one()
        _account_cache[name] = account.id
    return _account_cache[name]


def record_loan_payment(
    db: Session,
    loan: Loan,
    principal: Decimal,
    interest: Decimal,
    payment_date: date,
    payment_ref: str,
) -> JournalEntry | None:
    """Record a loan payment as a balanced 3-line journal entry.

    The caller supplies the principal/interest split from their lender's amortization
    schedule. This function does NOT compute amortization.

    Journal entry:
        Dr. Loan Liability Account  +principal   (debit reduces the liability)
        Dr. Non-Mortgage Interest   +interest    (debit increases the expense)
        Cr. Mercury Checking        -total        (credit reduces the asset)

    Args:
        db: SQLAlchemy session (caller is responsible for commit).
        loan: Loan ORM instance being paid.
        principal: Principal portion of the payment (>= 0).
        interest: Interest portion of the payment (>= 0).
        payment_date: Calendar date the payment was made.
        payment_ref: Caller-provided reference string, unique per payment per loan
            (e.g., "2026-01" for a January payment). Combined with loan.id in the
            source_id to guarantee idempotency.

    Returns:
        The created JournalEntry, or None if this payment was already recorded
        (idempotent skip via source_id ON CONFLICT DO NOTHING).

    Raises:
        ValueError: If principal or interest is negative, or both are zero.
    """
    if principal < Decimal("0"):
        raise ValueError(f"principal must be >= 0, got {principal}")
    if interest < Decimal("0"):
        raise ValueError(f"interest must be >= 0, got {interest}")
    if (principal + interest) <= Decimal("0"):
        raise ValueError(
            f"principal + interest must be > 0, got {principal + interest}"
        )

    total_payment = principal + interest

    interest_account_id = _get_account_id(db, _NON_MORTGAGE_INTEREST)
    cash_account_id = _get_account_id(db, _MERCURY_CHECKING)

    lines = [
        LineSpec(
            account_id=loan.account_id,
            amount=principal,
            description="Principal",
        ),
        LineSpec(
            account_id=interest_account_id,
            amount=interest,
            description="Interest",
        ),
        LineSpec(
            account_id=cash_account_id,
            amount=-total_payment,
            description="Cash payment",
        ),
    ]

    return create_journal_entry(
        db=db,
        entry_date=payment_date,
        description=f"Loan payment: {loan.name} -- {payment_ref}",
        source_type="loan_payment",
        source_id=f"loan_payment:{loan.id}:{payment_ref}",
        lines=lines,
        property_id=None,  # Loans are shared liabilities, not property-specific
    )


def get_loan_balance(db: Session, loan: Loan) -> Decimal:
    """Calculate the current outstanding balance of a loan.

    Sums all journal lines that debit the loan's liability account (each principal
    payment posts a positive/debit amount to the liability, which reduces it in the
    accounting sense). Returns original_balance minus total principal paid.

    Args:
        db: SQLAlchemy session.
        loan: Loan ORM instance.

    Returns:
        Outstanding balance as a Decimal. Returns original_balance if no payments
        have been recorded.
    """
    stmt = select(func.coalesce(func.sum(JournalLine.amount), Decimal("0"))).where(
        JournalLine.account_id == loan.account_id
    )
    total_principal_paid: Decimal = db.execute(stmt).scalar_one()
    return loan.original_balance - total_principal_paid
