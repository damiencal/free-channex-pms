"""Revenue recognition logic for all supported rental platforms.

Revenue recognition runs automatically as a BackgroundTask after each CSV import
(wired by Phase 9). It can also be triggered explicitly via the API operator endpoints
(POST /api/accounting/revenue/recognize and /recognize-all).

Platforms:
    - Airbnb: Deferred-then-recognized pattern.
        - On booking creation (Reservation row, no Payout yet): create Unearned Revenue
          liability entry (Dr. Accounts Receivable, Cr. Unearned Revenue).
        - On payout (Payout row present): recognize Rental Income, clear Unearned Revenue
          if applicable, and post Platform Fees.
        - Each adjustment row (Adjustment, Credit, Resolution) produces its own entry.
    - VRBO / RVshare: Single-event recognition — net amount treated as gross (no fee
      reconstruction without per-row fee data in CSV exports).

Fee model:
    Both 'split_fee' (3% host) and 'host_only' (15.5% host) use the same gross
    reconstruction formula: gross = net / (1 - fee_rate), fee = gross - net.

    NOTE: Switching fee models in config requires re-recognition of historical bookings
    (existing entries will not auto-update).

Account names (seeded by migration 003, confirmed 2026-02-27):
    1010  Mercury Checking    (asset)
    1020  Accounts Receivable (asset)
    2010  Unearned Revenue    (liability)
    4000  Rental Income       (revenue)
    4010  Promotional Discounts (revenue, contra)
    5010  Platform Fees       (expense)
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.accounting.journal import LineSpec, create_journal_entry
from app.models.account import Account
from app.models.journal_entry import JournalEntry

if TYPE_CHECKING:
    from app.config import AppConfig
    from app.models.booking import Booking

logger = logging.getLogger(__name__)

# Row types that represent post-booking host-side adjustments in Airbnb CSV exports.
ADJUSTMENT_ROW_TYPES: frozenset[str] = frozenset({"Adjustment", "Credit", "Resolution"})

# Discount row type labels (case-insensitive match applied at runtime).
_DISCOUNT_ROW_LABELS: frozenset[str] = frozenset({"discount", "promotional discount"})

# Module-level account cache: name -> Account.id
# Populated lazily on first query; avoids repeated SELECTs for ~20 static rows.
_account_cache: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_account_by_name(db: Session, name: str) -> Account:
    """Return Account for *name*, with module-level caching.

    Args:
        db: SQLAlchemy session.
        name: Exact account name as seeded in migration 003.

    Returns:
        Account ORM object.

    Raises:
        ValueError: If no account with that name exists in the database.
    """
    if name in _account_cache:
        # Return a lightweight proxy — caller only needs .id
        class _CachedAccount:
            id: int

            def __init__(self, account_id: int) -> None:
                self.id = account_id

        return _CachedAccount(_account_cache[name])  # type: ignore[return-value]

    account = db.query(Account).filter_by(name=name).first()
    if account is None:
        raise ValueError(
            f"Account '{name}' not found in chart of accounts. "
            "Ensure migration 003 has been applied and seeded."
        )
    _account_cache[name] = account.id
    return account


def _calculate_platform_fee(
    net_amount: Decimal,
    fee_rate: Decimal,
) -> tuple[Decimal, Decimal]:
    """Reconstruct gross revenue and platform fee from a net payout.

    Both 'split_fee' and 'host_only' models use the same formula because in both
    cases the CSV net_amount is the host's payout after the fee deduction:

        gross = net / (1 - fee_rate)
        fee   = gross - net

    Examples:
        split_fee (3%):   net=1000, gross=1000/0.97=1030.93, fee=30.93
        host_only (15.5%): net=1000, gross=1000/0.845=1183.43, fee=183.43

    Args:
        net_amount: Host's net payout as Decimal (no float).
        fee_rate: Fee rate as Decimal (e.g. Decimal("0.03") or Decimal("0.155")).

    Returns:
        Tuple of (gross_amount, fee_amount), both rounded to 2 decimal places.

    Raises:
        ValueError: If fee_rate >= 1 (would produce infinite/negative gross).
    """
    if fee_rate >= Decimal("1"):
        raise ValueError(
            f"Fee rate must be less than 1.0, got {fee_rate}. "
            "Check airbnb_host_fee_rate in config."
        )

    two_places = Decimal("0.01")
    gross = (net_amount / (Decimal("1") - fee_rate)).quantize(
        two_places, rounding=ROUND_HALF_UP
    )
    fee = (gross - net_amount).quantize(two_places, rounding=ROUND_HALF_UP)
    return gross, fee


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def recognize_booking_revenue(
    db: Session,
    booking: "Booking",
    config: "AppConfig",
) -> list[JournalEntry | None]:
    """Create revenue recognition journal entries for a booking.

    Called automatically as a BackgroundTask after CSV import, and also available
    via the operator-triggered API endpoints. Safe to call multiple times (idempotent).

    For Airbnb:
        - Inspects raw_platform_data["rows"] for row types.
        - Payout row present → full recognition (cash, rental income, platform fees).
          Also clears Unearned Revenue liability if a prior booking entry exists.
          Also processes any adjustment rows via record_adjustment_entries().
        - No Payout row → returns empty list (use create_unearned_revenue_entry()
          for deferred recognition when booking is first created).

    For VRBO / RVshare:
        - Single recognition entry. Net amount treated as gross (no fee data in CSV).

    Args:
        db: SQLAlchemy session. Caller is responsible for commit/rollback.
        booking: Booking ORM object with raw_platform_data populated.
        config: AppConfig with airbnb_fee_model and airbnb_host_fee_rate fields.

    Returns:
        List of JournalEntry results (may include None for idempotent skips).
    """
    platform = booking.platform.lower()

    if platform == "airbnb":
        return _recognize_airbnb_revenue(db, booking, config)
    elif platform == "vrbo":
        return _recognize_vrbo_revenue(db, booking)
    elif platform == "rvshare":
        return _recognize_rvshare_revenue(db, booking)
    else:
        raise ValueError(
            f"Unknown platform '{booking.platform}'. "
            "Expected one of: 'airbnb', 'vrbo', 'rvshare'."
        )


def _recognize_airbnb_revenue(
    db: Session,
    booking: "Booking",
    config: "AppConfig",
) -> list[JournalEntry | None]:
    """Internal: revenue recognition for Airbnb bookings."""
    entries: list[JournalEntry | None] = []
    rows: list[dict] = (booking.raw_platform_data or {}).get("rows", [])

    # Check whether any row is a Payout-type row.
    payout_row = next(
        (r for r in rows if r.get("type", "").lower() == "payout"),
        None,
    )

    if payout_row is None:
        logger.debug(
            "No Payout row found for Airbnb booking %s — skipping revenue recognition. "
            "Use create_unearned_revenue_entry() for deferred recognition.",
            booking.platform_booking_id,
        )
        return entries

    # --- Fee reconstruction ---
    fee_rate = Decimal(str(config.airbnb_host_fee_rate))
    net_amount = Decimal(str(booking.net_amount))
    gross_amount, fee_amount = _calculate_platform_fee(net_amount, fee_rate)

    # --- Account lookups ---
    cash_acct = _get_account_by_name(db, "Mercury Checking")
    income_acct = _get_account_by_name(db, "Rental Income")
    fees_acct = _get_account_by_name(db, "Platform Fees")

    # --- Payout recognition entry ---
    # Dr. Mercury Checking  +net_amount
    # Cr. Rental Income     -gross_amount
    # Dr. Platform Fees     +fee_amount
    payout_entry = create_journal_entry(
        db=db,
        entry_date=booking.check_in_date,
        description=f"Airbnb payout: {booking.platform_booking_id}",
        source_type="booking_payout",
        source_id=f"booking_payout:airbnb:{booking.platform_booking_id}",
        lines=[
            LineSpec(account_id=cash_acct.id, amount=net_amount,
                     description="Net payout from Airbnb"),
            LineSpec(account_id=income_acct.id, amount=-gross_amount,
                     description="Gross rental income"),
            LineSpec(account_id=fees_acct.id, amount=fee_amount,
                     description=f"Airbnb platform fee ({config.airbnb_fee_model}, "
                                 f"{config.airbnb_host_fee_rate:.1%})"),
        ],
        property_id=booking.property_id,
    )
    entries.append(payout_entry)

    # --- Clear Unearned Revenue if a prior deferred entry exists ---
    unearned_source_id = f"booking_unearned:airbnb:{booking.platform_booking_id}"
    unearned_entry = (
        db.query(JournalEntry)
        .filter_by(source_id=unearned_source_id)
        .first()
    )
    if unearned_entry is not None:
        ar_acct = _get_account_by_name(db, "Accounts Receivable")
        unearned_acct = _get_account_by_name(db, "Unearned Revenue")
        clearing_entry = create_journal_entry(
            db=db,
            entry_date=booking.check_in_date,
            description=f"Clear unearned revenue on payout: {booking.platform_booking_id}",
            source_type="booking_payout",
            source_id=f"booking_unearned_clear:airbnb:{booking.platform_booking_id}",
            lines=[
                LineSpec(account_id=unearned_acct.id, amount=net_amount,
                         description="Reverse deferred liability"),
                LineSpec(account_id=ar_acct.id, amount=-net_amount,
                         description="Clear accounts receivable"),
            ],
            property_id=booking.property_id,
        )
        entries.append(clearing_entry)

    # --- Adjustment rows ---
    adj_entries = record_adjustment_entries(db, booking)
    entries.extend(adj_entries)

    return entries


def _recognize_vrbo_revenue(
    db: Session,
    booking: "Booking",
) -> list[JournalEntry | None]:
    """Internal: revenue recognition for VRBO bookings.

    VRBO CSV exports do not contain per-booking fee breakdowns, so net_amount
    is treated as gross (no platform fee line). If fee data becomes available
    in a future adapter update, this function should be revisited.
    """
    return _recognize_simple_revenue(
        db=db,
        booking=booking,
        platform_label="vrbo",
        source_id=f"booking_payout:vrbo:{booking.platform_booking_id}",
    )


def _recognize_rvshare_revenue(
    db: Session,
    booking: "Booking",
) -> list[JournalEntry | None]:
    """Internal: revenue recognition for RVshare bookings.

    RVshare CSV exports do not contain per-booking fee breakdowns, so net_amount
    is treated as gross (no platform fee line).
    """
    return _recognize_simple_revenue(
        db=db,
        booking=booking,
        platform_label="rvshare",
        source_id=f"booking_payout:rvshare:{booking.platform_booking_id}",
    )


def _recognize_simple_revenue(
    db: Session,
    booking: "Booking",
    platform_label: str,
    source_id: str,
) -> list[JournalEntry | None]:
    """Shared helper: single-event recognition with no fee reconstruction."""
    net_amount = Decimal(str(booking.net_amount))
    cash_acct = _get_account_by_name(db, "Mercury Checking")
    income_acct = _get_account_by_name(db, "Rental Income")

    entry = create_journal_entry(
        db=db,
        entry_date=booking.check_in_date,
        description=f"{platform_label.upper()} payout: {booking.platform_booking_id}",
        source_type="booking_payout",
        source_id=source_id,
        lines=[
            LineSpec(account_id=cash_acct.id, amount=net_amount,
                     description="Net payout"),
            LineSpec(account_id=income_acct.id, amount=-net_amount,
                     description="Rental income"),
        ],
        property_id=booking.property_id,
    )
    return [entry]


def record_adjustment_entries(
    db: Session,
    booking: "Booking",
) -> list[JournalEntry | None]:
    """Create journal entries for each adjustment row in raw_platform_data.

    Per the locked accounting decision: each adjustment row (credit, clawback,
    correction) produces its own journal entry against the original booking.

    Handles:
        - ADJUSTMENT_ROW_TYPES {"Adjustment", "Credit", "Resolution"}:
            amount > 0 (credit to host):  Dr. Mercury Checking, Cr. Rental Income
            amount < 0 (clawback):        Dr. Rental Income, Cr. Mercury Checking
        - Discount rows {"Discount", "Promotional discount"} (case-insensitive):
            Dr. Promotional Discounts (+abs), Cr. Rental Income (-abs)
            DEBUG log when no discount rows found (expected — may not appear in CSV).

    Args:
        db: SQLAlchemy session. Caller is responsible for commit/rollback.
        booking: Booking ORM object with raw_platform_data populated.

    Returns:
        List of JournalEntry results (may include None for idempotent skips).
    """
    entries: list[JournalEntry | None] = []
    rows: list[dict] = (booking.raw_platform_data or {}).get("rows", [])

    cash_acct = _get_account_by_name(db, "Mercury Checking")
    income_acct = _get_account_by_name(db, "Rental Income")
    discount_acct = _get_account_by_name(db, "Promotional Discounts")

    found_discount = False

    for row_index, row in enumerate(rows):
        row_type: str = row.get("type", "")

        # --- Standard adjustment rows ---
        if row_type in ADJUSTMENT_ROW_TYPES:
            raw_amount = row.get("amount", 0)
            amount = Decimal(str(raw_amount))

            if amount == Decimal("0"):
                logger.debug(
                    "Skipping zero-amount adjustment row %d for booking %s",
                    row_index,
                    booking.platform_booking_id,
                )
                continue

            entry_date_raw = row.get("date") or row.get("start_date")
            if entry_date_raw and isinstance(entry_date_raw, date):
                adj_date = entry_date_raw
            else:
                adj_date = booking.check_in_date

            if amount > Decimal("0"):
                # Credit to host: cash increases, income increases
                lines = [
                    LineSpec(account_id=cash_acct.id, amount=amount,
                             description=f"Adjustment credit: {row_type}"),
                    LineSpec(account_id=income_acct.id, amount=-amount,
                             description=f"Rental income ({row_type})"),
                ]
            else:
                # Clawback from host: income decreases, cash decreases
                abs_amount = abs(amount)
                lines = [
                    LineSpec(account_id=income_acct.id, amount=abs_amount,
                             description=f"Adjustment reversal: {row_type}"),
                    LineSpec(account_id=cash_acct.id, amount=-abs_amount,
                             description=f"Clawback from host ({row_type})"),
                ]

            entry = create_journal_entry(
                db=db,
                entry_date=adj_date,
                description=(
                    f"Adjustment ({row_type}): {booking.platform_booking_id}"
                ),
                source_type="adjustment",
                source_id=(
                    f"adjustment:{booking.platform}:"
                    f"{booking.platform_booking_id}:{row_index}"
                ),
                lines=lines,
                property_id=booking.property_id,
            )
            entries.append(entry)

        # --- Discount rows (contra-revenue) ---
        elif row_type.lower() in _DISCOUNT_ROW_LABELS:
            found_discount = True
            raw_amount = row.get("amount", 0)
            discount_amount = abs(Decimal(str(raw_amount)))

            if discount_amount == Decimal("0"):
                continue

            entry_date_raw = row.get("date") or row.get("start_date")
            if entry_date_raw and isinstance(entry_date_raw, date):
                disc_date = entry_date_raw
            else:
                disc_date = booking.check_in_date

            entry = create_journal_entry(
                db=db,
                entry_date=disc_date,
                description=(
                    f"Promotional discount: {booking.platform_booking_id}"
                ),
                source_type="adjustment",
                source_id=(
                    f"discount:{booking.platform}:"
                    f"{booking.platform_booking_id}:{row_index}"
                ),
                lines=[
                    LineSpec(account_id=discount_acct.id, amount=discount_amount,
                             description="Promotional discount (contra-revenue)"),
                    LineSpec(account_id=income_acct.id, amount=-discount_amount,
                             description="Reduce recognized rental income"),
                ],
                property_id=booking.property_id,
            )
            entries.append(entry)

    if not found_discount:
        logger.debug(
            "No discount rows found for booking %s — discount data may not be "
            "available in CSV imports",
            booking.platform_booking_id,
        )

    return entries


def create_unearned_revenue_entry(
    db: Session,
    booking: "Booking",
) -> JournalEntry | None:
    """Create a deferred revenue liability entry for a new Airbnb booking.

    Called when an Airbnb booking is first imported and has a Reservation row
    but no Payout row yet (payout is pending until check-in date or shortly after).

    Entry:
        Dr. Accounts Receivable  +net_amount  (we are owed this amount)
        Cr. Unearned Revenue     -net_amount  (not yet earned — deferred liability)

    Args:
        db: SQLAlchemy session. Caller is responsible for commit/rollback.
        booking: Airbnb Booking ORM object with raw_platform_data populated.

    Returns:
        JournalEntry, or None if source_id already exists (idempotent skip).
    """
    rows: list[dict] = (booking.raw_platform_data or {}).get("rows", [])
    reservation_row = next(
        (r for r in rows if r.get("type", "").lower() == "reservation"),
        None,
    )

    entry_date_raw = (reservation_row or {}).get("date") if reservation_row else None
    if entry_date_raw and isinstance(entry_date_raw, date):
        entry_date = entry_date_raw
    else:
        entry_date = booking.check_in_date

    net_amount = Decimal(str(booking.net_amount))
    ar_acct = _get_account_by_name(db, "Accounts Receivable")
    unearned_acct = _get_account_by_name(db, "Unearned Revenue")

    return create_journal_entry(
        db=db,
        entry_date=entry_date,
        description=f"Airbnb booking received (unearned): {booking.platform_booking_id}",
        source_type="booking_unearned",
        source_id=f"booking_unearned:airbnb:{booking.platform_booking_id}",
        lines=[
            LineSpec(account_id=ar_acct.id, amount=net_amount,
                     description="Receivable from Airbnb (payout pending)"),
            LineSpec(account_id=unearned_acct.id, amount=-net_amount,
                     description="Deferred revenue — not yet earned"),
        ],
        property_id=booking.property_id,
    )


def reverse_journal_entry(
    db: Session,
    original_source_id: str,
    reversal_date: date,
    reason: str,
) -> JournalEntry | None:
    """Create a reversal entry that offsets an existing journal entry.

    Both the original and reversal entries remain in the database for a full
    audit trail. The reversal zeroes out the economic effect of the original.

    Args:
        db: SQLAlchemy session. Caller is responsible for commit/rollback.
        original_source_id: source_id of the entry to reverse.
        reversal_date: Date to record the reversal.
        reason: Human-readable reason for the reversal (e.g. "Booking cancelled").

    Returns:
        JournalEntry for the reversal, or None if reversal already exists (idempotent).

    Raises:
        ValueError: If no entry with original_source_id is found.
    """
    original = (
        db.query(JournalEntry)
        .filter_by(source_id=original_source_id)
        .first()
    )
    if original is None:
        raise ValueError(
            f"No journal entry found with source_id={original_source_id!r}. "
            "Cannot create reversal."
        )

    # Negate each line amount to exactly offset the original entry.
    reversed_lines = [
        LineSpec(
            account_id=line.account_id,
            amount=-line.amount,
            description=line.description,
        )
        for line in original.lines
    ]

    return create_journal_entry(
        db=db,
        entry_date=reversal_date,
        description=f"Reversal of: {original.description} -- {reason}",
        source_type="reversal",
        source_id=f"reversal:{original_source_id}",
        lines=reversed_lines,
        property_id=original.property_id,
    )
