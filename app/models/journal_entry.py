from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    """Calendar date of the journal entry."""
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    """Human-readable description of the transaction."""
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    """Category of source. E.g. 'booking_payout', 'expense', 'loan_payment', 'reversal', 'adjustment'."""
    source_id: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    """Idempotency key. Unique per logical transaction to prevent duplicate journal entries."""
    property_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("properties.id"), nullable=True
    )
    """FK to properties.id. None for shared/cross-property entries."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    lines: Mapped[list["JournalLine"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "JournalLine",
        back_populates="entry",
        cascade="all, delete-orphan",
    )
