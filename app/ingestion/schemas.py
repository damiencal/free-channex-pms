"""Pydantic schemas for canonical ingestion records.

Each platform adapter produces one of these canonical records.
The normalizer maps property_slug to property_id before persistence.
"""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class BookingRecord(BaseModel):
    """Canonical booking record produced by all platform adapters.

    Adapters for Airbnb, VRBO, and RVshare each parse their CSV format
    and return a list of these records. The normalizer resolves property_slug
    to a property_id using PropertyConfig.listing_slug_map before upsert.
    """

    platform: str
    """Platform source. One of: "airbnb", "vrbo", "rvshare"."""
    platform_booking_id: str
    """Booking/reservation ID from the platform. Used for idempotent upsert."""
    property_slug: str
    """Property slug resolved by the adapter from listing_slug_map. Normalizer maps to property_id."""
    guest_name: str
    check_in_date: date
    check_out_date: date
    net_amount: Decimal = Field(decimal_places=2)
    """Net payout amount after platform fees."""
    raw_platform_data: dict | None = None
    """Original CSV row as dict for audit trail."""


class BankTransactionRecord(BaseModel):
    """Canonical bank transaction record produced by Mercury adapter.

    Parsed from Mercury CSV exports. Stored in bank_transactions table
    for reconciliation against platform payouts.
    """

    transaction_id: str
    """Unique transaction ID from bank export. Used for idempotent upsert."""
    date: date
    description: str | None = None
    amount: Decimal = Field(decimal_places=2)
    """Transaction amount. Positive for credits, negative for debits."""
    raw_platform_data: dict | None = None
    """Original CSV row as dict for audit trail."""


class RVshareEntryRequest(BaseModel):
    """Request body for manual RVshare booking entry.

    RVshare does not export CSVs in the same format as Airbnb/VRBO.
    Operators enter bookings manually via this API endpoint.
    """

    confirmation_code: str
    """RVshare confirmation code. Used as platform_booking_id."""
    guest_name: str
    check_in_date: date
    check_out_date: date
    net_amount: Decimal
    property_slug: str
    """Property slug identifying which property this booking belongs to."""
    notes: str | None = None
    """Optional operator notes about this booking."""
