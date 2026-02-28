"""Financial reports API endpoints.

Exposes P&L and future financial reports via HTTP:
  - GET  /api/reports/pl   — Profit & Loss report with revenue by platform and expenses by category

Period parameters (all endpoints):
  start_date + end_date : explicit range
  month + year          : single calendar month
  quarter + year        : Q1–Q4 of a year
  year                  : full calendar year
  ytd                   : Jan 1 of current year through today
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.accounting.reports import generate_pl, resolve_period
from app.db import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/pl")
def get_pl(
    start_date: Optional[date] = Query(default=None, description="Explicit period start date (requires end_date)"),
    end_date: Optional[date] = Query(default=None, description="Explicit period end date (requires start_date)"),
    month: Optional[int] = Query(default=None, ge=1, le=12, description="Calendar month (1-12), requires year"),
    quarter: Optional[str] = Query(default=None, description="Quarter: Q1, Q2, Q3, or Q4 (requires year)"),
    year: Optional[int] = Query(default=None, ge=1900, le=2100, description="Calendar year (e.g., 2026)"),
    ytd: bool = Query(default=False, description="Year-to-date: Jan 1 of current year through today"),
    breakdown: str = Query(default="combined", description="'combined' (default) or 'property' for per-property columns"),
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
