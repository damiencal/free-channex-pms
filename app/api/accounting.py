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
  - GET  /api/accounting/finance-summary         — badge counts (uncategorized + unreconciled)
  - POST /api/accounting/reconciliation/run      — trigger reconciliation
  - GET  /api/accounting/reconciliation/unreconciled — unreconciled queue (with pending_confirmation)
  - POST /api/accounting/reconciliation/confirm  — confirm a match
  - POST /api/accounting/reconciliation/reject/{match_id} — reject a match
  - GET  /api/accounting/bank-transactions       — list with filters (min/max amount, dates)

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
    pending_confirmation: list[dict]  # auto-matched pairs awaiting operator approval


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


class CreateLoanRequest(BaseModel):
    name: str
    original_balance: Decimal
    interest_rate: Decimal  # Annual rate as decimal, e.g. 0.065 = 6.5%
    start_date: date
    property_id: int | None = None


@router.post("/loans", status_code=201)
def create_loan(
    body: CreateLoanRequest,
    db: Session = Depends(get_db),
) -> LoanResponse:
    """Create a new loan with an auto-generated liability account.

    A new liability account is created in the 2xxx range for the loan.
    """
    # Find next available liability account number in 2xxx range
    max_number = (
        db.query(func.max(Account.number))
        .filter(Account.number >= 2000, Account.number < 3000)
        .scalar()
    ) or 2099
    next_number = max_number + 10  # increment by 10 for spacing

    # Create liability account
    account = Account(
        number=next_number,
        name=f"{body.name} Payable",
        account_type="liability",
        is_active=True,
    )
    db.add(account)
    db.flush()  # get account.id

    # Create loan
    loan = Loan(
        name=body.name,
        account_id=account.id,
        original_balance=body.original_balance,
        interest_rate=body.interest_rate,
        start_date=body.start_date,
        property_id=body.property_id,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    return LoanResponse(
        id=loan.id,
        name=loan.name,
        account_id=loan.account_id,
        original_balance=loan.original_balance,
        interest_rate=loan.interest_rate,
        start_date=loan.start_date,
        current_balance=loan.original_balance,  # new loan, no payments yet
    )


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
    property_id: int | None = Query(default=None, description="Filter by property ID (affects booking-linked queues)"),
    db: Session = Depends(get_db),
) -> UnreconciledResponse:
    """Get the full unreconciled queue for operator review.

    Returns:
        UnreconciledResponse with simplified dicts for payouts, deposits,
        needs_review items, and pending_confirmation auto-matched pairs.
    """
    queue = get_unreconciled(db, property_id=property_id)

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

    pending_confirmation = [
        {
            "match_id": match.id,
            "booking": {
                "id": booking.id,
                "platform": booking.platform,
                "guest_name": booking.guest_name,
                "check_in_date": booking.check_in_date.isoformat() if booking.check_in_date else None,
                "net_amount": str(booking.net_amount),
            },
            "deposit": {
                "id": txn.id,
                "date": txn.date.isoformat() if txn.date else None,
                "amount": str(txn.amount),
                "description": txn.description,
            },
        }
        for match, booking, txn in queue["pending_confirmation"]
    ]

    return UnreconciledResponse(
        unmatched_payouts=unmatched_payouts,
        unmatched_deposits=unmatched_deposits,
        needs_review=needs_review,
        pending_confirmation=pending_confirmation,
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
# Finance summary endpoint (badge counts for Finance tab)
# ---------------------------------------------------------------------------


@router.get("/finance-summary")
def get_finance_summary(
    property_id: int | None = Query(default=None, description="Filter by property ID where applicable"),
    db: Session = Depends(get_db),
) -> dict:
    """Return badge counts for the Finance tab header.

    Returns uncategorized bank transaction count and total unreconciled item count.
    Registered before path-param routes to avoid route conflicts.

    Args:
        property_id: Optional property filter. Applied to booking-linked counts
            (unmatched payouts, pending confirmation). Bank transaction counts
            are cross-property.
        db: Database session.

    Returns:
        Dict with uncategorized_count and unreconciled_count.
    """
    # Uncategorized bank transactions (cross-property — no filter applied)
    uncategorized_stmt = select(func.count()).select_from(BankTransaction).where(
        BankTransaction.category.is_(None)
    )
    uncategorized_count = db.execute(uncategorized_stmt).scalar() or 0

    # needs_review is also cross-property
    needs_review_count = (
        db.query(func.count(BankTransaction.id))
        .filter(BankTransaction.reconciliation_status == "needs_review")
        .scalar() or 0
    )

    if property_id is not None:
        unmatched_payouts_count = (
            db.query(func.count(Booking.id))
            .filter(
                Booking.reconciliation_status == "unmatched",
                Booking.property_id == property_id,
            )
            .scalar() or 0
        )
        pending_count = (
            db.query(func.count(ReconciliationMatch.id))
            .join(Booking, Booking.id == ReconciliationMatch.booking_id)
            .filter(
                ReconciliationMatch.status == "matched",
                Booking.property_id == property_id,
            )
            .scalar() or 0
        )
    else:
        unmatched_payouts_count = (
            db.query(func.count(Booking.id))
            .filter(Booking.reconciliation_status == "unmatched")
            .scalar() or 0
        )
        pending_count = (
            db.query(func.count(ReconciliationMatch.id))
            .filter(ReconciliationMatch.status == "matched")
            .scalar() or 0
        )

    unreconciled_count = unmatched_payouts_count + needs_review_count + pending_count

    return {
        "uncategorized_count": uncategorized_count,
        "unreconciled_count": unreconciled_count,
    }


# ---------------------------------------------------------------------------
# Bank transaction categorization endpoints
# ---------------------------------------------------------------------------


@router.get("/bank-transactions")
def list_bank_transactions(
    categorized: str | None = Query(default=None, description="Filter: 'true', 'false', or 'all' (default)"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    property_id: int | None = Query(default=None, description="NOTE: BankTransaction has no property_id column; param accepted but not applied (bank statements are cross-property)."),
    min_amount: Decimal | None = Query(default=None, description="Filter transactions with amount >= min_amount"),
    max_amount: Decimal | None = Query(default=None, description="Filter transactions with amount <= max_amount"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[BankTransactionResponse]:
    """List bank transactions with optional filters, newest first.

    Args:
        categorized: Optional filter. 'true' returns only categorized, 'false' only uncategorized,
            None or 'all' returns all transactions.
        start_date: Filter transactions on or after this date.
        end_date: Filter transactions on or before this date.
        property_id: Accepted for API symmetry but not applied — BankTransaction has no
            property_id column; Mercury statements are cross-property by nature.
        min_amount: Filter transactions with amount >= min_amount.
        max_amount: Filter transactions with amount <= max_amount.
        limit: Maximum number of results (1-1000, default 100).
        offset: Number of results to skip (default 0).
        db: Database session.

    Returns:
        List of BankTransactionResponse ordered by date desc, id desc.
    """
    stmt = (
        select(BankTransaction)
        .order_by(BankTransaction.date.desc(), BankTransaction.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if categorized == "true":
        stmt = stmt.where(BankTransaction.category.is_not(None))
    elif categorized == "false":
        stmt = stmt.where(BankTransaction.category.is_(None))
    # None or "all": no category filter
    if start_date is not None:
        stmt = stmt.where(BankTransaction.date >= start_date)
    if end_date is not None:
        stmt = stmt.where(BankTransaction.date <= end_date)
    if min_amount is not None:
        stmt = stmt.where(BankTransaction.amount >= min_amount)
    if max_amount is not None:
        stmt = stmt.where(BankTransaction.amount <= max_amount)
    # property_id intentionally not applied — BankTransaction has no property_id column

    txns = db.execute(stmt).scalars().all()
    return [
        BankTransactionResponse(
            id=t.id,
            transaction_id=t.transaction_id,
            date=t.date,
            description=t.description,
            amount=t.amount,
            reconciliation_status=t.reconciliation_status,
            category=t.category,
            journal_entry_id=t.journal_entry_id,
        )
        for t in txns
    ]


@router.patch("/bank-transactions/categorize")
def categorize_bulk_transactions(
    body: BulkCategoryRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Bulk categorize bank transactions.

    Processes all assignments and collects errors without aborting. Commits once
    after all assignments are processed.

    Args:
        body: BulkCategoryRequest with list of CategoryAssignment items.
        db: Database session.

    Returns:
        Dict with 'categorized' (success count) and 'errors' (list of error dicts).
    """
    success_count = 0
    errors: list[dict] = []

    for assignment in body.assignments:
        txn = db.get(BankTransaction, assignment.id)
        if txn is None:
            errors.append({"id": assignment.id, "error": f"Bank transaction {assignment.id} not found"})
            continue

        if assignment.category not in ALL_CATEGORIES:
            errors.append({
                "id": assignment.id,
                "error": f"Invalid category {assignment.category!r}. Valid categories: {ALL_CATEGORIES}",
            })
            continue

        if txn.journal_entry_id is not None:
            errors.append({
                "id": assignment.id,
                "error": "Transaction already has a journal entry. Remove the existing categorization before re-categorizing.",
            })
            continue

        if assignment.category in EXPENSE_CATEGORIES:
            if not assignment.attribution:
                errors.append({
                    "id": assignment.id,
                    "error": "attribution is required for expense categories (jay, minnie, or shared)",
                })
                continue
            try:
                expense = record_expense(
                    db=db,
                    expense_date=txn.date,
                    amount=abs(txn.amount),
                    category=assignment.category,
                    description=txn.description or f"Bank transaction {txn.transaction_id}",
                    attribution=assignment.attribution,
                    property_id=assignment.property_id,
                )
            except ValueError as exc:
                errors.append({"id": assignment.id, "error": str(exc)})
                continue
            txn.journal_entry_id = expense.journal_entry_id

        txn.category = assignment.category
        success_count += 1

    db.commit()
    return {"categorized": success_count, "errors": errors}


@router.patch("/bank-transactions/{txn_id}/category")
def categorize_single_transaction(
    txn_id: int,
    body: SingleCategoryRequest,
    db: Session = Depends(get_db),
) -> BankTransactionResponse:
    """Assign a category to a single bank transaction.

    For expense categories, automatically creates the corresponding expense journal
    entry via record_expense() so the transaction appears in P&L reports.
    Non-expense categories (owner_deposit, loan_payment, transfer, personal) are
    stored without creating journal entries.

    Re-categorization is prevented when a journal entry already exists to avoid
    double-posting.

    Args:
        txn_id: Primary key of the BankTransaction to categorize.
        body: SingleCategoryRequest with category, optional attribution, optional property_id.
        db: Database session.

    Returns:
        Updated BankTransactionResponse.

    Raises:
        HTTPException 404: If bank transaction not found.
        HTTPException 422: If category invalid, re-categorization attempted, or attribution missing.
    """
    txn = db.get(BankTransaction, txn_id)
    if txn is None:
        raise HTTPException(status_code=404, detail=f"Bank transaction {txn_id} not found")

    if body.category not in ALL_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category {body.category!r}. Valid categories: {ALL_CATEGORIES}",
        )

    if txn.journal_entry_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Transaction already has a journal entry. Remove the existing categorization before re-categorizing.",
        )

    if body.category in EXPENSE_CATEGORIES:
        if not body.attribution:
            raise HTTPException(
                status_code=422,
                detail="attribution is required for expense categories (jay, minnie, or shared)",
            )
        try:
            expense = record_expense(
                db=db,
                expense_date=txn.date,
                amount=abs(txn.amount),
                category=body.category,
                description=txn.description or f"Bank transaction {txn.transaction_id}",
                attribution=body.attribution,
                property_id=body.property_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        txn.journal_entry_id = expense.journal_entry_id

    txn.category = body.category
    db.commit()

    return BankTransactionResponse(
        id=txn.id,
        transaction_id=txn.transaction_id,
        date=txn.date,
        description=txn.description,
        amount=txn.amount,
        reconciliation_status=txn.reconciliation_status,
        category=txn.category,
        journal_entry_id=txn.journal_entry_id,
    )


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
