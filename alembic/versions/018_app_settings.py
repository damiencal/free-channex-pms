"""Add app_settings table

Revision ID: 018_app_settings
Revises: 017_payment_booking_nullable
Create Date: 2026-03-11

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "018_app_settings"
down_revision = "017_payment_booking_nullable"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lead_channel", sa.String(100), nullable=False, server_default="direct"
        ),
        sa.Column(
            "default_check_in_time",
            sa.String(20),
            nullable=False,
            server_default="15:00",
        ),
        sa.Column(
            "default_check_out_time",
            sa.String(20),
            nullable=False,
            server_default="11:00",
        ),
        sa.Column(
            "timezone", sa.String(64), nullable=False, server_default="America/New_York"
        ),
        sa.Column("language", sa.String(20), nullable=False, server_default="en"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("channel_pricing_ratios", JSONB, nullable=False, server_default="{}"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("custom_channels", JSONB, nullable=False, server_default="[]"),
        sa.Column("income_categories", JSONB, nullable=False, server_default="[]"),
        sa.Column("expense_categories", JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )
    # Insert the single settings row with defaults
    op.execute("""
        INSERT INTO app_settings (
            lead_channel, default_check_in_time, default_check_out_time,
            timezone, language, currency,
            channel_pricing_ratios, tags, custom_channels,
            income_categories, expense_categories
        ) VALUES (
            'direct', '15:00', '11:00',
            'America/New_York', 'en', 'USD',
            '{}', '[]', '[]',
            '["Rental Income", "Cleaning Fees", "Late Check-out", "Other Income"]',
            '["Cleaning", "Maintenance", "Utilities", "Supplies", "Management Fees", "Other Expense"]'
        )
    """)
    # Add permissions column to users if not present
    op.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions JSONB NOT NULL DEFAULT '[]'
    """)


def downgrade():
    op.drop_table("app_settings")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS permissions")
