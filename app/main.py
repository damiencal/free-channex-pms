"""\nFastAPI application entry point.\n\nStartup sequence (via lifespan):\n  1. Load and validate config — FAIL-FAST (SystemExit on any invalid config)\n  2. Validate templates — FAIL-FAST (catches variable typos before accepting requests)\n  3. Verify database connection — FAIL-FAST (can't operate without DB)\n  3b. Sync properties from config YAML → database (upsert)\n  4. Check Ollama connectivity — NON-FATAL (LLM features disabled if unavailable)\n  5. Start compliance scheduler (daily urgency check)\n  6. Rebuild pre-arrival message scheduler jobs from database\n  7. Register Channex sync jobs and webhook (if CHANNEX_API_KEY is set)\n\nRun with:\n  uvicorn app.main:app --host 0.0.0.0 --port 8000\n"""\n\nimport os\nfrom contextlib import asynccontextmanager\n\nimport httpx\nimport structlog\nfrom apscheduler.schedulers.asyncio import AsyncIOScheduler\nfrom apscheduler.triggers.cron import CronTrigger\nfrom apscheduler.triggers.interval import IntervalTrigger\nfrom fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\nfrom sqlalchemy import text\nfrom starlette.staticfiles import StaticFiles as StarletteStaticFiles\n\nfrom app.api.accounting import router as accounting_router\nfrom app.api.channex import router as channex_router\nfrom app.api.communication import router as communication_router\nfrom app.api.compliance import router as compliance_router\nfrom app.api.dashboard import router as dashboard_router\nfrom app.api.health import router as health_router\nfrom app.api.ingestion import router as ingestion_router\nfrom app.api.query import router as query_router\nfrom app.api.reports import router as reports_router\nfrom app.channex.sync import sync_messages_job, sync_reservations_job, sync_reviews_job\nfrom app.communication.scheduler import rebuild_pre_arrival_jobs\nfrom app.compliance.urgency import run_urgency_check\nfrom app.config import load_app_config\nfrom app.db import SessionLocal, engine\nfrom app.logging import configure_logging\nfrom app.models.property import Property\nfrom app.templates import validate_all_templates\n\nconfigure_logging()\nlog = structlog.get_logger()\n\nscheduler = AsyncIOScheduler()\n

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
app.include_router(channex_router)

# SPA static files — MUST be last (catches all unmatched routes)
# Guarded: app starts without frontend build present (backend-only dev)
if os.path.isdir("frontend/dist"):
    app.mount("/", SPAStaticFiles(directory="frontend/dist", html=True), name="spa")
