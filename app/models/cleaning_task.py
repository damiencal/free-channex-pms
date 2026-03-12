"""ORM model: CleaningTask — housekeeping tasks auto-created on booking."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class CleaningTask(Base):
    """A housekeeping/cleaning task associated with a booking checkout.

    Tasks are auto-created when a booking is ingested, scheduled for the
    checkout date. They can be assigned to a team member and tracked
    through ``status``.
    """

    __tablename__ = "cleaning_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )
    """FK to the booking that triggered this task. Nullable for manual tasks."""

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )

    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    """Date the cleaning should occur — typically the checkout date."""

    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """Name or email of the person assigned to this task."""

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )
    """One of: pending | in_progress | completed | skipped"""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Optional notes for the cleaner."""

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
