"""ORM model: ChannexMessage — guest messages exchanged via the Channex API."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class ChannexMessage(Base):
    """A guest message tracked through Channex.io (inbound or outbound).

    Messages are synced from the Channex API and written here for display
    in the Actions tab. Outbound messages sent via ``POST /api/channex/messages``
    are also persisted here immediately.

    ``channex_message_id`` is UNIQUE — used for idempotent upserts on sync.
    """

    __tablename__ = "channex_messages"

    id: Mapped[int] = mapped_column(primary_key=True)

    channex_message_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    """Channex-assigned message UUID. Used as dedup key on sync."""

    channex_booking_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    """Channex booking UUID this message belongs to."""

    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )
    """FK to local bookings.id — resolved after booking sync. Nullable until resolved."""

    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id"), nullable=True
    )
    """FK to local properties.id — denormalized for quick filtering."""

    guest_name: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    """Guest name at time of message."""

    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    """Either 'inbound' (from guest) or 'outbound' (from host)."""

    body: Mapped[str] = mapped_column(Text, nullable=False)
    """Message text content."""

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """When the message was sent (per Channex)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
