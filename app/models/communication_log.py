"""Communication log model for guest messaging tracking.

Tracks the lifecycle of guest messages per booking:
- Airbnb welcome: native_configured (Airbnb handles natively)
- Airbnb pre-arrival: pending -> sent
- VRBO/RVshare welcome: pending -> sent (operator confirms manual send)
- VRBO/RVshare pre-arrival: pending -> sent (operator confirms manual send)

One row per (booking, message_type). UniqueConstraint enforces this.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    """FK to bookings.id — one log entry per (booking, message_type)."""

    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    """Message type: 'welcome' or 'pre_arrival'."""

    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    """Booking platform: 'airbnb', 'vrbo', or 'rvshare'."""

    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    """Message lifecycle status.
    Values: 'native_configured' (Airbnb welcome), 'pending', 'sent'.
    VRBO/RVshare: 'pending' until operator confirms manual send -> 'sent'.
    Airbnb pre-arrival: 'pending' until system sends -> 'sent'.
    """

    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """When the pre-arrival message is scheduled to fire. NULL for welcome messages
    and native_configured entries. Used for APScheduler job rebuild on restart."""

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """Timestamp when message was sent (Airbnb) or operator confirmed send (VRBO/RVshare)."""

    operator_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """When the operator notification email was sent (VRBO/RVshare only)."""

    rendered_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Full rendered message text. Stored for:
    - VRBO/RVshare: copy-paste into platform messaging
    - All platforms: audit trail of what was sent
    NULL for Airbnb welcome (native — system never renders it)."""

    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    """Last error message if sending/notification failed."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("booking_id", "message_type", name="uq_comm_log_booking_type"),
    )
