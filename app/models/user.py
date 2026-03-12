"""ORM model: User — team member with role-based access."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class User(Base):
    """A team member account.

    Passwords are stored as bcrypt hashes — never plaintext.
    Roles control what portions of the app are accessible.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    """bcrypt hash of the user's password."""

    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    role: Mapped[str] = mapped_column(String(32), nullable=False, default="admin")
    """One of: admin | manager | housekeeper | owner | accountant"""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
