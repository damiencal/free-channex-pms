"""Email delivery module for resort booking form submissions.

Provides async SMTP sending via aiosmtplib and a tenacity retry wrapper
for resilient email delivery with exponential backoff.
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


async def send_resort_email(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    form_bytes: bytes,
    confirmation_bytes: bytes | None = None,
) -> None:
    """Send a resort booking form email with PDF attachments via aiosmtplib.

    Attaches the filled booking form PDF and, when provided, the platform
    booking confirmation PDF.  Selects TLS vs STARTTLS based on port number:
    port 465 → use_tls=True, any other port → start_tls=True.

    Args:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port (465 for TLS, 587 for STARTTLS).
        smtp_user: SMTP authentication username.
        smtp_password: SMTP authentication password.
        from_email: Sender email address.
        to_email: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        form_bytes: Filled resort booking form PDF content.
        confirmation_bytes: Platform booking confirmation PDF content, or
            None to omit the second attachment.

    Raises:
        aiosmtplib.SMTPException: If SMTP delivery fails.
    """
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    msg.add_attachment(
        form_bytes,
        maintype="application",
        subtype="pdf",
        filename="booking_form.pdf",
    )

    if confirmation_bytes is not None:
        msg.add_attachment(
            confirmation_bytes,
            maintype="application",
            subtype="pdf",
            filename="booking_confirmation.pdf",
        )

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
        "Resort email sent",
        extra={
            "to": to_email,
            "subject": subject,
            "has_confirmation": confirmation_bytes is not None,
        },
    )


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=10, max=120),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def send_with_retry(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    form_bytes: bytes,
    confirmation_bytes: bytes | None = None,
) -> None:
    """Send a resort booking form email with exponential backoff retry.

    Wraps send_resort_email() with tenacity retry logic:
    - 4 total attempts
    - Exponential backoff: multiplier=2, min=10s, max=120s
    - Logs warnings before each retry sleep via stdlib logging
    - reraise=True: re-raises the final exception after all attempts fail

    All parameters are forwarded directly to send_resort_email().

    Args:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port (465 for TLS, 587 for STARTTLS).
        smtp_user: SMTP authentication username.
        smtp_password: SMTP authentication password.
        from_email: Sender email address.
        to_email: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        form_bytes: Filled resort booking form PDF content.
        confirmation_bytes: Platform booking confirmation PDF content, or
            None to omit the second attachment.

    Raises:
        aiosmtplib.SMTPException: Re-raised after all 4 attempts fail.
    """
    await send_resort_email(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        from_email=from_email,
        to_email=to_email,
        subject=subject,
        body=body,
        form_bytes=form_bytes,
        confirmation_bytes=confirmation_bytes,
    )
