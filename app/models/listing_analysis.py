"""ORM model: ListingAnalysis — AI listing audit results from Ollama."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class ListingAnalysis(Base):
    """AI-generated audit of a property listing's quality and optimization opportunities.

    Scores are 0–100 integers (higher = better):
      - overall_score: weighted composite
      - title_score: title clarity, keywords, searchability
      - description_score: completeness, tone, highlights
      - photos_score: photo count adequacy (actual quality requires manual review)
      - amenities_score: completeness vs typical comp set
      - pricing_score: price competitiveness vs market

    recommendations_json: list of {priority, category, finding, action, impact}
    listing_data_json: snapshot of the listing data that was analyzed
    """

    __tablename__ = "listing_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    overall_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    title_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    photos_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amenities_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pricing_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    recommendations_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    """[{priority: 'high'|'medium'|'low', category: str, finding: str, action: str, impact: str}]"""

    listing_data_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Snapshot of listing data used for the analysis."""

    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
