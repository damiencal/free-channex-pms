"""ORM model: NightAuditLog — record of nightly end-of-day audit runs."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class NightAuditLog(Base):
    """Record of each night audit (end-of-day) operation.

    The night audit closes the current business day and advances the
    selling date. This table stores the audit history.
    """

    __tablename__ = "night_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )

    audit_date: Mapped[date] = mapped_column(Date, nullable=False)
    """The business date being closed out."""

    selling_date: Mapped[date] = mapped_column(Date, nullable=False)
    """The new selling date after the audit (audit_date + 1)."""

    performed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
