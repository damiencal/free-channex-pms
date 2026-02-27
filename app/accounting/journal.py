"""Journal entry builder with balance enforcement and idempotent upsert."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine


@dataclass
class LineSpec:
    """Specification for a single debit or credit line in a journal entry."""

    account_id: int
    amount: Decimal
    """Positive = debit, negative = credit."""
    description: str | None = field(default=None)


def create_journal_entry(
    db: Session,
    entry_date: date,
    description: str,
    source_type: str,
    source_id: str,
    lines: list[LineSpec],
    property_id: int | None = None,
) -> JournalEntry | None:
    """Create a balanced, idempotent journal entry.

    Args:
        db: SQLAlchemy session (caller is responsible for commit).
        entry_date: Calendar date of the entry.
        description: Human-readable description.
        source_type: Category, e.g. 'booking_payout', 'expense', 'loan_payment'.
        source_id: Idempotency key — unique per logical transaction.
        lines: List of LineSpec objects. Must sum to zero and have at least 2 lines.
        property_id: Optional FK to properties.id; None for shared entries.

    Returns:
        The created JournalEntry, or None if source_id already exists (idempotent skip).

    Raises:
        ValueError: If lines do not balance (sum != 0) or fewer than 2 lines provided.
    """
    # --- Balance enforcement (must happen FIRST, before any DB interaction) ---
    if len(lines) < 2:
        raise ValueError(
            f"Journal entry requires at least 2 lines, got {len(lines)}."
        )

    total = sum(line.amount for line in lines)
    if total != Decimal("0"):
        raise ValueError(
            f"Journal entry lines must sum to zero. Got: {total} (source_id={source_id!r})."
        )

    # --- Idempotent insert via ON CONFLICT DO NOTHING ---
    stmt = (
        pg_insert(JournalEntry)
        .values(
            entry_date=entry_date,
            description=description,
            source_type=source_type,
            source_id=source_id,
            property_id=property_id,
        )
        .on_conflict_do_nothing(index_elements=["source_id"])
    )
    result = db.execute(stmt)

    if result.rowcount == 0:
        # Entry already exists — idempotent skip
        return None

    # Fetch the inserted entry to get its auto-generated id
    entry = db.query(JournalEntry).filter_by(source_id=source_id).one()

    # Create journal lines
    for spec in lines:
        line = JournalLine(
            entry_id=entry.id,
            account_id=spec.account_id,
            amount=spec.amount,
            description=spec.description,
        )
        db.add(line)

    db.flush()
    return entry
