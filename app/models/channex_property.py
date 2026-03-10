"""ORM model: ChannexProperty — maps Channex property UUIDs to local Property records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class ChannexProperty(Base):
    """Links a Channex.io property UUID to a local Property row.

    Populated by ``POST /api/channex/properties/sync``.
    Used by the reservation sync to resolve ``property_id`` from Channex booking data.
    """

    __tablename__ = "channex_properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id"), nullable=True, index=True
    )
    """FK to the local properties.id. Nullable until explicitly mapped."""

    channex_property_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    """Channex property UUID, e.g. 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'."""

    channex_property_name: Mapped[str] = mapped_column(String(255), nullable=False)
    """Display name from Channex — used for fuzzy matching to local properties."""

    channex_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """Channex property group UUID (if applicable)."""

    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """Timestamp of last successful data sync for this property."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
