"""Night Audit API.

The night audit advances the property's current selling date by one day and
archives a snapshot of that day's activity.

Routes:
  GET    /api/night-audit                    — current selling date + last audit info
  POST   /api/night-audit                    — run the night audit for a property
  GET    /api/night-audit/history            — paginated history of past audits
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.night_audit import NightAuditLog

log = structlog.get_logger()
router = APIRouter(prefix="/api/night-audit", tags=["night-audit"])


def _serialize(na: NightAuditLog) -> dict:
    return {
        "id": na.id,
        "property_id": na.property_id,
        "audit_date": na.audit_date.isoformat(),
        "selling_date": na.selling_date.isoformat(),
        "performed_by": na.performed_by,
        "notes": na.notes,
        "created_at": na.created_at.isoformat(),
    }


class NightAuditRequest(BaseModel):
    property_id: int
    notes: Optional[str] = None


@router.get("")
def current_state(
    property_id: int = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Return the last completed audit and derive the current selling date."""
    last = (
        db.query(NightAuditLog)
        .filter_by(property_id=property_id)
        .order_by(NightAuditLog.selling_date.desc())
        .first()
    )
    if last:
        current_selling_date = last.selling_date
        last_audit = _serialize(last)
    else:
        current_selling_date = date.today()
        last_audit = None

    return {
        "property_id": property_id,
        "current_selling_date": current_selling_date.isoformat(),
        "last_audit": last_audit,
    }


@router.post("", status_code=201)
def run_night_audit(
    body: NightAuditRequest,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
) -> dict:
    """Advance the selling date and record the audit entry.

    The audit_date is today (when the audit is performed) and the new
    selling_date becomes audit_date + 1 day.
    """
    today = date.today()

    # Determine the current selling date to avoid auditing the same date twice
    last = (
        db.query(NightAuditLog)
        .filter_by(property_id=body.property_id)
        .order_by(NightAuditLog.selling_date.desc())
        .first()
    )
    if last and last.audit_date == today:
        raise HTTPException(
            status_code=409,
            detail="Night audit has already been run for today",
        )

    new_selling_date = today + timedelta(days=1)

    na = NightAuditLog(
        property_id=body.property_id,
        audit_date=today,
        selling_date=new_selling_date,
        performed_by=user.get("user_id") if isinstance(user, dict) else None,
        notes=body.notes,
    )
    db.add(na)
    db.commit()
    db.refresh(na)
    log.info("Night audit completed", property_id=body.property_id, selling_date=new_selling_date)
    return _serialize(na)


@router.get("/history")
def audit_history(
    property_id: int = Query(...),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    q = (
        db.query(NightAuditLog)
        .filter_by(property_id=property_id)
        .order_by(NightAuditLog.audit_date.desc())
    )
    total = q.count()
    audits = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": [_serialize(na) for na in audits],
    }
