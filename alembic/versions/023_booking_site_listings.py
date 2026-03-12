"""add booking_site_listings table

Revision ID: 023_booking_site_listings
Revises: 022_channex_connections
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa

revision = "023_booking_site_listings"
down_revision = "022_channex_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "booking_site_listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "site_id",
            sa.Integer(),
            sa.ForeignKey("booking_sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint("site_id", "property_id", name="uq_bsl_site_property"),
    )
    op.create_index("ix_bsl_site_id", "booking_site_listings", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_bsl_site_id", table_name="booking_site_listings")
    op.drop_table("booking_site_listings")
