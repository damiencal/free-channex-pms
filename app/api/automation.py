"""Automation rules CRUD API."""

from typing import Optional, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from app.auth import require_auth
from app.db import get_db

router = APIRouter(prefix="/api/automation", tags=["automation"])


class AutomationRulePayload(BaseModel):
    name: str
    type: str
    trigger: str
    is_active: bool = True
    property_id: Optional[int] = None
    channel: Optional[str] = None
    conditions: dict[str, Any] = {}
    actions: dict[str, Any] = {}


def _row_to_dict(row) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "type": row.type,
        "trigger": row.trigger,
        "is_active": row.is_active,
        "property_id": row.property_id,
        "channel": row.channel,
        "conditions": row.conditions or {},
        "actions": row.actions or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/rules")
def list_rules(
    property_id: Optional[int] = None,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    if property_id:
        rows = db.execute(
            text(
                "SELECT * FROM automation_rules WHERE property_id = :p OR property_id IS NULL ORDER BY created_at DESC"
            ),
            {"p": property_id},
        ).fetchall()
    else:
        rows = db.execute(
            text("SELECT * FROM automation_rules ORDER BY created_at DESC")
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.post("/rules", status_code=201)
def create_rule(
    payload: AutomationRulePayload,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    import json

    row = db.execute(
        text("""
            INSERT INTO automation_rules (name, type, trigger, is_active, property_id, channel, conditions, actions)
            VALUES (:name, :type, :trigger, :is_active, :property_id, :channel, CAST(:conditions AS jsonb), CAST(:actions AS jsonb))
            RETURNING *
        """),
        {
            "name": payload.name,
            "type": payload.type,
            "trigger": payload.trigger,
            "is_active": payload.is_active,
            "property_id": payload.property_id,
            "channel": payload.channel,
            "conditions": json.dumps(payload.conditions),
            "actions": json.dumps(payload.actions),
        },
    ).fetchone()
    db.commit()
    return _row_to_dict(row)


@router.put("/rules/{rule_id}")
def update_rule(
    rule_id: int,
    payload: AutomationRulePayload,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    import json

    row = db.execute(
        text("""
            UPDATE automation_rules
            SET name = :name, type = :type, trigger = :trigger,
                is_active = :is_active, property_id = :property_id,
                channel = :channel, conditions = CAST(:conditions AS jsonb),
                actions = CAST(:actions AS jsonb),
                updated_at = now()
            WHERE id = :id
            RETURNING *
        """),
        {
            "id": rule_id,
            "name": payload.name,
            "type": payload.type,
            "trigger": payload.trigger,
            "is_active": payload.is_active,
            "property_id": payload.property_id,
            "channel": payload.channel,
            "conditions": json.dumps(payload.conditions),
            "actions": json.dumps(payload.actions),
        },
    ).fetchone()
    db.commit()
    if not row:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Rule not found")
    return _row_to_dict(row)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    db.execute(text("DELETE FROM automation_rules WHERE id = :id"), {"id": rule_id})
    db.commit()


@router.post("/rules/{rule_id}/toggle")
def toggle_rule(
    rule_id: int,
    body: dict,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    row = db.execute(
        text(
            "UPDATE automation_rules SET is_active = :v, updated_at = now() WHERE id = :id RETURNING *"
        ),
        {"v": body.get("is_active", True), "id": rule_id},
    ).fetchone()
    db.commit()
    if not row:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Rule not found")
    return _row_to_dict(row)


@router.get("/pending")
def list_pending(
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    rows = db.execute(
        text("""
            SELECT al.*, ar.type
            FROM automation_action_log al
            JOIN automation_rules ar ON al.rule_id = ar.id
            WHERE al.status = 'pending'
            ORDER BY al.created_at DESC
            LIMIT 50
        """)
    ).fetchall()
    result = []
    for r in rows:
        result.append(
            {
                "id": r.id,
                "type": r.type,
                "event": r.event,
                "date": r.date,
                "property_name": r.property_name,
                "channel": r.channel,
                "status": r.status,
            }
        )
    return result
