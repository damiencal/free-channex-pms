"""ORM models: RatePlan and RateDate — pricing management."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class RatePlan(Base):
    """A rate plan defines a pricing structure for a room type.

    Multiple rate plans can exist per room type (e.g. Rack Rate, Early Bird,
    Last Minute, Corporate). A rate plan can have a parent for hierarchy.
    """

    __tablename__ = "rate_plans"

    id: Mapped[int] = mapped_column(primary_key=True)

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )

    room_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("room_types.id"), nullable=True, index=True
    )
    """If set, this rate plan applies only to this room type."""

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    """e.g. "Rack Rate", "Early Bird -10%", "Corporate Rate" """

    code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    base_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )
    """Default nightly rate for this plan."""

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    min_stay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Minimum stay nights for this rate plan."""

    max_stay: Mapped[int | None] = mapped_column(Integer, nullable=True)

    parent_rate_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("rate_plans.id"), nullable=True
    )
    """Optional parent plan for hierarchical rate structures."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RateDate(Base):
    """A daily rate override for a specific rate plan and date.

    Allows dynamic/seasonal pricing: set a different rate for a specific
    calendar date, overriding the plan's base_rate.
    """

    __tablename__ = "rate_dates"

    id: Mapped[int] = mapped_column(primary_key=True)

    rate_plan_id: Mapped[int] = mapped_column(
        ForeignKey("rate_plans.id"), nullable=False, index=True
    )

    date: Mapped[date] = mapped_column(Date, nullable=False)

    rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    """Nightly rate for this specific date."""

    min_stay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Override minimum stay for this date only."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("rate_plan_id", "date", name="uq_rate_date"),
    )
