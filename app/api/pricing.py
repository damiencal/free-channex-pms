"""Pricing API — recommendations, rules, and manual price generation.

Endpoints:
  GET    /api/pricing/recommendations    — list with filters
  POST   /api/pricing/recommendations/{id}/accept
  POST   /api/pricing/recommendations/{id}/reject
  POST   /api/pricing/recommendations/bulk-accept
  POST   /api/pricing/generate           — trigger generation for date range
  GET    /api/pricing/rules/{property_id}
  PUT    /api/pricing/rules/{property_id}
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.price_recommendation import PriceRecommendation
from app.models.pricing_rule import PricingRule

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AcceptPayload(BaseModel):
    price: Optional[float] = None  # override the recommended price


class RejectPayload(BaseModel):
    reason: Optional[str] = None


class BulkAcceptPayload(BaseModel):
    ids: list[int]
    price: Optional[float] = None  # applied to all


class GeneratePayload(BaseModel):
    property_id: int
    date_from: date
    date_to: date

    @field_validator("date_to")
    @classmethod
    def date_to_after_from(cls, v: date, info) -> date:
        date_from = info.data.get("date_from")
        if date_from and v < date_from:
            raise ValueError("date_to must be >= date_from")
        if date_from and (v - date_from).days > 365:
            raise ValueError("date range cannot exceed 365 days")
        return v


class PricingRulePayload(BaseModel):
    strategy: str = "dynamic"
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    weekend_markup_pct: float = 15.0
    orphan_day_discount_pct: float = 20.0
    last_minute_window_days: int = 7
    last_minute_discount_pct: float = 15.0
    early_bird_window_days: int = 90
    early_bird_discount_pct: float = 10.0
    demand_sensitivity: float = 0.50
    min_stay: int = 1
    weekend_min_stay: int = 2

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v not in ("manual", "dynamic", "hybrid"):
            raise ValueError("strategy must be manual, dynamic, or hybrid")
        return v


def _serialize_rec(r: PriceRecommendation) -> dict:
    return {
        "id": r.id,
        "property_id": r.property_id,
        "date": r.date.isoformat(),
        "recommended_price": str(r.recommended_price),
        "base_price": str(r.base_price),
        "min_stay": r.recommended_min_stay,
        "status": r.status,
        "accepted_price": str(r.accepted_price) if r.accepted_price else None,
        "rejection_reason": r.rejection_reason,
        "demand_score": str(r.demand_score) if r.demand_score else None,
        "seasonal_factor": str(r.seasonal_factor) if r.seasonal_factor else None,
        "event_factor": str(r.event_factor) if r.event_factor else None,
        "weekend_factor": str(r.weekend_factor) if r.weekend_factor else None,
        "last_minute_factor": str(r.last_minute_factor)
        if r.last_minute_factor
        else None,
        "early_bird_factor": str(r.early_bird_factor) if r.early_bird_factor else None,
        "confidence": str(r.confidence) if r.confidence else None,
        "generated_at": r.created_at.isoformat(),
    }


def _serialize_rule(r: PricingRule) -> dict:
    return {
        "id": r.id,
        "property_id": r.property_id,
        "strategy": r.strategy,
        "min_price": str(r.min_price) if r.min_price else None,
        "max_price": str(r.max_price) if r.max_price else None,
        "weekend_markup_pct": str(r.weekend_markup_pct),
        "orphan_day_discount_pct": str(r.orphan_day_discount_pct),
        "last_minute_window_days": r.last_minute_window_days,
        "last_minute_discount_pct": str(r.last_minute_discount_pct),
        "early_bird_window_days": r.early_bird_window_days,
        "early_bird_discount_pct": str(r.early_bird_discount_pct),
        "demand_sensitivity": str(r.demand_sensitivity),
        "min_stay": r.min_stay_default if r.min_stay_default is not None else 1,
        "weekend_min_stay": r.weekend_min_stay if r.weekend_min_stay is not None else 2,
        "updated_at": r.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


@router.get("/recommendations")
def list_recommendations(
    property_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(PriceRecommendation)
    if property_id is not None:
        q = q.filter(PriceRecommendation.property_id == property_id)
    if date_from:
        q = q.filter(PriceRecommendation.date >= date_from)
    if date_to:
        q = q.filter(PriceRecommendation.date <= date_to)
    if status:
        q = q.filter(PriceRecommendation.status == status)
    recs = q.order_by(PriceRecommendation.property_id, PriceRecommendation.date).all()
    return [_serialize_rec(r) for r in recs]


@router.post("/recommendations/{rec_id}/accept")
def accept_recommendation(
    rec_id: int,
    payload: AcceptPayload = AcceptPayload(),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    rec = db.query(PriceRecommendation).filter(PriceRecommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if rec.status not in ("pending", "rejected"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot accept a recommendation with status '{rec.status}'",
        )

    from datetime import datetime, timezone

    rec.status = "accepted"
    rec.accepted_price = (
        Decimal(str(payload.price)) if payload.price else rec.recommended_price
    )
    rec.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Write the accepted price to RateDates and push to Channex ARI
    _apply_accepted_price(db, rec)

    db.refresh(rec)
    return _serialize_rec(rec)


@router.post("/recommendations/{rec_id}/reject")
def reject_recommendation(
    rec_id: int,
    payload: RejectPayload = RejectPayload(),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    rec = db.query(PriceRecommendation).filter(PriceRecommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if rec.status == "accepted":
        raise HTTPException(
            status_code=409, detail="Cannot reject an already-accepted recommendation"
        )

    from datetime import datetime, timezone

    rec.status = "rejected"
    rec.rejection_reason = payload.reason
    rec.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)
    return _serialize_rec(rec)


@router.post("/recommendations/bulk-accept")
def bulk_accept_recommendations(
    payload: BulkAcceptPayload,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    if not payload.ids:
        raise HTTPException(status_code=422, detail="ids list cannot be empty")
    if len(payload.ids) > 500:
        raise HTTPException(
            status_code=422,
            detail="Cannot bulk-accept more than 500 recommendations at once",
        )

    from datetime import datetime, timezone

    recs = (
        db.query(PriceRecommendation)
        .filter(
            PriceRecommendation.id.in_(payload.ids),
            PriceRecommendation.status == "pending",
        )
        .all()
    )
    override_price = Decimal(str(payload.price)) if payload.price else None
    now = datetime.now(timezone.utc)
    for rec in recs:
        rec.status = "accepted"
        rec.accepted_price = override_price if override_price else rec.recommended_price
        rec.updated_at = now
        _apply_accepted_price(db, rec)

    db.commit()
    return {"accepted": len(recs), "requested": len(payload.ids)}


@router.post("/generate")
async def generate_recommendations(
    payload: GeneratePayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Trigger on-demand HLP price generation for a property and date range.

    Runs in a background task — returns immediately with a job reference.
    Poll /api/pricing/recommendations to see the results.
    """
    background_tasks.add_task(
        _run_generation_background,
        payload.property_id,
        payload.date_from,
        payload.date_to,
    )
    return {
        "status": "queued",
        "property_id": payload.property_id,
        "date_from": payload.date_from.isoformat(),
        "date_to": payload.date_to.isoformat(),
        "message": "Price generation started. Check /api/pricing/recommendations for results.",
    }


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


@router.get("/rules/{property_id}")
def get_pricing_rule(
    property_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    rule = db.query(PricingRule).filter(PricingRule.property_id == property_id).first()
    if not rule:
        # Return sensible defaults for properties without an explicit rule
        return {
            "property_id": property_id,
            "strategy": "dynamic",
            "min_price": None,
            "max_price": None,
            "weekend_markup_pct": "15.00",
            "orphan_day_discount_pct": "20.00",
            "last_minute_window_days": 7,
            "last_minute_discount_pct": "15.00",
            "early_bird_window_days": 90,
            "early_bird_discount_pct": "10.00",
            "demand_sensitivity": "0.50",
            "min_stay": 1,
            "weekend_min_stay": 2,
            "updated_at": None,
        }
    return _serialize_rule(rule)


@router.put("/rules/{property_id}", status_code=200)
def upsert_pricing_rule(
    property_id: int,
    payload: PricingRulePayload,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    from datetime import datetime, timezone

    rule = db.query(PricingRule).filter(PricingRule.property_id == property_id).first()
    if rule is None:
        rule = PricingRule(property_id=property_id)
        db.add(rule)

    rule.strategy = payload.strategy
    rule.min_price = Decimal(str(payload.min_price)) if payload.min_price else None
    rule.max_price = Decimal(str(payload.max_price)) if payload.max_price else None
    rule.weekend_markup_pct = Decimal(str(payload.weekend_markup_pct))
    rule.orphan_day_discount_pct = Decimal(str(payload.orphan_day_discount_pct))
    rule.last_minute_window_days = payload.last_minute_window_days
    rule.last_minute_discount_pct = Decimal(str(payload.last_minute_discount_pct))
    rule.early_bird_window_days = payload.early_bird_window_days
    rule.early_bird_discount_pct = Decimal(str(payload.early_bird_discount_pct))
    rule.demand_sensitivity = Decimal(str(payload.demand_sensitivity))
    rule.min_stay_default = payload.min_stay
    rule.weekend_min_stay = payload.weekend_min_stay
    rule.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(rule)
    return _serialize_rule(rule)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_accepted_price(db: Session, rec: PriceRecommendation) -> None:
    """Write the accepted price to RateDates for this property + date."""
    try:
        from app.models.rate_plan import RatePlan
        from sqlalchemy import text

        # Find the active rate plan for this property
        rate_plan = (
            db.query(RatePlan)
            .filter(
                RatePlan.property_id == rec.property_id, RatePlan.is_default.is_(True)
            )
            .first()
        )
        if not rate_plan:
            rate_plan = (
                db.query(RatePlan)
                .filter(RatePlan.property_id == rec.property_id)
                .first()
            )
        if not rate_plan:
            return  # No rate plan found — cannot apply

        # Upsert into rate_dates
        db.execute(
            text(
                """
                INSERT INTO rate_dates (rate_plan_id, date, price, min_stay, updated_at)
                VALUES (:rate_plan_id, :date, :price, :min_stay, NOW())
                ON CONFLICT (rate_plan_id, date)
                DO UPDATE SET price = EXCLUDED.price,
                              min_stay = EXCLUDED.min_stay,
                              updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "rate_plan_id": rate_plan.id,
                "date": rec.date,
                "price": rec.accepted_price,
                "min_stay": rec.min_stay,
            },
        )
    except Exception:
        # Non-fatal: log but don't block the accept operation
        import logging

        logging.getLogger(__name__).warning(
            "Failed to write accepted price to rate_dates for rec %s",
            rec.id,
            exc_info=True,
        )


async def _run_generation_background(
    property_id: int, date_from: date, date_to: date
) -> None:
    """Background task — run HLP engine for the given property + date range."""
    from app.db import SessionLocal

    with SessionLocal() as db:
        try:
            from app.pricing.engine import generate_recommendations
            from app.pricing.providers import InternalMarketDataProvider

            provider = InternalMarketDataProvider(db)
            await generate_recommendations(
                db, property_id, date_from, date_to, provider
            )
        except Exception:
            import logging

            logging.getLogger(__name__).error(
                "Background pricing generation failed for property %s",
                property_id,
                exc_info=True,
            )
