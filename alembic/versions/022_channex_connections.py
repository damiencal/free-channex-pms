"""Add channex_connections table for storing Channex API token connections.

Revision ID: 022
Revises: 021_pricing_fixes
"""

from alembic import op
import sqlalchemy as sa

revision = "022_channex_connections"
down_revision = "021_pricing_fixes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS channex_connections (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(255) NOT NULL,
            api_token   VARCHAR(512) NOT NULL,
            status      VARCHAR(32)  NOT NULL DEFAULT 'active',
            listing_count INTEGER NOT NULL DEFAULT 0,
            last_synced_at TIMESTAMP WITH TIME ZONE,
            created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS channex_connections")
