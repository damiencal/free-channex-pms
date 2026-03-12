"""Triggered messaging API.

CRUD for MessageTemplate + read-only list of TriggeredMessageLog entries.

Routes:
  GET    /api/messaging/templates         — list all templates
  POST   /api/messaging/templates         — create a template
  PUT    /api/messaging/templates/{id}    — update a template
  DELETE /api/messaging/templates/{id}    — delete a template
  GET    /api/messaging/logs              — list triggered message logs
"""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.message_template import MessageTemplate
from app.models.triggered_message_log import TriggeredMessageLog

log = structlog.get_logger()
router = APIRouter(prefix="/api/messaging", tags=["messaging"])

VALID_TRIGGER_EVENTS = {"booking_confirmed", "check_in", "check_out", "review_request"}
VALID_CHANNELS = {"channex", "email"}


class TemplateRequest(BaseModel):
    name: str
    trigger_event: str
    offset_hours: int = 0
    subject: str = ""
    body_template: str
    channel: str = "channex"
    is_active: bool = True
    property_id: Optional[int] = None


def _serialize_template(t: MessageTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "trigger_event": t.trigger_event,
        "offset_hours": t.offset_hours,
        "subject": t.subject,
        "body_template": t.body_template,
        "channel": t.channel,
        "is_active": t.is_active,
        "property_id": t.property_id,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
    }


@router.get("/templates")
def list_templates(
    property_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> list[dict]:
    q = db.query(MessageTemplate).order_by(
        MessageTemplate.trigger_event, MessageTemplate.offset_hours
    )
    if property_id is not None:
        q = q.filter(
            (MessageTemplate.property_id == property_id)
            | (MessageTemplate.property_id.is_(None))
        )
    return [_serialize_template(t) for t in q.all()]


@router.post("/templates", status_code=201)
def create_template(
    body: TemplateRequest,
    db: Session = Depends(get_db),
) -> dict:
    if body.trigger_event not in VALID_TRIGGER_EVENTS:
        raise HTTPException(
            status_code=422,
            detail=f"trigger_event must be one of: {sorted(VALID_TRIGGER_EVENTS)}",
        )
    if body.channel not in VALID_CHANNELS:
        raise HTTPException(
            status_code=422,
            detail=f"channel must be one of: {sorted(VALID_CHANNELS)}",
        )
    template = MessageTemplate(
        name=body.name,
        trigger_event=body.trigger_event,
        offset_hours=body.offset_hours,
        subject=body.subject,
        body_template=body.body_template,
        channel=body.channel,
        is_active=body.is_active,
        property_id=body.property_id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _serialize_template(template)


@router.put("/templates/{template_id}")
def update_template(
    template_id: int,
    body: TemplateRequest,
    db: Session = Depends(get_db),
) -> dict:
    template = db.query(MessageTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if body.trigger_event not in VALID_TRIGGER_EVENTS:
        raise HTTPException(
            status_code=422,
            detail=f"trigger_event must be one of: {sorted(VALID_TRIGGER_EVENTS)}",
        )
    template.name = body.name
    template.trigger_event = body.trigger_event
    template.offset_hours = body.offset_hours
    template.subject = body.subject
    template.body_template = body.body_template
    template.channel = body.channel
    template.is_active = body.is_active
    template.property_id = body.property_id
    db.commit()
    db.refresh(template)
    return _serialize_template(template)


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
) -> None:
    template = db.query(MessageTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()


@router.get("/logs")
def list_logs(
    booking_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
) -> list[dict]:
    q = db.query(TriggeredMessageLog).order_by(TriggeredMessageLog.created_at.desc())
    if booking_id is not None:
        q = q.filter_by(booking_id=booking_id)
    if status:
        q = q.filter_by(status=status)
    logs = q.limit(limit).all()
    return [
        {
            "id": lg.id,
            "template_id": lg.template_id,
            "booking_id": lg.booking_id,
            "status": lg.status,
            "scheduled_for": lg.scheduled_for.isoformat() if lg.scheduled_for else None,
            "sent_at": lg.sent_at.isoformat() if lg.sent_at else None,
            "rendered_body": lg.rendered_body,
            "error_message": lg.error_message,
            "created_at": lg.created_at.isoformat(),
        }
        for lg in logs
    ]
