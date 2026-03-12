"""Triggered message scheduling for MessageTemplate-based automations.

Provides:
  schedule_triggered_messages_for_booking() — register APScheduler jobs for
      each active MessageTemplate that applies to a newly-created booking.
  send_triggered_message()                  — job payload: render template,
      send via Channex or email, update TriggeredMessageLog.

Trigger events and how send time is computed
--------------------------------------------
booking_confirmed  → booking.created_at  + offset_hours
check_in           → booking.check_in_date  at 14:00 UTC + offset_hours
check_out          → booking.check_out_date at 10:00 UTC + offset_hours
review_request     → booking.check_out_date at 10:00 UTC + offset_hours  (positive offset)
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING

import structlog
from apscheduler.triggers.date import DateTrigger
from jinja2 import Template
from sqlalchemy import select

from app.db import SessionLocal
from app.models.booking import Booking
from app.models.message_template import MessageTemplate
from app.models.triggered_message_log import TriggeredMessageLog

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = structlog.get_logger()

# Default send hour (UTC) for date-relative events
_CHECK_IN_SEND_HOUR = 14  # 9am EST / 10am EDT  (2 days before check-in)
_CHECK_OUT_SEND_HOUR = 10  # 5am EST / 6am EDT   (checkout morning)


def _compute_send_time(booking: Booking, template: MessageTemplate) -> datetime:
    """Return timezone-aware UTC datetime for when to fire this template.

    Args:
        booking: The booking the message relates to.
        template: MessageTemplate with trigger_event + offset_hours.

    Returns:
        UTC datetime for the APScheduler job.
    """
    offset = timedelta(hours=template.offset_hours)

    if template.trigger_event == "booking_confirmed":
        base: datetime = booking.created_at
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        return base + offset

    if template.trigger_event in ("check_in",):
        base = datetime(
            booking.check_in_date.year,
            booking.check_in_date.month,
            booking.check_in_date.day,
            _CHECK_IN_SEND_HOUR,
            0,
            0,
            tzinfo=timezone.utc,
        )
        return base + offset

    # check_out or review_request
    base = datetime(
        booking.check_out_date.year,
        booking.check_out_date.month,
        booking.check_out_date.day,
        _CHECK_OUT_SEND_HOUR,
        0,
        0,
        tzinfo=timezone.utc,
    )
    return base + offset


def schedule_triggered_messages_for_booking(booking_id: int, db: "Session") -> int:
    """Register APScheduler jobs for all active templates matching a booking.

    Creates a TriggeredMessageLog row (status='scheduled') for each template
    and registers a DateTrigger job.  Idempotent: templates already logged for
    this booking are skipped.

    Args:
        booking_id: Local Booking.id.
        db: Active SQLAlchemy session.

    Returns:
        Number of jobs scheduled.
    """
    from app.main import scheduler  # late import to avoid circular dependency

    booking = db.get(Booking, booking_id)
    if not booking:
        log.warning(
            "schedule_triggered_messages: booking not found", booking_id=booking_id
        )
        return 0

    templates = (
        db.execute(
            select(MessageTemplate).where(
                MessageTemplate.is_active == True,  # noqa: E712
                (MessageTemplate.property_id == booking.property_id)
                | (MessageTemplate.property_id == None),  # noqa: E711
            )
        )
        .scalars()
        .all()
    )

    if not templates:
        return 0

    # Collect already-scheduled template IDs for this booking
    existing = {
        row.template_id
        for row in db.execute(
            select(TriggeredMessageLog.template_id).where(
                TriggeredMessageLog.booking_id == booking_id
            )
        ).all()
    }

    scheduled = 0
    now = datetime.now(timezone.utc)

    for tmpl in templates:
        if tmpl.id in existing:
            continue

        send_at = _compute_send_time(booking, tmpl)

        if send_at <= now:
            log.info(
                "triggered_message: send time already passed, marking skipped",
                template_id=tmpl.id,
                booking_id=booking_id,
                send_at=send_at.isoformat(),
            )
            db.add(
                TriggeredMessageLog(
                    template_id=tmpl.id,
                    booking_id=booking_id,
                    status="skipped",
                    scheduled_for=send_at,
                )
            )
            continue

        msg_log = TriggeredMessageLog(
            template_id=tmpl.id,
            booking_id=booking_id,
            status="scheduled",
            scheduled_for=send_at,
        )
        db.add(msg_log)
        db.flush()  # get msg_log.id before commit

        job_id = f"triggered_{tmpl.id}_{booking_id}"
        scheduler.add_job(
            send_triggered_message,
            trigger=DateTrigger(run_date=send_at),
            id=job_id,
            args=[msg_log.id],
            replace_existing=True,
        )

        log.info(
            "triggered_message_scheduled",
            job_id=job_id,
            template=tmpl.name,
            booking_id=booking_id,
            send_at=send_at.isoformat(),
        )
        scheduled += 1

    db.commit()
    return scheduled


def send_triggered_message(log_id: int) -> None:
    """APScheduler job: render a MessageTemplate and deliver via configured channel.

    This is a synchronous function called by APScheduler. It opens its own
    DB session (APScheduler runs jobs outside request context).

    Args:
        log_id: TriggeredMessageLog primary key.
    """
    with SessionLocal() as db:
        msg_log = db.get(TriggeredMessageLog, log_id)
        if not msg_log:
            log.error("send_triggered_message: log not found", log_id=log_id)
            return

        if msg_log.status != "scheduled":
            log.info(
                "send_triggered_message: skipping — status not 'scheduled'",
                log_id=log_id,
                status=msg_log.status,
            )
            return

        template: MessageTemplate | None = db.get(MessageTemplate, msg_log.template_id)
        booking: Booking | None = db.get(Booking, msg_log.booking_id)

        if not template or not booking:
            msg_log.status = "failed"
            msg_log.error_message = "template or booking missing"
            db.commit()
            return

        # Render Jinja2 body
        try:
            rendered = Template(template.body_template).render(
                guest_name=booking.guest_name,
                check_in=booking.check_in_date.isoformat(),
                check_out=booking.check_out_date.isoformat(),
                property_id=booking.property_id,
            )
        except Exception as exc:  # noqa: BLE001
            msg_log.status = "failed"
            msg_log.error_message = f"template render error: {exc}"
            db.commit()
            log.error("triggered_message: render error", log_id=log_id, error=str(exc))
            return

        msg_log.rendered_body = rendered

        # Deliver
        try:
            if template.channel == "channex":
                asyncio.run(_send_channex(booking, rendered))
            else:
                asyncio.run(
                    _send_email(booking, template.subject or template.name, rendered)
                )
        except Exception as exc:  # noqa: BLE001
            msg_log.status = "failed"
            msg_log.error_message = str(exc)
            db.commit()
            log.error("triggered_message: send error", log_id=log_id, error=str(exc))
            return

        from datetime import datetime, timezone

        msg_log.status = "sent"
        msg_log.sent_at = datetime.now(timezone.utc)
        db.commit()
        log.info("triggered_message_sent", log_id=log_id, channel=template.channel)


async def _send_channex(booking: Booking, body: str) -> None:
    """Send via Channex messaging API (requires channex_booking_id in raw_platform_data)."""
    from app.channex.client import get_channex_client
    from app.channex.messaging import send_message

    channex_booking_id: str | None = None
    if booking.raw_platform_data:
        channex_booking_id = booking.raw_platform_data.get("channex_booking_id")

    if not channex_booking_id:
        raise ValueError("no channex_booking_id in raw_platform_data for booking")

    async with get_channex_client() as client:
        await send_message(client, channex_booking_id, body)


async def _send_email(booking: Booking, subject: str, body: str) -> None:
    """Send via SMTP email (requires SMTP env vars configured)."""
    import os

    import aiosmtplib
    from email.message import EmailMessage

    guest_email: str | None = None
    if booking.raw_platform_data:
        guest_email = booking.raw_platform_data.get("guest_email")

    if not guest_email:
        raise ValueError("no guest_email available for triggered message email")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_FROM", "noreply@example.com")
    msg["To"] = guest_email
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname=os.environ.get("SMTP_HOST", "localhost"),
        port=int(os.environ.get("SMTP_PORT", "587")),
        username=os.environ.get("SMTP_USER"),
        password=os.environ.get("SMTP_PASS"),
        start_tls=True,
    )
