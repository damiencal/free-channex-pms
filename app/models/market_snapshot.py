"""ORM model: MarketSnapshot — periodic market data capture."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class MarketSnapshot(Base):
    """Daily snapshot of market-level pricing and occupancy metrics.

    For the MVP, these snapshots are computed from internal booking data.
    Future: enriched with external market data (AirDNA, PriceLabs, etc.)

    property_id=None snapshots represent portfolio-wide aggregates.
    demand_index: relative demand index 0–100 derived from booking velocity.
    source: 'internal' | 'airdna' | 'pricelabs'
    """

    __tablename__ = "market_snapshots"
    __table_args__ = (
        UniqueConstraint("property_id", "snapshot_date", name="uq_market_snapshot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("properties.id"), nullable=True, index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    avg_market_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    median_market_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    market_occupancy_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    market_adr: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    market_revpar: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    supply_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    demand_index: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 3), nullable=True
    )
    """Relative demand index 0–100 derived from booking velocity and lead times."""

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    raw_data_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
