"""Core guest messaging service.

Coordinates template rendering, message delivery, and communication log
updates. Called by:
- APScheduler for pre-arrival messages (scheduled 2 days before check-in)
- Booking ingestion hooks for welcome messages (immediate on booking)

Platform behavior:
- Airbnb welcome: marked 'native_configured' — Airbnb's native scheduled
  messaging feature handles delivery automatically. The system only tracks
  status; it never renders or sends the welcome message for Airbnb.
- Airbnb pre-arrival: system renders the template text and marks it 'sent'.
  The rendered text is stored for the operator to copy into the Airbnb app's
  messaging interface. This is NOT fully automated — the operator must
  manually send the pre-arrival message via the Airbnb app using the
  rendered text. The system automates preparation, not delivery.
- VRBO/RVshare welcome and pre-arrival: system renders text, emails operator
  with copy-pasteable message, status stays 'pending' until operator confirms
  manual send via API.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.communication.emailer import send_operator_notification_with_retry
from app.config import get_config, PropertyConfig
from app.db import SessionLocal
from app.models.booking import Booking
from app.models.communication_log import CommunicationLog
from app.models.property import Property
from app.templates import render_message_template

log = structlog.get_logger()


def render_guest_message(
    booking: Booking,
    prop_config: PropertyConfig,
    template_name: str,
) -> str:
    """Render a guest message template with booking and property data.

    Builds the full template variable dictionary from the booking ORM model
    and PropertyConfig, then delegates to app.templates.render_message_template().
    Message templates live in templates/messages/ (e.g., welcome.j2,
    pre_arrival.j2) and are shared across all properties — per-property
    data comes from config variables, not per-property template overrides.

    Templates are re-read from disk on each call (hot reload — a new
    Jinja2 Environment is created per render_message_template() call).

    Args:
        booking: Booking ORM instance with guest_name, check_in_date, etc.
        prop_config: PropertyConfig with lock_code, address, wifi, etc.
        template_name: Template filename in templates/messages/
            (e.g., "welcome.j2", "pre_arrival.j2").

    Returns:
        Rendered message text string.

    Raises:
        jinja2.UndefinedError: If a template variable is missing from the data dict.
        jinja2.TemplateNotFound: If the template file does not exist.
    """
    data = {
        "guest_name": booking.guest_name,
        "property_name": prop_config.display_name,
        "checkin_date": booking.check_in_date.strftime("%B %d, %Y"),
        "checkout_date": booking.check_out_date.strftime("%B %d, %Y"),
        "lock_code": prop_config.lock_code,
        "site_number": prop_config.site_number,
        "resort_checkin_instructions": prop_config.resort_checkin_instructions,
        "wifi_password": prop_config.wifi_password,
        "address": prop_config.address,
        "check_in_time": prop_config.check_in_time,
        "check_out_time": prop_config.check_out_time,
        "parking_instructions": prop_config.parking_instructions,
        "local_tips": prop_config.local_tips,
        "custom": prop_config.custom,
        "platform": booking.platform,
    }
    return render_message_template(
        template_name=template_name,
        data=data,
    )


def _find_property_config(slug: str) -> PropertyConfig | None:
    """Find the PropertyConfig matching a property slug.

    Args:
        slug: Property slug (e.g., "jay", "minnie").

    Returns:
        PropertyConfig if found, None otherwise.
    """
    config = get_config()
    for pc in config.properties:
        if pc.slug == slug:
            return pc
    return None


async def send_pre_arrival_message(booking_id: int) -> None:
    """Send or prepare a pre-arrival message for a booking.

    Called by APScheduler DateTrigger at the scheduled send time
    (2 days before check-in, 14:00 UTC). Creates its own DB session
    because APScheduler runs outside FastAPI request context.

    For Airbnb:
      - Renders the template and stores rendered_message
      - Updates status to 'sent' and sets sent_at
      - The rendered text serves as the message the operator sends
        via the Airbnb app (or it matches what Airbnb native messaging sends)

    For VRBO/RVshare:
      - Renders the template and stores rendered_message
      - Sends operator notification email with copy-paste text
      - Updates operator_notified_at but keeps status as 'pending'
      - Status transitions to 'sent' only when operator confirms via API

    Args:
        booking_id: Database ID of the booking.
    """
    db: Session = SessionLocal()
    try:
        # Load communication log entry
        comm_log = db.execute(
            select(CommunicationLog).where(
                CommunicationLog.booking_id == booking_id,
                CommunicationLog.message_type == "pre_arrival",
            )
        ).scalar_one_or_none()

        if comm_log is None:
            log.error("No pre_arrival CommunicationLog found", booking_id=booking_id)
            return

        if comm_log.status == "sent":
            log.info("Pre-arrival already sent, skipping", booking_id=booking_id)
            return

        # Load booking and property
        booking = db.get(Booking, booking_id)
        if booking is None:
            log.error("Booking not found", booking_id=booking_id)
            return

        prop = db.get(Property, booking.property_id)
        if prop is None:
            log.error("Property not found", property_id=booking.property_id)
            return

        prop_config = _find_property_config(prop.slug)
        if prop_config is None:
            log.error("PropertyConfig not found", slug=prop.slug)
            return

        # Render the pre-arrival template (hot reload — reads from disk)
        try:
            rendered = render_guest_message(booking, prop_config, "pre_arrival.j2")
        except Exception as exc:
            comm_log.error_message = f"Template render error: {exc}"
            db.commit()
            log.exception("Pre-arrival template render failed", booking_id=booking_id)
            return

        # Store rendered message for audit trail + VRBO/RVshare copy-paste
        comm_log.rendered_message = rendered

        config = get_config()

        if booking.platform == "airbnb":
            # Airbnb pre-arrival: system renders the message text and sends
            # the operator a notification email with copy-pasteable text.
            # The operator manually sends the message via the Airbnb app.
            # Status stays 'pending' until operator confirms via API.
            try:
                await send_operator_notification_with_retry(
                    smtp_host=config.smtp_host,
                    smtp_port=config.smtp_port,
                    smtp_user=config.smtp_user,
                    smtp_password=config.smtp_password,
                    from_email=config.smtp_from_email,
                    guest_name=booking.guest_name,
                    platform=booking.platform,
                    platform_booking_id=booking.platform_booking_id,
                    check_in_date=booking.check_in_date.strftime("%B %d, %Y"),
                    message_type="pre_arrival",
                    rendered_message=rendered,
                )
                comm_log.operator_notified_at = datetime.now(timezone.utc)
                db.commit()
                log.info(
                    "Airbnb pre-arrival operator notification sent",
                    booking_id=booking_id,
                    guest=booking.guest_name,
                )
            except Exception as exc:
                comm_log.error_message = f"Operator notification failed: {exc}"
                db.commit()
                log.exception(
                    "Airbnb pre-arrival operator notification failed",
                    booking_id=booking_id,
                )
        else:
            # VRBO/RVshare: send operator notification email, keep as pending
            try:
                await send_operator_notification_with_retry(
                    smtp_host=config.smtp_host,
                    smtp_port=config.smtp_port,
                    smtp_user=config.smtp_user,
                    smtp_password=config.smtp_password,
                    from_email=config.smtp_from_email,
                    guest_name=booking.guest_name,
                    platform=booking.platform,
                    platform_booking_id=booking.platform_booking_id,
                    check_in_date=booking.check_in_date.strftime("%B %d, %Y"),
                    message_type="pre_arrival",
                    rendered_message=rendered,
                )
                comm_log.operator_notified_at = datetime.now(timezone.utc)
                db.commit()
                log.info(
                    "Pre-arrival operator notification sent",
                    booking_id=booking_id,
                    platform=booking.platform,
                    guest=booking.guest_name,
                )
            except Exception as exc:
                comm_log.error_message = f"Operator notification failed: {exc}"
                db.commit()
                log.exception(
                    "Pre-arrival operator notification failed",
                    booking_id=booking_id,
                )

    except Exception:
        db.rollback()
        log.exception("send_pre_arrival_message failed", booking_id=booking_id)
    finally:
        db.close()


async def prepare_welcome_message(
    booking_id: int,
    platform: str,
    db: Session,
) -> None:
    """Create a CommunicationLog entry for the welcome message and handle
    VRBO/RVshare operator notification.

    Called during booking ingestion (synchronous DB context from normalizer,
    but the API endpoint fires this as a background task for async email).

    For Airbnb:
      - Creates CommunicationLog with status='native_configured'
      - No message rendered, no email sent (Airbnb handles natively)

    For VRBO/RVshare:
      - Creates CommunicationLog with status='pending'
      - Renders welcome template and stores rendered_message
      - Sends operator notification email with copy-paste text
      - Updates operator_notified_at

    Args:
        booking_id: Database ID of the booking.
        platform: Platform identifier ('airbnb', 'vrbo', 'rvshare').
        db: Active SQLAlchemy session.
    """
    # Check for existing log (idempotent)
    existing = db.execute(
        select(CommunicationLog).where(
            CommunicationLog.booking_id == booking_id,
            CommunicationLog.message_type == "welcome",
        )
    ).scalar_one_or_none()

    if existing is not None:
        return  # Already created — idempotent

    if platform == "airbnb":
        # Airbnb welcome is fully automated via Airbnb's native scheduled
        # messaging feature — the system only records that it is configured.
        # No message is rendered or sent by our system for Airbnb welcome.
        comm_log = CommunicationLog(
            booking_id=booking_id,
            message_type="welcome",
            platform=platform,
            status="native_configured",
        )
        db.add(comm_log)
        db.flush()
        log.info(
            "Airbnb welcome tracked as native_configured",
            booking_id=booking_id,
        )
        return

    # VRBO/RVshare: render welcome and notify operator
    booking = db.get(Booking, booking_id)
    if booking is None:
        log.error("Booking not found for welcome", booking_id=booking_id)
        return

    prop = db.get(Property, booking.property_id)
    if prop is None:
        log.error("Property not found for welcome", property_id=booking.property_id)
        return

    prop_config = _find_property_config(prop.slug)
    if prop_config is None:
        log.error("PropertyConfig not found for welcome", slug=prop.slug)
        return

    # Render welcome template
    try:
        rendered = render_guest_message(booking, prop_config, "welcome.j2")
    except Exception as exc:
        log.exception("Welcome template render failed", booking_id=booking_id)
        comm_log = CommunicationLog(
            booking_id=booking_id,
            message_type="welcome",
            platform=platform,
            status="pending",
            error_message=f"Template render error: {exc}",
        )
        db.add(comm_log)
        db.flush()
        return

    comm_log = CommunicationLog(
        booking_id=booking_id,
        message_type="welcome",
        platform=platform,
        status="pending",
        rendered_message=rendered,
    )
    db.add(comm_log)
    db.flush()

    # Send operator notification email
    config = get_config()
    if not config.smtp_user or not config.smtp_from_email:
        log.warning("SMTP not configured — skipping welcome operator notification")
        return

    try:
        await send_operator_notification_with_retry(
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_user=config.smtp_user,
            smtp_password=config.smtp_password,
            from_email=config.smtp_from_email,
            guest_name=booking.guest_name,
            platform=booking.platform,
            platform_booking_id=booking.platform_booking_id,
            check_in_date=booking.check_in_date.strftime("%B %d, %Y"),
            message_type="welcome",
            rendered_message=rendered,
        )
        comm_log.operator_notified_at = datetime.now(timezone.utc)
        db.flush()
        log.info(
            "Welcome operator notification sent",
            booking_id=booking_id,
            platform=platform,
            guest=booking.guest_name,
        )
    except Exception as exc:
        comm_log.error_message = f"Operator notification failed: {exc}"
        db.flush()
        log.exception(
            "Welcome operator notification failed",
            booking_id=booking_id,
        )
