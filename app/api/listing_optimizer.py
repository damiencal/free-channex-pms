"""Listing Optimizer API — AI-powered listing quality analysis.

Uses Ollama (or heuristic fallback) to score and recommend improvements for
title, description, photos, amenities, and pricing.

Endpoints:
  POST /api/listing-optimizer/{property_id}/analyze  — trigger analysis
  GET  /api/listing-optimizer/{property_id}/results  — latest result
  GET  /api/listing-optimizer/{property_id}/history  — last N analyses
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.listing_analysis import ListingAnalysis

router = APIRouter(prefix="/api/listing-optimizer", tags=["listing-optimizer"])


def _serialize_analysis(a: ListingAnalysis) -> dict:
    return {
        "id": a.id,
        "property_id": a.property_id,
        "overall_score": a.overall_score,
        "title_score": a.title_score,
        "description_score": a.description_score,
        "photos_score": a.photos_score,
        "amenities_score": a.amenities_score,
        "pricing_score": a.pricing_score,
        "recommendations": a.recommendations_json or [],
        "model_used": a.model_used,
        "analyzed_at": a.analyzed_at.isoformat(),
    }


@router.post("/{property_id}/analyze", status_code=201)
async def analyze_listing(
    property_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Trigger AI analysis of the listing quality for this property.

    Creates a new ListingAnalysis record and returns it immediately.
    Analysis may take a few seconds if Ollama is used.
    """
    from app.pricing.listing_optimizer import analyze_listing as _analyze

    analysis = await _analyze(db, property_id)
    return _serialize_analysis(analysis)


@router.get("/{property_id}/results")
def get_latest_analysis(
    property_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Return the most recent analysis for this property."""
    analysis = (
        db.query(ListingAnalysis)
        .filter(ListingAnalysis.property_id == property_id)
        .order_by(ListingAnalysis.analyzed_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="No analysis found. POST to /{property_id}/analyze to create one.",
        )
    return _serialize_analysis(analysis)


@router.get("/{property_id}/history")
def get_analysis_history(
    property_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    """Return the last N analyses for trend tracking."""
    if limit > 50:
        limit = 50
    analyses = (
        db.query(ListingAnalysis)
        .filter(ListingAnalysis.property_id == property_id)
        .order_by(ListingAnalysis.analyzed_at.desc())
        .limit(limit)
        .all()
    )
    return [_serialize_analysis(a) for a in analyses]
