"""
FastAPI application entry point.

Startup sequence (via lifespan):
  1. Load and validate config — FAIL-FAST (SystemExit on any invalid config)
  2. Validate templates — FAIL-FAST (catches variable typos before accepting requests)
  3. Verify database connection — FAIL-FAST (can't operate without DB)
  4. Check Ollama connectivity — NON-FATAL (LLM features disabled if unavailable)

Run with:
  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from sqlalchemy import text

from app.api.health import router as health_router
from app.api.ingestion import router as ingestion_router
from app.config import load_app_config
from app.db import engine
from app.logging import configure_logging
from app.templates import validate_all_templates

configure_logging()
log = structlog.get_logger()


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

    log.info("Startup complete — ready to accept requests")

    yield  # App is running

    # --- Shutdown ---
    log.info("Shutting down")


app = FastAPI(
    title="Rental Management Suite",
    description="Self-hosted vacation rental management platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(ingestion_router)
