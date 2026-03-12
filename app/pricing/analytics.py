"""Portfolio analytics engine — daily KPI computation.

Computes standard hospitality KPIs and caches them in portfolio_metrics
for fast dashboard retrieval.

KPIs computed:
  - occupancy_rate: booked_nights / available_nights
  - ADR (Average Daily Rate): total_revenue / booked_nights
  - RevPAR (Revenue Per Available Room/Night): total_revenue / available_nights
  - TREVPAR: Total revenue (room + extras) / available_nights
  - revenue, expenses (for the calendar month of metric_date)
  - booking_pace: rolling 30-day booking velocity vs same point LY
  - booking_count: number of bookings in the period
"""

from __future__ import annotations

import calendar as cal
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.booking import Booking
from app.models.extra import BookingExtra
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.models.portfolio_metric import PortfolioMetric
from app.models.property import Property

log = structlog.get_logger()


def _days_in_month(year: int, month: int) -> int:
    return cal.monthrange(year, month)[1]


def _get_booked_nights(
    db: Session,
    property_id: int,
    period_start: date,
    period_end: date,
) -> tuple[int, int]:
    """Count booked nights and booking count for a period.

    Returns (booked_nights, booking_count).
    """
    bookings = (
        db.query(Booking)
        .filter(
            Booking.property_id == property_id,
            Booking.check_in_date <= period_end,
            Booking.check_out_date > period_start,
            Booking.booking_state.notin_(["cancelled", "no_show"]),
        )
        .all()
    )

    total_nights = 0
    for b in bookings:
        overlap_start = max(b.check_in_date, period_start)
        overlap_end = min(b.check_out_date, period_end + timedelta(days=1))
        if overlap_end > overlap_start:
            total_nights += (overlap_end - overlap_start).days

    return total_nights, len(bookings)


def _get_period_revenue(
    db: Session,
    property_id: int,
    period_start: date,
    period_end: date,
) -> Decimal:
    """Sum net booking revenue for the period (from bookings.net_amount)."""
    bookings = (
        db.query(Booking)
        .filter(
            Booking.property_id == property_id,
            Booking.check_in_date <= period_end,
            Booking.check_out_date > period_start,
            Booking.booking_state.notin_(["cancelled", "no_show"]),
        )
        .all()
    )

    revenue = Decimal("0")
    for b in bookings:
        # Pro-rate revenue proportional to overlap
        total_nights = (b.check_out_date - b.check_in_date).days
        if total_nights <= 0:
            continue
        overlap_start = max(b.check_in_date, period_start)
        overlap_end = min(b.check_out_date, period_end + timedelta(days=1))
        overlap_nights = (overlap_end - overlap_start).days
        if overlap_nights > 0:
            revenue += (
                b.net_amount * Decimal(str(overlap_nights)) / Decimal(str(total_nights))
            )

    return revenue


def _get_period_expenses(
    db: Session,
    property_id: int,
    period_start: date,
    period_end: date,
) -> Decimal:
    """Sum journal-line expenses for the period."""
    from app.models.expense import Expense  # type: ignore

    query = (
        db.query(func.sum(Expense.amount))
        .filter(
            Expense.property_id == property_id,
            Expense.expense_date >= period_start,
            Expense.expense_date <= period_end,
        )
        .scalar()
    )
    return query or Decimal("0")


def _get_booking_pace(
    db: Session,
    property_id: int,
    as_of_date: date,
    forward_window_days: int = 90,
    lookback_days: int = 30,
) -> Optional[Decimal]:
    """Compute booking pace: bookings created in lookback window for forward window.

    booking_pace = count of bookings created in (as_of_date - lookback_days, as_of_date)
                   with check_in_date in (as_of_date, as_of_date + forward_window_days)
    """
    from_date = as_of_date - timedelta(days=lookback_days)
    to_future = as_of_date + timedelta(days=forward_window_days)

    count = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.property_id == property_id,
            Booking.created_at >= from_date,
            Booking.created_at <= as_of_date,
            Booking.check_in_date >= as_of_date,
            Booking.check_in_date <= to_future,
            Booking.booking_state.notin_(["cancelled"]),
        )
        .scalar()
    )
    return Decimal(str(count or 0))


def compute_monthly_metrics(
    db: Session,
    property_id: int,
    year: int,
    month: int,
) -> PortfolioMetric:
    """Compute and upsert portfolio metrics for a specific property + month.

    The metric_date is set to the first of the month for monthly aggregates.
    """
    period_start = date(year, month, 1)
    period_end = date(year, month, _days_in_month(year, month))
    available_nights = _days_in_month(year, month)

    booked_nights, booking_count = _get_booked_nights(
        db, property_id, period_start, period_end
    )
    revenue = _get_period_revenue(db, property_id, period_start, period_end)
    expenses = _get_period_expenses(db, property_id, period_start, period_end)

    occupancy_rate = (
        Decimal(str(booked_nights)) / Decimal(str(available_nights))
        if available_nights > 0
        else Decimal("0")
    )
    adr = revenue / Decimal(str(booked_nights)) if booked_nights > 0 else Decimal("0")
    revpar = (
        revenue / Decimal(str(available_nights))
        if available_nights > 0
        else Decimal("0")
    )
    trevpar = revpar  # For MVP, TREVPAR = RevPAR (extras not yet factored)

    # Booking pace as of end of period
    booking_pace = _get_booking_pace(db, property_id, period_end)

    # Booking pace same point last year
    ly_period_end = date(year - 1, month, _days_in_month(year - 1, month))
    booking_pace_ly = _get_booking_pace(db, property_id, ly_period_end)

    # Upsert
    existing = (
        db.query(PortfolioMetric)
        .filter(
            PortfolioMetric.property_id == property_id,
            PortfolioMetric.metric_date == period_start,
        )
        .first()
    )

    if existing:
        existing.occupancy_rate = occupancy_rate
        existing.adr = adr
        existing.revpar = revpar
        existing.trevpar = trevpar
        existing.revenue = revenue
        existing.expenses = expenses
        existing.available_nights = available_nights
        existing.booked_nights = booked_nights
        existing.booking_count = booking_count
        existing.booking_pace = booking_pace
        existing.booking_pace_ly = booking_pace_ly
        metric = existing
    else:
        metric = PortfolioMetric(
            property_id=property_id,
            metric_date=period_start,
            occupancy_rate=occupancy_rate,
            adr=adr,
            revpar=revpar,
            trevpar=trevpar,
            revenue=revenue,
            expenses=expenses,
            available_nights=available_nights,
            booked_nights=booked_nights,
            booking_count=booking_count,
            booking_pace=booking_pace,
            booking_pace_ly=booking_pace_ly,
        )
        db.add(metric)

    db.commit()
    return metric


def compute_all_properties_metrics(db: Session, year: int, month: int) -> int:
    """Compute metrics for all active properties for the given month.

    Returns count of properties updated.
    """
    properties = db.query(Property).all()
    count = 0
    for prop in properties:
        try:
            compute_monthly_metrics(db, prop.id, year, month)
            count += 1
        except Exception as exc:
            log.error("Failed to compute metrics", property_id=prop.id, error=str(exc))
    log.info("Portfolio metrics computed", count=count, year=year, month=month)
    return count


def get_kpi_summary(
    db: Session,
    property_id: Optional[int],
    months: int = 12,
) -> list[dict]:
    """Return monthly KPI summary for the last N months.

    If property_id is None, aggregates across all properties.
    """
    today = date.today()
    results = []

    for delta in range(months - 1, -1, -1):
        # Walk backwards from this month
        month_date = date(today.year, today.month, 1) - timedelta(days=delta * 30)
        month_date = month_date.replace(day=1)

        query = db.query(PortfolioMetric).filter(
            PortfolioMetric.metric_date == month_date
        )
        if property_id is not None:
            query = query.filter(PortfolioMetric.property_id == property_id)

        metrics = query.all()

        if not metrics:
            results.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "occupancy_rate": None,
                    "adr": None,
                    "revpar": None,
                    "trevpar": None,
                    "revenue": None,
                    "booked_nights": None,
                    "booking_count": None,
                }
            )
            continue

        # Aggregate across properties if not filtered
        total_revenue = sum(float(m.revenue or 0) for m in metrics)
        total_booked = sum(m.booked_nights or 0 for m in metrics)
        total_available = sum(m.available_nights or 30 for m in metrics)
        total_bookings = sum(m.booking_count or 0 for m in metrics)

        occ = total_booked / total_available if total_available > 0 else 0
        adr = total_revenue / total_booked if total_booked > 0 else 0
        revpar = total_revenue / total_available if total_available > 0 else 0

        results.append(
            {
                "month": month_date.strftime("%Y-%m"),
                "occupancy_rate": round(occ, 4),
                "adr": round(adr, 2),
                "revpar": round(revpar, 2),
                "trevpar": round(revpar, 2),
                "revenue": round(total_revenue, 2),
                "booked_nights": total_booked,
                "booking_count": total_bookings,
            }
        )

    return results
