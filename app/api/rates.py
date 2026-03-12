"""Rate Plans and Daily Rate Management API.

Routes:
  GET    /api/rate-plans              — list rate plans
  POST   /api/rate-plans              — create rate plan
  GET    /api/rate-plans/{id}         — get rate plan with date rates
  PUT    /api/rate-plans/{id}         — update rate plan
  DELETE /api/rate-plans/{id}         — delete rate plan

  GET    /api/rate-plans/{id}/rates   — list daily rate overrides for a date range
  POST   /api/rate-plans/{id}/rates   — set daily rate override(s)
  DELETE /api/rate-plans/{id}/rates   — bulk clear rates for a date range
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.rate_plan import RateDate, RatePlan

log = structlog.get_logger()
router = APIRouter(prefix="/api/rate-plans", tags=["rates"])


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_plan(rp: RatePlan) -> dict:
    return {
        "id": rp.id,
        "property_id": rp.property_id,
        "room_type_id": rp.room_type_id,
        "name": rp.name,
        "code": rp.code,
        "description": rp.description,
        "base_rate": str(rp.base_rate),
        "currency": rp.currency,
        "min_stay": rp.min_stay,
        "max_stay": rp.max_stay,
        "parent_rate_plan_id": rp.parent_rate_plan_id,
        "is_active": rp.is_active,
        "created_at": rp.created_at.isoformat(),
        "updated_at": rp.updated_at.isoformat(),
    }


def _serialize_date_rate(rd: RateDate) -> dict:
    return {
        "id": rd.id,
        "rate_plan_id": rd.rate_plan_id,
        "date": rd.date.isoformat(),
        "rate": str(rd.rate),
        "min_stay": rd.min_stay,
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RatePlanCreate(BaseModel):
    property_id: int
    room_type_id: Optional[int] = None
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    base_rate: Decimal = Decimal("0")
    currency: str = "USD"
    min_stay: Optional[int] = None
    max_stay: Optional[int] = None
    parent_rate_plan_id: Optional[int] = None
    is_active: bool = True


class RatePlanUpdate(BaseModel):
    room_type_id: Optional[int] = None
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    base_rate: Optional[Decimal] = None
    currency: Optional[str] = None
    min_stay: Optional[int] = None
    max_stay: Optional[int] = None
    parent_rate_plan_id: Optional[int] = None
    is_active: Optional[bool] = None


class RateDateEntry(BaseModel):
    date: date
    rate: Decimal
    min_stay: Optional[int] = None


class BulkRateDateRequest(BaseModel):
    rates: list[RateDateEntry]


# ---------------------------------------------------------------------------
# Rate Plan endpoints
# ---------------------------------------------------------------------------

@router.get("")
def list_rate_plans(
    property_id: Optional[int] = Query(None),
    room_type_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(RatePlan).order_by(RatePlan.property_id, RatePlan.name)
    if property_id is not None:
        q = q.filter_by(property_id=property_id)
    if room_type_id is not None:
        q = q.filter_by(room_type_id=room_type_id)
    if is_active is not None:
        q = q.filter_by(is_active=is_active)
    return [_serialize_plan(rp) for rp in q.all()]


@router.post("", status_code=201)
def create_rate_plan(
    body: RatePlanCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    rp = RatePlan(**body.model_dump())
    db.add(rp)
    db.commit()
    db.refresh(rp)
    log.info("Rate plan created", id=rp.id, name=rp.name)
    return _serialize_plan(rp)


@router.get("/{rate_plan_id}")
def get_rate_plan(
    rate_plan_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    rp = db.query(RatePlan).filter_by(id=rate_plan_id).first()
    if not rp:
        raise HTTPException(status_code=404, detail="Rate plan not found")
    data = _serialize_plan(rp)
    return data


@router.put("/{rate_plan_id}")
def update_rate_plan(
    rate_plan_id: int,
    body: RatePlanUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    rp = db.query(RatePlan).filter_by(id=rate_plan_id).first()
    if not rp:
        raise HTTPException(status_code=404, detail="Rate plan not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(rp, field, value)
    db.commit()
    db.refresh(rp)
    return _serialize_plan(rp)


@router.delete("/{rate_plan_id}", status_code=204)
def delete_rate_plan(
    rate_plan_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    rp = db.query(RatePlan).filter_by(id=rate_plan_id).first()
    if not rp:
        raise HTTPException(status_code=404, detail="Rate plan not found")
    db.delete(rp)
    db.commit()


# ---------------------------------------------------------------------------
# Daily rate date endpoints
# ---------------------------------------------------------------------------

@router.get("/{rate_plan_id}/rates")
def list_rate_dates(
    rate_plan_id: int,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    rp = db.query(RatePlan).filter_by(id=rate_plan_id).first()
    if not rp:
        raise HTTPException(status_code=404, detail="Rate plan not found")
    q = db.query(RateDate).filter_by(rate_plan_id=rate_plan_id)
    if date_from:
        q = q.filter(RateDate.date >= date_from)
    if date_to:
        q = q.filter(RateDate.date <= date_to)
    return [_serialize_date_rate(rd) for rd in q.order_by(RateDate.date).all()]


@router.post("/{rate_plan_id}/rates", status_code=201)
def set_rate_dates(
    rate_plan_id: int,
    body: BulkRateDateRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    """Upsert daily rate overrides. Existing entries for the same date are updated."""
    rp = db.query(RatePlan).filter_by(id=rate_plan_id).first()
    if not rp:
        raise HTTPException(status_code=404, detail="Rate plan not found")

    results = []
    for entry in body.rates:
        existing = (
            db.query(RateDate)
            .filter_by(rate_plan_id=rate_plan_id, date=entry.date)
            .first()
        )
        if existing:
            existing.rate = entry.rate
            if entry.min_stay is not None:
                existing.min_stay = entry.min_stay
            results.append(existing)
        else:
            rd = RateDate(
                rate_plan_id=rate_plan_id,
                date=entry.date,
                rate=entry.rate,
                min_stay=entry.min_stay,
            )
            db.add(rd)
            results.append(rd)

    db.commit()
    for rd in results:
        db.refresh(rd)
    return [_serialize_date_rate(rd) for rd in results]


@router.delete("/{rate_plan_id}/rates", status_code=204)
def clear_rate_dates(
    rate_plan_id: int,
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    """Remove all daily rate overrides for a date range."""
    rp = db.query(RatePlan).filter_by(id=rate_plan_id).first()
    if not rp:
        raise HTTPException(status_code=404, detail="Rate plan not found")
    (
        db.query(RateDate)
        .filter(
            RateDate.rate_plan_id == rate_plan_id,
            RateDate.date >= date_from,
            RateDate.date <= date_to,
        )
        .delete()
    )
    db.commit()
