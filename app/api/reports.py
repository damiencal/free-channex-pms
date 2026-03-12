"""Financial reports API endpoints.

Exposes P&L and future financial reports via HTTP:
  - GET  /api/reports/pl                — Profit & Loss report with revenue by platform and expenses by category
  - GET  /api/reports/balance-sheet     — Balance sheet snapshot as of a given date
  - GET  /api/reports/income-statement  — Income statement with optional monthly drill-down

Period parameters (all endpoints except balance-sheet):
  start_date + end_date : explicit range
  month + year          : single calendar month
  quarter + year        : Q1–Q4 of a year
  year                  : full calendar year
  ytd                   : Jan 1 of current year through today
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounting.reports import (
    generate_balance_sheet,
    generate_income_statement,
    generate_pl,
    resolve_period,
)
from app.db import get_db
from app.models.booking import Booking
from app.models.expense import Expense

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/pl")
def get_pl(
    start_date: Optional[date] = Query(
        default=None, description="Explicit period start date (requires end_date)"
    ),
    end_date: Optional[date] = Query(
        default=None, description="Explicit period end date (requires start_date)"
    ),
    month: Optional[int] = Query(
        default=None, ge=1, le=12, description="Calendar month (1-12), requires year"
    ),
    quarter: Optional[str] = Query(
        default=None, description="Quarter: Q1, Q2, Q3, or Q4 (requires year)"
    ),
    year: Optional[int] = Query(
        default=None, ge=1900, le=2100, description="Calendar year (e.g., 2026)"
    ),
    ytd: bool = Query(
        default=False, description="Year-to-date: Jan 1 of current year through today"
    ),
    breakdown: str = Query(
        default="combined",
        description="'combined' (default) or 'property' for per-property columns",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Generate a Profit & Loss report for a given period.

    Revenue is broken down by platform (airbnb, vrbo, rvshare) with monthly
    rows nested under each platform. Expenses are shown as category totals.

    Period resolution priority (first match wins):
    1. start_date + end_date
    2. month + year
    3. quarter + year
    4. year
    5. ytd=True
    6. No valid period → 422 error

    Args:
        start_date: Explicit period start.
        end_date: Explicit period end.
        month: Calendar month (1–12). Requires year.
        quarter: Quarter string "Q1"–"Q4". Requires year.
        year: Calendar year.
        ytd: If True, Jan 1 of current year through today.
        breakdown: "combined" or "property".

    Returns:
        P&L dict with revenue by platform, expenses by category, and net_income.

    Raises:
        HTTPException 422: If period parameters are invalid or breakdown is not recognized.
    """
    # Resolve period
    try:
        resolved_start, resolved_end = resolve_period(
            start_date=start_date,
            end_date=end_date,
            month=month,
            quarter=quarter,
            year=year,
            ytd=ytd,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Validate breakdown
    if breakdown not in ("combined", "property"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid breakdown: {breakdown!r}. Must be 'combined' or 'property'.",
        )

    return generate_pl(db, resolved_start, resolved_end, breakdown)


@router.get("/balance-sheet")
def get_balance_sheet(
    as_of: date = Query(
        ..., description="Period-end date for the balance sheet snapshot"
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Generate a balance sheet snapshot as of a given date.

    Shows assets, liabilities (including loan balances via amortization schedule),
    and equity (including computed Retained Earnings). Combined-only — no per-property
    breakdown. Loan liability balances are sourced from Loan records rather than
    journal line sums (since loan origination entries were not created).

    Args:
        as_of: Point-in-time date for the snapshot (inclusive of all entries on that date).

    Returns:
        Balance sheet dict with assets, liabilities, equity sections and
        total_liabilities_and_equity. All monetary amounts as strings.

    Raises:
        HTTPException 422: If as_of is not provided (FastAPI enforces via Query(...)).
    """
    return generate_balance_sheet(db, as_of)


@router.get("/income-statement")
def get_income_statement(
    start_date: Optional[date] = Query(
        default=None, description="Explicit period start date (requires end_date)"
    ),
    end_date: Optional[date] = Query(
        default=None, description="Explicit period end date (requires start_date)"
    ),
    month: Optional[int] = Query(
        default=None, ge=1, le=12, description="Calendar month (1-12), requires year"
    ),
    quarter: Optional[str] = Query(
        default=None, description="Quarter: Q1, Q2, Q3, or Q4 (requires year)"
    ),
    year: Optional[int] = Query(
        default=None, ge=1900, le=2100, description="Calendar year (e.g., 2026)"
    ),
    ytd: bool = Query(
        default=False, description="Year-to-date: Jan 1 of current year through today"
    ),
    breakdown: str = Query(
        default="totals",
        description="'totals' (default) or 'monthly' for month-by-month drill-down",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Generate an income statement for a given period.

    Combined-only view suitable for tax/accounting purposes. Revenue is broken down
    by account name. Expenses are shown by account name. Supports month-by-month
    drill-down via breakdown=monthly.

    Period resolution priority (first match wins):
    1. start_date + end_date
    2. month + year
    3. quarter + year
    4. year
    5. ytd=True
    6. No valid period → 422 error

    Args:
        start_date: Explicit period start.
        end_date: Explicit period end.
        month: Calendar month (1–12). Requires year.
        quarter: Quarter string "Q1"–"Q4". Requires year.
        year: Calendar year.
        ytd: If True, Jan 1 of current year through today.
        breakdown: "totals" (default) or "monthly".

    Returns:
        Income statement dict with revenue by account, expenses by account, and
        net_income (totals mode), or months list plus totals (monthly mode).
        All monetary amounts as strings.

    Raises:
        HTTPException 422: If period parameters are invalid or breakdown is not recognized.
    """
    # Resolve period
    try:
        resolved_start, resolved_end = resolve_period(
            start_date=start_date,
            end_date=end_date,
            month=month,
            quarter=quarter,
            year=year,
            ytd=ytd,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Validate breakdown
    if breakdown not in ("totals", "monthly"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid breakdown: {breakdown!r}. Must be 'totals' or 'monthly'.",
        )

    return generate_income_statement(db, resolved_start, resolved_end, breakdown)


@router.get("/occupancy")
def get_occupancy(
    year: int = Query(
        ..., ge=2000, le=2100, description="Calendar year for occupancy analysis"
    ),
    property_id: Optional[int] = Query(
        default=None, description="Limit to a specific property"
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Generate a monthly occupancy rate report for a given year.

    Occupancy rate = booked nights / available nights, aggregated by month.
    Available nights = days in month (28–31). All non-inquiry, non-direct-inquiry
    bookings are counted as occupied nights.

    Args:
        year: The calendar year to analyse.
        property_id: Optional property filter.

    Returns:
        Dict with `year`, `property_id`, and `months` list of
        ``{month, booked_nights, available_nights, occupancy_pct}`` dicts.
    """
    from calendar import monthrange

    # Fetch all relevant bookings for the year
    stmt = select(
        Booking.check_in_date, Booking.check_out_date, Booking.property_id
    ).where(
        Booking.platform != "inquiry",
    )
    if property_id is not None:
        stmt = stmt.where(Booking.property_id == property_id)
    rows = db.execute(stmt).all()

    # Accumulate booked nights per month
    booked: dict[int, int] = {m: 0 for m in range(1, 13)}
    for check_in, check_out, _ in rows:
        # Iterate each night in the booking; only count nights in `year`
        from datetime import timedelta

        cur = check_in
        while cur < check_out:
            if cur.year == year:
                booked[cur.month] += 1
            cur += timedelta(days=1)

    months = []
    for m in range(1, 13):
        _, days_in_month = monthrange(year, m)
        booked_nights = booked[m]
        pct = round(booked_nights / days_in_month * 100, 1) if days_in_month else 0
        months.append(
            {
                "month": m,
                "booked_nights": booked_nights,
                "available_nights": days_in_month,
                "occupancy_pct": pct,
            }
        )

    total_booked = sum(b["booked_nights"] for b in months)
    total_available = sum(b["available_nights"] for b in months)
    overall_pct = (
        round(total_booked / total_available * 100, 1) if total_available else 0
    )

    return {
        "year": year,
        "property_id": property_id,
        "overall_occupancy_pct": overall_pct,
        "months": months,
    }


@router.get("/schedule-e")
def get_schedule_e(
    year: int = Query(
        ..., ge=2000, le=2100, description="Tax year for Schedule E preparation"
    ),
    property_id: Optional[int] = Query(
        default=None, description="Limit to a specific property"
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Generate Schedule E (Supplemental Income and Loss) summary data.

    Schedule E is used by US taxpayers to report rental income and expenses.
    Returns gross rents received, common expense categories, and net income.

    Args:
        year: The tax year.
        property_id: Optional property filter.

    Returns:
        Dict with `year`, `property_id`, `gross_rents`, `expenses` (breakdown
        by category), `total_expenses`, and `net_income`.  All monetary amounts
        are strings with 2 decimal places.
    """
    from datetime import date as _date

    period_start = _date(year, 1, 1)
    period_end = _date(year, 12, 31)

    # Gross rents = sum of net_amount for all non-inquiry bookings in the year
    rent_stmt = select(func.coalesce(func.sum(Booking.net_amount), 0)).where(
        Booking.check_in_date >= period_start,
        Booking.check_in_date <= period_end,
        Booking.platform != "inquiry",
    )
    if property_id is not None:
        rent_stmt = rent_stmt.where(Booking.property_id == property_id)
    gross_rents: Decimal = db.execute(rent_stmt).scalar_one() or Decimal("0")

    # Expenses grouped by category
    exp_stmt = select(Expense.category, func.sum(Expense.amount).label("total")).where(
        Expense.expense_date >= period_start,
        Expense.expense_date <= period_end,
    )
    if property_id is not None:
        exp_stmt = exp_stmt.where(Expense.property_id == property_id)
    exp_stmt = exp_stmt.group_by(Expense.category).order_by(Expense.category)
    expense_rows = db.execute(exp_stmt).all()

    expenses = [
        {"category": row.category, "amount": str(row.total)} for row in expense_rows
    ]
    total_expenses = sum(Decimal(e["amount"]) for e in expenses)
    net_income = gross_rents - total_expenses

    return {
        "year": year,
        "property_id": property_id,
        "gross_rents": str(gross_rents),
        "expenses": expenses,
        "total_expenses": str(total_expenses),
        "net_income": str(net_income),
    }
