"""Pre-arrival message scheduling via APScheduler DateTrigger.

Provides two key functions:
1. schedule_pre_arrival_job() — register a one-time job for a booking
2. rebuild_pre_arrival_jobs() — re-register all pending jobs after restart

APScheduler uses MemoryJobStore by default. All scheduled jobs are lost on
Docker restart. rebuild_pre_arrival_jobs() queries communication_logs for
pending pre-arrival entries with future scheduled_for times and re-registers
each one, ensuring no message is missed.

Pre-arrival send time: 14:00 UTC = 9:00 AM EST / 10:00 AM EDT
This covers the Eastern US timezone (Fort Myers Beach) within the
9-10am morning window from the context decision.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import structlog
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.communication_log import CommunicationLog

log = structlog.get_logger()

# Pre-arrival send time: 14:00 UTC = 9am EST / 10am EDT
PRE_ARRIVAL_SEND_HOUR_UTC = 14
PRE_ARRIVAL_SEND_MINUTE_UTC = 0
PRE_ARRIVAL_DAYS_BEFORE = 2


def compute_pre_arrival_send_time(check_in_date: date) -> datetime:
    """Compute the UTC datetime for sending a pre-arrival message.

    Pre-arrival is sent 2 days before check-in at 14:00 UTC
    (9:00 AM EST / 10:00 AM EDT).

    Args:
        check_in_date: Guest check-in date.

    Returns:
        Timezone-aware datetime in UTC.
    """
    send_date = check_in_date - timedelta(days=PRE_ARRIVAL_DAYS_BEFORE)
    return datetime(
        send_date.year,
        send_date.month,
        send_date.day,
        PRE_ARRIVAL_SEND_HOUR_UTC,
        PRE_ARRIVAL_SEND_MINUTE_UTC,
        0,
        tzinfo=timezone.utc,
    )


def schedule_pre_arrival_job(booking_id: int, check_in_date: date) -> datetime | None:
    """Schedule a pre-arrival message job via APScheduler DateTrigger.

    Computes the send time (check_in - 2 days, 14:00 UTC) and registers
    a one-time DateTrigger job. If the send time has already passed,
    logs a warning and returns None (does NOT register a job that would
    silently never fire).

    Uses replace_existing=True so re-importing a booking does not create
    duplicate scheduler jobs.

    Args:
        booking_id: Database ID of the booking.
        check_in_date: Guest check-in date.

    Returns:
        The scheduled datetime (UTC) if job was registered, None if
        the send window has already passed.
    """
    # Import here to avoid circular import (scheduler defined in main.py)
    from app.main import scheduler

    run_at = compute_pre_arrival_send_time(check_in_date)

    if run_at <= datetime.now(timezone.utc):
        log.warning(
            "Pre-arrival send time already passed — skipping schedule",
            booking_id=booking_id,
            run_at=run_at.isoformat(),
            check_in_date=check_in_date.isoformat(),
        )
        return None

    # Import the async job function
    from app.communication.messenger import send_pre_arrival_message

    scheduler.add_job(
        send_pre_arrival_message,
        trigger=DateTrigger(run_date=run_at),
        id=f"pre_arrival_{booking_id}",
        args=[booking_id],
        replace_existing=True,
    )

    log.info(
        "Pre-arrival job scheduled",
        booking_id=booking_id,
        run_at=run_at.isoformat(),
        check_in_date=check_in_date.isoformat(),
    )
    return run_at


async def rebuild_pre_arrival_jobs() -> int:
    """Re-register all pending pre-arrival jobs after app restart.

    Queries communication_logs for entries where:
    - message_type = 'pre_arrival'
    - status = 'pending'
    - scheduled_for > now (still in the future)

    For each, registers a DateTrigger job with the stored scheduled_for time.
    Uses its own DB session (runs in lifespan context, not request context).

    Returns:
        Number of jobs re-registered.
    """
    # Import here to avoid circular import
    from app.main import scheduler
    from app.communication.messenger import send_pre_arrival_message

    db: Session = SessionLocal()
    count = 0

    try:
        now = datetime.now(timezone.utc)
        pending = db.execute(
            select(CommunicationLog).where(
                CommunicationLog.message_type == "pre_arrival",
                CommunicationLog.status == "pending",
                CommunicationLog.scheduled_for > now,
            )
        ).scalars().all()

        for entry in pending:
            scheduler.add_job(
                send_pre_arrival_message,
                trigger=DateTrigger(run_date=entry.scheduled_for),
                id=f"pre_arrival_{entry.booking_id}",
                args=[entry.booking_id],
                replace_existing=True,
            )
            count += 1

        log.info(
            "Pre-arrival jobs rebuilt from database",
            rebuilt_count=count,
            total_pending=len(pending),
        )

    except Exception:
        log.exception("Failed to rebuild pre-arrival jobs")
    finally:
        db.close()

    return count
