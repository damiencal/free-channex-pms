"""ORM model: RoomType — categories of rooms (SNG, DBL, SUITE, etc.)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class RoomType(Base):
    """A category of room within a property.

    Examples: Single, Double, Suite, Deluxe.
    Room types drive rate plans and inventory allocation.
    """

    __tablename__ = "room_types"

    id: Mapped[int] = mapped_column(primary_key=True)

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    """e.g. "Standard Single", "Double Deluxe", "Suite" """

    code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """Short code used as identifier, e.g. "SNG", "DBL", "STE". """

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    max_occupancy: Mapped[int | None] = mapped_column(nullable=True)
    """Maximum number of guests allowed in this room type."""

    base_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    """Default nightly rate when no rate plan override applies."""

    min_stay: Mapped[int | None] = mapped_column(nullable=True)
    """Minimum nights required when booking this room type."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
