"""Channex.io reservations service.

Fetches bookings from the Channex API and syncs them into the local
``bookings`` table (the same table used by CSV-imported bookings).

Channex bookings are stored with:
  - ``platform`` = normalised OTA name ("airbnb", "vrbo", "rvshare", …)
                   or "channex" for direct bookings / unknown channels
  - ``platform_booking_id = <channex booking UUID>``
  - ``raw_platform_data`` = full Channex JSON for audit trail

This lets Channex-synced bookings co-exist with—and potentially match—
CSV-imported bookings from the same OTA, since both use identical platform
identifiers.

Idempotency is guaranteed by the existing unique constraint on
``(platform, platform_booking_id)`` in the bookings table.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.channex.client import ChannexClient
from app.channex.properties import resolve_local_property_id
from app.models.booking import Booking

log = structlog.get_logger()

_FALLBACK_PLATFORM = "channex"

# Map Channex channel_code values to the platform identifiers used in the
# bookings table (must match what the CSV adapters write).
_CHANNEL_CODE_MAP: dict[str, str] = {
    # Airbnb
    "airbnb": "airbnb",
    "airbnb_api": "airbnb",
    "airbnbofficial": "airbnb",
    # VRBO / HomeAway family
    "vrbo": "vrbo",
    "homeaway": "vrbo",
    "homeaway_api": "vrbo",
    "vrboapi": "vrbo",
    # RVshare
    "rvshare": "rvshare",
    # Expedia (standalone channel — NOT vrbo)
    "expedia": "expedia",
    "expedia_api": "expedia",
    "expediavacationrentals": "expedia",
    "expedia_vacation_rentals": "expedia",
    "hotels.com": "expedia",  # Hotels.com is an Expedia Group brand
    "hotelscom": "expedia",
    # Booking.com
    "booking": "booking",
    "bookingcom": "booking",
    "booking.com": "booking",
}


def _resolve_platform(channex_booking: dict) -> str:
    """Return the normalised platform name for a Channex booking.

    Reads ``channel_code`` (or ``ota_name`` as fallback) from the booking dict,
    lower-cases it, and maps it to a canonical platform identifier.  Falls back
    to ``"channex"`` for direct / unrecognised channels.
    """
    raw = (
        channex_booking.get("channel_code")
        or channex_booking.get("ota_name")
        or channex_booking.get("channel")
        or ""
    )
    normalised = str(raw).lower().strip().replace(" ", "_")
    return _CHANNEL_CODE_MAP.get(normalised, _FALLBACK_PLATFORM)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


async def list_bookings(
    client: ChannexClient,
    updated_since: datetime | None = None,
    channex_property_id: str | None = None,
    statuses: list[str] | None = None,
) -> list[dict]:
    """Fetch bookings from Channex, optionally filtered by update time or property.

    Args:
        client: Authenticated Channex client.
        updated_since: If set, only return bookings modified after this datetime.
        channex_property_id: Filter to a specific Channex property UUID.
        statuses: List of booking statuses to include (e.g. ['new', 'modified']).
                  Defaults to ['new', 'modified', 'confirmed'].
    """
    params: dict = {}
    if updated_since:
        params["updated_at[gte]"] = updated_since.strftime("%Y-%m-%dT%H:%M:%SZ")
    if channex_property_id:
        params["property_id"] = channex_property_id
    if statuses:
        for i, s in enumerate(statuses):
            params[f"status[{i}]"] = s

    raw_items = await client.paginate("/bookings", params=params)
    bookings = []
    for item in raw_items:
        if isinstance(item, dict):
            attrs = item.get("attributes", item)
            attrs["id"] = item.get("id", attrs.get("id", ""))
            bookings.append(attrs)
    return bookings


async def get_booking(client: ChannexClient, channex_booking_id: str) -> dict:
    """Fetch a single Channex booking by UUID."""
    raw = await client.get(f"/bookings/{channex_booking_id}")
    if isinstance(raw, dict):
        attrs = raw.get("attributes", raw)
        attrs["id"] = raw.get("id", attrs.get("id", ""))
        return attrs
    return raw


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_date(val: object) -> date | None:
    if not val:
        return None
    if isinstance(val, date):
        return val
    s = str(val)
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
    return None


def _parse_amount(val: object) -> Decimal:
    try:
        return Decimal(str(val)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return Decimal("0.00")


def _extract_booking_fields(channex_booking: dict) -> dict:
    """Extract canonical booking fields from a Channex booking dict.

    Handles both flat (attributes merged) and nested (JSON:API) structures.
    """
    rooms = channex_booking.get("rooms", []) or []
    first_room = rooms[0] if rooms else {}

    check_in = _parse_date(
        channex_booking.get("arrival_date")
        or channex_booking.get("check_in_date")
        or first_room.get("arrival_date")
    )
    check_out = _parse_date(
        channex_booking.get("departure_date")
        or channex_booking.get("check_out_date")
        or first_room.get("departure_date")
    )

    # Amount: prefer total_price, fall back to amount/price
    amount = _parse_amount(
        channex_booking.get("total_price")
        or channex_booking.get("amount")
        or channex_booking.get("price")
        or "0"
    )

    # Guest name from nested customer/guest dict or flat fields
    customer = channex_booking.get("customer") or channex_booking.get("guest") or {}
    first_name = (
        customer.get("name")  # Channex uses "name" for first name
        or customer.get("first_name")
        or channex_booking.get("guest_first_name")
        or ""
    )
    last_name = (
        customer.get("surname")  # Channex uses "surname" for last name
        or customer.get("last_name")
        or channex_booking.get("guest_last_name")
        or ""
    )
    guest_name = f"{first_name} {last_name}".strip() or "Unknown"

    channex_property_id = str(
        channex_booking.get("property_id")
        or channex_booking.get("property", {}).get("id")
        or ""
    )

    return {
        "channex_booking_id": str(channex_booking.get("id", "")),
        "platform": _resolve_platform(channex_booking),
        "guest_name": guest_name,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "net_amount": amount,
        "channex_property_id": channex_property_id,
    }


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def sync_booking_to_db(
    db: Session,
    channex_booking: dict,
) -> dict[str, str]:
    """Upsert a single Channex booking into the local ``bookings`` table.

    Returns a status dict: ``{"action": "inserted" | "updated" | "skipped", "id": "..."}``.
    """
    fields = _extract_booking_fields(channex_booking)
    booking_id = fields["channex_booking_id"]

    if not booking_id:
        return {"action": "skipped", "id": "", "reason": "missing channex booking id"}

    if not fields["check_in_date"] or not fields["check_out_date"]:
        return {
            "action": "skipped",
            "id": booking_id,
            "reason": "missing check-in or check-out date",
        }

    local_property_id = resolve_local_property_id(db, fields["channex_property_id"])

    if local_property_id is None:
        log.debug(
            "channex_booking_skipped_no_property",
            booking_id=booking_id,
            channex_property_id=fields["channex_property_id"],
        )
        return {
            "action": "skipped",
            "id": booking_id,
            "reason": "channex property not linked to a local property",
        }

    # Build the upsert statement (PostgreSQL ON CONFLICT DO UPDATE)
    stmt = (
        pg_insert(Booking)
        .values(
            platform=fields["platform"],
            platform_booking_id=booking_id,
            property_id=local_property_id,  # guaranteed non-None above
            guest_name=fields["guest_name"],
            check_in_date=fields["check_in_date"],
            check_out_date=fields["check_out_date"],
            net_amount=fields["net_amount"],
            reconciliation_status="unmatched",
            raw_platform_data=channex_booking,
            updated_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_update(
            constraint="uq_booking_platform_id",
            set_={
                "guest_name": fields["guest_name"],
                "check_in_date": fields["check_in_date"],
                "check_out_date": fields["check_out_date"],
                "net_amount": fields["net_amount"],
                "property_id": local_property_id,
                "raw_platform_data": channex_booking,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        .returning(Booking.id)
    )

    try:
        result = db.execute(stmt)
        db.flush()
        row = result.fetchone()
        action = "upserted"
        inserted_id = row[0] if row else 0
        log.debug(
            "channex_booking_synced",
            booking_id=booking_id,
            action=action,
            local_id=inserted_id,
        )
        return {"action": action, "id": booking_id, "local_id": str(inserted_id)}
    except Exception as exc:
        log.warning(
            "channex_booking_sync_failed",
            booking_id=booking_id,
            error=str(exc),
        )
        db.rollback()
        return {"action": "failed", "id": booking_id, "reason": str(exc)}


async def sync_all_reservations(
    db: Session,
    client: ChannexClient,
    since: datetime | None = None,
    channex_property_id: str | None = None,
) -> dict[str, int]:
    """Pull all bookings from Channex and sync each to the local DB.

    Args:
        db: SQLAlchemy session.
        client: Authenticated Channex client.
        since: Only sync bookings updated after this datetime (incremental).
        channex_property_id: Limit sync to one Channex property.

    Returns:
        Summary dict: ``{"upserted": N, "skipped": N, "failed": N}``.
    """
    bookings = await list_bookings(
        client,
        updated_since=since,
        channex_property_id=channex_property_id,
    )

    upserted = skipped = failed = 0
    for booking in bookings:
        result = sync_booking_to_db(db, booking)
        if result["action"] == "upserted":
            upserted += 1
        elif result["action"] == "failed":
            failed += 1
        else:
            skipped += 1

    db.commit()
    log.info(
        "channex_reservations_synced",
        upserted=upserted,
        skipped=skipped,
        failed=failed,
        since=since.isoformat() if since else "all",
    )
    return {"upserted": upserted, "skipped": skipped, "failed": failed}
