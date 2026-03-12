"""ORM model: PricingRule — per-property smart pricing configuration."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class PricingRule(Base):
    """Smart pricing configuration for a property.

    Defines the strategy, guardrails (min/max price), and adjustment factors
    used by the dynamic pricing engine to generate recommendations.

    strategy: 'manual' | 'dynamic' | 'hybrid'
      - manual:  No recommendations generated; operator sets all prices
      - dynamic: Fully algorithm-driven recommendations
      - hybrid:  Algorithm generates with operator review required per date

    base_price_source: 'rate_plan' | 'custom'
      - rate_plan: Use the primary active RatePlan's base_rate as the anchor
      - custom:    Use a custom base price (stored in a separate field)
    """

    __tablename__ = "pricing_rules"
    __table_args__ = (
        UniqueConstraint("property_id", name="uq_pricing_rules_property"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, unique=True, index=True
    )

    strategy: Mapped[str] = mapped_column(String(16), nullable=False, default="dynamic")
    base_price_source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="rate_plan"
    )

    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    """Hard floor — recommended price never goes below this."""

    max_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    """Hard ceiling — recommended price never goes above this."""

    min_stay_default: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=1
    )
    weekend_min_stay: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=2
    )
    max_stay_default: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # --- Adjustment factors ---
    weekend_markup_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("15.00")
    )
    """Friday/Saturday nights get this % premium (e.g. 15 = +15%)."""

    orphan_day_discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("20.00")
    )
    """Isolated 1-2 night gaps between bookings get this % discount to fill them."""

    last_minute_window_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7
    )
    last_minute_discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("15.00")
    )
    """Within N days of check-in, apply this % discount to fill last-minute availability."""

    early_bird_window_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90
    )
    early_bird_discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("10.00")
    )
    """More than N days out, apply this % discount to incentivize early bookings."""

    demand_sensitivity: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.50")
    )
    """0.0 = ignore demand signal, 1.0 = maximally responsive to demand score."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
