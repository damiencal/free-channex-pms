from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("journal_entries.id"), nullable=False, index=True
    )
    """FK to journal_entries.id."""
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False, index=True
    )
    """FK to accounts.id."""
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    """Signed amount. Positive = debit, negative = credit."""
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """Optional line-level description."""

    entry: Mapped["JournalEntry"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "JournalEntry",
        back_populates="lines",
    )
    account: Mapped["Account"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Account",
    )
