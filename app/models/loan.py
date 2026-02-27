from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    """Descriptive name for the loan (e.g., "RV Purchase Loan")."""
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    """FK to accounts.id — the liability account in the chart of accounts."""
    original_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    """Principal balance at loan origination."""
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    """Annual interest rate as a decimal (e.g., 0.0650 = 6.5%)."""
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    """Date the loan was originated."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    account: Mapped["Account"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Account",
    )
