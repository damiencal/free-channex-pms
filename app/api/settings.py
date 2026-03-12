"""Settings API — global application settings and team management.

Routes:
  GET    /api/settings                    — get app settings
  PUT    /api/settings                    — update app settings
  GET    /api/settings/team               — list team members
  POST   /api/settings/team/invite        — invite (create) a team member
  DELETE /api/settings/team/{id}          — remove a team member
"""

from __future__ import annotations

from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth, hash_password
from app.db import get_db
from app.models.user import User

log = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["settings"])

# ---------------------------------------------------------------------------
# Helpers — lazy DB row access
# ---------------------------------------------------------------------------


def _settings_row(db: Session):
    from sqlalchemy import text

    row = db.execute(text("SELECT * FROM app_settings LIMIT 1")).mappings().first()
    if row is None:
        db.execute(
            text("""
            INSERT INTO app_settings (lead_channel, default_check_in_time, default_check_out_time,
                timezone, language, currency, channel_pricing_ratios, tags, custom_channels,
                income_categories, expense_categories)
            VALUES ('direct', '15:00', '11:00', 'America/New_York', 'en', 'USD',
                '{}', '[]', '[]',
                '["Rental Income", "Cleaning Fees", "Other Income"]',
                '["Cleaning", "Maintenance", "Utilities", "Other Expense"]')
        """)
        )
        db.commit()
        row = db.execute(text("SELECT * FROM app_settings LIMIT 1")).mappings().first()
    return row


def _row_to_dict(row) -> dict:
    return {
        "lead_channel": row["lead_channel"] or "direct",
        "default_check_in_time": row["default_check_in_time"] or "15:00",
        "default_check_out_time": row["default_check_out_time"] or "11:00",
        "timezone": row["timezone"] or "America/New_York",
        "language": row["language"] or "en",
        "currency": row["currency"] or "USD",
        "channel_pricing_ratios": row["channel_pricing_ratios"] or {},
        "tags": row["tags"] or [],
        "custom_channels": row["custom_channels"] or [],
        "income_categories": row["income_categories"] or [],
        "expense_categories": row["expense_categories"] or [],
    }


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class SettingsUpdate(BaseModel):
    lead_channel: Optional[str] = None
    default_check_in_time: Optional[str] = None
    default_check_out_time: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    currency: Optional[str] = None
    channel_pricing_ratios: Optional[dict] = None
    tags: Optional[list] = None
    custom_channels: Optional[list] = None
    income_categories: Optional[list] = None
    expense_categories: Optional[list] = None


class InviteRequest(BaseModel):
    email: str
    name: str
    role: str = "staff"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    row = _settings_row(db)
    return _row_to_dict(row)


@router.put("/settings")
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    from sqlalchemy import text

    row = _settings_row(db)
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        return _row_to_dict(row)

    set_clauses = []
    params: dict[str, Any] = {"id": row["id"]}
    for key, val in updates.items():
        set_clauses.append(f"{key} = :{key}")
        params[key] = (
            val if not isinstance(val, (dict, list)) else __import__("json").dumps(val)
        )

    set_clauses.append("updated_at = now()")
    sql = text(f"UPDATE app_settings SET {', '.join(set_clauses)} WHERE id = :id")
    db.execute(sql, params)
    db.commit()

    updated = (
        db.execute(text("SELECT * FROM app_settings WHERE id = :id"), {"id": row["id"]})
        .mappings()
        .first()
    )
    return _row_to_dict(updated)


@router.get("/settings/team")
def list_team(
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    users = (
        db.query(User).filter(User.is_active == True).order_by(User.created_at).all()
    )
    return [_serialize_user(u) for u in users]


@router.post("/settings/team/invite", status_code=201)
def invite_member(
    payload: InviteRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use")

    user = User(
        email=payload.email,
        full_name=payload.name,
        role=payload.role,
        hashed_password=hash_password("changeme123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.delete("/settings/team/{user_id}", status_code=204)
def remove_member(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove owner")
    if user.id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    user.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def _serialize_user(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.full_name,
        "role": u.role,
        "permissions": getattr(u, "permissions", []) or [],
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat(),
    }
