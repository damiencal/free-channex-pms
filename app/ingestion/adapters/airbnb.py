"""Airbnb Transaction History CSV adapter.

Transforms Airbnb CSV exports into canonical BookingRecord objects.

Known quirks handled transparently (per CONTEXT.md — these are not errors):
- Apostrophe-prefixed amounts: e.g., ``'$180.00`` or ``'-$15.50``
- US date format: MM/DD/YYYY (non-ISO)
- Multiple rows per booking: grouped by Confirmation Code into one record

Public API:
    validate_headers(df)  — raises ValueError on wrong structure
    parse(df)             — returns (records, errors)

Column name verification status:
    SYNTHETIC — headers UNVERIFIED against a real Airbnb export.
    If Airbnb renames columns, update the COL_* constants below.
    See tests/fixtures/AIRBNB_CSV_NOTES.md for verification instructions.
    Last verified: NEVER — update when verified from a real export.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

import polars as pl

from app.config import get_config
from app.ingestion.schemas import BookingRecord

# ---------------------------------------------------------------------------
# AIRBNB CSV COLUMN MAPPING
#
# These constants define the expected column names from Airbnb Transaction
# History CSV exports. Update these if Airbnb renames any columns.
#
# Source: Synthetic guess — UNVERIFIED. Must be confirmed against a real
# Airbnb Transaction History CSV export before production use.
# See tests/fixtures/AIRBNB_CSV_NOTES.md for verification instructions.
# ---------------------------------------------------------------------------

COL_DATE = "Date"
COL_TYPE = "Type"
COL_CONFIRMATION_CODE = "Confirmation Code"
COL_LISTING = "Listing"
COL_GUEST = "Guest"
COL_AMOUNT = "Amount"
COL_START_DATE = "Start Date"
COL_END_DATE = "End Date"

# Start/End Date columns are UNVERIFIED — they may be "Start Date"/"End Date",
# "Check In"/"Check Out", or embedded within a "Details" field in real exports.
# The fixture uses "Start Date"/"End Date". Update if the real export differs.

REQUIRED_HEADERS: frozenset[str] = frozenset([
    COL_DATE,
    COL_TYPE,
    COL_CONFIRMATION_CODE,
    COL_LISTING,
    COL_AMOUNT,
])

# Optional columns: COL_GUEST, COL_START_DATE, COL_END_DATE are not required
# for header validation — they may be absent or named differently in real exports.
# The adapter handles missing values gracefully with row-level errors.

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_headers(df: pl.DataFrame) -> None:
    """Fail immediately if the DataFrame lacks required Airbnb CSV columns.

    Called before parse() to detect wrong file type or renamed headers early.
    Only checks REQUIRED_HEADERS (columns we cannot function without).

    Args:
        df: Polars DataFrame read from the uploaded CSV.

    Raises:
        ValueError: Descriptive message listing expected and missing headers.
    """
    actual = frozenset(df.columns)
    missing = REQUIRED_HEADERS - actual
    if missing:
        raise ValueError(
            "This doesn't look like an Airbnb Transaction History CSV. "
            f"Expected headers: {sorted(REQUIRED_HEADERS)}. "
            f"Got: {sorted(actual)}. "
            f"Missing: {sorted(missing)}"
        )


def parse(
    df: pl.DataFrame,
) -> tuple[list[BookingRecord], list[str]]:
    """Parse Airbnb Transaction History CSV rows into canonical BookingRecords.

    Handles known Airbnb quirks silently (not as errors):
    - Apostrophe-prefixed amounts (``'$180.00``, ``'-$15.50``)
    - Dollar signs and commas in amounts
    - US date format MM/DD/YYYY

    Row-level problems (bad amounts, bad dates) are collected and returned
    as error strings rather than raising immediately. The caller
    (normalizer.ingest_csv) raises ValueError if errors is non-empty, so
    nothing is written to the DB until all rows pass.

    Multi-row grouping: Multiple rows sharing the same Confirmation Code
    (e.g., Reservation + Payout + Host Fee) are collapsed into one
    BookingRecord with the net amount (sum of all row amounts in the group).
    The first non-empty Guest and first non-null Start/End Dates are used.

    Property resolution: Listing names are resolved to property slugs via
    the unified listing_slug_map from AppConfig. Groups whose listing name
    has no mapping produce an error.

    Args:
        df: Polars DataFrame produced by pl.read_csv(..., infer_schema_length=0).
            All columns are Utf8 strings.

    Returns:
        (records, errors) where records is a list of BookingRecord and
        errors is a list of human-readable error strings. If errors is
        non-empty, records may be empty or partial.
    """
    # Build listing → property_slug lookup from all loaded property configs
    config = get_config()
    listing_lookup: dict[str, str] = {}
    for prop in config.properties:
        listing_lookup.update(prop.listing_slug_map)

    errors: list[str] = []

    # Parse amounts and dates row-by-row, collecting errors per row
    # Row numbers start at 2 (row 1 is the header)
    row_data: list[dict] = []
    for row_num, row in enumerate(df.iter_rows(named=True), start=2):
        confirmation_code = (row.get(COL_CONFIRMATION_CODE) or "").strip()
        if not confirmation_code:
            errors.append(f"Row {row_num}: {COL_CONFIRMATION_CODE} is missing or empty")
            continue

        amount_raw = row.get(COL_AMOUNT)
        amount, amount_err = _normalize_amount(amount_raw, row_num)
        if amount_err:
            errors.append(amount_err)

        start_date: date | None = None
        end_date: date | None = None

        if COL_START_DATE in df.columns:
            start_raw = row.get(COL_START_DATE)
            start_date, start_err = _parse_date(start_raw, COL_START_DATE, row_num)
            if start_err:
                errors.append(start_err)

        if COL_END_DATE in df.columns:
            end_raw = row.get(COL_END_DATE)
            end_date, end_err = _parse_date(end_raw, COL_END_DATE, row_num)
            if end_err:
                errors.append(end_err)

        row_data.append({
            "row_num": row_num,
            "confirmation_code": confirmation_code,
            "listing": (row.get(COL_LISTING) or "").strip(),
            "guest": (row.get(COL_GUEST) or "").strip(),
            "amount": amount,        # Decimal | None
            "start_date": start_date,
            "end_date": end_date,
            "raw_row": dict(row),
        })

    # If any row-level errors, return immediately — no partial records
    if errors:
        return [], errors

    # Group rows by Confirmation Code
    grouped: dict[str, list[dict]] = {}
    for row in row_data:
        code = row["confirmation_code"]
        grouped.setdefault(code, []).append(row)

    records: list[BookingRecord] = []
    for confirmation_code, group_rows in grouped.items():
        # Net amount: sum of all non-None amounts in the group
        net_amount = Decimal("0")
        for r in group_rows:
            if r["amount"] is not None:
                net_amount += r["amount"]

        # Guest name: first non-empty guest from the group
        guest_name = "Unknown Guest"
        for r in group_rows:
            if r["guest"]:
                guest_name = r["guest"]
                break

        # Listing: first non-empty listing from the group
        listing = ""
        for r in group_rows:
            if r["listing"]:
                listing = r["listing"]
                break

        # Start/End dates: first non-None from the group
        check_in: date | None = None
        check_out: date | None = None
        for r in group_rows:
            if check_in is None and r["start_date"] is not None:
                check_in = r["start_date"]
            if check_out is None and r["end_date"] is not None:
                check_out = r["end_date"]

        # Resolve listing to property_slug
        if listing not in listing_lookup:
            first_row_num = group_rows[0]["row_num"]
            errors.append(
                f"Row {first_row_num} (confirmation {confirmation_code}): "
                f"listing '{listing}' not found in listing_slug_map. "
                "Add this listing identifier to the property's listing_slug_map in its YAML config."
            )
            continue

        property_slug = listing_lookup[listing]

        # check_in/check_out are required for a BookingRecord
        if check_in is None:
            first_row_num = group_rows[0]["row_num"]
            errors.append(
                f"Row {first_row_num} (confirmation {confirmation_code}): "
                f"no valid {COL_START_DATE} found in any row of this group"
            )
            continue

        if check_out is None:
            first_row_num = group_rows[0]["row_num"]
            errors.append(
                f"Row {first_row_num} (confirmation {confirmation_code}): "
                f"no valid {COL_END_DATE} found in any row of this group"
            )
            continue

        records.append(
            BookingRecord(
                platform="airbnb",
                platform_booking_id=confirmation_code,
                property_slug=property_slug,
                guest_name=guest_name,
                check_in_date=check_in,
                check_out_date=check_out,
                net_amount=net_amount,
                raw_platform_data={"rows": [r["raw_row"] for r in group_rows]},
            )
        )

    if errors:
        return [], errors

    return records, []


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

# Matches an optional apostrophe, optional minus, optional dollar sign,
# then digits/commas/dots, for example:
#   '$180.00  ->  180.00
#   '-$15.50  ->  -15.50
#   -$50.00   ->  -50.00
#   $1,234.56 ->  1234.56
_AMOUNT_STRIP_RE = re.compile(r"['\$,\s]")


def _normalize_amount(
    raw: str | None,
    row_num: int,
) -> tuple[Decimal | None, str | None]:
    """Parse a raw Airbnb amount string into a Decimal.

    Silently strips apostrophe, dollar sign, commas, and whitespace.
    Preserves the minus sign for negative amounts.

    Args:
        raw:     Raw cell value from the CSV (may be None or empty).
        row_num: 1-based row number for error messages.

    Returns:
        (Decimal, None) on success, or (None, error_string) on failure.
    """
    if raw is None or raw.strip() == "":
        return None, f"Row {row_num}: {COL_AMOUNT} is missing or empty"

    # Preserve minus sign — strip everything else that isn't digits or dot
    cleaned = raw.strip()

    # Check if there's a minus sign (before or after apostrophe/dollar)
    is_negative = "-" in cleaned

    # Remove apostrophe, dollar, comma, whitespace, and the minus sign itself
    digits_only = _AMOUNT_STRIP_RE.sub("", cleaned).replace("-", "")

    if not digits_only:
        return None, f"Row {row_num}: {COL_AMOUNT} is not a number ({raw!r})"

    try:
        value = Decimal(digits_only)
        if is_negative:
            value = -value
        return value, None
    except InvalidOperation:
        return None, f"Row {row_num}: {COL_AMOUNT} is not a number ({raw!r})"


def _parse_date(
    raw: str | None,
    col_name: str,
    row_num: int,
) -> tuple[date | None, str | None]:
    """Parse a raw date string in MM/DD/YYYY format into a date object.

    Handles both zero-padded (01/15/2025) and non-padded (1/5/2025) values.

    Args:
        raw:      Raw cell value from the CSV (may be None or empty).
        col_name: Column name for use in error messages.
        row_num:  1-based row number for error messages.

    Returns:
        (date, None) on success, or (None, error_string) on failure.
        Returns (None, None) if the value is empty/None (not all rows have dates).
    """
    if raw is None or raw.strip() == "":
        # Empty dates are acceptable for non-Reservation rows (payout rows
        # often omit dates). The grouping logic takes the first non-None date.
        return None, None

    cleaned = raw.strip()

    # Try MM/DD/YYYY (Airbnb primary format — confirmed quirk from CONTEXT.md)
    try:
        parts = cleaned.split("/")
        if len(parts) == 3:
            month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
            return date(year, month, day), None
    except (ValueError, IndexError):
        pass

    # Fallback: try ISO YYYY-MM-DD in case future exports switch format
    try:
        parts = cleaned.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            return date(year, month, day), None
    except (ValueError, IndexError):
        pass

    return None, (
        f"Row {row_num}: {col_name} has unrecognised date format ({raw!r}). "
        "Expected MM/DD/YYYY (e.g., 01/15/2025)"
    )
