"""Listing optimizer — AI-powered listing quality analysis using Ollama.

Analyzes a property's listing data and generates prioritized recommendations
for improving title, description, photos, amenities, and pricing.

Uses the existing Ollama integration (already initialized at startup) to
generate natural language analysis via structured prompts.

Output:
  - Category scores (0–100) for title, description, photos, amenities, pricing
  - Overall score (weighted average)
  - Prioritized recommendations list with impact ratings
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog
from sqlalchemy.orm import Session

from app.config import load_app_config
from app.models.booking import Booking
from app.models.listing_analysis import ListingAnalysis
from app.models.property import Property
from app.models.rate_plan import RatePlan

log = structlog.get_logger()

ANALYSIS_PROMPT_TEMPLATE = """You are an expert vacation rental listing analyst. Analyze the following property listing data and provide a structured quality assessment.

Property: {property_name}
Type: {property_type}
Bedrooms: {bedrooms}
Bathrooms: {bathrooms}
Max Guests: {max_guests}
Amenities: {amenities}
Current Base Rate: {base_rate}

Recent Performance:
- Total Bookings (12 months): {booking_count}
- Average Occupancy: {occupancy_pct}%
- Average Daily Rate: ${avg_adr}

Respond ONLY with a valid JSON object in this exact format:
{{
  "overall_score": <0-100 integer>,
  "title_score": <0-100 integer>,
  "description_score": <0-100 integer>,
  "photos_score": <0-100 integer>,
  "amenities_score": <0-100 integer>,
  "pricing_score": <0-100 integer>,
  "score_reasoning": {{
    "title": "<one sentence>",
    "description": "<one sentence>",
    "photos": "<one sentence>",
    "amenities": "<one sentence>",
    "pricing": "<one sentence>"
  }},
  "recommendations": [
    {{
      "priority": "high",
      "category": "title",
      "finding": "<what is wrong or missing>",
      "action": "<specific improvement action>",
      "impact": "<expected improvement outcome>"
    }}
  ]
}}

Focus: Generate 5-8 specific, actionable recommendations ordered by impact (high → medium → low priority).
Score 'photos' based on amenity description completeness as a proxy (no actual photo access).
Score 'title' and 'description' based on what typical high-performing listings include.
Score 'pricing' by comparing the rate to what comparable properties with this profile typically charge.
"""


def _build_listing_data(
    db: Session,
    prop: Property,
) -> dict[str, Any]:
    """Gather listing attributes for analysis."""
    from datetime import date, timedelta

    # Rate plan
    rate_plan = (
        db.query(RatePlan)
        .filter(RatePlan.property_id == prop.id, RatePlan.is_active.is_(True))
        .order_by(RatePlan.id)
        .first()
    )

    # Recent performance
    today = date.today()
    year_ago = today - timedelta(days=365)
    bookings = (
        db.query(Booking)
        .filter(
            Booking.property_id == prop.id,
            Booking.check_in_date >= year_ago,
            Booking.booking_state.notin_(["cancelled", "no_show"]),
        )
        .all()
    )

    booking_count = len(bookings)
    total_nights = sum((b.check_out_date - b.check_in_date).days for b in bookings)
    total_revenue = sum(float(b.net_amount) for b in bookings)
    avg_adr = (total_revenue / total_nights) if total_nights > 0 else 0
    occupancy_pct = round((total_nights / 365) * 100, 1) if booking_count > 0 else 0

    return {
        "property_id": prop.id,
        "property_name": prop.display_name,
        "property_type": prop.property_type or "villa",
        "bedrooms": prop.bedrooms,
        "bathrooms": str(prop.bathrooms) if prop.bathrooms else None,
        "max_guests": prop.max_guests,
        "amenities": prop.amenities_json or [],
        "address": prop.address,
        "city": prop.city,
        "base_rate": str(rate_plan.base_rate) if rate_plan else "N/A",
        "booking_count": booking_count,
        "avg_adr": round(avg_adr, 2),
        "occupancy_pct": occupancy_pct,
        "total_nights": total_nights,
    }


async def analyze_listing(
    db: Session,
    property_id: int,
) -> ListingAnalysis:
    """Run AI analysis on a property listing and store the results.

    Falls back to heuristic scores if Ollama is unavailable.
    """
    config = load_app_config()
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise ValueError(f"Property {property_id} not found")

    listing_data = _build_listing_data(db, prop)

    # Build prompt
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        property_name=listing_data["property_name"],
        property_type=listing_data["property_type"],
        bedrooms=listing_data["bedrooms"] or "N/A",
        bathrooms=listing_data["bathrooms"] or "N/A",
        max_guests=listing_data["max_guests"] or "N/A",
        amenities=", ".join(listing_data["amenities"])
        if listing_data["amenities"]
        else "Not specified",
        base_rate=listing_data["base_rate"],
        booking_count=listing_data["booking_count"],
        occupancy_pct=listing_data["occupancy_pct"],
        avg_adr=listing_data["avg_adr"],
    )

    analysis_result: Optional[dict] = None
    model_used = config.ollama_model

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{config.ollama_url}/api/generate",
                json={
                    "model": config.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            response.raise_for_status()
            ollama_resp = response.json()
            raw_text = ollama_resp.get("response", "{}")
            analysis_result = json.loads(raw_text)

    except Exception as exc:
        log.warning("Ollama listing analysis failed, using heuristics", error=str(exc))
        analysis_result = _heuristic_analysis(listing_data)
        model_used = "heuristic"

    # Validate and extract scores
    overall = _safe_score(analysis_result.get("overall_score"))
    title = _safe_score(analysis_result.get("title_score"))
    description = _safe_score(analysis_result.get("description_score"))
    photos = _safe_score(analysis_result.get("photos_score"))
    amenities = _safe_score(analysis_result.get("amenities_score"))
    pricing = _safe_score(analysis_result.get("pricing_score"))
    recommendations = analysis_result.get("recommendations", [])

    # If overall not computed, derive it
    if overall is None:
        scores = [
            s for s in [title, description, photos, amenities, pricing] if s is not None
        ]
        overall = round(sum(scores) / len(scores)) if scores else 50

    # Create analysis record
    analysis = ListingAnalysis(
        property_id=property_id,
        analyzed_at=datetime.now(timezone.utc),
        overall_score=overall,
        title_score=title,
        description_score=description,
        photos_score=photos,
        amenities_score=amenities,
        pricing_score=pricing,
        recommendations_json=recommendations,
        listing_data_json=listing_data,
        model_used=model_used,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    log.info(
        "Listing analysis complete",
        property_id=property_id,
        overall_score=overall,
        model=model_used,
    )
    return analysis


def _safe_score(value: Any) -> Optional[int]:
    """Clamp score to 0–100 range."""
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return None


def _heuristic_analysis(listing_data: dict) -> dict:
    """Fallback heuristic scoring when Ollama is unavailable."""
    amenities = listing_data.get("amenities") or []
    amenity_count = len(amenities)

    title_score = 75  # We don't have the actual title, assume moderate
    description_score = 70
    photos_score = min(
        100, 40 + amenity_count * 3
    )  # More amenity mentions → higher proxy score
    amenities_score = min(100, 30 + amenity_count * 5)
    pricing_score = 65 if listing_data.get("occupancy_pct", 0) > 60 else 50

    overall = round(
        (
            title_score
            + description_score
            + photos_score
            + amenities_score
            + pricing_score
        )
        / 5
    )

    recommendations = [
        {
            "priority": "high",
            "category": "title",
            "finding": "Title effectiveness cannot be analyzed without listing access",
            "action": "Ensure your title includes: location highlights, property type, and 1-2 key amenities",
            "impact": "Titles with location + amenity keywords rank 20-30% higher in search results",
        },
        {
            "priority": "high",
            "category": "photos",
            "finding": "Photo count and quality assessment requires direct listing review",
            "action": "Aim for 20+ high-quality photos covering all rooms, outdoor spaces, and key amenities",
            "impact": "Listings with 20+ photos convert at 40% higher rates than those with fewer",
        },
        {
            "priority": "medium",
            "category": "amenities",
            "finding": f"Currently {amenity_count} amenities listed in property profile",
            "action": "Review and add any missing amenities: WiFi speed, streaming services, kitchen equipment",
            "impact": "Complete amenity lists reduce pre-booking inquiries and improve search ranking",
        },
        {
            "priority": "medium",
            "category": "description",
            "finding": "Description quality assessment requires direct listing review",
            "action": "Structure description: hook sentence → key features → neighborhood → call to action",
            "impact": "Well-structured descriptions increase booking conversion by 15-25%",
        },
        {
            "priority": "low",
            "category": "pricing",
            "finding": f"Current occupancy: {listing_data.get('occupancy_pct', 0)}%",
            "action": "Enable dynamic pricing to automatically optimize rates based on demand signals",
            "impact": f"Properties with dynamic pricing typically achieve 15-20% higher RevPAR",
        },
    ]

    return {
        "overall_score": overall,
        "title_score": title_score,
        "description_score": description_score,
        "photos_score": photos_score,
        "amenities_score": amenities_score,
        "pricing_score": pricing_score,
        "recommendations": recommendations,
    }
