"""Booking widget public API.

CORS-enabled public endpoints for embeddable booking widgets.
No authentication required — these are consumed by external websites.

Routes:
  GET  /api/widget/{slug}/info          — property info for widget display
  GET  /api/widget/{slug}/availability  — check date availability
  POST /api/widget/{slug}/inquiry       — submit a booking inquiry
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.booking import Booking
from app.models.guidebook import Guidebook
from app.models.property import Property

log = structlog.get_logger()
router = APIRouter(prefix="/api/widget", tags=["widget"])


class InquiryRequest(BaseModel):
    guest_name: str
    guest_email: str
    guest_phone: str = ""
    check_in_date: date
    check_out_date: date
    message: str = ""


@router.get("/{slug}/info")
def widget_property_info(slug: str, db: Session = Depends(get_db)) -> dict:
    """Return public property information for widget display."""
    prop = db.query(Property).filter_by(slug=slug).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    # Include published guidebook sections for display
    g = db.query(Guidebook).filter_by(property_id=prop.id).first()
    sections = []
    if g and g.is_published:
        sections = g.sections or []

    return {
        "slug": prop.slug,
        "display_name": prop.display_name,
        "guidebook_sections": sections,
    }


@router.get("/{slug}/availability")
def check_availability(
    slug: str,
    check_in: date = Query(...),
    check_out: date = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """Check if dates are available (no confirmed booking overlap)."""
    if check_out <= check_in:
        raise HTTPException(status_code=422, detail="check_out must be after check_in")

    prop = db.query(Property).filter_by(slug=slug).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    # A conflict exists if an existing booking overlaps the requested range.
    # Two date ranges [A,B) and [C,D) overlap iff A < D and C < B.
    conflict = (
        db.query(Booking)
        .filter(
            Booking.property_id == prop.id,
            Booking.check_in_date < check_out,
            Booking.check_out_date > check_in,
        )
        .first()
    )

    return {
        "available": conflict is None,
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "nights": (check_out - check_in).days,
    }


@router.post("/{slug}/inquiry", status_code=201)
def submit_inquiry(
    slug: str,
    body: InquiryRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Submit a booking inquiry from an external widget.

    Creates a booking record with platform='inquiry' and
    reconciliation_status='unmatched'. The operator sees it
    in the dashboard and can convert it to a confirmed direct booking.
    """
    if body.check_out_date <= body.check_in_date:
        raise HTTPException(status_code=422, detail="check_out must be after check_in")

    prop = db.query(Property).filter_by(slug=slug).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    import uuid

    ref = f"INQ-{uuid.uuid4().hex[:8].upper()}"

    booking = Booking(
        platform="inquiry",
        platform_booking_id=ref,
        property_id=prop.id,
        guest_name=body.guest_name,
        check_in_date=body.check_in_date,
        check_out_date=body.check_out_date,
        net_amount=0,
        reconciliation_status="unmatched",
        raw_platform_data={
            "source": "widget_inquiry",
            "guest_email": body.guest_email,
            "guest_phone": body.guest_phone,
            "message": body.message,
        },
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    log.info("widget_inquiry_created", ref=ref, property_slug=slug)
    return {
        "ok": True,
        "reference": ref,
        "message": "Your inquiry has been received. The host will contact you shortly.",
    }
