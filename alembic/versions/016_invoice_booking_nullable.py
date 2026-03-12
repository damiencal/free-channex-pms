"""Make invoices.booking_id nullable (standalone invoices support)

Revision ID: 016_invoice_booking_nullable
Revises: 656cee3e984b
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa

revision = "016_invoice_booking_nullable"
down_revision = "1bf0ed7491fa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("invoices", "booking_id", nullable=True)


def downgrade() -> None:
    op.alter_column("invoices", "booking_id", nullable=False)
