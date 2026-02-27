from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    """Calendar date on which the expense was incurred."""
    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id"), nullable=True
    )
    """FK to properties.id. None indicates a shared (cross-property) expense."""
    attribution: Mapped[str] = mapped_column(String(32), nullable=False)
    """Who the expense is attributed to. One of: 'jay', 'minnie', 'shared'."""
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    """Schedule E-aligned expense category. Must be one of EXPENSE_CATEGORIES."""
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    """Expense amount in USD. Always positive."""
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    """Human-readable description of the expense."""
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """Optional vendor or payee name."""
    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id"), nullable=True
    )
    """FK to journal_entries.id. Set after journal entry creation."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
