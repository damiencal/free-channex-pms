"""Channex.io webhook receiver and event dispatcher.

Inbound webhooks from Channex are:
  1. Signature-verified (HMAC-SHA256 via ``X-Channex-Signature`` header).
  2. Persisted to ``channex_webhook_events`` for audit and replay.
  3. Dispatched to the appropriate service (reservations, messaging, reviews).

Channex sends a ``X-Channex-Signature`` header containing the
HMAC-SHA256 hex digest of the raw body, keyed with ``CHANNEX_WEBHOOK_SECRET``.
Verification is skipped if ``channex_webhook_secret`` is empty (dev/test mode).

Event type normalisation:
  Channex may send types in either dot-notation (``booking.new``) or
  underscore notation (``bookings_new``). All are normalised to dot-notation
  internally before routing.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.channex.exceptions import ChannexWebhookSignatureError
from app.channex.messaging import sync_messages_to_db
from app.channex.reservations import sync_booking_to_db
from app.channex.reviews import sync_reviews_to_db
from app.models.channex_webhook_event import ChannexWebhookEvent

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def verify_signature(
    payload_bytes: bytes,
    signature_header: str,
    secret: str,
) -> None:
    """Verify the HMAC-SHA256 webhook signature from Channex.

    Args:
        payload_bytes: Raw request body bytes (before any parsing).
        signature_header: Value of the ``X-Channex-Signature`` header.
        secret: The configured ``channex_webhook_secret``.

    Raises:
        ChannexWebhookSignatureError: If the computed HMAC does not match.
    """
    expected = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    # Remove any ``sha256=`` prefix Channex may prepend
    received = signature_header.lstrip("sha256=").strip()

    if not hmac.compare_digest(expected, received):
        raise ChannexWebhookSignatureError(
            "Webhook HMAC-SHA256 signature mismatch — "
            "check CHANNEX_WEBHOOK_SECRET in .env"
        )


# ---------------------------------------------------------------------------
# Event type normalisation
# ---------------------------------------------------------------------------


def _normalise_event_type(raw: str) -> str:
    """Normalise Channex event type to dot-notation.

    Examples:
        ``bookings_new``     → ``booking.new``
        ``booking.new``      → ``booking.new``
        ``messages_new``     → ``message.new``
        ``reviews_new``      → ``review.new``
        ``booking_modified`` → ``booking.modified``
    """
    lower = raw.lower().replace("-", "_")
    # underscore → dot: first underscore becomes dot
    # handles: bookings_new, booking_modified, messages_new, reviews_new
    mapping = {
        "bookings_new": "booking.new",
        "booking_new": "booking.new",
        "bookings_modified": "booking.modified",
        "booking_modified": "booking.modified",
        "bookings_cancelled": "booking.cancelled",
        "booking_cancelled": "booking.cancelled",
        "bookings_canceled": "booking.cancelled",
        "booking_canceled": "booking.cancelled",
        "messages_new": "message.new",
        "message_new": "message.new",
        "reviews_new": "review.new",
        "review_new": "review.new",
    }
    if lower in mapping:
        return mapping[lower]
    # Already dot-notation or unknown — pass through
    return lower.replace("_", ".", 1) if "_" in lower and "." not in lower else lower


# ---------------------------------------------------------------------------
# Event persistence
# ---------------------------------------------------------------------------


def save_webhook_event(
    db: Session,
    event_id: str | None,
    event_type: str,
    payload: dict,
    raw_body: str = "",
) -> ChannexWebhookEvent:
    """Persist a webhook event to the DB idempotently.

    If an event with the same ``channex_event_id`` already exists,
    returns the existing row without modification (idempotent replay guard).

    Args:
        db: SQLAlchemy session (caller must commit).
        event_id: Channex event UUID or None.
        event_type: Normalized event type string.
        payload: Deserialized JSON payload.
        raw_body: Raw request body string for audit.

    Returns:
        The ``ChannexWebhookEvent`` row (existing or newly created).
    """
    if event_id:
        existing = (
            db.query(ChannexWebhookEvent)
            .filter_by(channex_event_id=event_id)
            .first()
        )
        if existing:
            return existing  # Already processed — don't duplicate

    event = ChannexWebhookEvent(
        channex_event_id=event_id or None,
        event_type=event_type,
        payload=payload,
        raw_body=raw_body[:65535] if raw_body else None,  # guard against huge bodies
        status="received",
        received_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.flush()
    return event


# ---------------------------------------------------------------------------
# Event dispatch
# ---------------------------------------------------------------------------


def dispatch_event(
    db: Session,
    event_type: str,
    payload: dict,
) -> None:
    """Route a normalised Channex event to the correct service handler.

    Args:
        db: SQLAlchemy session (caller commits upon success).
        event_type: Normalised event type (dot-notation).
        payload: Deserialized event payload from Channex.
    """
    # Extract the nested data object — Channex wraps events differently per type
    data = payload.get("data") or payload

    if event_type in ("booking.new", "booking.modified", "booking.cancelled"):
        booking_data = data.get("booking") or data
        if isinstance(booking_data, dict) and booking_data:
            result = sync_booking_to_db(db, booking_data)
            log.info(
                "webhook_booking_synced",
                event_type=event_type,
                booking_id=result.get("id"),
                action=result.get("action"),
            )

    elif event_type == "message.new":
        message_data = data.get("message") or data
        if isinstance(message_data, dict):
            sync_messages_to_db(db, [message_data])

    elif event_type == "review.new":
        review_data = data.get("review") or data
        if isinstance(review_data, dict):
            sync_reviews_to_db(db, [review_data])

    else:
        log.debug("webhook_event_unhandled", event_type=event_type)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def process_webhook(
    db: Session,
    payload: dict,
    raw_body: bytes,
    signature_header: str = "",
    webhook_secret: str = "",
) -> ChannexWebhookEvent:
    """Full webhook processing pipeline.

    1. Verify HMAC signature (if secret is configured).
    2. Persist the event to ``channex_webhook_events`` (idempotent).
    3. Dispatch to the correct service handler.
    4. Mark event as ``processed`` on success, ``failed`` on error.
    5. Commit the session.

    Args:
        db: SQLAlchemy session.
        payload: Deserialized JSON payload.
        raw_body: Raw request body bytes for signature verification.
        signature_header: Value of ``X-Channex-Signature`` header.
        webhook_secret: Value of ``channex_webhook_secret`` config.

    Returns:
        The persisted ``ChannexWebhookEvent`` row.

    Raises:
        ChannexWebhookSignatureError: If signature verification fails.
    """
    # 1. Signature verification (skip if no secret configured)
    if webhook_secret and signature_header:
        verify_signature(raw_body, signature_header, webhook_secret)

    # Extract event metadata from payload
    event_id: str | None = str(payload.get("event_id") or payload.get("id") or "") or None
    raw_event_type: str = str(
        payload.get("event")
        or payload.get("event_type")
        or payload.get("type")
        or "unknown"
    )
    event_type = _normalise_event_type(raw_event_type)

    # 2. Persist (idempotent)
    event_row = save_webhook_event(
        db,
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        raw_body=raw_body.decode("utf-8", errors="replace"),
    )

    # Return early if this was a duplicate (already processed)
    if event_row.status == "processed":
        return event_row

    # 3. Dispatch
    try:
        dispatch_event(db, event_type, payload)
        event_row.status = "processed"
        event_row.processed_at = datetime.now(timezone.utc)
    except Exception as exc:
        log.error(
            "webhook_dispatch_failed",
            event_type=event_type,
            error=str(exc),
        )
        event_row.status = "failed"
        event_row.error_message = str(exc)[:1024]

    # 5. Commit
    db.commit()
    return event_row
