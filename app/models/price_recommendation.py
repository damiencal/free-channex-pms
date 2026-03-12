"""ORM model: PriceRecommendation — AI-generated daily price and min-stay suggestions."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class PriceRecommendation(Base):
    """A pricing recommendation for a specific property and date.

    Generated nightly by the HLP (Hyper Local Pulse) pricing engine.
    Operators review and accept/reject recommendations. Accepted recommendations
    are written to RateDate and pushed to Channex (ARI sync).

    status: 'pending' | 'accepted' | 'rejected' | 'expired'
      - pending:  Awaiting operator decision
      - accepted: Operator approved; price has been applied to RateDates
      - rejected: Operator declined with optional reason
      - expired:  Recommendation date is in the past without a decision

    confidence: 0.0–1.0 score indicating data quality / prediction reliability.
    """

    __tablename__ = "price_recommendations"
    __table_args__ = (
        UniqueConstraint("property_id", "date", name="uq_price_rec_property_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    recommended_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    recommended_min_stay: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # --- Input signals (stored for explainability) ---
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    demand_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=Decimal("0.500")
    )
    supply_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=Decimal("0.500")
    )
    seasonal_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("1.0")
    )
    event_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("1.0")
    )
    weekend_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("1.0")
    )
    last_minute_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("1.0")
    )
    early_bird_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("1.0")
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=Decimal("0.500")
    )

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    accepted_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
