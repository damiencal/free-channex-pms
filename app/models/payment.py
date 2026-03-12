"""ORM model: Payment — record of a payment against an invoice."""

from __future__ import annotations

from datetime import date, datetime

from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class Payment(Base):
    """A payment applied against an invoice.

    Multiple partial payments can be applied to an invoice. Supports
    cash, card, bank transfer, cheque, etc.
    """

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id"), nullable=False, index=True
    )

    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    """Payment amount. Positive = payment received; negative = refund."""

    payment_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default="cash"
    )
    """One of: cash | credit_card | debit_card | bank_transfer | check | other"""

    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """Transaction reference, confirmation number, or cheque number."""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    payment_date: Mapped[date] = mapped_column(Date, nullable=False)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
