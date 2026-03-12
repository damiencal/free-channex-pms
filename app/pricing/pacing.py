"""Pacing engine — compare current booking velocity vs prior year and market.

Pacing data answers: "Are we booking ahead of pace vs last year?"
Used in portfolio analytics to identify properties trending up or down.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.market_snapshot import MarketSnapshot


def _count_bookings_made_for_window(
    db: Session,
    property_id: int,
    booked_as_of: date,
    checkin_start: date,
    checkin_end: date,
    lookback_days: int = 30,
) -> int:
    """Count bookings made within lookback_days of booked_as_of,
    with checkin dates in the forward window."""
    created_from = booked_as_of - timedelta(days=lookback_days)

    count = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.property_id == property_id,
            Booking.created_at >= created_from,
            Booking.created_at <= booked_as_of,
            Booking.check_in_date >= checkin_start,
            Booking.check_in_date <= checkin_end,
            Booking.booking_state.notin_(["cancelled"]),
        )
        .scalar()
    )
    return count or 0


def get_pacing_data(
    db: Session,
    property_id: int,
    target_month: date,
    lookback_days: int = 30,
) -> dict:
    """Generate pacing report for a target month.

    Returns comparison of:
    - this_year: bookings made in last N days for target_month
    - last_year: bookings made at same point in prior year
    - market_avg: from market_snapshots if available (else None)
    - pace_index: this_year / last_year (1.0 = on par, >1 = ahead)

    target_month: first day of the month to track pacing for.
    """
    today = date.today()
    month_start = target_month.replace(day=1)
    # Last day of target month
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_end = next_month - timedelta(days=1)

    # Current pacing
    ty_count = _count_bookings_made_for_window(
        db,
        property_id,
        booked_as_of=today,
        checkin_start=month_start,
        checkin_end=month_end,
        lookback_days=lookback_days,
    )

    # Last year pacing (same days-out point, same forward window)
    ly_same_point = today.replace(year=today.year - 1)
    ly_month_start = month_start.replace(year=month_start.year - 1)
    ly_month_end = month_end.replace(year=month_end.year - 1)

    ly_count = _count_bookings_made_for_window(
        db,
        property_id,
        booked_as_of=ly_same_point,
        checkin_start=ly_month_start,
        checkin_end=ly_month_end,
        lookback_days=lookback_days,
    )

    # Pace index
    pace_index: Optional[float] = None
    if ly_count > 0:
        pace_index = round(ty_count / ly_count, 3)

    # Market average from snapshots
    market_snap = (
        db.query(MarketSnapshot)
        .filter(
            MarketSnapshot.property_id.is_(None),  # Portfolio-level snapshot
            MarketSnapshot.snapshot_date == today,
        )
        .first()
    )
    market_avg_occ = float(market_snap.market_occupancy_pct) if market_snap else None

    # Weekly pickup series for chart (last 12 weeks)
    weekly_pickup: list[dict] = []
    for weeks_ago in range(11, -1, -1):
        week_point = today - timedelta(weeks=weeks_ago)
        week_window_start = week_point - timedelta(days=7)
        wk_count = (
            db.query(func.count(Booking.id))
            .filter(
                Booking.property_id == property_id,
                Booking.created_at >= week_window_start,
                Booking.created_at <= week_point,
                Booking.check_in_date >= month_start,
                Booking.check_in_date <= month_end,
                Booking.booking_state.notin_(["cancelled"]),
            )
            .scalar()
        ) or 0

        # Last year equivalent
        ly_week_point = week_point.replace(year=week_point.year - 1)
        ly_week_start = ly_week_point - timedelta(days=7)
        ly_wk_count = (
            db.query(func.count(Booking.id))
            .filter(
                Booking.property_id == property_id,
                Booking.created_at >= ly_week_start,
                Booking.created_at <= ly_week_point,
                Booking.check_in_date >= ly_month_start,
                Booking.check_in_date <= ly_month_end,
                Booking.booking_state.notin_(["cancelled"]),
            )
            .scalar()
        ) or 0

        weekly_pickup.append(
            {
                "week": week_point.strftime("%Y-%m-%d"),
                "this_year": wk_count,
                "last_year": ly_wk_count,
            }
        )

    return {
        "target_month": target_month.strftime("%Y-%m"),
        "this_year_bookings": ty_count,
        "last_year_bookings": ly_count,
        "pace_index": pace_index,
        "market_avg_occupancy": market_avg_occ,
        "weekly_pickup": weekly_pickup,
        "lookback_days": lookback_days,
    }
