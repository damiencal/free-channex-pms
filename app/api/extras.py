"""Extras (Add-ons) API.

Routes:
  GET    /api/extras               — list extra definitions
  POST   /api/extras               — create extra definition
  GET    /api/extras/{id}          — get extra definition
  PUT    /api/extras/{id}          — update extra definition
  DELETE /api/extras/{id}          — soft-delete extra definition

  GET    /api/bookings/{booking_id}/extras        — list extras on booking
  POST   /api/bookings/{booking_id}/extras        — add extra to booking
  PUT    /api/booking-extras/{id}                  — update booking extra quantity/notes
  DELETE /api/booking-extras/{id}                  — remove extra from booking
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.booking import Booking
from app.models.extra import BookingExtra, Extra

log = structlog.get_logger()
router = APIRouter(tags=["extras"])


def _serialize_extra(e: Extra) -> dict:
    return {
        "id": e.id,
        "property_id": e.property_id,
        "name": e.name,
        "description": e.description,
        "price": str(e.price),
        "price_type": e.price_type,
        "is_active": e.is_active,
        "created_at": e.created_at.isoformat(),
        "updated_at": e.updated_at.isoformat(),
    }


def _serialize_booking_extra(be: BookingExtra, extra_name: str | None = None) -> dict:
    return {
        "id": be.id,
        "booking_id": be.booking_id,
        "extra_id": be.extra_id,
        "extra_name": extra_name,
        "quantity": be.quantity,
        "unit_price": str(be.unit_price),
        "amount": str(be.amount),
        "notes": be.notes,
        "created_at": be.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ExtraCreate(BaseModel):
    property_id: int
    name: str
    description: Optional[str] = None
    price: Decimal = Decimal("0")
    price_type: str = "per_stay"
    is_active: bool = True


class ExtraUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    price_type: Optional[str] = None
    is_active: Optional[bool] = None


class BookingExtraCreate(BaseModel):
    extra_id: int
    quantity: int = 1
    unit_price: Optional[Decimal] = None
    notes: Optional[str] = None


class BookingExtraUpdate(BaseModel):
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Extra definition endpoints
# ---------------------------------------------------------------------------

VALID_PRICE_TYPES = {"per_stay", "per_night", "per_person", "per_person_per_night"}


@router.get("/api/extras")
def list_extras(
    property_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(Extra).order_by(Extra.name)
    if property_id is not None:
        q = q.filter_by(property_id=property_id)
    if is_active is not None:
        q = q.filter_by(is_active=is_active)
    return [_serialize_extra(e) for e in q.all()]


@router.post("/api/extras", status_code=201)
def create_extra(
    body: ExtraCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    if body.price_type not in VALID_PRICE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"price_type must be one of {sorted(VALID_PRICE_TYPES)}",
        )
    extra = Extra(**body.model_dump())
    db.add(extra)
    db.commit()
    db.refresh(extra)
    return _serialize_extra(extra)


@router.get("/api/extras/{extra_id}")
def get_extra(
    extra_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    extra = db.query(Extra).filter_by(id=extra_id).first()
    if not extra:
        raise HTTPException(status_code=404, detail="Extra not found")
    return _serialize_extra(extra)


@router.put("/api/extras/{extra_id}")
def update_extra(
    extra_id: int,
    body: ExtraUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    extra = db.query(Extra).filter_by(id=extra_id).first()
    if not extra:
        raise HTTPException(status_code=404, detail="Extra not found")
    updates = body.model_dump(exclude_none=True)
    if "price_type" in updates and updates["price_type"] not in VALID_PRICE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"price_type must be one of {sorted(VALID_PRICE_TYPES)}",
        )
    for field, value in updates.items():
        setattr(extra, field, value)
    db.commit()
    db.refresh(extra)
    return _serialize_extra(extra)


@router.delete("/api/extras/{extra_id}", status_code=204)
def delete_extra(
    extra_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    extra = db.query(Extra).filter_by(id=extra_id).first()
    if not extra:
        raise HTTPException(status_code=404, detail="Extra not found")
    extra.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Booking extras endpoints
# ---------------------------------------------------------------------------

@router.get("/api/bookings/{booking_id}/extras")
def list_booking_extras(
    booking_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    booking = db.query(Booking).filter_by(id=booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    bes = db.query(BookingExtra).filter_by(booking_id=booking_id).all()
    extra_ids = {be.extra_id for be in bes}
    extra_names = {
        e.id: e.name
        for e in db.query(Extra).filter(Extra.id.in_(extra_ids)).all()
    }
    return [_serialize_booking_extra(be, extra_names.get(be.extra_id)) for be in bes]


@router.post("/api/bookings/{booking_id}/extras", status_code=201)
def add_booking_extra(
    booking_id: int,
    body: BookingExtraCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    booking = db.query(Booking).filter_by(id=booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    extra = db.query(Extra).filter_by(id=body.extra_id).first()
    if not extra:
        raise HTTPException(status_code=404, detail="Extra not found")

    unit_price = body.unit_price if body.unit_price is not None else extra.price
    amount = unit_price * body.quantity

    be = BookingExtra(
        booking_id=booking_id,
        extra_id=body.extra_id,
        quantity=body.quantity,
        unit_price=unit_price,
        amount=amount,
        notes=body.notes,
    )
    db.add(be)
    db.commit()
    db.refresh(be)
    return _serialize_booking_extra(be, extra.name)
def update_booking_extra(
    booking_extra_id: int,
    body: BookingExtraUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    be = db.query(BookingExtra).filter_by(id=booking_extra_id).first()
    if not be:
        raise HTTPException(status_code=404, detail="Booking extra not found")
    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(be, field, value)
    # Recalculate amount if quantity or unit_price changed
    if "quantity" in updates or "unit_price" in updates:
        be.amount = be.unit_price * be.quantity
    db.commit()
    db.refresh(be)
    extra_obj = db.query(Extra).filter_by(id=be.extra_id).first()
    return _serialize_booking_extra(be, extra_obj.name if extra_obj else None)


@router.delete("/api/booking-extras/{booking_extra_id}", status_code=204)
def remove_booking_extra(
    booking_extra_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    be = db.query(BookingExtra).filter_by(id=booking_extra_id).first()
    if not be:
        raise HTTPException(status_code=404, detail="Booking extra not found")
    db.delete(be)
    db.commit()
