"""Guests (CRM) API — unified guest profile management.

Routes:
  GET    /api/guests              — list / search guests
  POST   /api/guests              — create guest profile
  GET    /api/guests/{id}         — get guest with booking history
  PUT    /api/guests/{id}         — update guest profile
  DELETE /api/guests/{id}         — deactivate guest (soft delete)
  GET    /api/guests/{id}/bookings — guest booking history
"""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.booking import Booking
from app.models.guest import Guest

log = structlog.get_logger()
router = APIRouter(prefix="/api/guests", tags=["guests"])

VALID_GUEST_TYPES = {"individual", "corporate", "vip", "group"}


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize(g: Guest) -> dict:
    return {
        "id": g.id,
        "first_name": g.first_name,
        "last_name": g.last_name,
        "full_name": g.full_name,
        "email": g.email,
        "phone": g.phone,
        "address": g.address,
        "city": g.city,
        "state": g.state,
        "country": g.country,
        "postal_code": g.postal_code,
        "guest_type": g.guest_type,
        "notes": g.notes,
        "balance": str(g.balance),
        "is_active": g.is_active,
        "created_at": g.created_at.isoformat(),
        "updated_at": g.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GuestCreate(BaseModel):
    first_name: str
    last_name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    guest_type: str = "individual"
    notes: Optional[str] = None


class GuestUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    guest_type: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
def list_guests(
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    guest_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    q = db.query(Guest)

    if is_active is not None:
        q = q.filter_by(is_active=is_active)

    if guest_type:
        q = q.filter_by(guest_type=guest_type)

    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                Guest.first_name.ilike(term),
                Guest.last_name.ilike(term),
                Guest.email.ilike(term),
                Guest.phone.ilike(term),
            )
        )

    total = q.count()
    guests = q.order_by(Guest.last_name, Guest.first_name).offset(offset).limit(limit).all()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [_serialize(g) for g in guests],
    }


@router.post("", status_code=201)
def create_guest(
    body: GuestCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    if body.guest_type not in VALID_GUEST_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid guest_type. Must be one of: {sorted(VALID_GUEST_TYPES)}",
        )
    guest = Guest(**body.model_dump())
    db.add(guest)
    db.commit()
    db.refresh(guest)
    log.info("Guest created", id=guest.id, name=guest.full_name)
    return _serialize(guest)


@router.get("/{guest_id}")
def get_guest(
    guest_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    guest = db.query(Guest).filter_by(id=guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    data = _serialize(guest)
    # Include booking history count
    booking_count = db.query(Booking).filter_by(guest_id=guest_id).count()
    data["booking_count"] = booking_count
    return data


@router.put("/{guest_id}")
def update_guest(
    guest_id: int,
    body: GuestUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    guest = db.query(Guest).filter_by(id=guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    updates = body.model_dump(exclude_none=True)
    if "guest_type" in updates and updates["guest_type"] not in VALID_GUEST_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid guest_type. Must be one of: {sorted(VALID_GUEST_TYPES)}",
        )
    for field, value in updates.items():
        setattr(guest, field, value)
    db.commit()
    db.refresh(guest)
    return _serialize(guest)


@router.delete("/{guest_id}", status_code=204)
def deactivate_guest(
    guest_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    guest = db.query(Guest).filter_by(id=guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    guest.is_active = False
    db.commit()


@router.get("/{guest_id}/bookings")
def get_guest_bookings(
    guest_id: int,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    guest = db.query(Guest).filter_by(id=guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    # Also match by name for unlinked bookings
    bookings = (
        db.query(Booking)
        .filter(
            or_(
                Booking.guest_id == guest_id,
                Booking.guest_name == guest.full_name,
            )
        )
        .order_by(Booking.check_in_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": b.id,
            "platform": b.platform,
            "property_id": b.property_id,
            "check_in_date": b.check_in_date.isoformat(),
            "check_out_date": b.check_out_date.isoformat(),
            "net_amount": str(b.net_amount),
            "booking_state": b.booking_state,
        }
        for b in bookings
    ]
