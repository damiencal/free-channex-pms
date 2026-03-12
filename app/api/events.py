"""Events API — CRUD for market events (holidays, local events, seasons, conferences).

Market events are used by the dynamic pricing engine as demand modifiers.
Global events (no property_id) apply to all properties.
Per-property events override or supplement global events.

Endpoints:
  GET    /api/events              — List events with optional filters
  POST   /api/events              — Create new event
  GET    /api/events/{id}         — Get single event
  PUT    /api/events/{id}         — Update event
  DELETE /api/events/{id}         — Delete event
  POST   /api/events/seed-holidays — Seed US federal holidays for current + next year
"""

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.market_event import MarketEvent

router = APIRouter(prefix="/api/events", tags=["events"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class EventCreate(BaseModel):
    name: str
    event_type: str = "local_event"
    start_date: date
    end_date: date
    demand_modifier: float = 1.0
    recurrence: str = "none"
    description: Optional[str] = None
    property_id: Optional[int] = None
    is_active: bool = True

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        valid = {"holiday", "local_event", "season", "conference", "custom"}
        if v not in valid:
            raise ValueError(f"event_type must be one of {valid}")
        return v

    @field_validator("recurrence")
    @classmethod
    def validate_recurrence(cls, v: str) -> str:
        if v not in ("none", "yearly"):
            raise ValueError("recurrence must be 'none' or 'yearly'")
        return v

    @field_validator("demand_modifier")
    @classmethod
    def validate_modifier(cls, v: float) -> float:
        if not 0.1 <= v <= 5.0:
            raise ValueError("demand_modifier must be between 0.1 and 5.0")
        return v


class EventUpdate(BaseModel):
    name: Optional[str] = None
    event_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    demand_modifier: Optional[float] = None
    recurrence: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


def _serialize_event(e: MarketEvent) -> dict:
    return {
        "id": e.id,
        "property_id": e.property_id,
        "name": e.name,
        "event_type": e.event_type,
        "start_date": e.start_date.isoformat(),
        "end_date": e.end_date.isoformat(),
        "demand_modifier": str(e.demand_modifier),
        "recurrence": e.recurrence,
        "description": e.description,
        "is_active": e.is_active,
        "created_at": e.created_at.isoformat(),
        "updated_at": e.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
def list_events(
    property_id: Optional[int] = Query(None),
    include_global: bool = Query(True),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    event_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    """List market events with optional filters."""
    q = db.query(MarketEvent)

    if property_id is not None:
        if include_global:
            q = q.filter(
                (MarketEvent.property_id == property_id)
                | (MarketEvent.property_id.is_(None))
            )
        else:
            q = q.filter(MarketEvent.property_id == property_id)
    elif not include_global:
        q = q.filter(MarketEvent.property_id.is_not(None))

    if start_date:
        q = q.filter(MarketEvent.end_date >= start_date)
    if end_date:
        q = q.filter(MarketEvent.start_date <= end_date)
    if event_type:
        q = q.filter(MarketEvent.event_type == event_type)
    if is_active is not None:
        q = q.filter(MarketEvent.is_active.is_(is_active))

    events = q.order_by(MarketEvent.start_date).all()
    return [_serialize_event(e) for e in events]


@router.post("", status_code=201)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Create a new market event."""
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="end_date must be >= start_date")

    from decimal import Decimal

    event = MarketEvent(
        property_id=payload.property_id,
        name=payload.name,
        event_type=payload.event_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        demand_modifier=Decimal(str(payload.demand_modifier)),
        recurrence=payload.recurrence,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _serialize_event(event)


@router.get("/{event_id}")
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    event = db.query(MarketEvent).filter(MarketEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _serialize_event(event)


@router.put("/{event_id}")
def update_event(
    event_id: int,
    payload: EventUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    event = db.query(MarketEvent).filter(MarketEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    from decimal import Decimal

    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "demand_modifier":
            setattr(event, field, Decimal(str(value)))
        else:
            setattr(event, field, value)

    event.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return _serialize_event(event)


@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    event = db.query(MarketEvent).filter(MarketEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()


@router.post("/seed-holidays", status_code=201)
def seed_holidays(
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Seed common US federal holidays and vacation demand events.

    Creates global events (property_id=None) with appropriate demand modifiers.
    Safe to call multiple times — checks for existing events by name + recurrence.
    """
    from decimal import Decimal

    HOLIDAYS = [
        # (name, month, day, duration_days, modifier, event_type)
        ("New Year's Day", 1, 1, 3, 1.30, "holiday"),
        ("Martin Luther King Jr. Day", 1, 15, 3, 1.10, "holiday"),
        ("Presidents Day Weekend", 2, 14, 4, 1.15, "holiday"),
        ("Spring Break (March)", 3, 10, 14, 1.35, "season"),
        ("Spring Break (April)", 4, 1, 14, 1.35, "season"),
        ("Memorial Day Weekend", 5, 23, 5, 1.45, "holiday"),
        ("Independence Day Week", 6, 28, 10, 1.50, "holiday"),
        ("Labor Day Weekend", 8, 29, 5, 1.45, "holiday"),
        ("Columbus Day Weekend", 10, 7, 4, 1.15, "holiday"),
        ("Thanksgiving Week", 11, 23, 7, 1.40, "holiday"),
        ("Christmas Week", 12, 23, 9, 1.50, "holiday"),
        ("New Year's Eve Week", 12, 26, 6, 1.45, "holiday"),
        # Season modifiers
        ("Summer High Season", 6, 15, 76, 1.25, "season"),
        ("Winter Shoulder", 1, 10, 60, 0.85, "season"),
        ("Fall Shoulder", 9, 15, 45, 0.90, "season"),
    ]

    created = 0
    skipped = 0
    import datetime as dt

    for name, month, day, duration, modifier, etype in HOLIDAYS:
        # Check if already exists (by name + recurrence=yearly)
        existing = (
            db.query(MarketEvent)
            .filter(
                MarketEvent.name == name,
                MarketEvent.recurrence == "yearly",
                MarketEvent.property_id.is_(None),
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        year = dt.date.today().year
        start = dt.date(year, month, min(day, 28))
        end = start + dt.timedelta(days=duration - 1)

        event = MarketEvent(
            property_id=None,
            name=name,
            event_type=etype,
            start_date=start,
            end_date=end,
            demand_modifier=Decimal(str(modifier)),
            recurrence="yearly",
            description=f"Auto-seeded US {etype}: {name}",
            is_active=True,
        )
        db.add(event)
        created += 1

    db.commit()
    return {"created": created, "skipped": skipped}
