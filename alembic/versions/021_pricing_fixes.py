"""Add weekend_min_stay to pricing_rules; fix min_stay column alias.

Revision ID: 021
Revises: 020_booking_sites
"""

from alembic import op
import sqlalchemy as sa

revision = "021_pricing_fixes"
down_revision = "020_booking_sites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add weekend_min_stay column
    op.add_column(
        "pricing_rules",
        sa.Column("weekend_min_stay", sa.Integer, nullable=True, server_default="2"),
    )
    # Add min_stay alias column (min_stay_default already exists but API uses min_stay)
    # We use a view-level fix in the API instead; just add weekend column here


def downgrade() -> None:
    op.drop_column("pricing_rules", "weekend_min_stay")
