"""009 — Guest guidebooks.

Creates the ``guidebooks`` table: one digital guest guidebook per property,
with JSON ``sections`` and a ``is_published`` flag for public access.
"""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guidebooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "title", sa.String(255), nullable=False, server_default="Guest Guide"
        ),
        sa.Column("sections", sa.JSON(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_guidebooks_property_id", "guidebooks", ["property_id"], unique=True
    )


def downgrade() -> None:
    op.drop_table("guidebooks")
