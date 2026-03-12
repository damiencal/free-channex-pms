"""Owner portal API.

Token-based read-only access for property owners. No login required —
owners access the portal via an opaque token distributed by admins.

Routes (admin):
  POST /api/owner/access            — create / rotate an owner access token
  GET  /api/owner/access            — list all owner access records
  DELETE /api/owner/access/{id}     — revoke access

Routes (owner — token auth via ?token= query param):
  GET  /api/owner/portal            — property info + bookings + P&L summary
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.booking import Booking
from app.models.owner_access import OwnerAccess
from app.models.property import Property

log = structlog.get_logger()
router = APIRouter(prefix="/api/owner", tags=["owner"])


class CreateAccessRequest(BaseModel):
    property_id: int
    owner_name: str
    owner_email: str


def _resolve_token(token: str, db: Session) -> OwnerAccess:
    access = db.query(OwnerAccess).filter_by(token=token, is_active=True).first()
    if not access:
        raise HTTPException(status_code=403, detail="Invalid or revoked access token")
    return access


# ---------------------------------------------------------------------------
# Admin routes (no auth guard — app is single-user for now)
# ---------------------------------------------------------------------------


@router.post("/access", status_code=201)
def create_access(
    body: CreateAccessRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Generate a new owner access token for a property."""
    prop = db.query(Property).filter_by(id=body.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    token = uuid.uuid4().hex + uuid.uuid4().hex  # 64 hex chars
    access = OwnerAccess(
        property_id=body.property_id,
        token=token,
        owner_name=body.owner_name,
        owner_email=body.owner_email,
    )
    db.add(access)
    db.commit()
    db.refresh(access)
    return {
        "id": access.id,
        "property_id": access.property_id,
        "property_name": prop.display_name,
        "owner_name": access.owner_name,
        "owner_email": access.owner_email,
        "token": access.token,
        "portal_url": f"/owner?token={access.token}",
        "created_at": access.created_at.isoformat(),
    }


@router.get("/access")
def list_access(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(OwnerAccess).order_by(OwnerAccess.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "property_id": a.property_id,
            "owner_name": a.owner_name,
            "owner_email": a.owner_email,
            "is_active": a.is_active,
            "token": a.token,
            "portal_url": f"/owner?token={a.token}",
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]


@router.delete("/access/{access_id}", status_code=204)
def revoke_access(access_id: int, db: Session = Depends(get_db)) -> None:
    access = db.query(OwnerAccess).filter_by(id=access_id).first()
    if not access:
        raise HTTPException(status_code=404, detail="Access record not found")
    access.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Owner portal route (token-authenticated)
# ---------------------------------------------------------------------------


@router.get("/portal")
def owner_portal(
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """Read-only owner portal: property info, recent bookings, P&L summary."""
    access = _resolve_token(token, db)
    prop = db.query(Property).filter_by(id=access.property_id).first()

    # Bookings: last 12 months
    from datetime import datetime, timezone
    from dateutil.relativedelta import relativedelta

    twelve_months_ago = (datetime.now(timezone.utc) - relativedelta(months=12)).date()

    bookings = (
        db.query(Booking)
        .filter(
            Booking.property_id == access.property_id,
            Booking.check_in_date >= twelve_months_ago,
        )
        .order_by(Booking.check_in_date.desc())
        .all()
    )

    # Revenue + nights summary
    total_revenue = sum(float(b.net_amount) for b in bookings)
    total_nights = sum((b.check_out_date - b.check_in_date).days for b in bookings)
    platform_breakdown: dict[str, float] = {}
    for b in bookings:
        platform_breakdown[b.platform] = platform_breakdown.get(
            b.platform, 0.0
        ) + float(b.net_amount)

    # Occupancy: nights booked / 365
    occupancy_rate = round(min(total_nights / 365.0, 1.0) * 100, 1)

    return {
        "property": {
            "id": prop.id,
            "slug": prop.slug,
            "display_name": prop.display_name,
        },
        "owner": {
            "name": access.owner_name,
            "email": access.owner_email,
        },
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_bookings": len(bookings),
            "total_nights": total_nights,
            "occupancy_rate_pct": occupancy_rate,
            "platform_breakdown": platform_breakdown,
        },
        "bookings": [
            {
                "id": b.id,
                "platform": b.platform,
                "guest_name": b.guest_name,
                "check_in_date": b.check_in_date.isoformat(),
                "check_out_date": b.check_out_date.isoformat(),
                "net_amount": str(b.net_amount),
                "nights": (b.check_out_date - b.check_in_date).days,
            }
            for b in bookings
        ],
    }
