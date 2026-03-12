"""010 — Cleaning tasks.

Creates the ``cleaning_tasks`` table for housekeeping task management.
Tasks are auto-created from bookings (checkout date = scheduled_date).
"""

import sqlalchemy as sa
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cleaning_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.Integer(),
            sa.ForeignKey("bookings.id"),
            nullable=True,
        ),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id"),
            nullable=False,
        ),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_cleaning_tasks_booking_id", "cleaning_tasks", ["booking_id"])
    op.create_index("ix_cleaning_tasks_property_id", "cleaning_tasks", ["property_id"])
    op.create_index(
        "ix_cleaning_tasks_scheduled_date", "cleaning_tasks", ["scheduled_date"]
    )
    op.create_index("ix_cleaning_tasks_status", "cleaning_tasks", ["status"])


def downgrade() -> None:
    op.drop_table("cleaning_tasks")
