"""ORM model: Room — individual bookable unit within a property."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class Room(Base):
    """An individual bookable room within a property.

    Rooms have a housekeeping status that is updated by housekeeping staff.
    Each room belongs to a RoomType which drives pricing and availability.
    """

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )

    room_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("room_types.id"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    """Display name, e.g. "Room 101", "Ocean Suite" """

    number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """Room number/identifier, e.g. "101", "2A". """

    floor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """Floor or level, e.g. "1", "Ground", "Penthouse". """

    building: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """Building or wing, e.g. "East Wing", "Annex". """

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="clean")
    """Housekeeping status. One of: clean | dirty | maintenance | out_of_order"""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Whether the room is active and can receive bookings."""

    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Whether the room is visible in the online booking engine."""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Internal notes about the room (e.g. maintenance issues)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
