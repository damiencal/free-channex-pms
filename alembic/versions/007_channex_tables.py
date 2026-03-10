"""007 — Channex.io PMS integration tables.

Creates four tables supporting the Channex.io integration:

  - channex_properties   — Maps Channex property UUIDs to local Property rows.
  - channex_messages     — Guest messages synced from / sent via Channex.
  - channex_reviews      — Guest reviews synced from Channex.
  - channex_webhook_events — Raw webhook event payloads for audit and replay.
"""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # channex_properties
    # ------------------------------------------------------------------
    op.create_table(
        "channex_properties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id"),
            nullable=True,
        ),
        sa.Column("channex_property_id", sa.String(64), nullable=False),
        sa.Column("channex_property_name", sa.String(255), nullable=False),
        sa.Column("channex_group_id", sa.String(64), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_channex_properties_channex_property_id",
        "channex_properties",
        ["channex_property_id"],
        unique=True,
    )
    op.create_index(
        "ix_channex_properties_property_id",
        "channex_properties",
        ["property_id"],
    )

    # ------------------------------------------------------------------
    # channex_messages
    # ------------------------------------------------------------------
    op.create_table(
        "channex_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channex_message_id", sa.String(128), nullable=False),
        sa.Column("channex_booking_id", sa.String(128), nullable=False),
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
            nullable=True,
        ),
        sa.Column(
            "guest_name",
            sa.String(255),
            nullable=False,
            server_default="",
        ),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_channex_messages_channex_message_id",
        "channex_messages",
        ["channex_message_id"],
        unique=True,
    )
    op.create_index(
        "ix_channex_messages_channex_booking_id",
        "channex_messages",
        ["channex_booking_id"],
    )
    op.create_index(
        "ix_channex_messages_booking_id",
        "channex_messages",
        ["booking_id"],
    )

    # ------------------------------------------------------------------
    # channex_reviews
    # ------------------------------------------------------------------
    op.create_table(
        "channex_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channex_review_id", sa.String(128), nullable=False),
        sa.Column("channex_booking_id", sa.String(128), nullable=True),
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
            nullable=True,
        ),
        sa.Column(
            "guest_name",
            sa.String(255),
            nullable=False,
            server_default="",
        ),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="new",
        ),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_channex_reviews_channex_review_id",
        "channex_reviews",
        ["channex_review_id"],
        unique=True,
    )
    op.create_index(
        "ix_channex_reviews_channex_booking_id",
        "channex_reviews",
        ["channex_booking_id"],
    )
    op.create_index(
        "ix_channex_reviews_booking_id",
        "channex_reviews",
        ["booking_id"],
    )

    # ------------------------------------------------------------------
    # channex_webhook_events
    # ------------------------------------------------------------------
    op.create_table(
        "channex_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channex_event_id", sa.String(128), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("raw_body", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="received",
        ),
        sa.Column("error_message", sa.String(1024), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_channex_webhook_events_channex_event_id",
        "channex_webhook_events",
        ["channex_event_id"],
        unique=True,
        postgresql_where=sa.text("channex_event_id IS NOT NULL"),
    )
    op.create_index(
        "ix_channex_webhook_events_event_type",
        "channex_webhook_events",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_table("channex_webhook_events")
    op.drop_table("channex_reviews")
    op.drop_table("channex_messages")
    op.drop_table("channex_properties")
