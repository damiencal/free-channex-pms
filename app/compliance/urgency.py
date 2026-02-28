"""Daily urgency check for resort booking form submissions.

Runs once per day (via APScheduler) to:
1. Find all pending submissions where check-in is within 3 days
2. Flag them as is_urgent=True in the database
3. Send a single daily digest email to the operator listing all newly-urgent bookings

This ensures no 3-day submission deadline is silently missed.
"""

from datetime import date, timedelta
from email.message import EmailMessage

import aiosmtplib
import structlog
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.config import get_config
from app.db import SessionLocal
from app.models.booking import Booking
from app.models.resort_submission import ResortSubmission

log = structlog.get_logger()

URGENCY_WINDOW_DAYS = 3


async def run_urgency_check() -> None:
    """Check for pending submissions approaching the 3-day deadline.

    Creates its own DB session (not from FastAPI dependency injection)
    because APScheduler runs outside of request context.

    Steps:
    1. Query pending submissions where booking check_in_date <= today + 3 days
    2. Filter to only those not already flagged as urgent (avoid duplicate alerts)
    3. Flag all matches as is_urgent=True
    4. If any newly-urgent bookings found, send a daily digest email to operator

    This function is designed to be called by APScheduler's AsyncIOScheduler.
    """
    config = get_config()
    db: Session = SessionLocal()

    try:
        deadline = date.today() + timedelta(days=URGENCY_WINDOW_DAYS)

        # Find pending, non-urgent submissions with check-in approaching
        stmt = (
            select(ResortSubmission, Booking)
            .join(Booking, ResortSubmission.booking_id == Booking.id)
            .where(
                and_(
                    ResortSubmission.status == "pending",
                    ResortSubmission.is_urgent == False,  # noqa: E712 -- only newly urgent
                    Booking.check_in_date <= deadline,
                )
            )
        )
        rows = db.execute(stmt).all()

        if not rows:
            log.info("Urgency check: no new urgent submissions")
            return

        # Flag all as urgent
        newly_urgent: list[dict] = []
        for submission, booking in rows:
            submission.is_urgent = True
            newly_urgent.append({
                "booking_id": booking.id,
                "guest_name": booking.guest_name,
                "platform_booking_id": booking.platform_booking_id,
                "check_in_date": booking.check_in_date.isoformat(),
                "days_until": (booking.check_in_date - date.today()).days,
            })

        db.commit()

        log.warning(
            "Urgency check: flagged urgent submissions",
            count=len(newly_urgent),
            bookings=[u["platform_booking_id"] for u in newly_urgent],
        )

        # Send digest alert to operator
        await _send_urgency_digest(newly_urgent, config)

    except Exception:
        db.rollback()
        log.exception("Urgency check failed")
    finally:
        db.close()


async def _send_urgency_digest(urgent_bookings: list[dict], config) -> None:
    """Send a single daily digest email listing all newly-urgent submissions.

    Sent to the operator (smtp_from_email), NOT the resort contact.
    Only called when there are actual urgent bookings to report.

    Args:
        urgent_bookings: List of dicts with booking info for the digest.
        config: AppConfig instance.
    """
    if not config.smtp_user or not config.smtp_from_email:
        log.warning("SMTP not configured -- skipping urgency digest email")
        return

    # Build digest body
    lines = ["The following resort booking submissions are URGENT (check-in within 3 days):\n"]
    for booking in urgent_bookings:
        lines.append(
            f"  - {booking['guest_name']} ({booking['platform_booking_id']}) "
            f"-- check-in {booking['check_in_date']} "
            f"({booking['days_until']} days away)"
        )
    lines.append("\nPlease review and submit these bookings via the compliance API.")
    lines.append("POST /compliance/process-pending to process all pending submissions.")

    body = "\n".join(lines)
    subject = f"URGENT: {len(urgent_bookings)} resort submission(s) approaching deadline"

    msg = EmailMessage()
    msg["From"] = config.smtp_from_email
    msg["To"] = config.smtp_from_email  # Operator receives the alert
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        await aiosmtplib.send(
            msg,
            hostname=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_user,
            password=config.smtp_password,
            use_tls=(config.smtp_port == 465),
            start_tls=(config.smtp_port == 587),
        )
        log.info("Urgency digest email sent", count=len(urgent_bookings))
    except Exception:
        # Don't let email failure prevent urgency flagging (DB already committed)
        log.exception("Failed to send urgency digest email")
