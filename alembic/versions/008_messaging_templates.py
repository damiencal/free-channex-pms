"""008 — Messaging templates and triggered message logs.

Creates two tables:
  - message_templates       — configurable triggered messaging templates
  - triggered_message_logs  — audit log for each message send attempt
"""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # message_templates
    # ------------------------------------------------------------------
    op.create_table(
        "message_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("trigger_event", sa.String(64), nullable=False),
        sa.Column("offset_hours", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subject", sa.String(512), nullable=False, server_default=""),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False, server_default="channex"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id"),
            nullable=True,
        ),
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
        "ix_message_templates_property_id",
        "message_templates",
        ["property_id"],
    )

    # ------------------------------------------------------------------
    # triggered_message_logs
    # ------------------------------------------------------------------
    op.create_table(
        "triggered_message_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("message_templates.id"),
            nullable=False,
        ),
        sa.Column(
            "booking_id",
            sa.Integer(),
            sa.ForeignKey("bookings.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rendered_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_triggered_message_logs_template_id",
        "triggered_message_logs",
        ["template_id"],
    )
    op.create_index(
        "ix_triggered_message_logs_booking_id",
        "triggered_message_logs",
        ["booking_id"],
    )


def downgrade() -> None:
    op.drop_table("triggered_message_logs")
    op.drop_table("message_templates")
