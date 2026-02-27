"""create properties table

Revision ID: 001
Revises:
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_properties_slug", "properties", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_properties_slug", table_name="properties")
    op.drop_table("properties")
