"""Make payment.booking_id nullable

Revision ID: 017_payment_booking_nullable
Revises: 016_invoice_booking_nullable
Create Date: 2026-03-11

"""

from alembic import op

revision = "017_payment_booking_nullable"
down_revision = "016_invoice_booking_nullable"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("payments", "booking_id", nullable=True)


def downgrade():
    # Note: this will fail if there are NULL values in the column
    op.alter_column("payments", "booking_id", nullable=False)
