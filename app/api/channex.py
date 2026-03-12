"""Channex.io API endpoints.

All routes are prefixed with ``/api/channex`` and tagged ``channex``.

Endpoints:
  GET  /api/channex/properties           — List properties from Channex API
  POST /api/channex/properties/sync      — Sync Channex properties to local DB
  GET  /api/channex/calendar/{id}        — Get availability + rates for a property
  PUT  /api/channex/calendar/{id}        — Update availability/rates
  GET  /api/channex/reservations         — List bookings from Channex API (pass-through)
  POST /api/channex/reservations/sync    — Trigger full reservation sync
  GET  /api/channex/messages             — List messages from local DB
  POST /api/channex/messages             — Send a message via Channex API
  GET  /api/channex/reviews              — List reviews from local DB
  POST /api/channex/reviews/{id}/respond — Submit host response to a review
  POST /api/channex/webhooks             — Receive Channex webhook event
  GET  /api/channex/webhook-events       — List recent webhook events (debugging)
  POST /api/channex/webhooks/register    — Register this app's webhook URL with Channex

All endpoints require ``CHANNEX_API_KEY`` to be configured (returns 503 otherwise).
The webhook receiver returns 200 even on dispatch errors (Channex will retry on 5xx).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.channex.calendar import (
    AvailabilityUpdate,
    RateUpdate,
    get_availability,
    get_rate_plans,
    get_rates,
    get_room_types,
    update_availability,
    update_rates,
)
from app.channex.client import ChannexClient, get_channex_client
from app.channex.exceptions import (
    ChannexAPIError,
    ChannexAuthError,
    ChannexWebhookSignatureError,
)
from app.channex.messaging import list_messages, send_message, sync_all_messages
from app.channex.properties import list_properties, sync_properties
from app.channex.reservations import list_bookings, sync_all_reservations
from app.channex.reviews import list_reviews, respond_to_review, sync_all_reviews
from app.channex.sync import register_webhook
from app.channex.webhooks import process_webhook
from app.config import get_config
from app.db import get_db
from app.models.channex_message import ChannexMessage
from app.models.channex_property import ChannexProperty
from app.models.channex_review import ChannexReview
from app.models.channex_webhook_event import ChannexWebhookEvent
from app.models.property import Property

log = structlog.get_logger()
router = APIRouter(prefix="/api/channex", tags=["channex"])


# ---------------------------------------------------------------------------
# Dependency: require Channex API key (returns 503 if not configured)
# ---------------------------------------------------------------------------


def require_channex_client() -> ChannexClient:
    """FastAPI dependency that raises 503 if Channex API key is not configured."""
    config = get_config()
    if not config.channex_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "Channex integration is not configured. "
                "Set CHANNEX_API_KEY in .env to enable it."
            ),
        )
    return get_channex_client()


# ---------------------------------------------------------------------------
# Pydantic request/response schemas
# ---------------------------------------------------------------------------


class AvailabilityUpdateItem(BaseModel):
    room_type_id: str
    date_from: date
    date_to: date
    availability: Optional[int] = None
    min_stay_arrival: Optional[int] = None
    max_stay: Optional[int] = None
    closed_to_arrival: Optional[bool] = None
    closed_to_departure: Optional[bool] = None
    stop_sell: Optional[bool] = None


class RateUpdateItem(BaseModel):
    rate_plan_id: str
    date_from: date
    date_to: date
    rate: Optional[float] = None


class CalendarUpdateRequest(BaseModel):
    availability_updates: list[AvailabilityUpdateItem] = []
    rate_updates: list[RateUpdateItem] = []


class SendMessageRequest(BaseModel):
    channex_booking_id: str
    body: str


class RespondToReviewRequest(BaseModel):
    response_text: str


class RegisterWebhookRequest(BaseModel):
    callback_url: str


# ---------------------------------------------------------------------------
# Error handling helper
# ---------------------------------------------------------------------------


def _handle_channex_error(exc: ChannexAPIError) -> None:
    """Convert a ChannexAPIError to an appropriate HTTP exception."""
    if isinstance(exc, ChannexAuthError):
        raise HTTPException(status_code=401, detail=str(exc))
    if exc.status_code == 404:
        raise HTTPException(status_code=404, detail=str(exc))
    if exc.status_code == 422:
        raise HTTPException(status_code=422, detail=str(exc))
    raise HTTPException(
        status_code=502,
        detail=f"Channex API error: {exc.message}",
    )


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


@router.get("/properties")
async def get_channex_properties(
    client: ChannexClient = Depends(require_channex_client),
) -> list[dict]:
    """List all properties from the Channex API."""
    try:
        async with client:
            return await list_properties(client)
    except ChannexAPIError as exc:
        _handle_channex_error(exc)
        return []  # unreachable


@router.post("/properties/sync")
async def sync_channex_properties(
    db: Session = Depends(get_db),
    client: ChannexClient = Depends(require_channex_client),
) -> dict:
    """Pull Channex properties and upsert into the local ``channex_properties`` table.

    Returns a summary of how many properties were synced and linked to local Property rows.
    """
    try:
        async with client:
            return await sync_properties(db, client)
    except ChannexAPIError as exc:
        _handle_channex_error(exc)
        return {}


@router.get("/properties/local")
def get_local_channex_properties(
    db: Session = Depends(get_db),
) -> list[dict]:
    """List locally-synced Channex properties with their mapping to local Property rows.

    Returns each channex_properties row joined with the linked local property name/slug.
    Does NOT call the live Channex API — reads from the local DB only.
    """
    rows = (
        db.query(ChannexProperty).order_by(ChannexProperty.channex_property_name).all()
    )
    local_props = {p.id: p for p in db.query(Property).all()}
    result = []
    for row in rows:
        local = local_props.get(row.property_id) if row.property_id else None
        result.append(
            {
                "id": row.id,
                "channex_property_id": row.channex_property_id,
                "channex_property_name": row.channex_property_name,
                "channex_group_id": row.channex_group_id,
                "property_id": row.property_id,
                "property_slug": local.slug if local else None,
                "property_display_name": local.display_name if local else None,
                "synced_at": row.synced_at.isoformat() if row.synced_at else None,
            }
        )
    return result


class LinkPropertyRequest(BaseModel):
    property_id: int | None


@router.patch("/properties/{channex_property_id}/link")
def link_channex_property(
    channex_property_id: str,
    body: LinkPropertyRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Manually link (or unlink) a Channex property to a local Property row.

    Pass ``property_id: null`` to clear the mapping.
    """
    row = (
        db.query(ChannexProperty)
        .filter_by(channex_property_id=channex_property_id)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Channex property '{channex_property_id}' not found in local DB. Run /properties/sync first.",
        )

    if body.property_id is not None:
        local = db.query(Property).filter_by(id=body.property_id).first()
        if not local:
            raise HTTPException(
                status_code=404,
                detail=f"Local property id={body.property_id} not found.",
            )
        row.property_id = body.property_id
    else:
        row.property_id = None

    db.commit()
    db.refresh(row)
    local = (
        db.query(Property).filter_by(id=row.property_id).first()
        if row.property_id
        else None
    )
    return {
        "channex_property_id": row.channex_property_id,
        "channex_property_name": row.channex_property_name,
        "property_id": row.property_id,
        "property_slug": local.slug if local else None,
        "property_display_name": local.display_name if local else None,
    }


# ---------------------------------------------------------------------------
# Calendar (availability + rates)
# ---------------------------------------------------------------------------


@router.get("/calendar/{channex_property_id}")
async def get_channex_calendar(
    channex_property_id: str,
    date_from: date = Query(default_factory=date.today),
    date_to: date = Query(default_factory=lambda: date.today().replace(day=28)),
    client: ChannexClient = Depends(require_channex_client),
) -> dict:
    """Get availability, rates, and room types for a Channex property.

    Query params:
      - ``date_from``: Start date (default: today).
      - ``date_to``: End date (default: end of current month).
    """
    try:
        async with client:
            avail, rate_plans, room_types, rates = await _fetch_calendar_data(
                client, channex_property_id, date_from, date_to
            )
        return {
            "channex_property_id": channex_property_id,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "availability": avail,
            "rate_plans": rate_plans,
            "room_types": room_types,
            "rates": rates,
        }
    except ChannexAPIError as exc:
        _handle_channex_error(exc)
        return {}


async def _fetch_calendar_data(
    client: ChannexClient,
    channex_property_id: str,
    date_from: date,
    date_to: date,
) -> tuple[dict, list, list, dict]:
    """Fetch availability, rate plan metadata, room types, and per-date rates.

    Each sub-request is guarded individually so a missing availability or rates
    configuration on the Channex side doesn't prevent the rest from loading.
    """
    avail: dict = {}
    rates: dict = {}
    rate_plans: list = []
    room_types: list = []

    try:
        avail = (
            await get_availability(client, channex_property_id, date_from, date_to)
            or {}
        )
    except ChannexAPIError as exc:
        log.warning(
            "channex_availability_fetch_failed",
            property_id=channex_property_id,
            error=str(exc),
        )

    try:
        rates = await get_rates(client, channex_property_id, date_from, date_to) or {}
    except ChannexAPIError as exc:
        log.warning(
            "channex_rates_fetch_failed",
            property_id=channex_property_id,
            error=str(exc),
        )

    try:
        rate_plans = await get_rate_plans(client, channex_property_id) or []
    except ChannexAPIError as exc:
        log.warning(
            "channex_rate_plans_fetch_failed",
            property_id=channex_property_id,
            error=str(exc),
        )

    try:
        room_types = await get_room_types(client, channex_property_id) or []
    except ChannexAPIError as exc:
        log.warning(
            "channex_room_types_fetch_failed",
            property_id=channex_property_id,
            error=str(exc),
        )

    return avail, rate_plans, room_types, rates


@router.put("/calendar/{channex_property_id}")
async def update_channex_calendar(
    channex_property_id: str,
    body: CalendarUpdateRequest,
    client: ChannexClient = Depends(require_channex_client),
) -> dict:
    """Push availability and/or rate updates to Channex.

    Rate updates and availability updates are sent as separate batch requests.
    Both are optional — include only what you want to change.
    """
    results: dict = {"channex_property_id": channex_property_id}
    try:
        async with client:
            if body.availability_updates:
                av_updates = [
                    AvailabilityUpdate(
                        room_type_id=u.room_type_id,
                        date_from=u.date_from,
                        date_to=u.date_to,
                        availability=u.availability,
                        min_stay_arrival=u.min_stay_arrival,
                        max_stay=u.max_stay,
                        closed_to_arrival=u.closed_to_arrival,
                        closed_to_departure=u.closed_to_departure,
                        stop_sell=u.stop_sell,
                    )
                    for u in body.availability_updates
                ]
                results["availability"] = await update_availability(client, av_updates)

            if body.rate_updates:
                rate_updates = [
                    RateUpdate(
                        rate_plan_id=u.rate_plan_id,
                        date_from=u.date_from,
                        date_to=u.date_to,
                        rate=u.rate,
                    )
                    for u in body.rate_updates
                ]
                results["rates"] = await update_rates(client, rate_updates)
    except ChannexAPIError as exc:
        _handle_channex_error(exc)

    return results


# ---------------------------------------------------------------------------
# Reservations
# ---------------------------------------------------------------------------


@router.get("/reservations")
async def get_channex_reservations(
    channex_property_id: Optional[str] = Query(None),
    updated_since: Optional[datetime] = Query(None),
    client: ChannexClient = Depends(require_channex_client),
) -> list[dict]:
    """List bookings from the Channex API (pass-through, paginated).

    Query params:
      - ``channex_property_id``: Filter by Channex property UUID.
      - ``updated_since``: Only return bookings updated after this ISO datetime.
    """
    try:
        async with client:
            return await list_bookings(
                client,
                updated_since=updated_since,
                channex_property_id=channex_property_id,
            )
    except ChannexAPIError as exc:
        _handle_channex_error(exc)
        return []


@router.post("/reservations/sync")
async def sync_channex_reservations(
    channex_property_id: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    client: ChannexClient = Depends(require_channex_client),
) -> dict:
    """Pull bookings from Channex and upsert them into the local ``bookings`` table.

    Query params:
      - ``channex_property_id``: Limit sync to one Channex property.
      - ``since``: Incremental sync — only fetch bookings updated after this datetime.

    Returns:
        Summary with ``upserted``, ``skipped``, and ``failed`` counts.
    """
    try:
        async with client:
            return await sync_all_reservations(
                db,
                client,
                since=since,
                channex_property_id=channex_property_id,
            )
    except ChannexAPIError as exc:
        _handle_channex_error(exc)
        return {}


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


@router.get("/messages")
def get_channex_messages(
    channex_booking_id: Optional[str] = Query(None),
    direction: Optional[str] = Query(None, description="'inbound' or 'outbound'"),
    booking_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List messages from the local ``channex_messages`` table.

    Query params:
      - ``channex_booking_id``: Filter by Channex booking UUID.
      - ``direction``: ``'inbound'`` or ``'outbound'``.
      - ``booking_id``: Filter by local booking FK.
      - ``limit``: Max rows to return (default 50, max 200).
    """
    query = db.query(ChannexMessage).order_by(ChannexMessage.sent_at.desc())
    if channex_booking_id:
        query = query.filter(ChannexMessage.channex_booking_id == channex_booking_id)
    if direction:
        query = query.filter(ChannexMessage.direction == direction)
    if booking_id:
        query = query.filter(ChannexMessage.booking_id == booking_id)

    messages = query.limit(limit).all()
    return [
        {
            "id": m.id,
            "channex_message_id": m.channex_message_id,
            "channex_booking_id": m.channex_booking_id,
            "booking_id": m.booking_id,
            "property_id": m.property_id,
            "guest_name": m.guest_name,
            "direction": m.direction,
            "body": m.body,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/messages")
async def send_channex_message(
    body: SendMessageRequest,
    db: Session = Depends(get_db),
    client: ChannexClient = Depends(require_channex_client),
) -> dict:
    """Send an outbound message to a guest via the Channex API.

    The message is also saved to the local ``channex_messages`` table
    with ``direction='outbound'``.
    """
    try:
        async with client:
            result = await send_message(client, body.channex_booking_id, body.body)
    except ChannexAPIError as exc:
        _handle_channex_error(exc)
        return {}

    # Persist outbound message locally
    now = datetime.utcnow().replace(tzinfo=None)
    if isinstance(result, dict):
        msg_id = str(
            result.get("id") or f"outbound-{body.channex_booking_id}-{now.timestamp()}"
        )
    else:
        msg_id = f"outbound-{body.channex_booking_id}-{now.timestamp()}"

    from app.models.channex_message import ChannexMessage as Msg
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = (
        pg_insert(Msg)
        .values(
            channex_message_id=msg_id,
            channex_booking_id=body.channex_booking_id,
            direction="outbound",
            body=body.body,
            guest_name="",
            sent_at=datetime.utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["channex_message_id"])
    )
    db.execute(stmt)
    db.commit()

    return result if isinstance(result, dict) else {"status": "sent"}


@router.post("/messages/sync")
async def sync_channex_messages(
    since: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    client: ChannexClient = Depends(require_channex_client),
) -> dict:
    """Pull messages from Channex and sync to local DB."""
    try:
        async with client:
            return await sync_all_messages(db, client, since=since)
    except ChannexAPIError as exc:
        _handle_channex_error(exc)
        return {}


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


@router.get("/reviews")
def get_channex_reviews(
    status: Optional[str] = Query(None, description="'new' or 'responded'"),
    booking_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List reviews from the local ``channex_reviews`` table.

    Query params:
      - ``status``: ``'new'`` or ``'responded'``.
      - ``booking_id``: Filter by local booking FK.
      - ``limit``: Max rows to return (default 50, max 200).
    """
    query = db.query(ChannexReview).order_by(ChannexReview.reviewed_at.desc())
    if status:
        query = query.filter(ChannexReview.status == status)
    if booking_id:
        query = query.filter(ChannexReview.booking_id == booking_id)

    reviews = query.limit(limit).all()
    return [
        {
            "id": r.id,
            "channex_review_id": r.channex_review_id,
            "channex_booking_id": r.channex_booking_id,
            "booking_id": r.booking_id,
            "property_id": r.property_id,
            "guest_name": r.guest_name,
            "rating": r.rating,
            "review_text": r.review_text,
            "status": r.status,
            "response_text": r.response_text,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "responded_at": r.responded_at.isoformat() if r.responded_at else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]


@router.post("/reviews/{channex_review_id}/respond")
async def respond_channex_review(
    channex_review_id: str,
    body: RespondToReviewRequest,
    db: Session = Depends(get_db),
    client: ChannexClient = Depends(require_channex_client),
) -> dict:
    """Submit a host response to a guest review via the Channex API.

    Updates the local ``channex_reviews`` row with the response text and
    sets ``status = 'responded'``.
    """
    review = (
        db.query(ChannexReview).filter_by(channex_review_id=channex_review_id).first()
    )
    if not review:
        raise HTTPException(
            status_code=404, detail=f"Review {channex_review_id} not found"
        )
    if review.status == "responded":
        raise HTTPException(
            status_code=409, detail="This review has already been responded to"
        )

    try:
        async with client:
            result = await respond_to_review(
                client, db, channex_review_id, body.response_text
            )
    except ChannexAPIError as exc:
        _handle_channex_error(exc)
        return {}

    return result if isinstance(result, dict) else {"status": "responded"}


@router.post("/reviews/{channex_review_id}/ai-suggest")
async def ai_suggest_review_response(
    channex_review_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Generate an AI-suggested response for a guest review using Ollama.

    Returns ``{"suggestion": "..."}`` or raises 503 if Ollama is unavailable.
    """
    review = (
        db.query(ChannexReview).filter_by(channex_review_id=channex_review_id).first()
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    config = get_config()
    prop_cfg = None
    if review.property_id:
        prop = db.query(Property).filter_by(id=review.property_id).first()
        if prop:
            prop_cfg = next((p for p in config.properties if p.slug == prop.slug), None)

    property_name = prop_cfg.display_name if prop_cfg else "our property"
    host_name = prop_cfg.host_name if prop_cfg else "Your host"

    system = (
        f"You are {host_name}, the manager of {property_name}, a vacation rental. "
        "Write a warm, professional, grateful response to the following guest review. "
        "Keep it under 100 words. Output only the response body — no salutation or signature."
    )

    review_text = review.review_text or "(no review text provided)"
    rating_line = f"Rating: {review.rating}/5 stars" if review.rating else ""
    user_content = f"{rating_line}\nGuest review:\n{review_text}"

    from app.query.ollama_client import get_ollama_client

    try:
        client = get_ollama_client()
        response = await client.chat(
            model=config.ollama_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            options={"temperature": 0.7},
        )
        suggestion = response["message"]["content"].strip()
    except Exception as exc:
        log.error("ai_review_suggest_failed", error=str(exc))
        raise HTTPException(status_code=503, detail=f"AI suggestion failed: {exc}")

    return {"suggestion": suggestion}


@router.post("/reviews/sync")
async def sync_channex_reviews(
    since: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    client: ChannexClient = Depends(require_channex_client),
) -> dict:
    """Pull reviews from Channex and sync to local DB."""
    try:
        async with client:
            return await sync_all_reviews(db, client, since=since)
    except ChannexAPIError as exc:
        _handle_channex_error(exc)
        return {}


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


@router.post("/webhooks")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Receive and process a Channex webhook event.

    - Verifies HMAC-SHA256 signature (skipped if ``CHANNEX_WEBHOOK_SECRET`` is not set).
    - Persists the event to ``channex_webhook_events`` (idempotent).
    - Dispatches to the appropriate service handler.
    - Always returns 200 to prevent Channex from retrying dispatched events.
      Processing failures are logged and visible via ``GET /webhook-events``.
    """
    config = get_config()
    raw_body = await request.body()

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    signature = request.headers.get("X-Channex-Signature", "")

    try:
        event_row = process_webhook(
            db,
            payload=payload,
            raw_body=raw_body,
            signature_header=signature,
            webhook_secret=config.channex_webhook_secret,
        )
    except ChannexWebhookSignatureError as exc:
        log.warning("webhook_signature_rejected", error=str(exc))
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    return Response(
        content=f'{{"status": "ok", "event_id": {event_row.id}}}',
        media_type="application/json",
        status_code=200,
    )


@router.get("/webhook-events")
def list_webhook_events(
    status: Optional[str] = Query(
        None, description="'received', 'processed', or 'failed'"
    ),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List recent Channex webhook events for debugging and auditing.

    Query params:
      - ``status``: Filter by processing status.
      - ``event_type``: Filter by event type (e.g. ``'booking.new'``).
      - ``limit``: Max rows to return (default 50, max 200).
    """
    query = db.query(ChannexWebhookEvent).order_by(
        ChannexWebhookEvent.received_at.desc()
    )
    if status:
        query = query.filter(ChannexWebhookEvent.status == status)
    if event_type:
        query = query.filter(ChannexWebhookEvent.event_type == event_type)

    events = query.limit(limit).all()
    return [
        {
            "id": e.id,
            "channex_event_id": e.channex_event_id,
            "event_type": e.event_type,
            "status": e.status,
            "error_message": e.error_message,
            "received_at": e.received_at.isoformat(),
            "processed_at": e.processed_at.isoformat() if e.processed_at else None,
        }
        for e in events
    ]


@router.post("/webhooks/register")
async def register_channex_webhook(
    body: RegisterWebhookRequest,
) -> dict:
    """Register this app's URL as a Channex webhook subscriber.

    Point Channex to the callback URL so it delivers real-time events.
    Typically called once after deployment with:
      ``{"callback_url": "https://your-domain.com/api/channex/webhooks"}``

    Requires ``CHANNEX_API_KEY`` to be configured.
    """
    config = get_config()
    if not config.channex_api_key:
        raise HTTPException(
            status_code=503,
            detail="Channex integration is not configured. Set CHANNEX_API_KEY in .env.",
        )
    try:
        return await register_webhook(body.callback_url)
    except ChannexAPIError as exc:
        _handle_channex_error(exc)
        return {}
