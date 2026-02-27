from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    """Chart of accounts number (1000–9999)."""
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    """Human-readable account name."""
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    """One of: 'asset', 'liability', 'equity', 'revenue', 'expense'."""
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Whether this account is active and available for journal entries."""

    __table_args__ = (
        CheckConstraint(
            "number >= 1000 AND number <= 9999",
            name="ck_account_number_range",
        ),
    )
