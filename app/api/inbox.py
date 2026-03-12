"""Unified inbox API.

Aggregates Channex messages into conversation threads grouped by
``channex_booking_id``, enriched with booking and property context.
Also provides an AI reply suggestion endpoint backed by Ollama.

Routes:
  GET  /api/inbox/threads                                — list threads
  GET  /api/inbox/threads/{channex_booking_id}/messages  — thread history
  POST /api/inbox/threads/{channex_booking_id}/ai-suggest — AI reply
  POST /api/inbox/threads/{channex_booking_id}/send      — send message
  POST /api/inbox/sync                                   — trigger message sync
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.channex.client import ChannexClient, get_channex_client
from app.channex.exceptions import ChannexAPIError
from app.channex.messaging import send_message, sync_all_messages
from app.config import get_config
from app.db import get_db
from app.inbox.ai import generate_reply_suggestion
from app.models.booking import Booking
from app.models.channex_message import ChannexMessage
from app.models.property import Property

log = structlog.get_logger()
router = APIRouter(prefix="/api/inbox", tags=["inbox"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _require_channex_client() -> ChannexClient:
    config = get_config()
    if not config.channex_api_key:
        raise HTTPException(
            status_code=503,
            detail="Channex integration not configured. Set CHANNEX_API_KEY in .env.",
        )
    return get_channex_client()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/threads")
def list_threads(
    property_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List conversation threads sorted by most-recent message time.

    Each thread represents all messages for a single Channex booking.
    ``unread_count`` is the number of inbound messages that arrived after
    the last outbound reply (heuristic for 'needs response').
    """
    # Use DISTINCT ON to get exactly one row per booking (the latest message),
    # avoiding duplicate rows when multiple messages share the same sent_at.
    where_clause = ""
    params: dict = {"limit": limit}
    if property_id is not None:
        where_clause = "WHERE property_id = :property_id"
        params["property_id"] = property_id

    sql = text(f"""
        SELECT * FROM (
            SELECT DISTINCT ON (channex_booking_id)
                channex_booking_id,
                guest_name,
                property_id,
                booking_id,
                sent_at AS last_message_at,
                COUNT(*) OVER (PARTITION BY channex_booking_id) AS message_count
            FROM channex_messages
            {where_clause}
            ORDER BY channex_booking_id, sent_at DESC
        ) t
        ORDER BY last_message_at DESC NULLS LAST
        LIMIT :limit
    """)
    rows = db.execute(sql, params).mappings().all()

    # Build enriched response
    result = []
    for row in rows:
        booking_info: dict = {}
        if row.booking_id:
            b = db.query(Booking).filter_by(id=row.booking_id).first()
            if b:
                booking_info = {
                    "check_in_date": b.check_in_date.isoformat(),
                    "check_out_date": b.check_out_date.isoformat(),
                    "platform": b.platform,
                    "net_amount": str(b.net_amount),
                }

        property_name = None
        if row.property_id:
            p = db.query(Property).filter_by(id=row.property_id).first()
            if p:
                property_name = p.display_name

        # Unread = inbound messages after the last outbound message
        last_outbound_at = (
            db.query(func.max(ChannexMessage.sent_at))
            .filter_by(channex_booking_id=row.channex_booking_id, direction="outbound")
            .scalar()
        )
        unread_q = db.query(func.count(ChannexMessage.id)).filter_by(
            channex_booking_id=row.channex_booking_id, direction="inbound"
        )
        if last_outbound_at:
            unread_q = unread_q.filter(ChannexMessage.sent_at > last_outbound_at)
        unread_count = unread_q.scalar() or 0

        result.append(
            {
                "channex_booking_id": row.channex_booking_id,
                "guest_name": row.guest_name,
                "property_id": row.property_id,
                "property_name": property_name,
                "booking_id": row.booking_id,
                "last_message_at": (
                    row.last_message_at.isoformat() if row.last_message_at else None
                ),
                "message_count": row.message_count,
                "unread_count": unread_count,
                **booking_info,
            }
        )

    return result


@router.get("/threads/{channex_booking_id}/messages")
def get_thread_messages(
    channex_booking_id: str,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return all messages for a thread in chronological order."""
    messages = (
        db.query(ChannexMessage)
        .filter_by(channex_booking_id=channex_booking_id)
        .order_by(ChannexMessage.sent_at.asc())
        .all()
    )
    return [
        {
            "id": m.id,
            "channex_message_id": m.channex_message_id,
            "direction": m.direction,
            "body": m.body,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "guest_name": m.guest_name,
        }
        for m in messages
    ]


@router.post("/threads/{channex_booking_id}/ai-suggest")
async def ai_suggest_reply(
    channex_booking_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Generate an AI-suggested reply for a conversation thread.

    Returns ``{"suggestion": "..."}`` or raises 503 if Ollama unavailable.
    """
    messages = (
        db.query(ChannexMessage)
        .filter_by(channex_booking_id=channex_booking_id)
        .order_by(ChannexMessage.sent_at.asc())
        .all()
    )
    if not messages:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Resolve property config for context injection
    prop_cfg = None
    if messages[0].property_id:
        p = db.query(Property).filter_by(id=messages[0].property_id).first()
        if p:
            config = get_config()
            prop_cfg = next((pc for pc in config.properties if pc.slug == p.slug), None)

    msg_dicts = [{"direction": m.direction, "body": m.body} for m in messages]
    try:
        suggestion = await generate_reply_suggestion(msg_dicts, prop_cfg)
    except Exception as exc:
        log.error("ai_suggest_failed", error=str(exc))
        raise HTTPException(status_code=503, detail=f"AI suggestion failed: {exc}")

    return {"suggestion": suggestion}


class SendMessageRequest(BaseModel):
    body: str


@router.post("/threads/{channex_booking_id}/send")
async def send_inbox_message(
    channex_booking_id: str,
    body: SendMessageRequest,
    db: Session = Depends(get_db),
    client: ChannexClient = Depends(_require_channex_client),
) -> dict:
    """Send an outbound message to a guest via Channex and persist it locally."""
    try:
        async with client:
            result = await send_message(client, channex_booking_id, body.body)
    except ChannexAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Derive context from existing thread messages
    first_msg = (
        db.query(ChannexMessage)
        .filter_by(channex_booking_id=channex_booking_id)
        .first()
    )

    # Channex returns the created message id; fall back to local timestamp key
    msg_id = str(
        (result or {}).get("id")
        or f"local-{channex_booking_id}-{datetime.now(timezone.utc).timestamp()}"
    )

    stmt = (
        pg_insert(ChannexMessage)
        .values(
            channex_message_id=msg_id,
            channex_booking_id=channex_booking_id,
            booking_id=first_msg.booking_id if first_msg else None,
            property_id=first_msg.property_id if first_msg else None,
            guest_name=first_msg.guest_name if first_msg else "",
            direction="outbound",
            body=body.body,
            sent_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_nothing(index_elements=["channex_message_id"])
    )
    db.execute(stmt)
    db.commit()

    return {"ok": True}


@router.post("/sync")
async def sync_inbox(
    db: Session = Depends(get_db),
) -> dict:
    """Trigger a manual inbox sync from Channex.

    Falls back to seeding from bookings if the Channex Messages API is
    unavailable for the account (returns 404/403).
    """
    config = get_config()
    if not config.channex_api_key:
        raise HTTPException(
            status_code=503,
            detail="Channex integration not configured.",
        )
    async with get_channex_client() as client:
        result = await sync_all_messages(db, client)
    return {"synced": result.get("upserted", 0), "status": "ok"}
