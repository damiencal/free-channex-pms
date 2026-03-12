"""Create booking_sites table.

Revision ID: 020
Revises: 019
"""

from alembic import op
import sqlalchemy as sa

revision = "020_booking_sites"
down_revision = "019_automation_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "booking_sites",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("type", sa.Text, nullable=False, server_default="hosted"),
        sa.Column("domain", sa.Text, nullable=True),
        sa.Column("custom_domain", sa.Text, nullable=True),
        sa.Column("listing_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("hero_title", sa.Text, nullable=True),
        sa.Column("hero_subtitle", sa.Text, nullable=True),
        sa.Column("site_logo_url", sa.Text, nullable=True),
        sa.Column("contact_phone", sa.Text, nullable=True),
        sa.Column("contact_email", sa.Text, nullable=True),
        sa.Column("seo_title", sa.Text, nullable=True),
        sa.Column("seo_description", sa.Text, nullable=True),
        sa.Column("seo_keywords", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("booking_sites")
