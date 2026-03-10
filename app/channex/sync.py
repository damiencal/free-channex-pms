"""Background sync jobs for Channex.io.

These functions are registered as APScheduler jobs in ``app/main.py``.
Each job creates its own DB session and Channex client, runs the sync,
then closes both — matching the pattern used in the compliance scheduler.

Jobs registered:
  - ``channex_reservations_sync``  — every N minutes (configurable)
  - ``channex_messages_sync``      — every 30 minutes
  - ``channex_reviews_sync``       — every 60 minutes
  - ``channex_webhook_register``   — once at startup (not recurring)

Webhook registration:
  On startup, the app registers its own public URL with Channex as a webhook
  subscriber. This ensures Channex always has the correct callback URL.
  The operator supplies the public URL via ``POST /api/channex/webhooks/register``.
  During development a tunnel (ngrok/cloudflared) is required.
"""

from __future__ import annotations

import structlog

from app.channex.client import get_channex_client
from app.channex.messaging import sync_all_messages
from app.channex.reservations import sync_all_reservations
from app.channex.reviews import sync_all_reviews
from app.db import SessionLocal

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Scheduler jobs (called by APScheduler — must be async)
# ---------------------------------------------------------------------------


async def sync_reservations_job() -> None:
    """Pull new/modified bookings from Channex and upsert into local DB."""
    try:
        async with get_channex_client() as client:
            with SessionLocal() as db:
                result = await sync_all_reservations(db, client)
        log.info("channex_reservations_job_complete", **result)
    except Exception as exc:
        log.error("channex_reservations_job_failed", error=str(exc))


async def sync_messages_job() -> None:
    """Pull new messages from Channex and sync to ``channex_messages``."""
    try:
        async with get_channex_client() as client:
            with SessionLocal() as db:
                result = await sync_all_messages(db, client)
        log.info("channex_messages_job_complete", **result)
    except Exception as exc:
        log.error("channex_messages_job_failed", error=str(exc))


async def sync_reviews_job() -> None:
    """Pull new reviews from Channex and sync to ``channex_reviews``."""
    try:
        async with get_channex_client() as client:
            with SessionLocal() as db:
                result = await sync_all_reviews(db, client)
        log.info("channex_reviews_job_complete", **result)
    except Exception as exc:
        log.error("channex_reviews_job_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Webhook registration
# ---------------------------------------------------------------------------


async def register_webhook(callback_url: str) -> dict:
    """Register (or update) this app's webhook URL with Channex.

    Called once on startup (if ``channex_api_key`` is configured) and also
    exposed as ``POST /api/channex/webhooks/register`` for operator use.

    Args:
        callback_url: The fully-qualified public URL that Channex should
            POST to, e.g. ``https://my-app.example.com/api/channex/webhooks``.

    Returns:
        The Channex API response dict for the created/updated subscription.
    """
    async with get_channex_client() as client:
        result = await client.post(
            "/webhooks",
            json={
                "webhook": {
                    "callback_url": callback_url,
                    "event_mask": [
                        "bookings_new",
                        "bookings_modified",
                        "bookings_cancelled",
                        "messages_new",
                        "reviews_new",
                    ],
                    "is_active": True,
                }
            },
        )
    log.info("channex_webhook_registered", callback_url=callback_url)
    return result
