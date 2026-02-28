"""add category/journal_entry_id to bank_transactions; property_id to loans

Revision ID: 004
Revises: 003
Create Date: 2026-02-28

Adds Phase 4 columns to existing tables:
  - bank_transactions.category (VARCHAR(64), nullable) — user-assigned transaction category
  - bank_transactions.journal_entry_id (FK to journal_entries.id, nullable) — expense journal entry link
  - loans.property_id (FK to properties.id, nullable) — per-property loan attribution
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add category to bank_transactions
    op.add_column(
        "bank_transactions",
        sa.Column("category", sa.String(64), nullable=True),
    )

    # 2. Add journal_entry_id to bank_transactions
    op.add_column(
        "bank_transactions",
        sa.Column(
            "journal_entry_id",
            sa.Integer(),
            sa.ForeignKey("journal_entries.id"),
            nullable=True,
        ),
    )

    # 3. Add property_id to loans
    op.add_column(
        "loans",
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("loans", "property_id")
    op.drop_column("bank_transactions", "journal_entry_id")
    op.drop_column("bank_transactions", "category")
