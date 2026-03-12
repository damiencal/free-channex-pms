"""ORM models: CompSet and CompSetProperty — comparable property groups."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class CompSet(Base):
    """A named group of comparable properties for competitive benchmarking.

    Filters are stored as JSON and define criteria like:
      {"bedrooms": 3, "radius_km": 10, "min_price": 100, "max_price": 400}
    """

    __tablename__ = "comp_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )
    """The reference property this comp set is analyzing against."""

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filters_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Filter criteria used to build this comp set."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CompSetProperty(Base):
    """A single property entry within a comp set.

    For MVP, source='internal' links to our own Property records.
    Future: source='airdna' | 'pricelabs' for external competitor data.
    """

    __tablename__ = "comp_set_properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    comp_set_id: Mapped[int] = mapped_column(
        ForeignKey("comp_sets.id"), nullable=False, index=True
    )
    property_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("properties.id"), nullable=True
    )
    """Non-null for internal properties. Null for external comparables."""

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    property_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    external_listing_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )

    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)
    amenities_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    avg_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    avg_occupancy: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True
    )

    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
