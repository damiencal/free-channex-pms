"""create resort_submissions table

Revision ID: 005
Revises: 004
Create Date: 2026-02-28

Creates Phase 5 compliance table:
  - resort_submissions — tracks lifecycle of resort booking form submissions
    (pending -> submitted -> confirmed) with FK to bookings and a unique
    constraint ensuring each booking has at most one submission.
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resort_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("submitted_automatically", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_urgent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("confirmation_attached", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(1024), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", name="uq_resort_submission_booking"),
    )


def downgrade() -> None:
    op.drop_table("resort_submissions")
