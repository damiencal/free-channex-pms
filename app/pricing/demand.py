"""Demand scoring engine for the HLP (Hyper Local Pulse) pricing algorithm.

Computes a composite demand score (0.0–1.0) for a property + date combination
using multiple weighted signals:

  0.30 × Historical occupancy trend (same period, prior years)
  0.20 × Booking lead time signal (are people booking far in advance?)
  0.20 × Day-of-week pattern (weekend vs weekday premium)
  0.15 × Event/holiday calendar modifier
  0.15 × Seasonal decomposition (12-month rolling window)

The demand score drives the price multiplier in the pricing engine.
A score of 0.5 is neutral (no adjustment). Above 0.5 pushes prices up,
below 0.5 allows discounting.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.market_event import MarketEvent
from app.pricing.providers import MarketDataProvider


def _get_event_modifier(
    db: Session,
    property_id: int,
    target_date: date,
) -> Decimal:
    """Return the demand modifier for any active events on the target date.

    Checks property-specific events first, then global (property_id=None).
    If multiple events overlap, returns the maximum modifier.
    Handles yearly recurrence by checking the calendar month/day.
    """
    today_year = target_date.year

    events = (
        db.query(MarketEvent)
        .filter(
            MarketEvent.is_active.is_(True),
            MarketEvent.property_id.in_([property_id, None]),
        )
        .all()
    )

    max_modifier = Decimal("1.0")

    for event in events:
        if event.recurrence == "yearly":
            # Match month/day, ignoring year
            start_md = (event.start_date.month, event.start_date.day)
            end_md = (event.end_date.month, event.end_date.day)
            target_md = (target_date.month, target_date.day)

            # Handle year-wrap (e.g. Dec 30 – Jan 2)
            if start_md <= end_md:
                in_range = start_md <= target_md <= end_md
            else:
                in_range = target_md >= start_md or target_md <= end_md
        else:
            # Exact date range match
            actual_start = event.start_date
            actual_end = event.end_date
            in_range = actual_start <= target_date <= actual_end

        if in_range and event.demand_modifier > max_modifier:
            max_modifier = event.demand_modifier

    return max_modifier


def _get_seasonal_factor(
    provider: MarketDataProvider,
    property_id: int,
    target_date: date,
) -> Decimal:
    """Derive a seasonal factor by comparing target month occupancy to annual average.

    Uses proportional deviation: if the target month averages 0.8 occupancy
    and the annual average is 0.6, the seasonal factor is 0.8/0.6 = 1.33.
    Clamped to [0.5, 2.0] to avoid extreme values.
    """
    # Get the past 2 years of monthly occupancy rates to compute an average
    monthly_occs = []
    today = date.today()

    for delta_years in (1, 2):
        hist_year = today.year - delta_years
        for month in range(1, 13):
            if date(hist_year, month, 1) <= today:
                occ = provider.get_historical_occupancy(property_id, hist_year, month)
                monthly_occs.append(float(occ))

    if not monthly_occs:
        return Decimal("1.0")

    annual_avg = statistics.mean(monthly_occs)
    if annual_avg < 0.01:
        return Decimal("1.0")

    # Get target month occupancy from prior years
    target_month_occs = []
    for delta_years in (1, 2):
        hist_year = today.year - delta_years
        if hist_year <= today.year:
            occ = provider.get_historical_occupancy(
                property_id, hist_year, target_date.month
            )
            target_month_occs.append(float(occ))

    if not target_month_occs:
        return Decimal("1.0")

    target_avg = statistics.mean(target_month_occs)
    seasonal = target_avg / annual_avg
    seasonal = max(0.5, min(2.0, seasonal))

    return Decimal(str(round(seasonal, 4)))


def _get_lead_time_signal(
    provider: MarketDataProvider,
    property_id: int,
    target_date: date,
) -> Decimal:
    """Compute a demand signal from recent booking lead time patterns.

    Short average lead times near a future date indicate high demand
    (people are booking last-minute because high demand = urgency).
    Long average lead times suggest normal/lower urgency.

    Returns 0.0–1.0 where 0.5 is neutral baseline (30-day average lead time).
    """
    lead_times = provider.get_booking_lead_times(property_id, lookback_days=180)

    if not lead_times:
        return Decimal("0.5")

    # Days until target date from today
    days_out = (target_date - date.today()).days
    if days_out < 0:
        return Decimal("0.5")

    avg_lead = statistics.mean(lead_times)

    # If target date is closer than average lead time → high demand signal
    # Score: inverse sigmoid-like mapping
    if avg_lead < 1:
        return Decimal("0.5")

    # Ratio of days_out to avg_lead:
    # < 1.0 means people are booking this date with urgency → high demand
    # > 1.0 means plenty of lead time remaining → normal demand
    ratio = days_out / avg_lead
    signal = 1.0 / (1.0 + ratio)  # Falls from ~1 to ~0 as ratio increases
    # Normalize to 0.2–0.8 range to avoid extreme adjustments
    signal = 0.2 + (signal * 0.6)

    return Decimal(str(round(signal, 4)))


def _get_dow_pattern(target_date: date) -> Decimal:
    """Day-of-week demand pattern.

    Returns a modifier reflecting that weekends command higher demand:
    - Friday (4): 0.75 (strong demand)
    - Saturday (5): 0.80 (peak demand)
    - Sunday (6): 0.65 (moderate)
    - Weekdays (0-3): 0.45–0.50 (lower demand)
    """
    dow_scores = {
        0: Decimal("0.45"),  # Monday
        1: Decimal("0.43"),  # Tuesday
        2: Decimal("0.43"),  # Wednesday
        3: Decimal("0.45"),  # Thursday
        4: Decimal("0.72"),  # Friday
        5: Decimal("0.80"),  # Saturday
        6: Decimal("0.65"),  # Sunday
    }
    return dow_scores[target_date.weekday()]


def calculate_demand_score(
    db: Session,
    provider: MarketDataProvider,
    property_id: int,
    target_date: date,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Compute composite demand score (0.0–1.0) for a property and target date.

    Returns:
        (demand_score, seasonal_factor, event_factor, dow_raw_score)
        - demand_score: weighted composite 0.0–1.0
        - seasonal_factor: raw seasonal multiplier for future use
        - event_factor: raw event modifier for explainability
        - dow_score: raw day-of-week score

    Weights:
        0.30 × historical occupancy trend
        0.20 × lead time signal
        0.20 × day-of-week pattern
        0.15 × event modifier (normalized)
        0.15 × seasonal factor (normalized)
    """
    # Historical occupancy trend for the same month
    occ_score = provider.get_historical_occupancy(
        property_id,
        year=target_date.year - 1,
        month=target_date.month,
    )
    # Normalize occupancy (0.0–1.0) → already in range

    # Lead time signal
    lead_signal = _get_lead_time_signal(provider, property_id, target_date)

    # Day-of-week
    dow_score = _get_dow_pattern(target_date)

    # Event modifier (e.g. 1.25 → normalize to 0–1 demand signal)
    event_modifier = _get_event_modifier(db, property_id, target_date)
    # Normalize: 1.0 → 0.5, 2.0 → 1.0, 0.5 → 0.0
    event_signal = Decimal(str(min(1.0, max(0.0, (float(event_modifier) - 0.5) / 1.5))))

    # Seasonal factor
    seasonal_factor = _get_seasonal_factor(provider, property_id, target_date)
    # Normalize: 1.0 → 0.5, 2.0 → 1.0, 0.5 → 0.0
    seasonal_signal = Decimal(
        str(min(1.0, max(0.0, (float(seasonal_factor) - 0.5) / 1.5)))
    )

    # Weighted composite
    demand_score = (
        Decimal("0.30") * occ_score
        + Decimal("0.20") * lead_signal
        + Decimal("0.20") * dow_score
        + Decimal("0.15") * event_signal
        + Decimal("0.15") * seasonal_signal
    )
    demand_score = max(Decimal("0.0"), min(Decimal("1.0"), demand_score))

    return demand_score, seasonal_factor, event_modifier, dow_score


def calculate_confidence(
    provider: MarketDataProvider,
    property_id: int,
) -> Decimal:
    """Estimate recommendation confidence based on historical data availability.

    Returns 0.0–1.0 where:
      < 0.3: Very low confidence (< 1 month history)
      0.3–0.5: Low confidence (1–3 months)
      0.5–0.7: Medium confidence (3–6 months)
      0.7–0.9: High confidence (6–12 months)
      ≥ 0.9: Very high confidence (> 12 months)
    """
    lead_times = provider.get_booking_lead_times(property_id, lookback_days=365)
    booking_count = len(lead_times)

    if booking_count == 0:
        return Decimal("0.20")
    elif booking_count < 5:
        return Decimal("0.30")
    elif booking_count < 15:
        return Decimal("0.50")
    elif booking_count < 30:
        return Decimal("0.70")
    else:
        return Decimal("0.90")
