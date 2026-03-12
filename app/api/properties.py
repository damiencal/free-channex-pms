"""Properties API — CRUD for rental properties.

Routes:
  GET    /api/properties          — list all properties
  POST   /api/properties          — create a property
  GET    /api/properties/{id}     — get single property
  PUT    /api/properties/{id}     — update property
  POST   /api/properties/{id}/deactivate  — deactivate property
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.property import Property

router = APIRouter(prefix="/api/properties", tags=["properties"])


# ── Schemas ──────────────────────────────────────────────────────────


class PropertyOut(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    max_guests: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    tags: list[str] = []
    groups: list[str] = []
    is_active: bool = True
    allow_overbooking: bool = False
    stop_auto_sync: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyPayload(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    max_guests: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    tags: list[str] = []
    groups: list[str] = []
    allow_overbooking: bool = False
    stop_auto_sync: bool = False


class PropertyPatch(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    max_guests: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    tags: Optional[list[str]] = None
    groups: Optional[list[str]] = None
    allow_overbooking: Optional[bool] = None
    stop_auto_sync: Optional[bool] = None


# ── Helpers ──────────────────────────────────────────────────────────


def _to_out(p: Property) -> PropertyOut:
    return PropertyOut(
        id=p.id,
        name=p.display_name,
        address=p.address,
        city=p.city,
        country=p.country,
        timezone=p.timezone,
        latitude=float(p.latitude) if p.latitude is not None else None,
        longitude=float(p.longitude) if p.longitude is not None else None,
        max_guests=p.max_guests,
        bedrooms=p.bedrooms,
        bathrooms=float(p.bathrooms) if p.bathrooms is not None else None,
        check_in_time=p.check_in_time,
        check_out_time=p.check_out_time,
        tags=p.tags or [],
        groups=p.groups or [],
        is_active=p.is_active,
        allow_overbooking=p.allow_overbooking,
        stop_auto_sync=p.stop_auto_sync,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


# ── Routes ───────────────────────────────────────────────────────────


@router.get("", response_model=list[PropertyOut])
def list_properties(
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    props = db.query(Property).order_by(Property.display_name).all()
    return [_to_out(p) for p in props]


@router.post("", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyPayload,
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
    # Ensure uniqueness
    existing = db.query(Property).filter(Property.slug == slug).first()
    if existing:
        slug = f"{slug}-{int(datetime.now().timestamp())}"

    prop = Property(
        slug=slug,
        display_name=payload.name,
        address=payload.address,
        city=payload.city,
        country=payload.country,
        timezone=payload.timezone,
        latitude=Decimal(str(payload.latitude))
        if payload.latitude is not None
        else None,
        longitude=Decimal(str(payload.longitude))
        if payload.longitude is not None
        else None,
        max_guests=payload.max_guests,
        bedrooms=payload.bedrooms,
        bathrooms=Decimal(str(payload.bathrooms))
        if payload.bathrooms is not None
        else None,
        check_in_time=payload.check_in_time,
        check_out_time=payload.check_out_time,
        tags=payload.tags,
        groups=payload.groups,
        allow_overbooking=payload.allow_overbooking,
        stop_auto_sync=payload.stop_auto_sync,
        is_active=True,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return _to_out(prop)


@router.get("/{prop_id}", response_model=PropertyOut)
def get_property(
    prop_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    prop = db.query(Property).filter(Property.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return _to_out(prop)


@router.put("/{prop_id}", response_model=PropertyOut)
def update_property(
    prop_id: int,
    payload: PropertyPatch,
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    prop = db.query(Property).filter(Property.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        if field == "name":
            prop.display_name = value
        elif field in ("latitude", "longitude"):
            setattr(prop, field, Decimal(str(value)) if value is not None else None)
        elif field == "bathrooms":
            prop.bathrooms = Decimal(str(value)) if value is not None else None
        else:
            setattr(prop, field, value)

    db.commit()
    db.refresh(prop)
    return _to_out(prop)


@router.post("/{prop_id}/deactivate", response_model=PropertyOut)
def deactivate_property(
    prop_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    prop = db.query(Property).filter(Property.id == prop_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    prop.is_active = False
    db.commit()
    db.refresh(prop)
    return _to_out(prop)
