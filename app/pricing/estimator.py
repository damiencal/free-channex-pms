"""Revenue estimator — project earning potential for a property or location.

Uses historical booking data from similar internal properties as comparables.
Similarity is determined by bedrooms (±1) and approximate location (if available).
Output includes monthly and annual revenue estimates with confidence levels.
"""

from __future__ import annotations

import calendar as cal
import statistics
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.portfolio_metric import PortfolioMetric
from app.models.property import Property


def _find_comparable_properties(
    db: Session,
    bedrooms: Optional[int],
    property_type: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    radius_km: float = 50.0,
) -> list[Property]:
    """Find comparable internal properties by bedrooms and location."""
    query = db.query(Property)

    if bedrooms is not None:
        # Allow ±1 bedroom range
        query = query.filter(Property.bedrooms.between(bedrooms - 1, bedrooms + 1))

    # Location-based filtering using rough distance (1 degree ≈ 111 km)
    if latitude is not None and longitude is not None:
        degree_radius = radius_km / 111.0
        query = query.filter(
            Property.latitude.between(
                latitude - degree_radius, latitude + degree_radius
            ),
            Property.longitude.between(
                longitude - degree_radius, longitude + degree_radius
            ),
        )

    return query.all()


def _get_monthly_revenue_series(
    db: Session,
    property_id: int,
    months: int = 24,
) -> list[tuple[int, int, Decimal]]:
    """Return (year, month, revenue) tuples for the last N months."""
    today = date.today()
    series = []

    for delta in range(months):
        month_first = (today.replace(day=1) - timedelta(days=delta * 28)).replace(day=1)
        year, month = month_first.year, month_first.month
        days_in_month = cal.monthrange(year, month)[1]
        period_start = date(year, month, 1)
        period_end = date(year, month, days_in_month)

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
            total_nights = (b.check_out_date - b.check_in_date).days
            if total_nights <= 0:
                continue
            overlap_start = max(b.check_in_date, period_start)
            overlap_end = min(b.check_out_date, period_end + timedelta(days=1))
            overlap_nights = (overlap_end - overlap_start).days
            if overlap_nights > 0:
                revenue += (
                    b.net_amount
                    * Decimal(str(overlap_nights))
                    / Decimal(str(total_nights))
                )

        series.append((year, month, revenue))

    return series


def estimate_revenue(
    db: Session,
    bedrooms: Optional[int] = None,
    property_type: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    amenities: Optional[list[str]] = None,
    months_ahead: int = 12,
) -> dict:
    """Estimate annual and monthly revenue for a hypothetical property.

    Uses comparable properties from the portfolio as the data source.
    Returns 12-month projections with confidence level and comparables used.
    """
    comparables = _find_comparable_properties(
        db, bedrooms, property_type, latitude, longitude
    )

    if not comparables:
        # Fallback: use all properties
        comparables = db.query(Property).all()

    # Gather monthly revenue per comparable
    comp_monthly_revenues: dict[int, dict[int, list[float]]] = {}
    for prop in comparables:
        series = _get_monthly_revenue_series(db, prop.id, months=24)
        for year, month, rev in series:
            if month not in comp_monthly_revenues:
                comp_monthly_revenues[month] = {}
            if prop.id not in comp_monthly_revenues[month]:
                comp_monthly_revenues[month][prop.id] = []
            comp_monthly_revenues[month][prop.id].append(float(rev))

    # Build monthly projections
    today = date.today()
    monthly_estimates = []
    annual_total = 0.0
    monthly_avgs = {}

    for month_offset in range(months_ahead):
        target_month = (
            today.replace(day=1) + timedelta(days=month_offset * 31)
        ).replace(day=1)
        month_num = target_month.month

        # Collect historical revenues for this calendar month across comparables
        monthly_rev_data: list[float] = []
        for prop in comparables:
            prop_data = comp_monthly_revenues.get(month_num, {}).get(prop.id, [])
            monthly_rev_data.extend(prop_data)

        if monthly_rev_data:
            avg_rev = statistics.mean(monthly_rev_data)
            low_rev = min(monthly_rev_data)
            high_rev = max(monthly_rev_data)
        else:
            avg_rev = 0.0
            low_rev = 0.0
            high_rev = 0.0

        monthly_estimates.append(
            {
                "month": target_month.strftime("%Y-%m"),
                "estimated_revenue": round(avg_rev, 2),
                "low_estimate": round(low_rev, 2),
                "high_estimate": round(high_rev, 2),
            }
        )
        annual_total += avg_rev
        monthly_avgs[month_num] = avg_rev

    # ADR estimate from comparables
    adr_estimates = []
    for prop in comparables:
        bookings = (
            db.query(Booking)
            .filter(
                Booking.property_id == prop.id,
                Booking.booking_state.notin_(["cancelled", "no_show"]),
                Booking.check_in_date >= today - timedelta(days=365),
            )
            .all()
        )
        for b in bookings:
            nights = (b.check_out_date - b.check_in_date).days
            if nights > 0:
                adr_estimates.append(float(b.net_amount) / nights)

    avg_adr = statistics.mean(adr_estimates) if adr_estimates else 0.0

    # Occupancy estimate
    total_booked = 0
    total_available = len(comparables) * 365
    for prop in comparables:
        bookings = (
            db.query(Booking)
            .filter(
                Booking.property_id == prop.id,
                Booking.booking_state.notin_(["cancelled", "no_show"]),
                Booking.check_in_date >= today - timedelta(days=365),
                Booking.check_out_date <= today,
            )
            .all()
        )
        for b in bookings:
            total_booked += (b.check_out_date - b.check_in_date).days

    avg_occ = total_booked / total_available if total_available > 0 else 0

    # Confidence level
    data_points = sum(
        len(v)
        for month_data in comp_monthly_revenues.values()
        for v in month_data.values()
    )
    if data_points == 0:
        confidence = "very_low"
    elif data_points < 10:
        confidence = "low"
    elif data_points < 50:
        confidence = "medium"
    elif data_points < 200:
        confidence = "high"
    else:
        confidence = "very_high"

    # Highest and lowest revenue months
    sorted_months = sorted(monthly_avgs.items(), key=lambda x: x[1], reverse=True)
    peak_month = sorted_months[0][0] if sorted_months else None
    shoulder_month = sorted_months[-1][0] if sorted_months else None

    return {
        "annual_estimate": round(annual_total, 2),
        "avg_monthly_estimate": round(annual_total / months_ahead, 2)
        if months_ahead > 0
        else 0,
        "adr_estimate": round(avg_adr, 2),
        "occupancy_estimate": round(avg_occ, 4),
        "confidence": confidence,
        "data_points": data_points,
        "comparable_count": len(comparables),
        "comparable_property_ids": [p.id for p in comparables],
        "monthly_estimates": monthly_estimates,
        "peak_month": peak_month,
        "shoulder_month": shoulder_month,
        "criteria": {
            "bedrooms": bedrooms,
            "property_type": property_type,
            "latitude": latitude,
            "longitude": longitude,
        },
    }
