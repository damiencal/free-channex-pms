"""Manual reservations API.

Allows creating direct/manual bookings without channel import.

Routes:
  POST /api/bookings/manual          — create a manual booking
  GET  /api/bookings                 — list bookings (all platforms)
  GET  /api/bookings/{id}            — get single booking
  PUT  /api/bookings/{id}            — update booking (notes, amount, status)
  DELETE /api/bookings/{id}          — delete a manually-created booking
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.booking import Booking
from app.models.booking_audit import BookingAuditLog
from app.models.cleaning_task import CleaningTask
from app.models.property import Property
from app.models.room import Room

log = structlog.get_logger()
router = APIRouter(prefix="/api/bookings", tags=["bookings"])


VALID_BOOKING_STATES = {"reservation", "checked_in", "checked_out", "no_show", "cancelled"}


class ManualBookingRequest(BaseModel):
    property_id: int
    guest_name: str
    guest_email: str = ""
    guest_phone: str = ""
    check_in_date: date
    check_out_date: date
    net_amount: Decimal
    notes: str = ""
    adults: int = 1
    children: int = 0
    guest_id: Optional[int] = None
    room_id: Optional[int] = None
    group_id: Optional[int] = None


class BookingUpdateRequest(BaseModel):
    net_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    reconciliation_status: Optional[str] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    guest_id: Optional[int] = None
    room_id: Optional[int] = None
    group_id: Optional[int] = None
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None


def _serialize(b: Booking) -> dict:
    # For channel bookings the email/phone may be nested in raw_platform_data.
    raw = b.raw_platform_data or {}
    guest_raw = raw.get("guest") or {}
    guest_email: str | None = (
        b.guest_email
        or guest_raw.get("email")
        or raw.get("guest_email")
        or None
    )
    guest_phone: str | None = (
        b.guest_phone
        or guest_raw.get("phone")
        or raw.get("guest_phone")
        or None
    )

    return {
        "id": b.id,
        "platform": b.platform,
        "platform_booking_id": b.platform_booking_id,
        "property_id": b.property_id,
        "guest_name": b.guest_name,
        "guest_email": guest_email,
        "guest_phone": guest_phone,
        "check_in_date": b.check_in_date.isoformat(),
        "check_out_date": b.check_out_date.isoformat(),
        "net_amount": str(b.net_amount),
        "reconciliation_status": b.reconciliation_status,
        "booking_state": b.booking_state,
        "adults": b.adults,
        "children": b.children,
        "notes": b.notes,
        "guest_id": b.guest_id,
        "room_id": b.room_id,
        "group_id": b.group_id,
        "created_at": b.created_at.isoformat(),
        "updated_at": b.updated_at.isoformat(),
    }


def _auto_create_cleaning_task(booking: Booking, db: Session) -> None:
    """Create a cleaning task for a booking's checkout date."""
    try:
        existing = db.query(CleaningTask).filter_by(booking_id=booking.id).first()
        if existing:
            return
        task = CleaningTask(
            booking_id=booking.id,
            property_id=booking.property_id,
            scheduled_date=booking.check_out_date,
            status="pending",
        )
        db.add(task)
        db.commit()
    except Exception as exc:
        log.error(
            "cleaning_task_auto_create_failed", booking_id=booking.id, error=str(exc)
        )


@router.post("/manual", status_code=201)
def create_manual_booking(
    body: ManualBookingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
) -> dict:
    """Create a direct (non-channel) booking manually."""
    prop = db.query(Property).filter_by(id=body.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    # Generate a unique manual booking ID
    booking_ref = f"MANUAL-{uuid.uuid4().hex[:8].upper()}"

    booking = Booking(
        platform="direct",
        platform_booking_id=booking_ref,
        property_id=body.property_id,
        guest_name=body.guest_name,
        guest_email=body.guest_email or None,
        guest_phone=body.guest_phone or None,
        check_in_date=body.check_in_date,
        check_out_date=body.check_out_date,
        net_amount=body.net_amount,
        reconciliation_status="unmatched",
        booking_state="reservation",
        adults=body.adults,
        children=body.children,
        notes=body.notes or None,
        guest_id=body.guest_id,
        room_id=body.room_id,
        group_id=body.group_id,
        raw_platform_data={"source": "manual"},
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Auto-create a cleaning task for checkout day
    background_tasks.add_task(_auto_create_cleaning_task, booking, db)

    log.info("manual_booking_created", booking_id=booking.id, ref=booking_ref)
    return _serialize(booking)


@router.get("")
def list_bookings(
    platform: Optional[str] = Query(None),
    property_id: Optional[int] = Query(None),
    check_in_from: Optional[date] = Query(None),
    check_in_to: Optional[date] = Query(None),
    booking_state: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(Booking).order_by(Booking.check_in_date.desc())
    if platform:
        q = q.filter_by(platform=platform)
    if property_id:
        q = q.filter_by(property_id=property_id)
    if check_in_from:
        q = q.filter(Booking.check_in_date >= check_in_from)
    if check_in_to:
        q = q.filter(Booking.check_in_date <= check_in_to)
    if booking_state:
        q = q.filter_by(booking_state=booking_state)
    return [_serialize(b) for b in q.limit(limit).all()]


@router.get("/{booking_id}")
def get_booking(booking_id: int, db: Session = Depends(get_db), _user=Depends(require_auth)) -> dict:
    b = db.query(Booking).filter_by(id=booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _serialize(b)


@router.put("/{booking_id}")
def update_booking(
    booking_id: int,
    body: BookingUpdateRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    b = db.query(Booking).filter_by(id=booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    simple_fields = (
        "net_amount", "reconciliation_status", "adults", "children",
        "guest_id", "room_id", "group_id",
    )
    for field in simple_fields:
        val = getattr(body, field, None)
        if val is not None:
            setattr(b, field, val)
    if body.notes is not None:
        b.notes = body.notes
    if body.guest_email is not None:
        b.guest_email = body.guest_email
    if body.guest_phone is not None:
        b.guest_phone = body.guest_phone
    db.commit()
    db.refresh(b)
    return _serialize(b)


@router.delete("/{booking_id}", status_code=204)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    b = db.query(Booking).filter_by(id=booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.platform != "direct":
        raise HTTPException(
            status_code=403,
            detail="Only manually created bookings (platform='direct') can be deleted.",
        )
    db.delete(b)
    db.commit()


# ---------------------------------------------------------------------------
# Booking state transitions
# ---------------------------------------------------------------------------

def _write_audit(db: Session, booking: Booking, action: str, user_id: int | None, notes: str | None = None) -> None:
    log_entry = BookingAuditLog(
        booking_id=booking.id,
        user_id=user_id,
        action=action,
        new_value=booking.booking_state,
        notes=notes,
    )
    db.add(log_entry)


def _get_user_id(user: dict | None) -> int | None:
    if isinstance(user, dict):
        return user.get("user_id")
    return None


@router.post("/{booking_id}/check-in", status_code=200)
def check_in(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
) -> dict:
    b = db.query(Booking).filter_by(id=booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.booking_state not in ("reservation",):
        raise HTTPException(status_code=400, detail=f"Cannot check-in from state '{b.booking_state}'")
    b.booking_state = "checked_in"
    _write_audit(db, b, "checked_in", _get_user_id(user))
    db.commit()
    db.refresh(b)
    log.info("Guest checked in", booking_id=booking_id)
    return _serialize(b)


@router.post("/{booking_id}/check-out", status_code=200)
def check_out(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
) -> dict:
    b = db.query(Booking).filter_by(id=booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.booking_state not in ("checked_in",):
        raise HTTPException(status_code=400, detail=f"Cannot check-out from state '{b.booking_state}'")
    b.booking_state = "checked_out"
    _write_audit(db, b, "checked_out", _get_user_id(user))
    # Mark assigned room as dirty
    if b.room_id:
        room = db.query(Room).filter_by(id=b.room_id).first()
        if room:
            room.status = "dirty"
    db.commit()
    db.refresh(b)
    log.info("Guest checked out", booking_id=booking_id)
    return _serialize(b)


@router.post("/{booking_id}/no-show", status_code=200)
def no_show(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
) -> dict:
    b = db.query(Booking).filter_by(id=booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.booking_state not in ("reservation",):
        raise HTTPException(status_code=400, detail=f"Cannot mark no-show from state '{b.booking_state}'")
    b.booking_state = "no_show"
    _write_audit(db, b, "no_show", _get_user_id(user))
    db.commit()
    db.refresh(b)
    return _serialize(b)


@router.post("/{booking_id}/cancel", status_code=200)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
) -> dict:
    b = db.query(Booking).filter_by(id=booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.booking_state in ("checked_out", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a booking in state '{b.booking_state}'")
    b.booking_state = "cancelled"
    _write_audit(db, b, "cancelled", _get_user_id(user))
    db.commit()
    db.refresh(b)
    return _serialize(b)


@router.get("/{booking_id}/audit-log")
def get_audit_log(
    booking_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    entries = (
        db.query(BookingAuditLog)
        .filter_by(booking_id=booking_id)
        .order_by(BookingAuditLog.created_at.asc())
        .all()
    )
    return [
        {
            "id": e.id,
            "booking_id": e.booking_id,
            "user_id": e.user_id,
            "action": e.action,
            "field_name": e.field_name,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "notes": e.notes,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]
