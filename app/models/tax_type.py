"""ORM model: TaxType — tax definitions for charges and invoices."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class TaxType(Base):
    """A tax type that can be applied to invoice line items.

    Supports percentage rates, flat amounts, inclusive vs exclusive,
    and tiered brackets.
    """

    __tablename__ = "tax_types"

    id: Mapped[int] = mapped_column(primary_key=True)

    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id"), nullable=True, index=True
    )
    """If None, applies globally; otherwise property-specific."""

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    """e.g. "State Tax", "City Tourism Tax", "Service Charge" """

    rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6), nullable=False, default=Decimal("0")
    )
    """Percentage rate as a decimal, e.g. 0.12 for 12%."""

    is_inclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """If True, the tax is included in the stated price (not added on top)."""

    is_flat: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """If True, use flat_amount instead of percentage rate."""

    flat_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    """Fixed tax amount per night/stay (used when is_flat=True)."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
