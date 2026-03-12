"""012 — Owner access tokens for the read-only owner portal.

Creates the ``owner_access`` table mapping per-property opaque tokens
to owner contact details. Tokens are presented as URL query params
(e.g. GET /owner?token=<uuid>).
"""

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "owner_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id"),
            nullable=False,
        ),
        sa.Column("token", sa.String(128), nullable=False),
        sa.Column("owner_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("owner_email", sa.String(255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
    op.create_index("ix_owner_access_token", "owner_access", ["token"], unique=True)
    op.create_index("ix_owner_access_property_id", "owner_access", ["property_id"])


def downgrade() -> None:
    op.drop_table("owner_access")
