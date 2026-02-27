from datetime import datetime
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db import Base


class ImportRun(Base):
    __tablename__ = "import_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    """Platform the CSV was imported from. One of: "airbnb", "vrbo", "rvshare", "mercury"."""
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    """Original filename of the uploaded CSV."""
    archive_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    """Absolute path to the archived copy of the CSV file."""
    inserted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    """Number of new records inserted during this import run."""
    updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    """Number of existing records updated (upserted) during this import run."""
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    """Number of rows skipped (duplicates, missing property match, etc.)."""
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    """Timestamp when this import run completed."""
