"""Channex.io messaging service.

Fetches inbound/outbound messages from Channex and syncs them to the
local ``channex_messages`` table. Also provides an outbound send function
with a dedicated rate limiter (max 2 concurrent sends).

Message direction is inferred from the Channex ``senderRole`` field:
  - ``"traveler"`` / ``"guest"`` → ``"inbound"``
  - ``"owner"`` / ``"host"`` / ``"manager"`` → ``"outbound"``
  - Anything else → ``"inbound"`` (conservative default)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.channex.client import ChannexClient
from app.models.channex_message import ChannexMessage

log = structlog.get_logger()

# Separate semaphore for outbound messages — max 2 concurrent sends
_SEND_SEMAPHORE = asyncio.Semaphore(2)

_GUEST_ROLES = {"traveler", "guest", "customer"}
_HOST_ROLES = {"owner", "host", "manager", "hotel", "property"}


# ---------------------------------------------------------------------------
# Direction helpers
# ---------------------------------------------------------------------------


def _infer_direction(msg: dict) -> str:
    role = str(
        msg.get("sender_role") or msg.get("senderRole") or msg.get("author_role") or ""
    ).lower()
    if role in _HOST_ROLES:
        return "outbound"
    if role in _GUEST_ROLES:
        return "inbound"
    # Fall back to ``author_type`` if present
    atype = str(msg.get("author_type") or "").lower()
    if atype in _HOST_ROLES:
        return "outbound"
    return "inbound"


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


async def list_messages(
    client: ChannexClient,
    channex_booking_id: str | None = None,
    since: datetime | None = None,
) -> list[dict]:
    """Fetch messages from Channex, optionally filtered by booking or time.

    Returns a flat list of message dicts with all attributes merged.
    """
    params: dict = {}
    if channex_booking_id:
        params["booking_id"] = channex_booking_id
    if since:
        params["inserted_at[gte]"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    raw_items = await client.paginate("/messages", params=params)
    messages = []
    for item in raw_items:
        if isinstance(item, dict):
            attrs = item.get("attributes", item)
            attrs["id"] = item.get("id", attrs.get("id", ""))
            messages.append(attrs)
    return messages


async def send_message(
    client: ChannexClient,
    channex_booking_id: str,
    body: str,
) -> dict:
    """Send an outbound message to a guest via Channex.

    Rate-limited to 2 concurrent outbound sends. Returns the created
    message dict from the Channex API response.
    """
    async with _SEND_SEMAPHORE:
        result = await client.post(
            "/messages",
            json={
                "message": {
                    "booking_id": channex_booking_id,
                    "message": body,
                }
            },
        )
    return result


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def sync_messages_to_db(
    db: Session,
    messages: list[dict],
    local_booking_map: dict[str, int] | None = None,
    local_property_map: dict[str, int | None] | None = None,
) -> dict[str, int]:
    """Upsert a list of Channex messages into ``channex_messages``.

    Args:
        db: SQLAlchemy session.
        messages: List of Channex message dicts.
        local_booking_map: Optional ``{channex_booking_id: local_booking.id}`` map
            for resolving the ``booking_id`` FK. Pass None to skip resolution.
        local_property_map: Optional ``{channex_booking_id: property_id}`` map.

    Returns:
        ``{"upserted": N, "skipped": N}``.
    """
    upserted = skipped = 0

    for msg in messages:
        msg_id = str(msg.get("id") or msg.get("message_id") or "")
        if not msg_id:
            skipped += 1
            continue

        channex_booking_id = str(
            msg.get("booking_id") or msg.get("channex_booking_id") or ""
        )

        direction = _infer_direction(msg)
        body = str(msg.get("message") or msg.get("body") or msg.get("text") or "")
        guest_name = str(msg.get("guest_name") or msg.get("author_name") or "")

        sent_at_raw = (
            msg.get("inserted_at") or msg.get("sent_at") or msg.get("created_at")
        )
        sent_at: datetime | None = None
        if sent_at_raw:
            try:
                sent_at = datetime.fromisoformat(
                    str(sent_at_raw).replace("Z", "+00:00")
                )
            except ValueError:
                pass

        local_booking_id: int | None = None
        local_property_id: int | None = None
        if local_booking_map and channex_booking_id:
            local_booking_id = local_booking_map.get(channex_booking_id)
        if local_property_map and channex_booking_id:
            local_property_id = local_property_map.get(channex_booking_id)

        stmt = (
            pg_insert(ChannexMessage)
            .values(
                channex_message_id=msg_id,
                channex_booking_id=channex_booking_id,
                booking_id=local_booking_id,
                property_id=local_property_id,
                guest_name=guest_name,
                direction=direction,
                body=body,
                sent_at=sent_at,
            )
            .on_conflict_do_update(
                index_elements=["channex_message_id"],
                set_={
                    "body": body,
                    "direction": direction,
                    "guest_name": guest_name,
                    "sent_at": sent_at,
                    "booking_id": local_booking_id,
                    "property_id": local_property_id,
                },
            )
        )
        try:
            db.execute(stmt)
            upserted += 1
        except Exception as exc:
            log.warning("channex_message_sync_failed", msg_id=msg_id, error=str(exc))
            skipped += 1

    db.commit()
    log.info("channex_messages_synced", upserted=upserted, skipped=skipped)
    return {"upserted": upserted, "skipped": skipped}


async def sync_all_messages(
    db: Session,
    client: ChannexClient,
    since: datetime | None = None,
) -> dict[str, int]:
    """Pull all messages from Channex and sync to DB.

    Falls back to seeding booking-derived messages when the Channex messaging
    API is unavailable (e.g. plan limitations — /messages returns 404/403).
    """
    try:
        messages = await list_messages(client, since=since)
        if messages:
            return sync_messages_to_db(db, messages)
    except Exception as exc:
        log.warning(
            "channex_messages_api_unavailable",
            error=str(exc),
            hint="Falling back to booking-derived inbox messages",
        )

    # Fallback: seed inbox threads from bookings data
    return await _seed_messages_from_bookings(db, client)


async def _seed_messages_from_bookings(
    db: Session,
    client: ChannexClient,
) -> dict[str, int]:
    """Create one inbox thread per Channex booking as a fallback when the
    messaging API endpoint is not available for the account."""
    from app.models.booking import Booking

    try:
        all_bookings: list[dict] = []
        page = 1
        import math

        while True:
            r = await client.get(
                "/bookings", params={"pagination[limit]": 50, "pagination[page]": page}
            )
            data = r.get("data", [])
            meta = r.get("meta", {})
            all_bookings.extend(data)
            total = meta.get("total", 0)
            limit = meta.get("limit", 50)
            total_pages = math.ceil(total / limit) if limit else 1
            if page >= total_pages:
                break
            page += 1
    except Exception as exc:
        log.error("channex_booking_list_failed", error=str(exc))
        return {"upserted": 0, "skipped": 0}

    from sqlalchemy import text

    upserted = 0
    for b in all_bookings:
        attrs = b.get("attributes", b)
        bid = str(b.get("id") or attrs.get("booking_id") or attrs.get("id") or "")
        if not bid:
            continue

        cust = attrs.get("customer") or {}
        first_name = str(cust.get("name") or "")
        last_name = str(cust.get("surname") or "")
        guest_name = f"{first_name} {last_name}".strip() or "Guest"
        notes_text = str(attrs.get("notes") or "")
        ota = str(attrs.get("ota_name") or "Channel")
        reservation_code = str(attrs.get("ota_reservation_code") or "")
        arrival = str(attrs.get("arrival_date") or "")
        departure = str(attrs.get("departure_date") or "")
        status = str(attrs.get("status") or "")

        body = f"New {status} booking via {ota} (#{reservation_code})\n"
        body += f"Check-in: {arrival}, Check-out: {departure}\n"
        if notes_text.strip():
            body += f"Notes: {notes_text.strip()[:300]}"

        inserted_at_raw = str(attrs.get("inserted_at") or "")
        try:
            sent_at: datetime = (
                datetime.fromisoformat(inserted_at_raw.replace("Z", "+00:00"))
                if inserted_at_raw
                else datetime.now(timezone)
            )
        except Exception:
            sent_at = datetime.now(timezone.utc)

        # Resolve local booking and property IDs
        local_booking = db.execute(
            text(
                "SELECT id, property_id FROM bookings WHERE platform_booking_id = :bid"
            ),
            {"bid": bid},
        ).fetchone()
        local_booking_id: int | None = local_booking[0] if local_booking else None
        property_id: int | None = local_booking[1] if local_booking else None

        try:
            db.execute(
                text("""
                    INSERT INTO channex_messages
                        (channex_message_id, channex_booking_id, booking_id, property_id,
                         guest_name, direction, body, sent_at)
                    VALUES (:msg_id, :cbid, :bid, :pid, :gname, 'inbound', :body, :sent_at)
                    ON CONFLICT (channex_message_id) DO UPDATE SET
                        guest_name = EXCLUDED.guest_name,
                        body = EXCLUDED.body,
                        booking_id = EXCLUDED.booking_id,
                        property_id = EXCLUDED.property_id
                """),
                {
                    "msg_id": f"booking_{bid}",
                    "cbid": bid,
                    "bid": local_booking_id,
                    "pid": property_id,
                    "gname": guest_name,
                    "body": body.strip(),
                    "sent_at": sent_at,
                },
            )
            upserted += 1
        except Exception as exc:
            log.warning("channex_message_seed_failed", booking_id=bid, error=str(exc))

    db.commit()
    log.info("channex_messages_seeded_from_bookings", upserted=upserted)
    return {"upserted": upserted, "skipped": 0}
