"""ORM model: ChannexWebhookEvent — raw Channex webhook events for audit/replay."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class ChannexWebhookEvent(Base):
    """A raw webhook event payload received from Channex.io.

    Every inbound webhook is persisted here *before* processing. This provides:
    - An audit trail of all events
    - Idempotency (deduplicate on ``channex_event_id``)
    - Replay capability (status can be reset to 'received' to reprocess)

    Processing is idempotent: calling ``process_webhook`` with the same
    ``channex_event_id`` twice results in only one DB row (upsert).
    """

    __tablename__ = "channex_webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True)

    channex_event_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True, index=True
    )
    """Channex-supplied event UUID for deduplication. May be absent for some event types."""

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    """Event type string, e.g. 'booking.new', 'message.new', 'review.new'."""

    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    """Full deserialized JSON payload received from Channex."""

    raw_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Raw request body bytes as string — preserved for signature re-verification."""

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="received"
    )
    """Processing state. One of: 'received', 'processed', 'failed'."""

    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    """Set on status='failed' describing what went wrong."""

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    """Timestamp when this app received the event."""

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """Timestamp when the event was successfully dispatched."""
