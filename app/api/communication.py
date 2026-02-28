"""Communication API endpoints.

Exposes guest messaging management:
  - GET  /communication/logs             — List all communication log entries with booking details
  - POST /communication/confirm/{log_id} — Mark a VRBO/RVshare message as sent (operator confirmation)
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.booking import Booking
from app.models.communication_log import CommunicationLog
from app.models.property import Property

router = APIRouter(prefix="/communication", tags=["communication"])


# ---------------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------------


@router.get("/logs")
def list_communication_logs(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: pending, sent, native_configured",
    ),
    message_type: Optional[str] = Query(
        default=None,
        description="Filter by message type: welcome, pre_arrival",
    ),
    platform: Optional[str] = Query(
        default=None,
        description="Filter by platform: airbnb, vrbo, rvshare",
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return communication log entries with booking details.

    Includes: message type, platform, status, scheduled time, sent time,
    operator notification time, rendered message text (for VRBO/RVshare),
    guest name, check-in date, and property slug.

    Args:
        status: Optional filter by message status.
        message_type: Optional filter by message type.
        platform: Optional filter by booking platform.
        limit: Max results (default 100).
        offset: Pagination offset.

    Returns:
        List of communication log dicts with booking and property details.
    """
    stmt = (
        select(CommunicationLog, Booking, Property.slug.label("prop_slug"))
        .join(Booking, CommunicationLog.booking_id == Booking.id)
        .join(Property, Booking.property_id == Property.id)
        .order_by(desc(CommunicationLog.created_at))
        .limit(limit)
        .offset(offset)
    )

    if status is not None:
        stmt = stmt.where(CommunicationLog.status == status)
    if message_type is not None:
        stmt = stmt.where(CommunicationLog.message_type == message_type)
    if platform is not None:
        stmt = stmt.where(CommunicationLog.platform == platform)

    rows = db.execute(stmt).all()
    return [
        {
            "log_id": comm.id,
            "booking_id": comm.booking_id,
            "message_type": comm.message_type,
            "platform": comm.platform,
            "status": comm.status,
            "scheduled_for": comm.scheduled_for.isoformat() if comm.scheduled_for else None,
            "sent_at": comm.sent_at.isoformat() if comm.sent_at else None,
            "operator_notified_at": comm.operator_notified_at.isoformat() if comm.operator_notified_at else None,
            "rendered_message": comm.rendered_message,
            "error_message": comm.error_message,
            "created_at": comm.created_at.isoformat() if comm.created_at else None,
            "guest_name": booking.guest_name,
            "platform_booking_id": booking.platform_booking_id,
            "check_in_date": booking.check_in_date.isoformat() if booking.check_in_date else None,
            "check_out_date": booking.check_out_date.isoformat() if booking.check_out_date else None,
            "property_slug": prop_slug,
        }
        for comm, booking, prop_slug in rows
    ]


# ---------------------------------------------------------------------------
# Confirm endpoint — operator marks VRBO/RVshare message as sent
# ---------------------------------------------------------------------------


@router.post("/confirm/{log_id}")
def confirm_message_sent(
    log_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Mark a communication log entry as sent (operator confirmation).

    Used by VRBO/RVshare operators after manually sending a message on
    the platform. Transitions status from 'pending' to 'sent'.

    Idempotent: confirming an already-sent entry returns success.

    Args:
        log_id: ID of the CommunicationLog entry to confirm.

    Returns:
        Dict with status and log_id.

    Raises:
        HTTPException 404: If no communication log entry found.
        HTTPException 409: If entry is 'native_configured' (Airbnb welcome — cannot confirm).
    """
    comm_log = db.get(CommunicationLog, log_id)

    if comm_log is None:
        raise HTTPException(
            status_code=404,
            detail=f"Communication log entry {log_id} not found",
        )

    # Already sent — idempotent success
    if comm_log.status == "sent":
        return {"status": "already_sent", "log_id": log_id}

    # Native configured (Airbnb welcome) — cannot confirm via API
    if comm_log.status == "native_configured":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Communication log {log_id} is 'native_configured' "
                "(Airbnb handles this natively). Cannot confirm via API."
            ),
        )

    # Transition pending -> sent
    comm_log.status = "sent"
    comm_log.sent_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "confirmed", "log_id": log_id}
