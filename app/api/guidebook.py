"""Guest guidebook API.

Admin CRUD for guidebooks + a public read-only endpoint.

Routes (admin):
  GET    /api/guidebook                  — list all guidebooks
  GET    /api/guidebook/{property_id}    — get guidebook for property
  POST   /api/guidebook/{property_id}    — create/replace guidebook
  PUT    /api/guidebook/{property_id}    — update guidebook
  DELETE /api/guidebook/{property_id}    — delete guidebook

Routes (public — no auth):
  GET  /public/guide/{property_slug}     — rendered HTML guidebook
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_config
from app.db import get_db
from app.models.guidebook import Guidebook
from app.models.property import Property

log = structlog.get_logger()
router = APIRouter(tags=["guidebook"])
public_router = APIRouter(tags=["public"])


class GuidebookRequest(BaseModel):
    title: str = "Guest Guide"
    sections: list[dict[str, Any]] = []
    is_published: bool = False


def _serialize(g: Guidebook) -> dict:
    return {
        "id": g.id,
        "property_id": g.property_id,
        "title": g.title,
        "sections": g.sections or [],
        "is_published": g.is_published,
        "created_at": g.created_at.isoformat(),
        "updated_at": g.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@router.get("/api/guidebook")
def list_guidebooks(db: Session = Depends(get_db)) -> list[dict]:
    return [_serialize(g) for g in db.query(Guidebook).all()]


@router.get("/api/guidebook/{property_id}")
def get_guidebook(property_id: int, db: Session = Depends(get_db)) -> dict:
    g = db.query(Guidebook).filter_by(property_id=property_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Guidebook not found")
    return _serialize(g)


@router.post("/api/guidebook/{property_id}", status_code=201)
def create_guidebook(
    property_id: int,
    body: GuidebookRequest,
    db: Session = Depends(get_db),
) -> dict:
    prop = db.query(Property).filter_by(id=property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    existing = db.query(Guidebook).filter_by(property_id=property_id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Guidebook already exists for this property. Use PUT to update.",
        )
    g = Guidebook(
        property_id=property_id,
        title=body.title,
        sections=body.sections,
        is_published=body.is_published,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return _serialize(g)


@router.put("/api/guidebook/{property_id}")
def update_guidebook(
    property_id: int,
    body: GuidebookRequest,
    db: Session = Depends(get_db),
) -> dict:
    g = db.query(Guidebook).filter_by(property_id=property_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Guidebook not found")
    g.title = body.title
    g.sections = body.sections
    g.is_published = body.is_published
    db.commit()
    db.refresh(g)
    return _serialize(g)


@router.delete("/api/guidebook/{property_id}", status_code=204)
def delete_guidebook(
    property_id: int,
    db: Session = Depends(get_db),
) -> None:
    g = db.query(Guidebook).filter_by(property_id=property_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Guidebook not found")
    db.delete(g)
    db.commit()


# ---------------------------------------------------------------------------
# Public route — no authentication
# ---------------------------------------------------------------------------

_ICON_MAP = {
    "wifi": "📶",
    "key": "🔑",
    "parking": "🅿️",
    "food": "🍽️",
    "rules": "📋",
    "checkin": "🏠",
    "checkout": "👋",
    "local": "📍",
    "emergency": "🚨",
    "pool": "🏊",
    "trash": "🗑️",
    "laundry": "👕",
}


def _render_guidebook_html(prop: Property, g: Guidebook) -> str:
    sections_html = ""
    for sec in sorted(g.sections or [], key=lambda s: s.get("order", 999)):
        icon = _ICON_MAP.get(sec.get("icon", ""), "ℹ️")
        title = sec.get("title", "")
        body = sec.get("body", "").replace("\n", "<br>")
        sections_html += f"""
        <section class="section">
          <h2>{icon} {title}</h2>
          <p>{body}</p>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{g.title} — {prop.display_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f8fafc; color: #1e293b; min-height: 100vh; }}
    header {{ background: #0f172a; color: white; padding: 2rem 1.5rem; }}
    header h1 {{ font-size: 1.75rem; font-weight: 700; }}
    header p {{ opacity: 0.7; margin-top: 0.25rem; }}
    main {{ max-width: 720px; margin: 0 auto; padding: 2rem 1.5rem; }}
    .section {{ background: white; border-radius: 12px; padding: 1.5rem;
                margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
    .section h2 {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 0.75rem;
                   color: #0f172a; }}
    .section p {{ line-height: 1.6; color: #475569; }}
    footer {{ text-align: center; padding: 2rem; color: #94a3b8; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <header>
    <h1>{g.title}</h1>
    <p>{prop.display_name}</p>
  </header>
  <main>{sections_html}
  </main>
  <footer>Have a wonderful stay! 🌴</footer>
</body>
</html>"""


@public_router.get("/public/guide/{property_slug}", response_class=HTMLResponse)
def public_guidebook(property_slug: str, db: Session = Depends(get_db)) -> HTMLResponse:
    """Public guest guidebook — no authentication required."""
    prop = db.query(Property).filter_by(slug=property_slug).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    g = db.query(Guidebook).filter_by(property_id=prop.id).first()
    if not g or not g.is_published:
        raise HTTPException(status_code=404, detail="Guidebook not available")
    return HTMLResponse(content=_render_guidebook_html(prop, g))
