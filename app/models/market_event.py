"""ORM model: MarketEvent — demand calendar for pricing intelligence."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class MarketEvent(Base):
    """A local market event that affects demand and therefore pricing.

    Examples: holidays, local festivals, conferences, high/low seasons.
    Global events (property_id=None) apply to all properties.
    Per-property events override global ones for that date range.

    demand_modifier: multiplier applied to base pricing (e.g. 1.25 = +25% demand)
    recurrence: 'none' | 'yearly' — yearly events recur on the same calendar dates
    event_type: 'holiday' | 'local_event' | 'season' | 'conference' | 'custom'
    """

    __tablename__ = "market_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("properties.id"), nullable=True, index=True
    )
    """Null = global event applying to all properties."""

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="local_event"
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    demand_modifier: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("1.0")
    )
    """Price multiplier from 0.5 (50% off) to 3.0 (300% premium)."""

    recurrence: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    """'none' or 'yearly'."""

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
