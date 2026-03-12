"""ORM model: BookingAuditLog — change history for bookings."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class BookingAuditLog(Base):
    """Immutable audit trail of every change made to a booking.

    Every field modification, state transition, and payment action is
    recorded here for accountability and dispute resolution.
    """

    __tablename__ = "booking_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)

    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id"), nullable=False, index=True
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    """Staff member who performed the action; None for system actions."""

    action: Mapped[str] = mapped_column(String(64), nullable=False)
    """e.g. 'field_changed', 'checked_in', 'checked_out', 'payment_added'"""

    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """The database field that changed, e.g. 'net_amount', 'booking_state'."""

    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
