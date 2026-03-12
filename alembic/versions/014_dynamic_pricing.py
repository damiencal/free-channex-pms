"""014 — Dynamic Pricing, Portfolio Analytics, Market Intelligence, Listing Optimizer.

Adds all tables for the AI-powered dynamic pricing and analytics system:
  - market_events          — configurable local events/holidays/seasons calendar
  - pricing_rules          — per-property pricing strategy configuration
  - price_recommendations  — AI-generated price + min-stay suggestions
  - comp_sets              — comparable property groups
  - comp_set_properties    — properties within a comp set
  - market_snapshots       — periodic market metric captures
  - portfolio_metrics      — daily cached KPI computations
  - listing_analyses       — AI listing audit results

Also extends properties table with geo/size columns synced from YAML config:
  - address, city, state, country, latitude, longitude
  - bedrooms, bathrooms, max_guests, property_type, amenities_json, timezone
"""

import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Extend properties table with geo/size/config columns
    # -------------------------------------------------------------------------
    op.add_column("properties", sa.Column("address", sa.String(500), nullable=True))
    op.add_column("properties", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("properties", sa.Column("state", sa.String(100), nullable=True))
    op.add_column("properties", sa.Column("country", sa.String(100), nullable=True))
    op.add_column("properties", sa.Column("latitude", sa.Numeric(10, 7), nullable=True))
    op.add_column(
        "properties", sa.Column("longitude", sa.Numeric(10, 7), nullable=True)
    )
    op.add_column("properties", sa.Column("bedrooms", sa.Integer(), nullable=True))
    op.add_column("properties", sa.Column("bathrooms", sa.Numeric(4, 1), nullable=True))
    op.add_column("properties", sa.Column("max_guests", sa.Integer(), nullable=True))
    op.add_column(
        "properties",
        sa.Column(
            "property_type", sa.String(50), nullable=True, server_default="villa"
        ),
    )
    op.add_column("properties", sa.Column("amenities_json", sa.JSON(), nullable=True))
    op.add_column("properties", sa.Column("timezone", sa.String(64), nullable=True))

    # -------------------------------------------------------------------------
    # market_events — local demand calendar (holidays, events, seasons)
    # -------------------------------------------------------------------------
    op.create_table(
        "market_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=True
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "event_type", sa.String(32), nullable=False, server_default="local_event"
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "demand_modifier", sa.Numeric(5, 4), nullable=False, server_default="1.0"
        ),
        sa.Column("recurrence", sa.String(16), nullable=False, server_default="none"),
        sa.Column("description", sa.Text(), nullable=True),
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
    op.create_index("ix_market_events_property_id", "market_events", ["property_id"])
    op.create_index("ix_market_events_start_date", "market_events", ["start_date"])
    op.create_index("ix_market_events_end_date", "market_events", ["end_date"])

    # -------------------------------------------------------------------------
    # pricing_rules — per-property smart pricing configuration
    # -------------------------------------------------------------------------
    op.create_table(
        "pricing_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("strategy", sa.String(16), nullable=False, server_default="dynamic"),
        sa.Column(
            "base_price_source",
            sa.String(16),
            nullable=False,
            server_default="rate_plan",
        ),
        sa.Column("min_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_stay_default", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("max_stay_default", sa.Integer(), nullable=True),
        sa.Column(
            "weekend_markup_pct",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="15.00",
        ),
        sa.Column(
            "orphan_day_discount_pct",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="20.00",
        ),
        sa.Column(
            "last_minute_window_days", sa.Integer(), nullable=False, server_default="7"
        ),
        sa.Column(
            "last_minute_discount_pct",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="15.00",
        ),
        sa.Column(
            "early_bird_window_days", sa.Integer(), nullable=False, server_default="90"
        ),
        sa.Column(
            "early_bird_discount_pct",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="10.00",
        ),
        sa.Column(
            "demand_sensitivity",
            sa.Numeric(3, 2),
            nullable=False,
            server_default="0.50",
        ),
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
    op.create_index("ix_pricing_rules_property_id", "pricing_rules", ["property_id"])

    # -------------------------------------------------------------------------
    # price_recommendations — AI-generated pricing suggestions
    # -------------------------------------------------------------------------
    op.create_table(
        "price_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("recommended_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("recommended_min_stay", sa.Integer(), nullable=True),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "demand_score", sa.Numeric(4, 3), nullable=False, server_default="0.500"
        ),
        sa.Column(
            "supply_score", sa.Numeric(4, 3), nullable=False, server_default="0.500"
        ),
        sa.Column(
            "seasonal_factor", sa.Numeric(5, 4), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "event_factor", sa.Numeric(5, 4), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "weekend_factor", sa.Numeric(5, 4), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "last_minute_factor", sa.Numeric(5, 4), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "early_bird_factor", sa.Numeric(5, 4), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "confidence", sa.Numeric(4, 3), nullable=False, server_default="0.500"
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("accepted_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("property_id", "date", name="uq_price_rec_property_date"),
    )
    op.create_index(
        "ix_price_recommendations_property_id", "price_recommendations", ["property_id"]
    )
    op.create_index("ix_price_recommendations_date", "price_recommendations", ["date"])
    op.create_index(
        "ix_price_recommendations_status", "price_recommendations", ["status"]
    )

    # -------------------------------------------------------------------------
    # comp_sets — comparable property groups
    # -------------------------------------------------------------------------
    op.create_table(
        "comp_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("filters_json", sa.JSON(), nullable=True),
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
    op.create_index("ix_comp_sets_property_id", "comp_sets", ["property_id"])

    # -------------------------------------------------------------------------
    # comp_set_properties — property members of a comp set
    # -------------------------------------------------------------------------
    op.create_table(
        "comp_set_properties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "comp_set_id", sa.Integer(), sa.ForeignKey("comp_sets.id"), nullable=False
        ),
        sa.Column(
            "property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=True
        ),
        sa.Column("source", sa.String(32), nullable=False, server_default="internal"),
        sa.Column("property_name", sa.String(200), nullable=True),
        sa.Column("external_listing_id", sa.String(128), nullable=True),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Numeric(4, 1), nullable=True),
        sa.Column("amenities_json", sa.JSON(), nullable=True),
        sa.Column("avg_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("avg_occupancy", sa.Numeric(5, 4), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_comp_set_properties_comp_set_id", "comp_set_properties", ["comp_set_id"]
    )

    # -------------------------------------------------------------------------
    # market_snapshots — periodic market metric snapshots
    # -------------------------------------------------------------------------
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=True
        ),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("avg_market_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("median_market_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("market_occupancy_pct", sa.Numeric(5, 4), nullable=True),
        sa.Column("market_adr", sa.Numeric(10, 2), nullable=True),
        sa.Column("market_revpar", sa.Numeric(10, 2), nullable=True),
        sa.Column("supply_count", sa.Integer(), nullable=True),
        sa.Column("demand_index", sa.Numeric(6, 3), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="internal"),
        sa.Column("raw_data_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("property_id", "snapshot_date", name="uq_market_snapshot"),
    )
    op.create_index(
        "ix_market_snapshots_snapshot_date", "market_snapshots", ["snapshot_date"]
    )
    op.create_index(
        "ix_market_snapshots_property_id", "market_snapshots", ["property_id"]
    )

    # -------------------------------------------------------------------------
    # portfolio_metrics — daily cached KPI computations
    # -------------------------------------------------------------------------
    op.create_table(
        "portfolio_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False
        ),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("occupancy_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("adr", sa.Numeric(10, 2), nullable=True),
        sa.Column("revpar", sa.Numeric(10, 2), nullable=True),
        sa.Column("trevpar", sa.Numeric(10, 2), nullable=True),
        sa.Column("revenue", sa.Numeric(12, 2), nullable=True),
        sa.Column("expenses", sa.Numeric(12, 2), nullable=True),
        sa.Column("available_nights", sa.Integer(), nullable=True),
        sa.Column("booked_nights", sa.Integer(), nullable=True),
        sa.Column("booking_count", sa.Integer(), nullable=True),
        sa.Column("booking_pace", sa.Numeric(6, 3), nullable=True),
        sa.Column("booking_pace_ly", sa.Numeric(6, 3), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("property_id", "metric_date", name="uq_portfolio_metric"),
    )
    op.create_index(
        "ix_portfolio_metrics_property_id", "portfolio_metrics", ["property_id"]
    )
    op.create_index(
        "ix_portfolio_metrics_metric_date", "portfolio_metrics", ["metric_date"]
    )

    # -------------------------------------------------------------------------
    # listing_analyses — AI listing audit results from Ollama
    # -------------------------------------------------------------------------
    op.create_table(
        "listing_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False
        ),
        sa.Column(
            "analyzed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("title_score", sa.Integer(), nullable=True),
        sa.Column("description_score", sa.Integer(), nullable=True),
        sa.Column("photos_score", sa.Integer(), nullable=True),
        sa.Column("amenities_score", sa.Integer(), nullable=True),
        sa.Column("pricing_score", sa.Integer(), nullable=True),
        sa.Column("recommendations_json", sa.JSON(), nullable=True),
        sa.Column("listing_data_json", sa.JSON(), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_listing_analyses_property_id", "listing_analyses", ["property_id"]
    )
    op.create_index(
        "ix_listing_analyses_analyzed_at", "listing_analyses", ["analyzed_at"]
    )


def downgrade() -> None:
    op.drop_table("listing_analyses")
    op.drop_table("portfolio_metrics")
    op.drop_table("market_snapshots")
    op.drop_table("comp_set_properties")
    op.drop_table("comp_sets")
    op.drop_table("price_recommendations")
    op.drop_table("pricing_rules")
    op.drop_table("market_events")

    op.drop_column("properties", "timezone")
    op.drop_column("properties", "amenities_json")
    op.drop_column("properties", "property_type")
    op.drop_column("properties", "max_guests")
    op.drop_column("properties", "bathrooms")
    op.drop_column("properties", "bedrooms")
    op.drop_column("properties", "longitude")
    op.drop_column("properties", "latitude")
    op.drop_column("properties", "country")
    op.drop_column("properties", "state")
    op.drop_column("properties", "city")
    op.drop_column("properties", "address")
