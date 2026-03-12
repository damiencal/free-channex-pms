"""ORM models: CustomFieldDefinition and CustomFieldValue.

Allows admins to define arbitrary extra fields for bookings and guests.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class CustomFieldDefinition(Base):
    """Admin-defined custom field for bookings or guests."""

    __tablename__ = "custom_field_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)

    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id"), nullable=True
    )
    """If None, the field applies to all properties."""

    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    """One of: booking | guest"""

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    """Internal key used to reference this field."""

    label: Mapped[str] = mapped_column(String(100), nullable=False)
    """Human-readable label shown in the UI."""

    field_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text"
    )
    """One of: text | number | date | select | checkbox | textarea"""

    options: Mapped[str | None] = mapped_column(Text, nullable=True)
    """JSON array of option strings for 'select' fields, e.g. '["Yes","No","N/A"]'."""

    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Display order in the UI (lower = shown first)."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CustomFieldValue(Base):
    """A value for a custom field on a specific booking or guest record."""

    __tablename__ = "custom_field_values"

    id: Mapped[int] = mapped_column(primary_key=True)

    field_id: Mapped[int] = mapped_column(
        ForeignKey("custom_field_definitions.id"), nullable=False, index=True
    )

    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    """One of: booking | guest"""

    entity_id: Mapped[int] = mapped_column(nullable=False, index=True)
    """ID of the booking or guest record."""

    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "field_id", "entity_type", "entity_id", name="uq_custom_field_value"
        ),
    )
