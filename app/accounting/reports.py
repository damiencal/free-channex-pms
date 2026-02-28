"""Financial report generators and shared helpers.

This module contains:
- resolve_period(): shared date-range resolver for all report endpoints
- Category constants for bank transaction categorization
- Report generator functions (added by plans 04-02 and 04-03)
"""
import calendar
from datetime import date

from app.accounting.expenses import EXPENSE_CATEGORIES

# Non-expense categories for bank transactions that don't appear on P&L
NON_EXPENSE_CATEGORIES = [
    "owner_deposit",
    "loan_payment",
    "transfer",
    "personal",
]

# All valid categories for bank transaction categorization
ALL_CATEGORIES = EXPENSE_CATEGORIES + NON_EXPENSE_CATEGORIES


def resolve_period(
    start_date: date | None = None,
    end_date: date | None = None,
    month: int | None = None,
    quarter: str | None = None,  # "Q1", "Q2", "Q3", "Q4"
    year: int | None = None,
    ytd: bool = False,
) -> tuple[date, date]:
    """Resolve a reporting period into a (start_date, end_date) tuple.

    Resolution priority (first match wins):
    1. start_date + end_date: returned directly after validation
    2. month + year: first and last day of that calendar month
    3. quarter + year: first and last day of that quarter
    4. year alone: Jan 1 - Dec 31 of that year
    5. ytd=True: Jan 1 of current year through today
    6. No match: raises ValueError

    Args:
        start_date: Explicit period start (requires end_date).
        end_date: Explicit period end (requires start_date).
        month: Calendar month (1-12). Requires year.
        quarter: One of "Q1", "Q2", "Q3", "Q4" (case-insensitive). Requires year.
        year: Calendar year (e.g., 2026).
        ytd: If True, return Jan 1 of current year through today.

    Returns:
        Tuple of (start_date, end_date) as datetime.date objects.

    Raises:
        ValueError: If parameters are invalid or insufficient to determine a period.
    """
    # 1. Explicit start_date and end_date
    if start_date is not None and end_date is not None:
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date")
        return (start_date, end_date)

    # 2. month + year
    if month is not None:
        if year is None:
            raise ValueError("month requires year")
        last_day = calendar.monthrange(year, month)[1]
        return (date(year, month, 1), date(year, month, last_day))

    # 3. quarter + year
    if quarter is not None:
        if year is None:
            raise ValueError("quarter requires year")
        q_upper = quarter.upper()
        _QUARTER_MONTHS = {
            "Q1": (1, 3),
            "Q2": (4, 6),
            "Q3": (7, 9),
            "Q4": (10, 12),
        }
        if q_upper not in _QUARTER_MONTHS:
            raise ValueError(f"Invalid quarter: {quarter}. Use Q1, Q2, Q3, or Q4.")
        start_month, end_month = _QUARTER_MONTHS[q_upper]
        last_day = calendar.monthrange(year, end_month)[1]
        return (date(year, start_month, 1), date(year, end_month, last_day))

    # 4. year alone
    if year is not None:
        return (date(year, 1, 1), date(year, 12, 31))

    # 5. year-to-date
    if ytd:
        today = date.today()
        return (date(today.year, 1, 1), today)

    # 6. No valid period specified
    raise ValueError(
        "No valid period specified. Provide start_date/end_date, month+year, "
        "quarter+year, year, or ytd=True."
    )
