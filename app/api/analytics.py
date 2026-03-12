"""Analytics API — portfolio KPIs, pacing, market trends, comp sets.

Endpoints:
  GET  /api/analytics/portfolio    — monthly KPI metrics (occupancy, ADR, RevPAR)
  GET  /api/analytics/pacing       — booking pace vs last year
  GET  /api/analytics/trends       — multi-month trend series
  GET  /api/analytics/market       — market snapshot data for dashboards
  GET  /api/comp-sets              — list comp sets for a property
  POST /api/comp-sets              — create comp set
  GET  /api/comp-sets/{id}         — get comp set with member data
  PUT  /api/comp-sets/{id}         — update comp set
  DELETE /api/comp-sets/{id}       — delete comp set
  POST /api/comp-sets/{id}/refresh — refresh comp set data
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.comp_set import CompSet, CompSetProperty
from app.models.market_snapshot import MarketSnapshot
from app.models.portfolio_metric import PortfolioMetric

router = APIRouter(tags=["analytics"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CompSetCreate(BaseModel):
    property_id: int
    name: str
    filters_json: Optional[dict] = None


class CompSetUpdate(BaseModel):
    name: Optional[str] = None
    filters_json: Optional[dict] = None


class CompSetMemberCreate(BaseModel):
    name: str
    external_listing_id: Optional[str] = None
    source: str = "internal"
    ref_property_id: Optional[int] = None


def _serialize_metric(m: PortfolioMetric) -> dict:
    return {
        "id": m.id,
        "property_id": m.property_id,
        "metric_date": m.metric_date.isoformat(),
        "occupancy_rate": str(m.occupancy_rate)
        if m.occupancy_rate is not None
        else None,
        "adr": str(m.adr) if m.adr is not None else None,
        "revpar": str(m.revpar) if m.revpar is not None else None,
        "trevpar": str(m.trevpar) if m.trevpar is not None else None,
        "revenue": str(m.revenue) if m.revenue is not None else None,
        "available_nights": m.available_nights,
        "booked_nights": m.booked_nights,
        "booking_count": m.booking_count,
        "booking_pace": str(m.booking_pace) if m.booking_pace is not None else None,
        "booking_pace_ly": str(m.booking_pace_ly)
        if m.booking_pace_ly is not None
        else None,
    }


def _serialize_snapshot(s: MarketSnapshot) -> dict:
    return {
        "id": s.id,
        "property_id": s.property_id,
        "snapshot_date": s.snapshot_date.isoformat(),
        "avg_daily_rate": str(s.avg_daily_rate)
        if s.avg_daily_rate is not None
        else None,
        "occupancy_rate": str(s.occupancy_rate)
        if s.occupancy_rate is not None
        else None,
        "demand_index": str(s.demand_index) if s.demand_index is not None else None,
        "supply_count": s.supply_count,
        "source": s.source,
    }


def _serialize_comp_set(cs: CompSet) -> dict:
    return {
        "id": cs.id,
        "property_id": cs.property_id,
        "name": cs.name,
        "filters_json": cs.filters_json,
        "created_at": cs.created_at.isoformat(),
        "updated_at": cs.updated_at.isoformat(),
    }


def _serialize_comp_member(m: CompSetProperty) -> dict:
    return {
        "id": m.id,
        "comp_set_id": m.comp_set_id,
        "name": m.name,
        "external_listing_id": m.external_listing_id,
        "source": m.source,
        "ref_property_id": m.ref_property_id,
        "avg_rate": str(m.avg_rate) if m.avg_rate is not None else None,
        "avg_occupancy": str(m.avg_occupancy) if m.avg_occupancy is not None else None,
        "last_updated": m.last_updated.isoformat() if m.last_updated else None,
    }


# ---------------------------------------------------------------------------
# Portfolio KPIs
# ---------------------------------------------------------------------------


@router.get("/api/analytics/portfolio")
def portfolio_kpis(
    property_id: Optional[int] = Query(None),
    months: int = Query(12, ge=1, le=60),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    """Return monthly KPI metrics. Triggers compute for missing months."""
    from app.pricing.analytics import get_kpi_summary

    return get_kpi_summary(db, property_id, months)


@router.post("/api/analytics/compute")
async def compute_metrics(
    property_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Manually trigger metrics computation for current month."""
    import datetime
    from app.pricing.analytics import (
        compute_monthly_metrics,
        compute_all_properties_metrics,
    )

    today = datetime.date.today()
    if property_id:
        compute_monthly_metrics(db, property_id, today.year, today.month)
        return {"status": "ok", "property_id": property_id}
    else:
        compute_all_properties_metrics(db, today.year, today.month)
        return {"status": "ok", "scope": "all_properties"}


# ---------------------------------------------------------------------------
# Booking Pacing
# ---------------------------------------------------------------------------


@router.get("/api/analytics/pacing")
def pacing_data(
    property_id: int = Query(...),
    target_month: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Return booking pace data vs last year, plus weekly pickup series."""
    import datetime
    from app.pricing.pacing import get_pacing_data

    if target_month is None:
        today = datetime.date.today()
        target_month = today.replace(day=1)

    return get_pacing_data(db, property_id, target_month)


# ---------------------------------------------------------------------------
# Market Trends
# ---------------------------------------------------------------------------


@router.get("/api/analytics/trends")
def market_trends(
    property_id: Optional[int] = Query(None),
    months: int = Query(12, ge=1, le=36),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    """Return monthly portfolio KPI trend series for charting."""
    from app.pricing.analytics import get_kpi_summary

    return get_kpi_summary(db, property_id, months)


@router.get("/api/analytics/market")
def market_snapshots(
    property_id: Optional[int] = Query(None),
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    """Return market-wide demand and supply snapshots."""
    import datetime

    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    q = db.query(MarketSnapshot).filter(MarketSnapshot.snapshot_date >= cutoff)
    if property_id is not None:
        q = q.filter(MarketSnapshot.property_id == property_id)
    snapshots = q.order_by(MarketSnapshot.snapshot_date).all()
    return [_serialize_snapshot(s) for s in snapshots]


# ---------------------------------------------------------------------------
# Comp Sets
# ---------------------------------------------------------------------------


@router.get("/api/comp-sets")
def list_comp_sets(
    property_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(CompSet)
    if property_id is not None:
        q = q.filter(CompSet.property_id == property_id)
    return [_serialize_comp_set(cs) for cs in q.all()]


@router.post("/api/comp-sets", status_code=201)
def create_comp_set(
    payload: CompSetCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    cs = CompSet(
        property_id=payload.property_id,
        name=payload.name,
        filters_json=payload.filters_json or {},
    )
    db.add(cs)
    db.commit()
    db.refresh(cs)
    return _serialize_comp_set(cs)


@router.get("/api/comp-sets/{comp_set_id}")
def get_comp_set(
    comp_set_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    cs = db.query(CompSet).filter(CompSet.id == comp_set_id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Comp set not found")
    members = (
        db.query(CompSetProperty)
        .filter(CompSetProperty.comp_set_id == comp_set_id)
        .all()
    )
    result = _serialize_comp_set(cs)
    result["members"] = [_serialize_comp_member(m) for m in members]
    return result


@router.put("/api/comp-sets/{comp_set_id}")
def update_comp_set(
    comp_set_id: int,
    payload: CompSetUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    cs = db.query(CompSet).filter(CompSet.id == comp_set_id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Comp set not found")
    if payload.name is not None:
        cs.name = payload.name
    if payload.filters_json is not None:
        cs.filters_json = payload.filters_json
    from datetime import datetime, timezone

    cs.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cs)
    return _serialize_comp_set(cs)


@router.delete("/api/comp-sets/{comp_set_id}", status_code=204)
def delete_comp_set(
    comp_set_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    cs = db.query(CompSet).filter(CompSet.id == comp_set_id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Comp set not found")
    db.delete(cs)
    db.commit()


@router.post("/api/comp-sets/{comp_set_id}/members", status_code=201)
def add_comp_set_member(
    comp_set_id: int,
    payload: CompSetMemberCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    cs = db.query(CompSet).filter(CompSet.id == comp_set_id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Comp set not found")
    member = CompSetProperty(
        comp_set_id=comp_set_id,
        name=payload.name,
        external_listing_id=payload.external_listing_id,
        source=payload.source,
        ref_property_id=payload.ref_property_id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return _serialize_comp_member(member)


@router.delete("/api/comp-sets/{comp_set_id}/members/{member_id}", status_code=204)
def remove_comp_set_member(
    comp_set_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    member = (
        db.query(CompSetProperty)
        .filter(
            CompSetProperty.id == member_id,
            CompSetProperty.comp_set_id == comp_set_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()


@router.post("/api/comp-sets/{comp_set_id}/refresh")
async def refresh_comp_set(
    comp_set_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Refresh avg_rate and avg_occupancy data for internal comp set members."""
    cs = db.query(CompSet).filter(CompSet.id == comp_set_id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Comp set not found")

    members = (
        db.query(CompSetProperty)
        .filter(
            CompSetProperty.comp_set_id == comp_set_id,
            CompSetProperty.source == "internal",
            CompSetProperty.ref_property_id.is_not(None),
        )
        .all()
    )

    from datetime import datetime, date as dt_date, timedelta, timezone
    from decimal import Decimal
    from app.pricing.providers import InternalMarketDataProvider

    provider = InternalMarketDataProvider(db)
    today = dt_date.today()
    start = today - timedelta(days=90)
    updated = 0

    for member in members:
        try:
            metrics = await provider.get_market_metrics(
                member.ref_property_id, start, today
            )
            member.avg_rate = (
                Decimal(str(metrics.avg_daily_rate)) if metrics.avg_daily_rate else None
            )
            member.avg_occupancy = (
                Decimal(str(metrics.occupancy_rate)) if metrics.occupancy_rate else None
            )
            member.last_updated = datetime.now(timezone.utc)
            updated += 1
        except Exception:
            pass

    db.commit()
    return {"updated": updated, "total": len(members)}
