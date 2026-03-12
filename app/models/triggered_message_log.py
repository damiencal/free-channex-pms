"""ORM model: TriggeredMessageLog — audit trail for triggered message sends."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class TriggeredMessageLog(Base):
    """Log entry for a triggered message that was scheduled or sent."""

    __tablename__ = "triggered_message_logs"

    id: Mapped[int] = mapped_column(primary_key=True)

    template_id: Mapped[int] = mapped_column(
        ForeignKey("message_templates.id"), nullable=False, index=True
    )
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    """One of: scheduled | sent | failed | skipped"""

    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """When the message is/was scheduled to send."""

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """When the message was actually sent."""

    rendered_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    """The fully rendered message body (after Jinja2 rendering)."""

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Error detail if status='failed'."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
