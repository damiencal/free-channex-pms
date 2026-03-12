"""ORM model: MessageTemplate — configurable triggered messaging templates."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class MessageTemplate(Base):
    """A triggered message template.

    Templates fire based on ``trigger_event`` relative to booking dates.
    ``offset_hours`` is signed: negative = before event, positive = after.

    Examples:
      - trigger_event='booking_confirmed', offset_hours=0  → send immediately on booking
      - trigger_event='check_in',          offset_hours=-48 → 2 days before check-in
      - trigger_event='check_out',         offset_hours=24  → 1 day after check-out
    """

    __tablename__ = "message_templates"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    """Human-readable template name shown in the dashboard."""

    trigger_event: Mapped[str] = mapped_column(String(64), nullable=False)
    """One of: booking_confirmed | check_in | check_out | review_request"""

    offset_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Hours relative to trigger_event. Negative = before, positive = after."""

    subject: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    """Email subject line (Jinja2 template). Unused for Channex channel."""

    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    """Jinja2 template body. Variables: guest_name, property_name, check_in_date,
    check_out_date, check_in_time, check_out_time, wifi_password, lock_code, etc."""

    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="channex")
    """Delivery channel. One of: channex | email"""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Whether this template is active and will fire for new bookings."""

    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id"), nullable=True, index=True
    )
    """FK to properties.id. NULL means the template applies to all properties."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
