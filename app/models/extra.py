"""ORM models: Extra and BookingExtra — add-on services management."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class Extra(Base):
    """An available add-on service or amenity.

    Examples: Breakfast, Parking, Airport Transfer, Late Checkout,
    Baby Cot, Bicycle Rental.
    """

    __tablename__ = "extras"

    id: Mapped[int] = mapped_column(primary_key=True)

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )

    price_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="per_stay"
    )
    """One of: per_stay | per_night | per_person | per_person_per_night"""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BookingExtra(Base):
    """An extra/add-on attached to a specific booking."""

    __tablename__ = "booking_extras"

    id: Mapped[int] = mapped_column(primary_key=True)

    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id"), nullable=False, index=True
    )

    extra_id: Mapped[int] = mapped_column(
        ForeignKey("extras.id"), nullable=False
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    """Price per unit at time of adding (snapshot to protect against future changes)."""

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    """Total: quantity × unit_price."""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
