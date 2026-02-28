"""Resort submission tracking model.

Tracks the lifecycle of resort booking form submissions:
pending -> submitted -> confirmed

Each booking has at most one submission (unique constraint on booking_id).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class ResortSubmission(Base):
    __tablename__ = "resort_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")

    submitted_automatically: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    is_urgent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    confirmation_attached: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_resort_submission_booking"),
    )
