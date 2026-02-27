from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db import Base


class ReconciliationMatch(Base):
    __tablename__ = "reconciliation_matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id"), nullable=False, unique=True
    )
    """FK to bookings.id. Unique: one match per booking."""
    bank_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("bank_transactions.id"), nullable=False, unique=True
    )
    """FK to bank_transactions.id. Unique: one match per bank transaction."""
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    """Match status. One of: 'matched' (auto), 'confirmed' (operator), 'needs_review' (ambiguous), 'rejected' (operator)."""
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    """Timestamp when the match record was created."""
    confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    """Operator identifier who confirmed or rejected the match. None for auto-matched."""
