"""Market data provider interface + internal implementation.

Defines the abstract MarketDataProvider interface that decouples the pricing
engine from any specific data source. The InternalMarketDataProvider satisfies
the interface using historical booking data already in the database.

Future external providers (AirDNA, Mashvisor, PriceLabs) can be added by
implementing the abstract methods — no changes to consumers required.
"""

from __future__ import annotations

import statistics
from abc import ABC, abstractmethod
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.property import Property


class MarketMetrics:
    """Aggregate market metrics for a date range."""

    def __init__(
        self,
        avg_rate: Decimal,
        median_rate: Decimal,
        occupancy_pct: Decimal,
        adr: Decimal,
        revpar: Decimal,
        supply_count: int,
        demand_index: Decimal,
        source: str = "internal",
    ) -> None:
        self.avg_rate = avg_rate
        self.median_rate = median_rate
        self.occupancy_pct = occupancy_pct
        self.adr = adr
        self.revpar = revpar
        self.supply_count = supply_count
        self.demand_index = demand_index
        self.source = source


class MarketDataProvider(ABC):
    """Abstract interface for market data sources."""

    @abstractmethod
    def get_historical_occupancy(
        self,
        property_id: int,
        year: int,
        month: int,
    ) -> Decimal:
        """Return occupancy rate (0.0–1.0) for a property in a given month."""

    @abstractmethod
    def get_avg_rate_for_period(
        self,
        property_id: int,
        start: date,
        end: date,
    ) -> Decimal:
        """Return average nightly rate for bookings in the given date range."""

    @abstractmethod
    def get_booking_lead_times(
        self,
        property_id: int,
        lookback_days: int = 180,
    ) -> list[int]:
        """Return list of lead times (days between created_at and check_in_date)
        for bookings created in the last N days."""

    @abstractmethod
    def get_market_metrics(
        self,
        property_id: int,
        target_date: date,
    ) -> MarketMetrics:
        """Return aggregated market metrics for the date's context window."""

    @abstractmethod
    def get_comp_set_rates(
        self,
        property_ids: list[int],
        start: date,
        end: date,
    ) -> dict[int, Decimal]:
        """Return average rates per property_id over the date range."""


class InternalMarketDataProvider(MarketDataProvider):
    """Market data derived entirely from our own booking history.

    No external API calls — derives all metrics from the bookings table.
    Suitable for MVP and small portfolios with ≥ 3 months of booking history.

    Low-data properties (< 10 historical bookings) return metrics with
    defaults that trigger low-confidence flags on recommendations.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_historical_occupancy(
        self,
        property_id: int,
        year: int,
        month: int,
    ) -> Decimal:
        """Compute occupancy rate for a past month from booking data."""
        import calendar as cal

        days_in_month = cal.monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)

        bookings = (
            self._db.query(Booking)
            .filter(
                Booking.property_id == property_id,
                Booking.check_in_date <= month_end,
                Booking.check_out_date > month_start,
                Booking.booking_state.notin_(["cancelled", "no_show"]),
            )
            .all()
        )

        booked_nights = 0
        for b in bookings:
            overlap_start = max(b.check_in_date, month_start)
            overlap_end = min(b.check_out_date, month_end + timedelta(days=1))
            if overlap_end > overlap_start:
                booked_nights += (overlap_end - overlap_start).days

        return Decimal(str(round(booked_nights / days_in_month, 4)))

    def get_avg_rate_for_period(
        self,
        property_id: int,
        start: date,
        end: date,
    ) -> Decimal:
        """Compute average nightly rate from completed bookings over a period."""
        bookings = (
            self._db.query(Booking)
            .filter(
                Booking.property_id == property_id,
                Booking.check_in_date >= start,
                Booking.check_in_date <= end,
                Booking.booking_state.notin_(["cancelled", "no_show"]),
            )
            .all()
        )

        if not bookings:
            # Fall back to any active rate plan base rate
            from app.models.rate_plan import RatePlan

            plan = (
                self._db.query(RatePlan)
                .filter(
                    RatePlan.property_id == property_id, RatePlan.is_active.is_(True)
                )
                .first()
            )
            return plan.base_rate if plan else Decimal("150.00")

        nightly_rates = []
        for b in bookings:
            nights = (b.check_out_date - b.check_in_date).days
            if nights > 0:
                nightly_rates.append(float(b.net_amount) / nights)

        if not nightly_rates:
            return Decimal("150.00")

        return Decimal(str(round(statistics.mean(nightly_rates), 2)))

    def get_booking_lead_times(
        self,
        property_id: int,
        lookback_days: int = 180,
    ) -> list[int]:
        """Return booking lead times from the most recent N days of activity."""
        cutoff = date.today() - timedelta(days=lookback_days)
        bookings = (
            self._db.query(Booking)
            .filter(
                Booking.property_id == property_id,
                Booking.created_at >= cutoff,
                Booking.booking_state.notin_(["cancelled"]),
            )
            .all()
        )

        lead_times = []
        for b in bookings:
            lead = (b.check_in_date - b.created_at.date()).days
            if lead >= 0:
                lead_times.append(lead)

        return lead_times

    def get_market_metrics(
        self,
        property_id: int,
        target_date: date,
    ) -> MarketMetrics:
        """Derive market metrics from portfolio-wide booking data."""
        # Use all properties as the "market" (internal comp set)
        all_properties = self._db.query(Property).all()
        supply_count = len(all_properties)

        # Context window: ±30 days around target date for historical comparison
        window_start = target_date - timedelta(days=30)
        window_end = target_date + timedelta(days=30)

        all_rates: list[float] = []
        total_booked = 0
        total_available = supply_count * 60  # 60 day window

        for prop in all_properties:
            prop_rate = float(
                self.get_avg_rate_for_period(prop.id, window_start, window_end)
            )
            all_rates.append(prop_rate)

            # Count booked nights in window
            bookings = (
                self._db.query(Booking)
                .filter(
                    Booking.property_id == prop.id,
                    Booking.check_in_date <= window_end,
                    Booking.check_out_date > window_start,
                    Booking.booking_state.notin_(["cancelled", "no_show"]),
                )
                .all()
            )
            for b in bookings:
                overlap_start = max(b.check_in_date, window_start)
                overlap_end = min(b.check_out_date, window_end)
                if overlap_end > overlap_start:
                    total_booked += (overlap_end - overlap_start).days

        avg_rate = statistics.mean(all_rates) if all_rates else 150.0
        med_rate = statistics.median(all_rates) if all_rates else 150.0
        occ_pct = total_booked / total_available if total_available > 0 else 0.0
        adr = avg_rate
        revpar = avg_rate * occ_pct

        # Demand index: 0–100 based on occupancy relative to a 80% "full" benchmark
        demand_index = min(100.0, (occ_pct / 0.80) * 100)

        return MarketMetrics(
            avg_rate=Decimal(str(round(avg_rate, 2))),
            median_rate=Decimal(str(round(med_rate, 2))),
            occupancy_pct=Decimal(str(round(occ_pct, 4))),
            adr=Decimal(str(round(adr, 2))),
            revpar=Decimal(str(round(revpar, 2))),
            supply_count=supply_count,
            demand_index=Decimal(str(round(demand_index, 3))),
            source="internal",
        )

    def get_comp_set_rates(
        self,
        property_ids: list[int],
        start: date,
        end: date,
    ) -> dict[int, Decimal]:
        """Return average nightly rates for a list of internal properties."""
        result: dict[int, Decimal] = {}
        for pid in property_ids:
            result[pid] = self.get_avg_rate_for_period(pid, start, end)
        return result
