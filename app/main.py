"""
FastAPI application entry point.

Startup sequence (via lifespan):
  1. Load and validate config — FAIL-FAST (SystemExit on any invalid config)
  2. Validate templates — FAIL-FAST (catches variable typos before accepting requests)
  3. Verify database connection — FAIL-FAST (can't operate without DB)
  3b. Sync properties from config YAML → database (upsert)
  4. Check Ollama connectivity — NON-FATAL (LLM features disabled if unavailable)
  5. Start compliance scheduler (daily urgency check)
  6. Rebuild pre-arrival message scheduler jobs from database
  7. Register Channex sync jobs and webhook (if CHANNEX_API_KEY is set)

Run with:
  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import os
from contextlib import asynccontextmanager

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from app.api.accounting import router as accounting_router
from app.api.automation import router as automation_router
from app.api.booking_sites import router as booking_sites_router
from app.api.bookings import router as bookings_router
from app.api.channex import router as channex_router
from app.api.communication import router as communication_router
from app.api.compliance import router as compliance_router
from app.api.custom_fields import router as custom_fields_router
from app.api.dashboard import router as dashboard_router
from app.api.extras import router as extras_router
from app.api.guidebook import public_router as guidebook_public_router
from app.api.guidebook import router as guidebook_router
from app.api.guests import router as guests_router
from app.api.health import router as health_router
from app.api.inbox import router as inbox_router
from app.api.ingestion import router as ingestion_router
from app.api.invoices import public_router as invoices_public_router
from app.api.invoices import router as invoices_router
from app.api.messaging import router as messaging_router
from app.api.night_audit import router as night_audit_router
from app.api.owner import router as owner_router
from app.api.payments import router as payments_router
from app.api.properties import router as properties_router
from app.api.query import router as query_router
from app.api.rates import router as rates_router
from app.api.reports import router as reports_router
from app.api.rooms import router as rooms_router
from app.api.settings import router as settings_router
from app.api.tasks import router as tasks_router
from app.api.taxes import router as taxes_router
from app.api.widget import router as widget_router
from app.api.analytics import router as analytics_router
from app.api.metrics import router as metrics_router
from app.api.connected_accounts import router as connected_accounts_router
from app.api.estimator import router as estimator_router
from app.api.events import router as events_router
from app.api.listing_optimizer import router as listing_optimizer_router
from app.api.pricing import router as pricing_router
from app.auth import router as auth_router
from app.channex.sync import sync_messages_job, sync_reservations_job, sync_reviews_job
from app.communication.scheduler import rebuild_pre_arrival_jobs
from app.compliance.urgency import run_urgency_check
from app.config import load_app_config
from app.db import SessionLocal, engine
from app.logging import configure_logging
from app.models.property import Property
from app.templates import validate_all_templates

configure_logging()
log = structlog.get_logger()

scheduler = AsyncIOScheduler()


class SPAStaticFiles(StarletteStaticFiles):
    """Serve index.html for any non-file path (SPA client-side routing fallback)."""

    async def get_response(self, path: str, scope: dict) -> object:  # type: ignore[override]
        from starlette.responses import Response

        try:
            response = await super().get_response(path, scope)
        except Exception:
            response = await super().get_response("index.html", scope)
        # Prevent caching of index.html so new builds are always picked up
        if path in ("", "index.html", "/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup checks then yield, shutdown on exit."""
    # --- Startup ---
    log.info("Starting Roost")

    # 1. Load and validate config (FAIL-FAST — aborts if invalid)
    config = load_app_config()
    property_slugs = [p.slug for p in config.properties]
    log.info("Config loaded", properties=len(config.properties), slugs=property_slugs)

    # 2. Validate templates (FAIL-FAST — catches variable typos before accepting requests)
    validate_all_templates([p.slug for p in config.properties])

    # 3. Verify DB connection (FAIL-FAST — Alembic migrations should have run first)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("Database connected")
    except Exception as e:
        log.error("Database connection failed", error=str(e))
        raise  # Fatal — can't operate without DB

    # 3b. Sync properties from config YAML → database
    with SessionLocal() as db:
        existing = {p.slug for p in db.query(Property).all()}
        for prop_cfg in config.properties:
            if prop_cfg.slug not in existing:
                db.add(Property(slug=prop_cfg.slug, display_name=prop_cfg.display_name))
                log.info("Property seeded", slug=prop_cfg.slug)
            else:
                # Build update dict — include new dynamic-pricing geo/size columns if set
                updates: dict = {"display_name": prop_cfg.display_name}
                if getattr(prop_cfg, "address", None):
                    updates["address"] = prop_cfg.address
                if getattr(prop_cfg, "city", None):
                    updates["city"] = prop_cfg.city
                if getattr(prop_cfg, "state", None):
                    updates["state"] = prop_cfg.state
                if getattr(prop_cfg, "country", None):
                    updates["country"] = prop_cfg.country
                if getattr(prop_cfg, "latitude", None) is not None:
                    updates["latitude"] = prop_cfg.latitude
                if getattr(prop_cfg, "longitude", None) is not None:
                    updates["longitude"] = prop_cfg.longitude
                if getattr(prop_cfg, "bedrooms", None) is not None:
                    updates["bedrooms"] = prop_cfg.bedrooms
                if getattr(prop_cfg, "bathrooms", None) is not None:
                    updates["bathrooms"] = prop_cfg.bathrooms
                if getattr(prop_cfg, "max_guests", None) is not None:
                    updates["max_guests"] = prop_cfg.max_guests
                if getattr(prop_cfg, "property_type", None):
                    updates["property_type"] = prop_cfg.property_type
                if getattr(prop_cfg, "timezone", None):
                    updates["timezone"] = prop_cfg.timezone
                db.query(Property).filter(Property.slug == prop_cfg.slug).update(
                    updates
                )
        db.commit()
    log.info("Properties synced", count=len(config.properties))

    # 4. Check Ollama connectivity (NON-FATAL — system works without it)
    ollama_url = config.ollama_url
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{ollama_url}/")
        if resp.status_code == 200:
            log.info("Ollama connected", url=ollama_url)
        else:
            log.warning(
                "Ollama responded with unexpected status",
                status=resp.status_code,
                url=ollama_url,
            )
    except Exception:
        log.warning("Ollama unavailable — LLM features disabled", url=ollama_url)

    # 5. Start compliance scheduler (daily urgency check)
    scheduler.add_job(
        run_urgency_check,
        trigger=CronTrigger(hour=8, minute=0),
        id="urgency_check",
        replace_existing=True,
    )
    scheduler.start()
    log.info("Compliance scheduler started (urgency check daily at 08:00)")

    # 6. Rebuild pre-arrival message scheduler jobs from database
    rebuilt_count = await rebuild_pre_arrival_jobs()
    log.info("Pre-arrival scheduler jobs rebuilt", rebuilt_count=rebuilt_count)

    # 7a. Dynamic pricing scheduler jobs (NON-FATAL)
    try:
        from app.pricing.engine import (
            generate_recommendations,
            expire_past_recommendations,
        )
        from app.pricing.analytics import compute_all_properties_metrics
        from app.pricing.providers import InternalMarketDataProvider
        import datetime

        async def _nightly_pricing_job() -> None:
            """Generate 90-day price recommendations for all dynamic/hybrid properties."""
            from app.models.pricing_rule import PricingRule

            with SessionLocal() as db:
                rules = (
                    db.query(PricingRule)
                    .filter(PricingRule.strategy.in_(["dynamic", "hybrid"]))
                    .all()
                )
                provider = InternalMarketDataProvider(db)
                today = datetime.date.today()
                window_end = today + datetime.timedelta(days=90)
                for rule in rules:
                    try:
                        await generate_recommendations(
                            db, rule.property_id, today, window_end, provider
                        )
                    except Exception as exc:
                        log.warning(
                            "Pricing generation failed",
                            property_id=rule.property_id,
                            error=str(exc),
                        )
                expire_past_recommendations(db)

        async def _nightly_metrics_job() -> None:
            """Compute portfolio metrics for the current and previous month."""
            with SessionLocal() as db:
                today = datetime.date.today()
                compute_all_properties_metrics(db, today.year, today.month)
                # Also recompute last month to capture late bookings
                first_of_month = today.replace(day=1)
                last_month = first_of_month - datetime.timedelta(days=1)
                compute_all_properties_metrics(db, last_month.year, last_month.month)

        scheduler.add_job(
            _nightly_pricing_job,
            trigger=CronTrigger(hour=2, minute=0),
            id="nightly_pricing",
            replace_existing=True,
        )
        scheduler.add_job(
            _nightly_metrics_job,
            trigger=CronTrigger(hour=3, minute=0),
            id="nightly_metrics",
            replace_existing=True,
        )
        log.info(
            "Dynamic pricing scheduler jobs registered (02:00 pricing, 03:00 metrics)"
        )
    except Exception as exc:
        log.warning("Dynamic pricing scheduler setup failed", error=str(exc))

    # 7. Channex.io integration (NON-FATAL — system works without it)
    if config.channex_api_key:
        try:
            scheduler.add_job(
                sync_reservations_job,
                trigger=IntervalTrigger(minutes=config.channex_sync_interval_minutes),
                id="channex_reservations_sync",
                replace_existing=True,
            )
            scheduler.add_job(
                sync_messages_job,
                trigger=IntervalTrigger(minutes=30),
                id="channex_messages_sync",
                replace_existing=True,
            )
            scheduler.add_job(
                sync_reviews_job,
                trigger=IntervalTrigger(minutes=60),
                id="channex_reviews_sync",
                replace_existing=True,
            )
            log.info(
                "Channex sync jobs scheduled",
                reservations_interval_minutes=config.channex_sync_interval_minutes,
            )
        except Exception as exc:
            log.warning("Channex scheduler setup failed", error=str(exc))
    else:
        log.info("Channex integration disabled — CHANNEX_API_KEY not set")

    log.info("Startup complete — ready to accept requests")

    yield  # App is running

    # --- Shutdown ---
    scheduler.shutdown()
    log.info("Shutting down")


app = FastAPI(
    title="Roost",
    description="Rental Operations Platform — Self-hosted vacation rental management",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow Vite dev server + widget origins
_widget_origins = os.environ.get("WIDGET_ALLOWED_ORIGINS", "").split(",")
_cors_origins = list(filter(None, ["http://localhost:5173"] + _widget_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r".*" if "*" in _widget_origins else None,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(inbox_router)
app.include_router(ingestion_router)
app.include_router(accounting_router)
app.include_router(bookings_router)
app.include_router(reports_router)
app.include_router(compliance_router)
app.include_router(communication_router)
app.include_router(dashboard_router)
app.include_router(messaging_router)
app.include_router(guidebook_router)
app.include_router(guidebook_public_router)
app.include_router(tasks_router)
app.include_router(owner_router)
app.include_router(widget_router)
app.include_router(query_router)
app.include_router(channex_router)
# Feature-parity routers
app.include_router(properties_router)
app.include_router(rooms_router)
app.include_router(guests_router)
app.include_router(rates_router)
app.include_router(taxes_router)
app.include_router(extras_router)
app.include_router(invoices_router)
app.include_router(invoices_public_router)
app.include_router(payments_router)
app.include_router(night_audit_router)
app.include_router(custom_fields_router)
app.include_router(settings_router)
app.include_router(automation_router)
app.include_router(booking_sites_router)
# Dynamic pricing + analytics routers
app.include_router(pricing_router)
app.include_router(events_router)
app.include_router(analytics_router)
app.include_router(metrics_router)
app.include_router(connected_accounts_router)
app.include_router(estimator_router)
app.include_router(listing_optimizer_router)

# SPA static files — MUST be last (catches all unmatched routes)
# Guarded: app starts without frontend build present (backend-only dev)
if os.path.isdir("frontend/dist"):
    app.mount("/", SPAStaticFiles(directory="frontend/dist", html=True), name="spa")
