from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db import Base


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    """Unique transaction identifier from the bank export (e.g., Mercury CSV)."""
    date: Mapped[date] = mapped_column(Date, nullable=False)
    """Transaction date (calendar date, no time component)."""
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    """Transaction description/memo from bank export."""
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    """Transaction amount. Positive for credits, negative for debits."""
    reconciliation_status: Mapped[str] = mapped_column(String(32), server_default="unmatched")
    """Reconciliation state. One of: 'unmatched', 'matched', 'confirmed', 'disputed'."""
    raw_platform_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    """Original row from the bank CSV, stored as JSON for audit trail."""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
