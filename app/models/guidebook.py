"""ORM model: Guidebook — per-property digital guest guidebook."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class Guidebook(Base):
    """Digital guest guidebook for a property.

    ``sections`` is a JSON array of section objects:
      [{"title": str, "body": str (markdown), "icon": str, "order": int}, ...]

    When ``is_published=True`` the guidebook is accessible at
    ``GET /public/guide/{property_slug}`` without authentication.
    """

    __tablename__ = "guidebooks"

    id: Mapped[int] = mapped_column(primary_key=True)

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, unique=True, index=True
    )
    """One guidebook per property (enforced by UNIQUE constraint)."""

    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Guest Guide"
    )

    sections: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    """Ordered list of section dicts: [{title, body, icon, order}, ...]"""

    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """When True the guidebook is publicly accessible."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
