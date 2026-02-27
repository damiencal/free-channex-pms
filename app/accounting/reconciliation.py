"""Bank reconciliation algorithm.

Matches platform payouts (Booking records) against Mercury bank deposits
(BankTransaction records) using exact amount + 7-day date window.

Match logic:
  - Exact Decimal amount equality (no float)
  - abs(deposit.date - booking.check_in_date) <= MATCH_WINDOW_DAYS
  - Airbnb typically pays out on or near check-in day

Auto-match: single candidate  -> status="matched"
Flag:       multiple candidates -> status="needs_review" (no match record created)
Skip:       zero candidates     -> deposit stays "unmatched"
"""

from sqlalchemy.orm import Session

from app.models.bank_transaction import BankTransaction
from app.models.booking import Booking
from app.models.reconciliation import ReconciliationMatch

MATCH_WINDOW_DAYS = 7  # per CONTEXT.md decision


def run_reconciliation(db: Session) -> dict:
    """Run batch reconciliation across all unmatched bookings and deposits.

    Returns a dict summarising the outcome:
      {
        "auto_matched":      [(booking_id, bank_transaction_id), ...],
        "needs_review":      [bank_transaction_id, ...],
        "unmatched_payouts": [booking_id, ...],
        "unmatched_deposits":[bank_transaction_id, ...],
      }

    Caller is responsible for committing the session.
    """
    # 1. Fetch all unreconciled bookings
    unmatched_bookings: list[Booking] = (
        db.query(Booking)
        .filter(Booking.reconciliation_status == "unmatched")
        .all()
    )

    # 2. Fetch all positive unreconciled bank deposits
    unmatched_deposits: list[BankTransaction] = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.amount > 0,
            BankTransaction.reconciliation_status == "unmatched",
        )
        .all()
    )

    # Mutable pool of bookings — remove matched ones to prevent double-matching
    available_bookings: list[Booking] = list(unmatched_bookings)

    auto_matched: list[tuple[int, int]] = []
    needs_review: list[int] = []

    # 3. Evaluate each deposit against the available booking pool
    for deposit in unmatched_deposits:
        candidates: list[Booking] = [
            booking
            for booking in available_bookings
            if (
                # Exact Decimal equality — both columns are Numeric(10,2)
                booking.net_amount == deposit.amount
                # Date within window
                and abs((deposit.date - booking.check_in_date).days) <= MATCH_WINDOW_DAYS
            )
        ]

        if len(candidates) == 1:
            # 4. Exactly one candidate — AUTO-MATCH
            booking = candidates[0]
            match = ReconciliationMatch(
                booking_id=booking.id,
                bank_transaction_id=deposit.id,
                status="matched",
            )
            db.add(match)
            booking.reconciliation_status = "matched"
            deposit.reconciliation_status = "matched"
            # Remove from pool so it cannot match another deposit
            available_bookings.remove(booking)
            auto_matched.append((booking.id, deposit.id))

        elif len(candidates) > 1:
            # 5. Multiple candidates — FLAG for review, do NOT create a match record
            deposit.reconciliation_status = "needs_review"
            needs_review.append(deposit.id)

        # 6. Zero candidates: deposit stays "unmatched" — no action needed

    db.flush()

    # Build output lists based on final state
    matched_booking_ids = {pair[0] for pair in auto_matched}
    matched_deposit_ids = {pair[1] for pair in auto_matched}

    unmatched_payouts = [
        b.id
        for b in unmatched_bookings
        if b.id not in matched_booking_ids
    ]
    unmatched_deposit_ids = [
        d.id
        for d in unmatched_deposits
        if d.id not in matched_deposit_ids and d.id not in needs_review
    ]

    return {
        "auto_matched": auto_matched,
        "needs_review": needs_review,
        "unmatched_payouts": unmatched_payouts,
        "unmatched_deposits": unmatched_deposit_ids,
    }


def confirm_match(
    db: Session,
    booking_id: int,
    bank_transaction_id: int,
    confirmed_by: str,
) -> ReconciliationMatch:
    """Confirm a match between a booking and a bank transaction.

    Handles both:
    - Confirming an existing auto-matched ReconciliationMatch
    - Creating a new match record for operator-resolved "needs_review" items

    Updates both booking and bank_transaction reconciliation_status to "confirmed".
    Returns the ReconciliationMatch record.
    """
    # Look for an existing match record (auto-match case)
    match = (
        db.query(ReconciliationMatch)
        .filter(
            ReconciliationMatch.booking_id == booking_id,
            ReconciliationMatch.bank_transaction_id == bank_transaction_id,
        )
        .first()
    )

    if match is None:
        # Manual confirmation for "needs_review" deposit — create new record
        match = ReconciliationMatch(
            booking_id=booking_id,
            bank_transaction_id=bank_transaction_id,
            status="confirmed",
            confirmed_by=confirmed_by,
        )
        db.add(match)
    else:
        match.status = "confirmed"
        match.confirmed_by = confirmed_by

    # Update both sides
    booking = db.query(Booking).filter(Booking.id == booking_id).one()
    booking.reconciliation_status = "confirmed"

    deposit = (
        db.query(BankTransaction)
        .filter(BankTransaction.id == bank_transaction_id)
        .one()
    )
    deposit.reconciliation_status = "confirmed"

    db.flush()
    return match


def reject_match(db: Session, match_id: int, confirmed_by: str) -> None:
    """Reject a reconciliation match, resetting both sides to 'unmatched'.

    Used when an operator determines that an auto-match was incorrect.
    The match record is kept for audit trail but marked "rejected".
    """
    match = db.query(ReconciliationMatch).filter(ReconciliationMatch.id == match_id).one()
    match.status = "rejected"
    match.confirmed_by = confirmed_by

    # Reset both sides so they re-enter the unreconciled queue
    booking = db.query(Booking).filter(Booking.id == match.booking_id).one()
    booking.reconciliation_status = "unmatched"

    deposit = (
        db.query(BankTransaction)
        .filter(BankTransaction.id == match.bank_transaction_id)
        .one()
    )
    deposit.reconciliation_status = "unmatched"

    db.flush()


def get_unreconciled(db: Session) -> dict:
    """Return the full unreconciled queue for operator review.

    Returns:
      {
        "unmatched_payouts":  [Booking objects with status=="unmatched"],
        "unmatched_deposits": [BankTransaction objects with status=="unmatched" and amount>0],
        "needs_review":       [BankTransaction objects with status=="needs_review"],
      }
    """
    unmatched_payouts = (
        db.query(Booking)
        .filter(Booking.reconciliation_status == "unmatched")
        .all()
    )

    unmatched_deposits = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.reconciliation_status == "unmatched",
            BankTransaction.amount > 0,
        )
        .all()
    )

    needs_review = (
        db.query(BankTransaction)
        .filter(BankTransaction.reconciliation_status == "needs_review")
        .all()
    )

    return {
        "unmatched_payouts": unmatched_payouts,
        "unmatched_deposits": unmatched_deposits,
        "needs_review": needs_review,
    }
