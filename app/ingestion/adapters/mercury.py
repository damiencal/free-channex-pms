"""Mercury bank transaction CSV adapter.

Transforms Mercury bank transaction CSV exports into canonical BankTransactionRecord
objects. Handles header validation, amount parsing, date parsing, and transaction
deduplication key determination.

MERCURY CSV COLUMN MAPPING
===========================
Source: Synthetic — UNVERIFIED, LOW confidence (no real Mercury export inspected).
        See tests/fixtures/MERCURY_CSV_NOTES.md for verification checklist.
Last verified: UNVERIFIED — confirm against real export before production use.
DEDUP STRATEGY: Composite key (Date + Amount + Description hash).
                Mercury's generic CSV does not appear to include a native transaction ID
                column. If a real export reveals one, set COL_TRANSACTION_ID below and
                update _generate_transaction_id() to read from that column.
"""

import hashlib
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import polars as pl

from app.ingestion.schemas import BankTransactionRecord

# ---------------------------------------------------------------------------
# Column name constants
# ---------------------------------------------------------------------------
# These must match the exact header strings in the real Mercury CSV export.
# Update here if Mercury changes their export format.
COL_DATE = "Date"
COL_DESCRIPTION = "Description"
COL_AMOUNT = "Amount"

# Uncomment and set if the real Mercury CSV export includes a native transaction ID:
# COL_TRANSACTION_ID = "Transaction ID"  # or whatever Mercury names it

# Only the three fields required to produce a BankTransactionRecord are mandatory.
# Additional columns (Running Balance, Category, Account, Bank Name) are ignored.
REQUIRED_HEADERS: frozenset[str] = frozenset([COL_DATE, COL_DESCRIPTION, COL_AMOUNT])

# ---------------------------------------------------------------------------
# Date formats to try in order — most to least common in Mercury exports
# ---------------------------------------------------------------------------
_DATE_FORMATS = ["%m/%d/%Y", "%-m/%-d/%Y", "%Y-%m-%d"]


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
        - Date format is assumed MM/DD/YYYY; falls back to ISO 8601.
        - Transaction ID is a composite SHA-256 hash (Date|Amount|Description)
          prefixed with "mercury-" since Mercury generic CSV has no native ID.
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

        # --- Transaction ID (composite key) ---
        # Composite key = "mercury-" + sha256(date|amount|description)[:16]
        # Stable as long as Date, Amount, and Description don't change between exports.
        assert parsed_date is not None
        assert parsed_amount is not None
        transaction_id = _generate_transaction_id(
            date_str=raw_date,
            amount_str=raw_amount,
            description=raw_description or "",
        )

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


def _generate_transaction_id(date_str: str, amount_str: str, description: str) -> str:
    """Generate a stable composite transaction ID for Mercury deduplication.

    Uses SHA-256 of the pipe-delimited composite "date|amount|description".
    The "mercury-" prefix ensures no collision with IDs from other platforms.

    Args:
        date_str: Raw date string from CSV (e.g. "01/15/2025").
        amount_str: Raw amount string from CSV (e.g. "-145.00" or "$1,234.56").
        description: Trimmed description string from CSV.

    Returns:
        A 24-character string like "mercury-a1b2c3d4e5f6g7h8".
    """
    composite = f"{date_str}|{amount_str}|{description}"
    hash_hex = hashlib.sha256(composite.encode()).hexdigest()[:16]
    return f"mercury-{hash_hex}"


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
