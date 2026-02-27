"""Mercury bank transaction CSV adapter.

Transforms Mercury bank transaction CSV exports into canonical BankTransactionRecord
objects. Handles header validation, amount parsing, date parsing, and transaction
deduplication key determination.

MERCURY CSV COLUMN MAPPING
===========================
Source: VERIFIED against real Mercury bank transaction CSV export (2026-02-27).
Last verified: 2026-02-27
DEDUP STRATEGY: Native "Tracking ID" column — stable bank-assigned transaction ID.
                Composite hash fallback is no longer needed.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import polars as pl

from app.ingestion.schemas import BankTransactionRecord

# ---------------------------------------------------------------------------
# Column name constants
# ---------------------------------------------------------------------------
# Confirmed against real Mercury bank transaction CSV export (2026-02-27).
# Update here if Mercury changes their export format.
COL_DATE = "Date (UTC)"
COL_DESCRIPTION = "Description"
COL_AMOUNT = "Amount"
COL_TRANSACTION_ID = "Tracking ID"  # Native bank-assigned transaction ID

# Only the fields required to produce a BankTransactionRecord are mandatory.
# Additional columns (Status, Source Account, Category, etc.) are ignored.
REQUIRED_HEADERS: frozenset[str] = frozenset([
    COL_DATE, COL_DESCRIPTION, COL_AMOUNT, COL_TRANSACTION_ID,
])

# ---------------------------------------------------------------------------
# Date formats to try in order
# Mercury exports use MM-DD-YYYY with dashes (e.g. "01-29-2026")
# ---------------------------------------------------------------------------
_DATE_FORMATS = ["%m-%d-%Y", "%m/%d/%Y", "%Y-%m-%d"]


def validate_headers(df: pl.DataFrame) -> None:
    """Validate that df has the expected Mercury bank transaction CSV headers.

    Raises ValueError immediately with a descriptive message if any required
    headers are missing — no row parsing attempted on structural failures.

    Args:
        df: DataFrame read from the uploaded CSV (all columns as strings).

    Raises:
        ValueError: If any required headers are absent from the DataFrame.
    """
    actual = frozenset(df.columns)
    missing = REQUIRED_HEADERS - actual
    if missing:
        raise ValueError(
            "This doesn't look like a Mercury bank transaction CSV. "
            f"Expected headers: {sorted(REQUIRED_HEADERS)}. "
            f"Got: {sorted(actual)}. "
            f"Missing: {sorted(missing)}"
        )


def parse(df: pl.DataFrame) -> tuple[list[BankTransactionRecord], list[str]]:
    """Parse Mercury CSV rows into canonical BankTransactionRecords.

    Each CSV row produces one BankTransactionRecord. Errors are collected
    across all rows (halt-and-report pattern) rather than failing on the first.

    Args:
        df: DataFrame with validated Mercury CSV headers (all columns as strings).

    Returns:
        A tuple of (records, errors) where:
        - records: successfully parsed BankTransactionRecord instances
        - errors: list of human-readable error strings with row number and field

    Notes:
        - Amount may include $ symbols and commas; these are stripped.
        - Date format is MM-DD-YYYY with dashes (e.g. "01-29-2026"); falls back
          to MM/DD/YYYY and ISO 8601.
        - Transaction ID comes from the native "Tracking ID" column (bank-assigned,
          stable across re-exports of the same transaction).
    """
    records: list[BankTransactionRecord] = []
    errors: list[str] = []

    for row_num, row in enumerate(df.iter_rows(named=True), start=2):
        row_errors: list[str] = []

        # --- Date ---
        raw_date = (row.get(COL_DATE) or "").strip()
        parsed_date: date | None = None
        if not raw_date:
            row_errors.append(f"Row {row_num}: {COL_DATE} is missing")
        else:
            parsed_date = _parse_date(raw_date)
            if parsed_date is None:
                row_errors.append(
                    f"Row {row_num}: {COL_DATE} is not a recognised date ({raw_date!r}). "
                    "Expected format: MM/DD/YYYY or YYYY-MM-DD"
                )

        # --- Description ---
        raw_description = (row.get(COL_DESCRIPTION) or "").strip() or None

        # --- Amount ---
        raw_amount = (row.get(COL_AMOUNT) or "").strip()
        parsed_amount: Decimal | None = None
        if not raw_amount:
            row_errors.append(f"Row {row_num}: {COL_AMOUNT} is missing")
        else:
            parsed_amount = _parse_amount(raw_amount)
            if parsed_amount is None:
                row_errors.append(
                    f"Row {row_num}: {COL_AMOUNT} is not a number ({raw_amount!r})"
                )

        if row_errors:
            errors.extend(row_errors)
            continue

        # --- Transaction ID (native Tracking ID) ---
        # Mercury's "Tracking ID" is a bank-assigned stable identifier.
        # Confirmed present in real exports (2026-02-27).
        assert parsed_date is not None
        assert parsed_amount is not None
        transaction_id = f"mercury-{(row.get(COL_TRANSACTION_ID) or '').strip()}"
        if transaction_id == "mercury-":
            row_errors.append(f"Row {row_num}: {COL_TRANSACTION_ID} is missing or empty")
            errors.extend(row_errors)
            continue

        records.append(
            BankTransactionRecord(
                transaction_id=transaction_id,
                date=parsed_date,
                description=raw_description,
                amount=parsed_amount,
                raw_platform_data=dict(row),
            )
        )

    return records, errors


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------



def _parse_date(raw: str) -> date | None:
    """Try to parse a date string using known Mercury date formats.

    Args:
        raw: Raw date string from the CSV cell.

    Returns:
        A datetime.date on success, or None if no format matched.
    """
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(raw: str) -> Decimal | None:
    """Parse an amount string, stripping currency symbols and commas.

    Handles values like "180.00", "-145.00", "$1,234.56", "-$85.00".
    Preserves the sign: positive = credit, negative = debit.

    Args:
        raw: Raw amount string from the CSV cell.

    Returns:
        A Decimal on success, or None if the value cannot be parsed.
    """
    # Strip whitespace, dollar signs, and commas; preserve sign
    cleaned = raw.strip().replace("$", "").replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
