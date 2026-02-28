"""Operator notification email for VRBO/RVshare guest messages.

When a VRBO or RVshare message is prepared, the operator receives an email
containing the full rendered message text ready to copy-paste into the
platform's messaging interface.
"""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def _build_notification_body(
    *,
    guest_name: str,
    platform: str,
    platform_booking_id: str,
    check_in_date: str,
    message_type: str,
    rendered_message: str,
) -> str:
    """Build the operator notification email body with copy-paste section.

    The email body includes:
    1. Header with guest/booking info for platform lookup
    2. A clearly delimited copy-paste section with the full message text
    3. A reminder to confirm via the API after sending

    Args:
        guest_name: Guest's name.
        platform: Booking platform (vrbo, rvshare).
        platform_booking_id: Reservation/booking ID for platform lookup.
        check_in_date: Check-in date formatted as string.
        message_type: 'welcome' or 'pre_arrival'.
        rendered_message: Full rendered message text ready for copy-paste.

    Returns:
        Formatted email body string.
    """
    type_display = message_type.replace("_", " ").title()
    platform_display = platform.upper()

    lines = [
        f"[Action Required] {type_display} message ready to send on {platform_display}",
        "",
        f"Guest: {guest_name}",
        f"Reservation ID: {platform_booking_id} (use this to find the conversation in {platform_display})",
        f"Check-in: {check_in_date}",
        "",
        "MESSAGE TO SEND (copy everything below this line):",
        "=" * 60,
        rendered_message,
        "=" * 60,
        "",
        "Once sent, confirm delivery at:",
        "  POST /communication/confirm/<log_id>",
        "  Or use the dashboard to mark as sent (Phase 7).",
    ]
    return "\n".join(lines)


async def send_operator_notification(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    guest_name: str,
    platform: str,
    platform_booking_id: str,
    check_in_date: str,
    message_type: str,
    rendered_message: str,
) -> None:
    """Send an operator notification email for a VRBO/RVshare message.

    The email contains the full message text ready to copy-paste into
    the platform's messaging interface.

    Args:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port (465 for TLS, 587 for STARTTLS).
        smtp_user: SMTP authentication username.
        smtp_password: SMTP authentication password.
        from_email: Sender email address (also the recipient — operator).
        guest_name: Guest's name.
        platform: Booking platform (vrbo, rvshare).
        platform_booking_id: Platform reservation ID.
        check_in_date: Formatted check-in date.
        message_type: 'welcome' or 'pre_arrival'.
        rendered_message: Full rendered message text.

    Raises:
        aiosmtplib.SMTPException: If SMTP delivery fails after retries.
    """
    type_display = message_type.replace("_", " ").title()
    platform_display = platform.upper()
    subject = f"[Action Required] {type_display} message ready - {guest_name} ({platform_display})"

    body = _build_notification_body(
        guest_name=guest_name,
        platform=platform,
        platform_booking_id=platform_booking_id,
        check_in_date=check_in_date,
        message_type=message_type,
        rendered_message=rendered_message,
    )

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = from_email  # Operator receives the alert (same as sender)
    msg["Subject"] = subject
    msg.set_content(body)

    use_tls = smtp_port == 465
    start_tls = not use_tls

    await aiosmtplib.send(
        msg,
        hostname=smtp_host,
        port=smtp_port,
        username=smtp_user,
        password=smtp_password,
        use_tls=use_tls,
        start_tls=start_tls,
    )

    logger.info(
        "Operator notification sent",
        extra={
            "guest_name": guest_name,
            "platform": platform,
            "message_type": message_type,
        },
    )


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=10, max=120),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def send_operator_notification_with_retry(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    guest_name: str,
    platform: str,
    platform_booking_id: str,
    check_in_date: str,
    message_type: str,
    rendered_message: str,
) -> None:
    """Send operator notification with exponential backoff retry.

    Wraps send_operator_notification() with tenacity retry:
    - 4 total attempts
    - Exponential backoff: multiplier=2, min=10s, max=120s
    - reraise=True: re-raises final exception after all attempts fail

    All parameters forwarded to send_operator_notification().
    """
    await send_operator_notification(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        from_email=from_email,
        guest_name=guest_name,
        platform=platform,
        platform_booking_id=platform_booking_id,
        check_in_date=check_in_date,
        message_type=message_type,
        rendered_message=rendered_message,
    )
