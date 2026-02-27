from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db import Base


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    """Platform identifier. One of: "airbnb", "vrbo", "rvshare"."""
    platform_booking_id: Mapped[str] = mapped_column(String(128), nullable=False)
    """Booking/reservation ID from the platform. Unique per platform."""
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False)
    """FK to properties.id — resolved from property_slug during import."""
    guest_name: Mapped[str] = mapped_column(String(255), nullable=False)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    """Calendar date only (no time component)."""
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    """Calendar date only (no time component)."""
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    """Net payout amount after platform fees."""
    reconciliation_status: Mapped[str] = mapped_column(String(32), server_default="unmatched")
    """Reconciliation state. One of: 'unmatched', 'matched', 'confirmed', 'disputed'."""
    raw_platform_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    """Original row from the platform CSV, stored as JSON for audit trail."""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("platform", "platform_booking_id", name="uq_booking_platform_id"),)
