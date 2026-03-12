"""013 — Feature parity: rooms, guests, rates, invoices, taxes, extras, audit.

Adds all tables required for full miniCal feature parity:
  - room_types, rooms
  - guests
  - booking_groups
  - rate_plans, rate_dates
  - tax_types
  - extras, booking_extras
  - invoices, invoice_items
  - payments
  - booking_audit_log
  - night_audit_log
  - custom_field_definitions, custom_field_values

Also alters bookings table to add:
  - booking_state, adults, children, notes
  - guest_email, guest_phone (promoted from raw_platform_data)
  - guest_id (FK → guests), room_id (FK → rooms), group_id (FK → booking_groups)
"""

import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # room_types
    # -------------------------------------------------------------------------
    op.create_table(
        "room_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("max_occupancy", sa.Integer(), nullable=True),
        sa.Column("base_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_stay", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_room_types_property_id", "room_types", ["property_id"])

    # -------------------------------------------------------------------------
    # rooms
    # -------------------------------------------------------------------------
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("room_type_id", sa.Integer(), sa.ForeignKey("room_types.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("number", sa.String(20), nullable=True),
        sa.Column("floor", sa.String(20), nullable=True),
        sa.Column("building", sa.String(100), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="clean"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rooms_property_id", "rooms", ["property_id"])
    op.create_index("ix_rooms_room_type_id", "rooms", ["room_type_id"])

    # -------------------------------------------------------------------------
    # guests
    # -------------------------------------------------------------------------
    op.create_table(
        "guests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("guest_type", sa.String(32), nullable=False, server_default="individual"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_guests_email", "guests", ["email"])

    # -------------------------------------------------------------------------
    # booking_groups
    # -------------------------------------------------------------------------
    op.create_table(
        "booking_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_booking_groups_property_id", "booking_groups", ["property_id"])

    # -------------------------------------------------------------------------
    # Alter bookings — add new columns
    # -------------------------------------------------------------------------
    op.add_column("bookings", sa.Column("booking_state", sa.String(32), nullable=False, server_default="reservation"))
    op.add_column("bookings", sa.Column("adults", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("bookings", sa.Column("children", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bookings", sa.Column("notes", sa.String(2048), nullable=True))
    op.add_column("bookings", sa.Column("guest_email", sa.String(255), nullable=True))
    op.add_column("bookings", sa.Column("guest_phone", sa.String(50), nullable=True))
    op.add_column("bookings", sa.Column("guest_id", sa.Integer(), sa.ForeignKey("guests.id"), nullable=True))
    op.add_column("bookings", sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=True))
    op.add_column("bookings", sa.Column("group_id", sa.Integer(), sa.ForeignKey("booking_groups.id"), nullable=True))
    op.create_index("ix_bookings_guest_id", "bookings", ["guest_id"])
    op.create_index("ix_bookings_room_id", "bookings", ["room_id"])

    # -------------------------------------------------------------------------
    # rate_plans
    # -------------------------------------------------------------------------
    op.create_table(
        "rate_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("room_type_id", sa.Integer(), sa.ForeignKey("room_types.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_rate", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("min_stay", sa.Integer(), nullable=True),
        sa.Column("max_stay", sa.Integer(), nullable=True),
        sa.Column("parent_rate_plan_id", sa.Integer(), sa.ForeignKey("rate_plans.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rate_plans_property_id", "rate_plans", ["property_id"])

    # -------------------------------------------------------------------------
    # rate_dates
    # -------------------------------------------------------------------------
    op.create_table(
        "rate_dates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rate_plan_id", sa.Integer(), sa.ForeignKey("rate_plans.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("min_stay", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("rate_plan_id", "date", name="uq_rate_date"),
    )
    op.create_index("ix_rate_dates_rate_plan_id", "rate_dates", ["rate_plan_id"])

    # -------------------------------------------------------------------------
    # tax_types
    # -------------------------------------------------------------------------
    op.create_table(
        "tax_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("rate", sa.Numeric(8, 6), nullable=False, server_default="0"),
        sa.Column("is_inclusive", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_flat", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("flat_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -------------------------------------------------------------------------
    # extras
    # -------------------------------------------------------------------------
    op.create_table(
        "extras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("price_type", sa.String(20), nullable=False, server_default="per_stay"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extras_property_id", "extras", ["property_id"])

    # -------------------------------------------------------------------------
    # booking_extras
    # -------------------------------------------------------------------------
    op.create_table(
        "booking_extras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("extra_id", sa.Integer(), sa.ForeignKey("extras.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_booking_extras_booking_id", "booking_extras", ["booking_id"])

    # -------------------------------------------------------------------------
    # invoices
    # -------------------------------------------------------------------------
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_number", sa.String(20), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("guest_id", sa.Integer(), sa.ForeignKey("guests.id"), nullable=True),
        sa.Column("guest_name", sa.String(255), nullable=False),
        sa.Column("guest_email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("public_token", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"], unique=True)
    op.create_index("ix_invoices_booking_id", "invoices", ["booking_id"])
    op.create_index("ix_invoices_public_token", "invoices", ["public_token"], unique=True)

    # -------------------------------------------------------------------------
    # invoice_items
    # -------------------------------------------------------------------------
    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("item_type", sa.String(32), nullable=False, server_default="room_charge"),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Numeric(8, 2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_type_id", sa.Integer(), sa.ForeignKey("tax_types.id"), nullable=True),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])

    # -------------------------------------------------------------------------
    # payments
    # -------------------------------------------------------------------------
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", sa.String(32), nullable=False, server_default="cash"),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])
    op.create_index("ix_payments_booking_id", "payments", ["booking_id"])

    # -------------------------------------------------------------------------
    # booking_audit_log
    # -------------------------------------------------------------------------
    op.create_table(
        "booking_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_booking_audit_booking_id", "booking_audit_log", ["booking_id"])

    # -------------------------------------------------------------------------
    # night_audit_log
    # -------------------------------------------------------------------------
    op.create_table(
        "night_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("audit_date", sa.Date(), nullable=False),
        sa.Column("selling_date", sa.Date(), nullable=False),
        sa.Column("performed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_night_audit_property_id", "night_audit_log", ["property_id"])

    # -------------------------------------------------------------------------
    # custom_field_definitions
    # -------------------------------------------------------------------------
    op.create_table(
        "custom_field_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=True),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("field_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("options", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -------------------------------------------------------------------------
    # custom_field_values
    # -------------------------------------------------------------------------
    op.create_table(
        "custom_field_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("field_id", sa.Integer(), sa.ForeignKey("custom_field_definitions.id"), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("field_id", "entity_type", "entity_id", name="uq_custom_field_value"),
    )
    op.create_index("ix_custom_field_values_field_id", "custom_field_values", ["field_id"])
    op.create_index("ix_custom_field_values_entity", "custom_field_values", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("custom_field_values")
    op.drop_table("custom_field_definitions")
    op.drop_table("night_audit_log")
    op.drop_table("booking_audit_log")
    op.drop_table("payments")
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.drop_table("booking_extras")
    op.drop_table("extras")
    op.drop_table("tax_types")
    op.drop_table("rate_dates")
    op.drop_table("rate_plans")
    op.drop_column("bookings", "group_id")
    op.drop_column("bookings", "room_id")
    op.drop_column("bookings", "guest_id")
    op.drop_column("bookings", "guest_phone")
    op.drop_column("bookings", "guest_email")
    op.drop_column("bookings", "notes")
    op.drop_column("bookings", "children")
    op.drop_column("bookings", "adults")
    op.drop_column("bookings", "booking_state")
    op.drop_table("booking_groups")
    op.drop_table("guests")
    op.drop_table("rooms")
    op.drop_table("room_types")
