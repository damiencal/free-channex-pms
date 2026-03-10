"""Expedia Vrbo / Expedia Partner Central reservation CSV adapter.

Transforms Expedia reservation export CSVs into canonical BookingRecord objects.

Expedia distributes vacation rental listings through two channels that share
the same export format:
  - Expedia Partner Central (hotels / non-VRBO listings)
  - Expedia VRBO-connected listings (Expedia as a separate channel from VRBO)

Both channels export a "Reservations" report with one row per booking.

EXPEDIA CSV COLUMN MAPPING
Source: Expedia Partner Central → Reporting → Reservations Export
Confidence: MEDIUM — derived from Expedia Partner Central documentation and
            community-verified sample exports. Must confirm against a real
            export before production.
Last verified: 2026-03-10

When a real Expedia Reservations export is obtained:
1. Compare actual headers against REQUIRED_HEADERS below
2. Confirm date format (ISO 8601 assumed; some exports use MM/DD/YYYY)
3. Confirm the exact Net Amount / Payout column name
4. Update this docstring with verification date and correct confidence level

Notes:
- One row per reservation — no grouping required (unlike VRBO multi-row payouts).
- Property is identified by the "Property ID" column (numeric Expedia listing ID).
  Map this to a property_slug via the property YAML ``listing_slug_map``.
- Amount column: "Net Amount" preferred; falls back to "Total Amount" so the
  adapter works with both Partner Central and Extranet export variants.
- Confirmation code: "Reservation ID" or "Booking Reference".
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import polars as pl

from app.config import get_config
from app.ingestion.schemas import BookingRecord

# ---------------------------------------------------------------------------
# Column name constants
# Update these if Expedia renames their export columns.
# ---------------------------------------------------------------------------

COL_RESERVATION_ID = "Reservation ID"      # Stable unique booking identifier
COL_BOOKING_REFERENCE = "Booking Reference" # Alternative ID column on some exports
COL_GUEST_FIRST_NAME = "Guest First Name"
COL_GUEST_LAST_NAME = "Guest Last Name"
COL_GUEST_NAME = "Guest Name"              # Some exports use a single name column
COL_PROPERTY_ID = "Property ID"
COL_CHECK_IN_DATE = "Check-in Date"
COL_CHECK_OUT_DATE = "Check-out Date"
COL_NET_AMOUNT = "Net Amount"              # Preferred payout column
COL_TOTAL_AMOUNT = "Total Amount"          # Fallback if Net Amount absent
COL_CURRENCY = "Currency"
COL_STATUS = "Status"                      # e.g. "Confirmed", "Cancelled"
COL_BOOKING_DATE = "Booking Date"

# Minimum columns to process a booking. Guest name is validated at row level.
REQUIRED_HEADERS: frozenset[str] = frozenset([
    COL_PROPERTY_ID,
    COL_CHECK_IN_DATE,
    COL_CHECK_OUT_DATE,
])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_headers(df: pl.DataFrame) -> None:
    """Fail immediately if the DataFrame is missing required Expedia columns.

    At least one of COL_RESERVATION_ID / COL_BOOKING_REFERENCE must be present
    alongside the REQUIRED_HEADERS columns.

    Args:
        df: Polars DataFrame read from the uploaded CSV (all columns as Utf8).

    Raises:
        ValueError: If required columns are missing, with a descriptive message.
    """
    actual = frozenset(df.columns)
    missing = REQUIRED_HEADERS - actual

    # Must have at least one booking-ID column
    has_id = (COL_RESERVATION_ID in actual) or (COL_BOOKING_REFERENCE in actual)

    if missing or not has_id:
        id_note = (
            ""
            if has_id
            else f" Also need one of: {COL_RESERVATION_ID!r} or {COL_BOOKING_REFERENCE!r}."
        )
        raise ValueError(
            f"This doesn't look like an Expedia Reservations CSV. "
            f"Expected headers: {sorted(REQUIRED_HEADERS)}. "
            f"Got: {sorted(actual)}. "
            f"Missing: {sorted(missing)}.{id_note}"
        )


def parse(df: pl.DataFrame) -> tuple[list[BookingRecord], list[str]]:
    """Parse an Expedia Reservations DataFrame into canonical BookingRecord objects.

    One row → one BookingRecord (no grouping needed; Expedia exports one row per
    reservation). Cancelled bookings (``Status == 'Cancelled'``) are skipped
    silently — they are not useful for financial reporting.

    Args:
        df: Polars DataFrame with required columns present (validate_headers called first).

    Returns:
        A (records, errors) tuple where:
        - records: List of BookingRecord objects (one per non-cancelled reservation)
        - errors:  List of human-readable error strings.
                   If non-empty, the normalizer aborts the import.
    """
    errors: list[str] = []
    listing_lookup = _build_listing_lookup()

    # Detect which ID column and which amount column are present
    actual_cols = frozenset(df.columns)
    id_col = COL_RESERVATION_ID if COL_RESERVATION_ID in actual_cols else COL_BOOKING_REFERENCE
    amount_col = COL_NET_AMOUNT if COL_NET_AMOUNT in actual_cols else COL_TOTAL_AMOUNT

    records: list[BookingRecord] = []

    for row_num, row in enumerate(df.iter_rows(named=True), start=2):
        reservation_id = (row.get(id_col) or "").strip()
        if not reservation_id:
            continue  # skip blank / summary rows

        # Skip cancelled bookings
        status = (row.get(COL_STATUS) or "").strip().lower()
        if status == "cancelled":
            continue

        # Guest name — try split columns first, then single column
        first_name = (row.get(COL_GUEST_FIRST_NAME) or "").strip()
        last_name = (row.get(COL_GUEST_LAST_NAME) or "").strip()
        guest_name = f"{first_name} {last_name}".strip()
        if not guest_name:
            guest_name = (row.get(COL_GUEST_NAME) or "").strip()
        if not guest_name:
            errors.append(f"Row {row_num}: Guest name is missing (reservation {reservation_id})")
            continue

        # Property ID → slug
        property_id_str = (row.get(COL_PROPERTY_ID) or "").strip()
        property_slug = listing_lookup.get(property_id_str)
        if not property_slug:
            errors.append(
                f"Row {row_num}: Expedia Property ID '{property_id_str}' not found in "
                f"any property's listing_slug_map. "
                f"Add it to the property YAML config."
            )
            continue

        # Dates
        check_in, check_in_err = _parse_date(row.get(COL_CHECK_IN_DATE), COL_CHECK_IN_DATE, row_num)
        if check_in_err:
            errors.append(check_in_err)
            continue

        check_out, check_out_err = _parse_date(row.get(COL_CHECK_OUT_DATE), COL_CHECK_OUT_DATE, row_num)
        if check_out_err:
            errors.append(check_out_err)
            continue

        # Amount
        amount, amount_err = _parse_amount(row.get(amount_col), amount_col, row_num)
        if amount_err:
            errors.append(amount_err)
            continue

        records.append(
            BookingRecord(
                platform="expedia",
                platform_booking_id=reservation_id,
                property_slug=property_slug,
                guest_name=guest_name,
                check_in_date=check_in,  # type: ignore[arg-type]
                check_out_date=check_out,  # type: ignore[arg-type]
                net_amount=amount,
                raw_platform_data={"row": dict(row)},
            )
        )

    return records, errors


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_listing_lookup() -> dict[str, str]:
    """Build listing_id → property_slug map from app config."""
    config = get_config()
    lookup: dict[str, str] = {}
    for prop in config.properties:
        lookup.update(prop.listing_slug_map)
    return lookup


def _parse_date(raw: object, col_name: str, row_num: int) -> tuple[date | None, str | None]:
    """Parse a date string from an Expedia CSV cell.

    Tries ISO 8601 (YYYY-MM-DD) first, then common US formats (MM/DD/YYYY).
    """
    if raw is None or str(raw).strip() == "":
        return None, f"Row {row_num}: {col_name} is missing"
    cleaned = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(cleaned, fmt).date(), None
        except ValueError:
            continue
    return None, f"Row {row_num}: {col_name} is not a valid date ({raw!r})"


def _parse_amount(raw: object, col_name: str, row_num: int) -> tuple[Decimal, str | None]:
    """Parse a currency amount string from an Expedia CSV cell."""
    if raw is None or str(raw).strip() == "":
        return Decimal("0.00"), None  # treat missing amount as zero (some exports omit it)
    cleaned = str(raw).strip().lstrip("'").replace("$", "").replace(",", "").replace("€", "").replace("£", "")
    try:
        return Decimal(cleaned).quantize(Decimal("0.01")), None
    except InvalidOperation:
        return Decimal("0.00"), f"Row {row_num}: {col_name} is not a valid number ({raw!r})"
