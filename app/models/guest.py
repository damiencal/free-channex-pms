"""ORM model: Guest — unified guest profile (CRM)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class Guest(Base):
    """A guest/customer profile.

    Guest profiles provide a CRM layer: all bookings can be linked to a
    unified guest record for history, preferences, and balance tracking.
    """

    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(primary_key=True)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    guest_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="individual"
    )
    """One of: individual | corporate | vip | group"""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Internal staff notes about guest preferences or history."""

    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    """Outstanding balance / credit on the guest account."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
