"""VRBO Payments Report CSV adapter.

Transforms VRBO Payments Report CSV exports into canonical BookingRecord objects.

Key behaviors:
- validate_headers(): fail immediately if required columns are missing
- parse(): group multi-row payouts by Reservation ID (sum amounts, take first
  guest/dates/property), resolve VRBO Property ID to property_slug, collect errors

VRBO CSV COLUMN MAPPING
From VRBO Payments Report CSV export.
Source: VRBO help documentation (https://help.vrbo.com/articles/How-do-I-read-my-payments-report)
Confidence: MEDIUM — verified from official docs; must confirm against real export before production
Last verified: 2026-02-27

When a real VRBO Payments Report is obtained:
1. Compare actual headers against REQUIRED_HEADERS below
2. Confirm Check In/Check Out date range separator (assumed " - ")
3. Confirm Payable To You has no currency symbols in real exports
4. Update this docstring with verification date
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

import polars as pl

from app.config import get_config
from app.ingestion.schemas import BookingRecord

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Column name constants
# Update these if VRBO changes their export format.
# ---------------------------------------------------------------------------

COL_REF_ID = "RefID"
COL_PAYOUT_ID = "Payout ID"
COL_RESERVATION_ID = "Reservation ID"          # Stable booking identifier
COL_CHECK_IN_OUT = "Check In/Check Out"        # Range: "MM/DD/YYYY - MM/DD/YYYY"
COL_NUMBER_OF_NIGHTS = "Number of Nights"
COL_SOURCE = "Source"
COL_SUBSCRIPTION_MODEL = "Subscription Model"
COL_PAYMENT_DATE = "Payment Date"
COL_DISBURSEMENT_DATE = "Disbursement Date"
COL_PAYMENT_TYPE = "Payment Type"
COL_PROPERTY_ID = "Property ID"                # VRBO's numeric property identifier
COL_GUEST_NAME = "Guest Name"
COL_PAYMENT_METHOD = "Payment Method"
COL_TAXABLE_REVENUE = "Taxable Revenue"
COL_NON_TAXABLE_REVENUE = "Non-Taxable Revenue"
COL_GUEST_PAYMENT = "Guest Payment"
COL_YOUR_REVENUE = "Your Revenue"
COL_PAYABLE_TO_YOU = "Payable To You"          # Net payout to owner after platform fees
COL_TAX = "Tax"
COL_SERVICE_FEE = "Service Fee"
COL_CURRENCY = "Currency"
COL_COMMISSION = "Commission"
COL_VAT_ON_COMMISSION = "VAT on Commission"
COL_PAYMENT_PROCESSING_FEE = "Payment Processing Fee"
COL_DEPOSIT_AMOUNT = "Deposit Amount"
COL_STAY_TAX_WE_REMIT = "Stay Tax We Remit"
COL_STAY_TAX_YOU_REMIT = "Stay Tax You Remit"
COL_REFUNDABLE_DEPOSIT = "Refundable Deposit"
COL_PAYOUT = "Payout"

# Required columns — subset of all 29 VRBO columns needed to build BookingRecord
REQUIRED_HEADERS: frozenset[str] = frozenset([
    COL_RESERVATION_ID,
    COL_GUEST_NAME,
    COL_PROPERTY_ID,
    COL_CHECK_IN_OUT,
    COL_PAYABLE_TO_YOU,
])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_headers(df: pl.DataFrame) -> None:
    """Fail immediately if the DataFrame is missing required VRBO columns.

    Args:
        df: Polars DataFrame read from the uploaded CSV (all columns as Utf8).

    Raises:
        ValueError: If any required column is missing, with a descriptive message
                    listing expected vs. actual headers so the operator can diagnose
                    whether they uploaded the wrong file.
    """
    actual = frozenset(df.columns)
    missing = REQUIRED_HEADERS - actual
    if missing:
        raise ValueError(
            f"This doesn't look like a VRBO Payments Report CSV. "
            f"Expected headers: {sorted(REQUIRED_HEADERS)}. "
            f"Got: {sorted(actual)}. "
            f"Missing: {sorted(missing)}"
        )


def parse(df: pl.DataFrame) -> tuple[list[BookingRecord], list[str]]:
    """Parse a VRBO Payments Report DataFrame into canonical BookingRecord objects.

    Groups multiple rows sharing the same Reservation ID into a single BookingRecord:
    - Sums the "Payable To You" amounts (net payout across all payment types)
    - Takes the first non-empty Guest Name per reservation
    - Takes the first non-empty Check In/Check Out per reservation
    - Takes the first Property ID per reservation (should be consistent within a reservation)

    Row-level errors are collected without aborting early (halt-and-report pattern).
    Rows with an empty Reservation ID are skipped entirely.

    Args:
        df: Polars DataFrame with all required columns present (validate_headers called first).

    Returns:
        A (records, errors) tuple where:
        - records: List of BookingRecord objects (one per unique Reservation ID)
        - errors:  List of human-readable error strings (row N: field: problem)
                   If non-empty, the normalizer will abort the import with all errors.
    """
    errors: list[str] = []
    listing_lookup = _build_listing_lookup()

    # Group data by Reservation ID in Python (iterate rows, accumulate per reservation)
    # Using a dict preserves insertion order (Python 3.7+), giving stable output.
    groups: dict[str, _ReservationGroup] = {}

    for row_num, row in enumerate(df.iter_rows(named=True), start=2):
        reservation_id = (row.get(COL_RESERVATION_ID) or "").strip()
        if not reservation_id:
            # Skip rows with no Reservation ID (e.g., summary or footer rows)
            continue

        raw_amount = row.get(COL_PAYABLE_TO_YOU)
        amount, amount_err = _normalize_amount(raw_amount, row_num)
        if amount_err:
            errors.append(amount_err)

        if reservation_id not in groups:
            # First row for this reservation — capture stable fields
            raw_check_in_out = row.get(COL_CHECK_IN_OUT)
            check_in, check_out, date_err = _parse_check_in_out(raw_check_in_out, row_num)
            if date_err:
                errors.append(date_err)

            property_id_str = (row.get(COL_PROPERTY_ID) or "").strip()
            guest_name = (row.get(COL_GUEST_NAME) or "").strip()

            # Resolve VRBO Property ID → property_slug via listing_slug_map
            property_slug: str | None = None
            if property_id_str:
                property_slug = listing_lookup.get(property_id_str)
                if property_slug is None:
                    errors.append(
                        f"Row {row_num}: VRBO Property ID '{property_id_str}' not found in "
                        f"any property's listing_slug_map. "
                        f"Add it to the property YAML config."
                    )

            groups[reservation_id] = _ReservationGroup(
                reservation_id=reservation_id,
                guest_name=guest_name,
                property_id_str=property_id_str,
                property_slug=property_slug,
                check_in=check_in,
                check_out=check_out,
                net_amount=amount or Decimal("0"),
                raw_rows=[dict(row)],
            )
        else:
            # Subsequent row for same reservation — accumulate amount only
            group = groups[reservation_id]
            if amount is not None:
                group.net_amount += amount
            group.raw_rows.append(dict(row))
            # Fill in guest_name if first row had it empty
            if not group.guest_name:
                group.guest_name = (row.get(COL_GUEST_NAME) or "").strip()

    if errors:
        return [], errors

    # Build BookingRecord for each reservation group
    records: list[BookingRecord] = []
    for group in groups.values():
        if not group.guest_name:
            errors.append(
                f"Reservation {group.reservation_id}: Guest Name is missing across all rows"
            )
            continue
        if group.check_in is None or group.check_out is None:
            errors.append(
                f"Reservation {group.reservation_id}: Check In/Check Out dates are missing"
            )
            continue
        if group.property_slug is None:
            # Error already recorded during row processing
            continue

        records.append(BookingRecord(
            platform="vrbo",
            platform_booking_id=group.reservation_id,
            property_slug=group.property_slug,
            guest_name=group.guest_name,
            check_in_date=group.check_in,
            check_out_date=group.check_out,
            net_amount=group.net_amount,
            raw_platform_data={"rows": group.raw_rows},
        ))

    if errors:
        return [], errors

    return records, []


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

class _ReservationGroup:
    """Accumulator for rows sharing a Reservation ID."""

    __slots__ = (
        "reservation_id",
        "guest_name",
        "property_id_str",
        "property_slug",
        "check_in",
        "check_out",
        "net_amount",
        "raw_rows",
    )

    def __init__(
        self,
        reservation_id: str,
        guest_name: str,
        property_id_str: str,
        property_slug: str | None,
        check_in: date | None,
        check_out: date | None,
        net_amount: Decimal,
        raw_rows: list[dict],
    ) -> None:
        self.reservation_id = reservation_id
        self.guest_name = guest_name
        self.property_id_str = property_id_str
        self.property_slug = property_slug
        self.check_in = check_in
        self.check_out = check_out
        self.net_amount = net_amount
        self.raw_rows = raw_rows


def _normalize_amount(raw: str | None, row_num: int) -> tuple[Decimal | None, str | None]:
    """Strip currency symbols from a VRBO amount string and parse as Decimal.

    VRBO Payments Reports generally do not use apostrophe prefixes (unlike Airbnb).
    This helper handles: plain numerics, values with "$", commas, and leading/trailing whitespace.

    Args:
        raw:     Raw string value from the CSV cell (may be None if cell was empty).
        row_num: 1-based row number (header = row 1, first data row = row 2) for error messages.

    Returns:
        (Decimal, None) on success, or (None, error_string) on failure.
    """
    if raw is None or str(raw).strip() == "":
        return None, f"Row {row_num}: {COL_PAYABLE_TO_YOU} is missing"
    cleaned = str(raw).strip().lstrip("'").replace("$", "").replace(",", "")
    try:
        return Decimal(cleaned), None
    except InvalidOperation:
        return None, f"Row {row_num}: {COL_PAYABLE_TO_YOU} is not a valid number ({raw!r})"


def _parse_date(raw: str | None, col_name: str, row_num: int) -> tuple[date | None, str | None]:
    """Parse a date string from a VRBO CSV cell.

    Tries common US date formats (MM/DD/YYYY, M/D/YYYY) and ISO 8601.

    Args:
        raw:      Raw string from the CSV cell.
        col_name: Column name for the error message.
        row_num:  Row number for the error message.

    Returns:
        (date, None) on success, or (None, error_string) on failure.
    """
    if raw is None or str(raw).strip() == "":
        return None, f"Row {row_num}: {col_name} is missing"
    cleaned = str(raw).strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%-m/%-d/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date(), None
        except ValueError:
            continue
    return None, f"Row {row_num}: {col_name} is not a valid date ({raw!r})"


def _parse_check_in_out(
    raw: str | None,
    row_num: int,
) -> tuple[date | None, date | None, str | None]:
    """Parse a VRBO "Check In/Check Out" range cell into two date objects.

    VRBO uses a single column with a date range, expected format:
        "MM/DD/YYYY - MM/DD/YYYY"

    The separator is assumed to be " - " (space-dash-space). If the format
    differs in a real export, update this function and VRBO_CSV_NOTES.md.

    Args:
        raw:     Raw string from the Check In/Check Out CSV cell.
        row_num: Row number for error messages.

    Returns:
        (check_in, check_out, None) on success, or (None, None, error_string) on failure.
    """
    if raw is None or str(raw).strip() == "":
        return None, None, f"Row {row_num}: {COL_CHECK_IN_OUT} is missing"

    parts = str(raw).strip().split(" - ")
    if len(parts) != 2:
        return (
            None,
            None,
            f"Row {row_num}: {COL_CHECK_IN_OUT} is not a valid date range ({raw!r}). "
            f"Expected format: MM/DD/YYYY - MM/DD/YYYY",
        )

    check_in, check_in_err = _parse_date(parts[0].strip(), f"{COL_CHECK_IN_OUT} (check-in)", row_num)
    check_out, check_out_err = _parse_date(parts[1].strip(), f"{COL_CHECK_IN_OUT} (check-out)", row_num)

    err = check_in_err or check_out_err
    if err:
        return None, None, err

    return check_in, check_out, None


def _build_listing_lookup() -> dict[str, str]:
    """Build a flat {vrbo_property_id: property_slug} lookup from all PropertyConfigs.

    Each PropertyConfig.listing_slug_map maps platform identifiers (including VRBO
    Property IDs) to this property's slug. This function merges all properties into
    a single lookup dict.

    Returns:
        Dict mapping VRBO Property ID strings to property slugs.
        Example: {"87654321": "jay", "11223344": "minnie"}
    """
    config = get_config()
    lookup: dict[str, str] = {}
    for prop in config.properties:
        lookup.update(prop.listing_slug_map)
    return lookup
