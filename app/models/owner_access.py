"""ORM model: OwnerAccess — token-based read-only portal for property owners."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class OwnerAccess(Base):
    """A read-only access token granting an owner view of their property's data.

    Owners access the portal via ``GET /owner?token=<token>`` — no login
    required. Tokens should be long random UUIDs and rotated periodically.
    """

    __tablename__ = "owner_access"

    id: Mapped[int] = mapped_column(primary_key=True)

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"), nullable=False, index=True
    )

    token: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    """Opaque access token (UUID4 hex). Used as URL query param."""

    owner_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
