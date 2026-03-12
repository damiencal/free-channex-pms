"""ORM models: Invoice, InvoiceItem — billing and folio management."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class Invoice(Base):
    """A guest invoice (folio) for a booking.

    Invoices are auto-created when a booking is confirmed and track all
    charges, taxes, and payments. A shareable public link can be generated
    from the invoice hash.
    """

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)

    invoice_number: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )
    """Sequential invoice number, e.g. "INV-00042"."""

    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False
    )

    guest_id: Mapped[int | None] = mapped_column(ForeignKey("guests.id"), nullable=True)

    guest_name: Mapped[str] = mapped_column(String(255), nullable=False)
    guest_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    """One of: open | paid | void | partially_paid"""

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    public_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    """Opaque token for the guest-facing public invoice link."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InvoiceItem(Base):
    """A line item on an invoice (room charge, extra, tax, discount)."""

    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id"), nullable=False, index=True
    )

    item_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="room_charge"
    )
    """One of: room_charge | extra | tax | discount | service_charge"""

    description: Mapped[str] = mapped_column(String(255), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=Decimal("1")
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    tax_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("tax_types.id"), nullable=True
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
