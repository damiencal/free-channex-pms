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

Run with:
  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import os
from contextlib import asynccontextmanager

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from app.api.accounting import router as accounting_router
from app.api.communication import router as communication_router
from app.api.compliance import router as compliance_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.ingestion import router as ingestion_router
from app.api.query import router as query_router
from app.api.reports import router as reports_router
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
        try:
            return await super().get_response(path, scope)
        except Exception:
            return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup checks then yield, shutdown on exit."""
    # --- Startup ---
    log.info("Starting Rental Management Suite")

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
                # Update display_name if config changed
                db.query(Property).filter(Property.slug == prop_cfg.slug).update(
                    {"display_name": prop_cfg.display_name}
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

    log.info("Startup complete — ready to accept requests")

    yield  # App is running

    # --- Shutdown ---
    scheduler.shutdown()
    log.info("Shutting down")


app = FastAPI(
    title="Rental Management Suite",
    description="Self-hosted vacation rental management platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow Vite dev server to call FastAPI directly (development only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(accounting_router)
app.include_router(reports_router)
app.include_router(compliance_router)
app.include_router(communication_router)
app.include_router(dashboard_router)
app.include_router(query_router)

# SPA static files — MUST be last (catches all unmatched routes)
# Guarded: app starts without frontend build present (backend-only dev)
if os.path.isdir("frontend/dist"):
    app.mount("/", SPAStaticFiles(directory="frontend/dist", html=True), name="spa")
