"""Accounting API endpoints.

Exposes all Phase 3 accounting functionality via HTTP:
  - GET  /api/accounting/journal-entries         — list with filters
  - GET  /api/accounting/journal-entries/{id}    — single entry with lines
  - GET  /api/accounting/balances                — account balances
  - POST /api/accounting/revenue/recognize       — operator-triggered single booking recognition
  - POST /api/accounting/revenue/recognize-all   — batch recognition for all unrecognized bookings
  - POST /api/accounting/expenses                — record single expense
  - POST /api/accounting/expenses/import         — CSV bulk import of expenses
  - GET  /api/accounting/expenses                — list expenses with filters
  - POST /api/accounting/loans/payments          — record loan payment (P&I split)
  - GET  /api/accounting/loans                   — list loans with current balances
  - POST /api/accounting/reconciliation/run      — trigger reconciliation
  - GET  /api/accounting/reconciliation/unreconciled — unreconciled queue
  - POST /api/accounting/reconciliation/confirm  — confirm a match
  - POST /api/accounting/reconciliation/reject/{match_id} — reject a match

Revenue recognition is OPERATOR-TRIGGERED via POST endpoints. It is never called
automatically during booking import (Phase 2). The operator imports bookings, reviews
them, then explicitly triggers recognition to post journal entries to the ledger.
"""

import csv
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounting.expenses import EXPENSE_CATEGORIES, bulk_import_expenses, record_expense
from app.accounting.loans import get_loan_balance, record_loan_payment
from app.accounting.reconciliation import (
    confirm_match,
    get_unreconciled,
    reject_match,
    run_reconciliation,
)
from app.accounting.reports import ALL_CATEGORIES, NON_EXPENSE_CATEGORIES
from app.accounting.revenue import recognize_booking_revenue
from app.config import get_config
from app.db import get_db
from app.models.account import Account
from app.models.bank_transaction import BankTransaction
from app.models.booking import Booking
from app.models.expense import Expense
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.models.loan import Loan
from app.models.reconciliation import ReconciliationMatch

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class JournalLineResponse(BaseModel):
    id: int
    account_name: str
    account_number: int
    amount: Decimal
    description: str | None


class JournalEntryResponse(BaseModel):
    id: int
    entry_date: date
    description: str
    source_type: str
    source_id: str
    property_id: int | None
    created_at: datetime
    lines: list[JournalLineResponse]


class AccountBalanceResponse(BaseModel):
    account_number: int
    account_name: str
    account_type: str
    balance: Decimal


class ExpenseRequest(BaseModel):
    expense_date: date
    amount: Decimal
    category: str
    description: str
    attribution: str  # jay, minnie, shared
    property_id: int | None = None
    vendor: str | None = None


class ExpenseResponse(BaseModel):
    id: int
    expense_date: date
    amount: Decimal
    category: str
    description: str
    attribution: str
    property_id: int | None
    vendor: str | None
    journal_entry_id: int | None


class LoanPaymentRequest(BaseModel):
    loan_id: int
    principal: Decimal
    interest: Decimal
    payment_date: date
    payment_ref: str  # e.g., "2026-01"


class LoanResponse(BaseModel):
    id: int
    name: str
    account_id: int
    original_balance: Decimal
    interest_rate: Decimal
    start_date: date
    current_balance: Decimal  # computed via get_loan_balance


class ReconciliationResultResponse(BaseModel):
    auto_matched: int
    needs_review: int
    unmatched_payouts: int
    unmatched_deposits: int


class UnreconciledResponse(BaseModel):
    unmatched_payouts: list[dict]  # simplified booking dicts
    unmatched_deposits: list[dict]  # simplified bank transaction dicts
    needs_review: list[dict]  # simplified bank transaction dicts


class MatchConfirmRequest(BaseModel):
    booking_id: int
    bank_transaction_id: int
    confirmed_by: str = "operator"


class RevenueRecognitionRequest(BaseModel):
    booking_id: int


class RevenueRecognitionResponse(BaseModel):
    booking_id: int
    entries_created: int
    entries_skipped: int  # idempotent skips
    message: str


class BankTransactionResponse(BaseModel):
    id: int
    transaction_id: str
    date: date
    description: str | None
    amount: Decimal
    reconciliation_status: str
    category: str | None
    journal_entry_id: int | None


class CategoryAssignment(BaseModel):
    id: int  # bank_transaction.id
    category: str
    property_id: int | None = None  # required for expense categories to set property attribution
    attribution: str | None = None  # "jay", "minnie", or "shared" -- required for expense categories


class SingleCategoryRequest(BaseModel):
    category: str
    property_id: int | None = None
    attribution: str | None = None


class BulkCategoryRequest(BaseModel):
    assignments: list[CategoryAssignment]


# ---------------------------------------------------------------------------
# Journal entry endpoints
# ---------------------------------------------------------------------------


def _build_journal_entry_response(entry: JournalEntry) -> JournalEntryResponse:
    """Convert a JournalEntry ORM object (with loaded lines) to a response model."""
    lines = [
        JournalLineResponse(
            id=line.id,
            account_name=line.account.name,
            account_number=line.account.number,
            amount=line.amount,
            description=line.description,
        )
        for line in entry.lines
    ]
    return JournalEntryResponse(
        id=entry.id,
        entry_date=entry.entry_date,
        description=entry.description,
        source_type=entry.source_type,
        source_id=entry.source_id,
        property_id=entry.property_id,
        created_at=entry.created_at,
        lines=lines,
    )


@router.get("/journal-entries")
def list_journal_entries(
    start_date: Optional[date] = Query(default=None, description="Filter entries on or after this date"),
    end_date: Optional[date] = Query(default=None, description="Filter entries on or before this date"),
    source_type: Optional[str] = Query(default=None, description="Filter by source type (e.g. 'booking_payout', 'expense')"),
    property_id: Optional[int] = Query(default=None, description="Filter by property ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> list[JournalEntryResponse]:
    """List journal entries with optional filters, newest first.

    Returns:
        List of JournalEntryResponse with all lines populated.
    """
    stmt = (
        select(JournalEntry)
        .order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if start_date is not None:
        stmt = stmt.where(JournalEntry.entry_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(JournalEntry.entry_date <= end_date)
    if source_type is not None:
        stmt = stmt.where(JournalEntry.source_type == source_type)
    if property_id is not None:
        stmt = stmt.where(JournalEntry.property_id == property_id)

    entries = db.execute(stmt).scalars().all()
    return [_build_journal_entry_response(e) for e in entries]


@router.get("/journal-entries/{entry_id}")
def get_journal_entry(
    entry_id: int,
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    """Get a single journal entry with all lines.

    Returns:
        JournalEntryResponse with lines populated.

    Raises:
        HTTPException 404: If no entry with entry_id exists.
    """
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found")
    return _build_journal_entry_response(entry)


# ---------------------------------------------------------------------------
# Account balances endpoint
# ---------------------------------------------------------------------------


@router.get("/balances")
def get_balances(
    account_type: Optional[str] = Query(default=None, description="Filter by account type (asset, liability, equity, revenue, expense)"),
    db: Session = Depends(get_db),
) -> list[AccountBalanceResponse]:
    """Return net balance for each account.

    Sums all JournalLine amounts per account (positive=debit, negative=credit).

    Returns:
        List of AccountBalanceResponse sorted by account number.
    """
    stmt = (
        select(
            Account.number,
            Account.name,
            Account.account_type,
            func.coalesce(func.sum(JournalLine.amount), Decimal("0")).label("balance"),
        )
        .outerjoin(JournalLine, JournalLine.account_id == Account.id)
        .where(Account.is_active == True)  # noqa: E712
        .group_by(Account.id, Account.number, Account.name, Account.account_type)
        .order_by(Account.number)
    )
    if account_type is not None:
        stmt = stmt.where(Account.account_type == account_type)

    rows = db.execute(stmt).all()
    return [
        AccountBalanceResponse(
            account_number=row.number,
            account_name=row.name,
            account_type=row.account_type,
            balance=row.balance,
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Revenue recognition endpoints
# ---------------------------------------------------------------------------


@router.post("/revenue/recognize")
def recognize_single_booking(
    body: RevenueRecognitionRequest,
    db: Session = Depends(get_db),
) -> RevenueRecognitionResponse:
    """Operator-triggered revenue recognition for a single booking.

    Looks up the booking by ID, loads AppConfig, and calls
    recognize_booking_revenue(). Returns a summary of entries created vs.
    idempotent skips.

    This is the ONLY way journal entries get created from bookings — recognition
    is never triggered automatically during CSV import.

    Args:
        body: RevenueRecognitionRequest with booking_id.

    Returns:
        RevenueRecognitionResponse with entries_created and entries_skipped counts.

    Raises:
        HTTPException 404: If booking not found.
        HTTPException 422: If recognize_booking_revenue raises ValueError.
    """
    booking = db.get(Booking, body.booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail=f"Booking {body.booking_id} not found")

    config = get_config()
    try:
        results = recognize_booking_revenue(db, booking, config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.commit()

    entries_created = sum(1 for r in results if r is not None)
    entries_skipped = sum(1 for r in results if r is None)

    return RevenueRecognitionResponse(
        booking_id=body.booking_id,
        entries_created=entries_created,
        entries_skipped=entries_skipped,
        message=(
            f"Recognized booking {body.booking_id}: "
            f"{entries_created} entries created, {entries_skipped} skipped (idempotent)"
        ),
    )


@router.post("/revenue/recognize-all")
def recognize_all_bookings(
    db: Session = Depends(get_db),
) -> dict:
    """Batch revenue recognition for all bookings that have no journal entry yet.

    Finds all bookings whose source_id pattern ('booking_payout:{platform}:{id}')
    does not already exist in journal_entries, then calls recognize_booking_revenue
    for each. Allows the operator to import a batch of bookings, review them,
    then run recognition on all at once.

    Returns:
        Dict with processed, entries_created, entries_skipped, errors counts.
    """
    config = get_config()

    # Collect all existing booking_payout source_ids from journal_entries
    existing_source_ids: set[str] = set(
        db.execute(
            select(JournalEntry.source_id).where(
                JournalEntry.source_type == "booking_payout"
            )
        )
        .scalars()
        .all()
    )

    # Fetch all bookings and filter to those with no payout entry
    all_bookings: list[Booking] = db.query(Booking).all()
    unrecognized: list[Booking] = [
        b
        for b in all_bookings
        if f"booking_payout:{b.platform}:{b.platform_booking_id}" not in existing_source_ids
    ]

    processed = 0
    total_created = 0
    total_skipped = 0
    errors: list[dict] = []

    for booking in unrecognized:
        try:
            results = recognize_booking_revenue(db, booking, config)
            db.commit()
            created = sum(1 for r in results if r is not None)
            skipped = sum(1 for r in results if r is None)
            total_created += created
            total_skipped += skipped
            processed += 1
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            errors.append(
                {"booking_id": booking.id, "platform_booking_id": booking.platform_booking_id, "error": str(exc)}
            )

    return {
        "processed": processed,
        "entries_created": total_created,
        "entries_skipped": total_skipped,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Expense endpoints
# ---------------------------------------------------------------------------


@router.post("/expenses", status_code=201)
def create_expense(
    body: ExpenseRequest,
    db: Session = Depends(get_db),
) -> ExpenseResponse:
    """Record a single expense and create its journal entry.

    Args:
        body: ExpenseRequest with all required expense fields.

    Returns:
        ExpenseResponse with 201 status.

    Raises:
        HTTPException 422: If record_expense raises ValueError.
    """
    try:
        expense = record_expense(
            db=db,
            expense_date=body.expense_date,
            amount=body.amount,
            category=body.category,
            description=body.description,
            attribution=body.attribution,
            property_id=body.property_id,
            vendor=body.vendor,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ExpenseResponse(
        id=expense.id,
        expense_date=expense.expense_date,
        amount=expense.amount,
        category=expense.category,
        description=expense.description,
        attribution=expense.attribution,
        property_id=expense.property_id,
        vendor=expense.vendor,
        journal_entry_id=expense.journal_entry_id,
    )


@router.post("/expenses/import")
async def import_expenses_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """Bulk import expenses from a CSV file.

    CSV format: expense_date,amount,category,description,attribution[,vendor[,property_id]]

    Args:
        file: CSV file upload.

    Returns:
        Dict with imported count and errors list.

    Raises:
        HTTPException 422: If file does not have .csv extension.
    """
    _require_csv_extension(file.filename)
    content = file.file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    rows = list(reader)
    result = bulk_import_expenses(db, rows)
    db.commit()
    return result


@router.get("/expenses")
def list_expenses(
    start_date: Optional[date] = Query(default=None, description="Filter expenses on or after this date"),
    end_date: Optional[date] = Query(default=None, description="Filter expenses on or before this date"),
    category: Optional[str] = Query(default=None, description="Filter by expense category"),
    attribution: Optional[str] = Query(default=None, description="Filter by attribution (jay, minnie, shared)"),
    property_id: Optional[int] = Query(default=None, description="Filter by property ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> list[ExpenseResponse]:
    """List expenses with optional filters, newest first.

    Returns:
        List of ExpenseResponse.
    """
    stmt = (
        select(Expense)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if start_date is not None:
        stmt = stmt.where(Expense.expense_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(Expense.expense_date <= end_date)
    if category is not None:
        stmt = stmt.where(Expense.category == category)
    if attribution is not None:
        stmt = stmt.where(Expense.attribution == attribution)
    if property_id is not None:
        stmt = stmt.where(Expense.property_id == property_id)

    expenses = db.execute(stmt).scalars().all()
    return [
        ExpenseResponse(
            id=e.id,
            expense_date=e.expense_date,
            amount=e.amount,
            category=e.category,
            description=e.description,
            attribution=e.attribution,
            property_id=e.property_id,
            vendor=e.vendor,
            journal_entry_id=e.journal_entry_id,
        )
        for e in expenses
    ]


# ---------------------------------------------------------------------------
# Loan endpoints
# ---------------------------------------------------------------------------


@router.post("/loans/payments", status_code=201)
def record_loan_payment_endpoint(
    body: LoanPaymentRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Record a loan payment with principal/interest split.

    The caller provides the P&I split from their lender's amortization schedule.
    This endpoint does NOT compute amortization.

    Args:
        body: LoanPaymentRequest with loan_id, principal, interest, payment_date, payment_ref.

    Returns:
        Dict with status and journal_entry_id (or None for idempotent skip).

    Raises:
        HTTPException 404: If loan not found.
        HTTPException 422: If record_loan_payment raises ValueError.
    """
    loan = db.get(Loan, body.loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail=f"Loan {body.loan_id} not found")

    try:
        entry = record_loan_payment(
            db=db,
            loan=loan,
            principal=body.principal,
            interest=body.interest,
            payment_date=body.payment_date,
            payment_ref=body.payment_ref,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if entry is None:
        return {"status": "skipped", "message": "Payment already recorded (idempotent)", "journal_entry_id": None}

    return {"status": "recorded", "journal_entry_id": entry.id}


@router.get("/loans")
def list_loans(
    db: Session = Depends(get_db),
) -> list[LoanResponse]:
    """List all loans with current outstanding balances.

    Returns:
        List of LoanResponse with current_balance computed via get_loan_balance.
    """
    loans = db.query(Loan).order_by(Loan.id).all()
    return [
        LoanResponse(
            id=loan.id,
            name=loan.name,
            account_id=loan.account_id,
            original_balance=loan.original_balance,
            interest_rate=loan.interest_rate,
            start_date=loan.start_date,
            current_balance=get_loan_balance(db, loan),
        )
        for loan in loans
    ]


# ---------------------------------------------------------------------------
# Reconciliation endpoints
# ---------------------------------------------------------------------------


@router.post("/reconciliation/run")
def trigger_reconciliation(
    db: Session = Depends(get_db),
) -> ReconciliationResultResponse:
    """Trigger batch reconciliation across all unmatched bookings and deposits.

    Returns:
        ReconciliationResultResponse with auto_matched, needs_review,
        unmatched_payouts, and unmatched_deposits counts.
    """
    result = run_reconciliation(db)
    db.commit()
    return ReconciliationResultResponse(
        auto_matched=len(result["auto_matched"]),
        needs_review=len(result["needs_review"]),
        unmatched_payouts=len(result["unmatched_payouts"]),
        unmatched_deposits=len(result["unmatched_deposits"]),
    )


@router.get("/reconciliation/unreconciled")
def get_unreconciled_queue(
    db: Session = Depends(get_db),
) -> UnreconciledResponse:
    """Get the full unreconciled queue for operator review.

    Returns:
        UnreconciledResponse with simplified dicts for payouts, deposits,
        and needs_review items.
    """
    queue = get_unreconciled(db)

    unmatched_payouts = [
        {
            "id": b.id,
            "platform": b.platform,
            "guest_name": b.guest_name,
            "check_in_date": b.check_in_date.isoformat() if b.check_in_date else None,
            "net_amount": str(b.net_amount),
        }
        for b in queue["unmatched_payouts"]
    ]

    unmatched_deposits = [
        {
            "id": t.id,
            "date": t.date.isoformat() if t.date else None,
            "amount": str(t.amount),
            "description": t.description,
        }
        for t in queue["unmatched_deposits"]
    ]

    needs_review = [
        {
            "id": t.id,
            "date": t.date.isoformat() if t.date else None,
            "amount": str(t.amount),
            "description": t.description,
        }
        for t in queue["needs_review"]
    ]

    return UnreconciledResponse(
        unmatched_payouts=unmatched_payouts,
        unmatched_deposits=unmatched_deposits,
        needs_review=needs_review,
    )


@router.post("/reconciliation/confirm")
def confirm_reconciliation_match(
    body: MatchConfirmRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Confirm a reconciliation match between a booking and bank transaction.

    Handles both confirming auto-matched records and creating new records for
    operator-resolved needs_review items.

    Args:
        body: MatchConfirmRequest with booking_id, bank_transaction_id, confirmed_by.

    Returns:
        Dict {"status": "confirmed"}.
    """
    try:
        confirm_match(
            db=db,
            booking_id=body.booking_id,
            bank_transaction_id=body.bank_transaction_id,
            confirmed_by=body.confirmed_by,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"status": "confirmed"}


@router.post("/reconciliation/reject/{match_id}")
def reject_reconciliation_match(
    match_id: int,
    confirmed_by: str = Query(default="operator", description="Who is rejecting the match"),
    db: Session = Depends(get_db),
) -> dict:
    """Reject a reconciliation match, resetting both sides to unmatched.

    Args:
        match_id: ID of the ReconciliationMatch to reject.
        confirmed_by: Who is performing the rejection.

    Returns:
        Dict {"status": "rejected"}.

    Raises:
        HTTPException 404: If match_id not found (sqlalchemy raises NoResultFound).
    """
    try:
        reject_match(db=db, match_id=match_id, confirmed_by=confirmed_by)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"status": "rejected"}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _require_csv_extension(filename: Optional[str]) -> None:
    """Raise HTTP 422 if the uploaded file does not have a .csv extension.

    Args:
        filename: Original filename from the upload (may be None).

    Raises:
        HTTPException 422: If filename is missing or does not end with .csv.
    """
    if not filename or not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422,
            detail=f"File must have a .csv extension. Got: {filename!r}",
        )
