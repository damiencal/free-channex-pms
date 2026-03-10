"""ORM model: ChannexReview — guest reviews received via the Channex API."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class ChannexReview(Base):
    """A guest review synced from Channex.io.

    ``channex_review_id`` is UNIQUE — used for idempotent upserts on sync.
    After the operator responds via ``POST /api/channex/reviews/{id}/respond``,
    ``status`` transitions to 'responded' and ``response_text`` is recorded.
    """

    __tablename__ = "channex_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)

    channex_review_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    """Channex-assigned review UUID. Used as dedup key on sync."""

    channex_booking_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    """Channex booking UUID this review is for (may be absent for older reviews)."""

    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )
    """FK to local bookings.id — resolved after booking sync. Nullable until resolved."""

    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id"), nullable=True
    )
    """FK to local properties.id — denormalized for quick filtering."""

    guest_name: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    """Guest name as reported by Channex."""

    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Numeric rating (e.g. 1–5) if provided by the channel."""

    review_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Guest review body text."""

    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="new")
    """Review lifecycle state. One of: 'new', 'responded'."""

    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Host response text, populated after a successful respond call."""

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """When the guest left the review."""

    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """When the host response was submitted."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
