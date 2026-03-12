"""Cleaning tasks API.

CRUD for housekeeping tasks with optional email notifications.

Routes:
  GET    /api/tasks               — list tasks
  POST   /api/tasks               — create manual task
  PUT    /api/tasks/{id}          — update task (status, assignment, notes)
  DELETE /api/tasks/{id}          — delete task
  POST   /api/tasks/{id}/notify  — email assignment notification to assigned_to
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.communication.emailer import send_operator_notification_with_retry
from app.config import get_config
from app.db import get_db
from app.models.booking import Booking
from app.models.cleaning_task import CleaningTask
from app.models.property import Property

log = structlog.get_logger()
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    property_id: int
    scheduled_date: date
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    booking_id: Optional[int] = None


class UpdateTaskRequest(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


VALID_STATUSES = {"pending", "in_progress", "completed", "skipped"}


def _serialize(t: CleaningTask, booking: Optional[Booking] = None) -> dict:
    return {
        "id": t.id,
        "booking_id": t.booking_id,
        "property_id": t.property_id,
        "scheduled_date": t.scheduled_date.isoformat(),
        "assigned_to": t.assigned_to,
        "status": t.status,
        "notes": t.notes,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
        # Booking context for display
        "guest_name": booking.guest_name if booking else None,
        "check_out_date": booking.check_out_date.isoformat() if booking else None,
    }


@router.get("")
def list_tasks(
    property_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
) -> list[dict]:
    q = db.query(CleaningTask).order_by(CleaningTask.scheduled_date.asc())
    if property_id is not None:
        q = q.filter_by(property_id=property_id)
    if status:
        q = q.filter_by(status=status)
    if date_from:
        q = q.filter(CleaningTask.scheduled_date >= date_from)
    if date_to:
        q = q.filter(CleaningTask.scheduled_date <= date_to)
    tasks = q.limit(limit).all()
    booking_cache: dict[int, Booking] = {}
    result = []
    for t in tasks:
        booking = None
        if t.booking_id:
            if t.booking_id not in booking_cache:
                b = db.query(Booking).filter_by(id=t.booking_id).first()
                if b:
                    booking_cache[t.booking_id] = b
            booking = booking_cache.get(t.booking_id)
        result.append(_serialize(t, booking))
    return result


@router.post("", status_code=201)
def create_task(
    body: CreateTaskRequest,
    db: Session = Depends(get_db),
) -> dict:
    prop = db.query(Property).filter_by(id=body.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    task = CleaningTask(
        property_id=body.property_id,
        booking_id=body.booking_id,
        scheduled_date=body.scheduled_date,
        assigned_to=body.assigned_to,
        notes=body.notes,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize(task)


@router.put("/{task_id}")
def update_task(
    task_id: int,
    body: UpdateTaskRequest,
    db: Session = Depends(get_db),
) -> dict:
    task = db.query(CleaningTask).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if body.status is not None:
        if body.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"status must be one of {sorted(VALID_STATUSES)}",
            )
        task.status = body.status
        if body.status == "completed" and not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)
    if body.assigned_to is not None:
        task.assigned_to = body.assigned_to
    if body.notes is not None:
        task.notes = body.notes
    db.commit()
    db.refresh(task)
    booking = (
        db.query(Booking).filter_by(id=task.booking_id).first()
        if task.booking_id
        else None
    )
    return _serialize(task, booking)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)) -> None:
    task = db.query(CleaningTask).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


async def _send_assignment_email(
    task: CleaningTask,
    booking: Optional[Booking],
    prop: Property,
) -> None:
    """Send assignment notification email to the cleaner."""
    config = get_config()
    if not config.smtp_user or not task.assigned_to:
        return

    guest_info = ""
    if booking:
        guest_info = (
            f"\nGuest: {booking.guest_name}"
            f"\nCheck-out: {booking.check_out_date.strftime('%B %d, %Y')}"
        )

    content = (
        f"You have been assigned a cleaning task at {prop.display_name}.\n"
        f"\nProperty: {prop.display_name}"
        f"\nDate: {task.scheduled_date.strftime('%B %d, %Y')}"
        f"{guest_info}"
        f"\n\nNotes: {task.notes or 'None'}"
        f"\n\nPlease confirm completion in the dashboard."
    )

    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = (
        f"Cleaning assignment: {prop.display_name} on {task.scheduled_date}"
    )
    msg["From"] = config.smtp_from_email or config.smtp_user
    msg["To"] = task.assigned_to
    msg.set_content(content)

    try:
        import aiosmtplib

        await aiosmtplib.send(
            msg,
            hostname=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_user,
            password=config.smtp_password,
            start_tls=True,
        )
        log.info(
            "cleaning_task_notification_sent", task_id=task.id, to=task.assigned_to
        )
    except Exception as exc:
        log.error("cleaning_task_notification_failed", task_id=task.id, error=str(exc))


@router.post("/{task_id}/notify")
async def notify_assigned(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """Send an email notification to the person assigned to this task."""
    task = db.query(CleaningTask).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.assigned_to:
        raise HTTPException(
            status_code=422, detail="Task has no assigned_to email/name"
        )
    prop = db.query(Property).filter_by(id=task.property_id).first()
    booking = (
        db.query(Booking).filter_by(id=task.booking_id).first()
        if task.booking_id
        else None
    )
    background_tasks.add_task(_send_assignment_email, task, booking, prop)
    return {"ok": True, "message": f"Notification queued for {task.assigned_to}"}
