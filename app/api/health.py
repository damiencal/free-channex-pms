"""
GET /health — system diagnostic endpoint.

Returns a JSON payload with:
  - status: "ok" or "degraded" (degraded if DB unreachable)
  - timestamp: ISO 8601 UTC
  - version: application version
  - properties: list of loaded properties (slug + display_name)
  - database: "connected" or "error: <message>"
  - ollama: "available" or "unavailable"

Ollama unavailability does NOT set status to "degraded" — Ollama is an
optional feature (Phase 8). The endpoint always returns HTTP 200 so that
Docker HEALTHCHECK can target it reliably.
"""

from datetime import datetime, timezone

import httpx
import structlog
from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_config
from app.db import engine

router = APIRouter()
log = structlog.get_logger()


@router.get("/health")
async def health():
    """Detailed health check with DB, Ollama, and config status."""
    config = get_config()

    result = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0",
        "properties": [
            {"slug": p.slug, "display_name": p.display_name}
            for p in config.properties
        ],
    }

    # Database check — failure sets status to "degraded"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["database"] = "connected"
    except Exception as e:
        result["database"] = f"error: {e}"
        result["status"] = "degraded"
        log.warning("Health check: database unreachable", error=str(e))

    # Ollama check — unavailability does NOT affect overall status
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{config.ollama_url}/")
        result["ollama"] = "available" if resp.status_code == 200 else "unavailable"
    except Exception:
        result["ollama"] = "unavailable"

    return result
