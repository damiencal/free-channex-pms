"""ORM model: PortfolioMetric — daily cached KPI computations."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class PortfolioMetric(Base):
    """Daily cached KPI metrics for a property.

    Computed nightly by the analytics batch job and stored for fast dashboard
    retrieval. KPIs follow standard hospitality definitions:

    ADR (Average Daily Rate): total_revenue / booked_nights
    RevPAR (Revenue Per Available Room): total_revenue / available_nights
    TREVPAR (Total RevPAR): includes extras/add-ons beyond room revenue

    booking_pace: bookings-on-the-books for forward window vs same date LY
    """

    __tablename__ = "portfolio_metrics"
    __table_args__ = (
        UniqueConstraint("property_id", "metric_date", name="uq_portfolio_metric"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    occupancy_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    """0.0–1.0 fraction of available nights booked."""

    adr: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    """Revenue / booked nights."""

    revpar: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    """Revenue / available nights."""

    trevpar: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    """Total revenue (room + extras) / available nights."""

    revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    expenses: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    available_nights: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    booked_nights: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    booking_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    booking_pace: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 3), nullable=True
    )
    """Bookings made over the trailing 30 days for the forward 90-day window."""

    booking_pace_ly: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 3), nullable=True
    )
    """Same metric from the same point last year, for YoY pacing comparison."""

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
