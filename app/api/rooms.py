"""Rooms and Room Types API — full CRUD with housekeeping status.

Routes:
  GET    /api/room-types                  — list room types
  POST   /api/room-types                  — create room type
  PUT    /api/room-types/{id}             — update room type
  DELETE /api/room-types/{id}             — delete room type

  GET    /api/rooms                       — list rooms (filter by property, status)
  POST   /api/rooms                       — create room
  GET    /api/rooms/{id}                  — get single room
  PUT    /api/rooms/{id}                  — update room (status, assignment, etc.)
  DELETE /api/rooms/{id}                  — delete room
  POST   /api/rooms/{id}/status           — quick housekeeping status update
"""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.room import Room
from app.models.room_type import RoomType

log = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["rooms"])

VALID_ROOM_STATUSES = {"clean", "dirty", "maintenance", "out_of_order"}


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_room_type(rt: RoomType) -> dict:
    return {
        "id": rt.id,
        "property_id": rt.property_id,
        "name": rt.name,
        "code": rt.code,
        "description": rt.description,
        "max_occupancy": rt.max_occupancy,
        "base_rate": str(rt.base_rate) if rt.base_rate is not None else None,
        "min_stay": rt.min_stay,
        "is_active": rt.is_active,
        "created_at": rt.created_at.isoformat(),
        "updated_at": rt.updated_at.isoformat(),
    }


def _serialize_room(r: Room) -> dict:
    return {
        "id": r.id,
        "property_id": r.property_id,
        "room_type_id": r.room_type_id,
        "name": r.name,
        "number": r.number,
        "floor": r.floor,
        "building": r.building,
        "status": r.status,
        "is_active": r.is_active,
        "is_online": r.is_online,
        "notes": r.notes,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Room Type schemas
# ---------------------------------------------------------------------------

class RoomTypeCreate(BaseModel):
    property_id: int
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    max_occupancy: Optional[int] = None
    base_rate: Optional[float] = None
    min_stay: Optional[int] = None
    is_active: bool = True


class RoomTypeUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    max_occupancy: Optional[int] = None
    base_rate: Optional[float] = None
    min_stay: Optional[int] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Room schemas
# ---------------------------------------------------------------------------

class RoomCreate(BaseModel):
    property_id: int
    room_type_id: Optional[int] = None
    name: str
    number: Optional[str] = None
    floor: Optional[str] = None
    building: Optional[str] = None
    status: str = "clean"
    is_active: bool = True
    is_online: bool = True
    notes: Optional[str] = None


class RoomUpdate(BaseModel):
    room_type_id: Optional[int] = None
    name: Optional[str] = None
    number: Optional[str] = None
    floor: Optional[str] = None
    building: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    is_online: Optional[bool] = None
    notes: Optional[str] = None


class RoomStatusUpdate(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Room Type endpoints
# ---------------------------------------------------------------------------

@router.get("/room-types")
def list_room_types(
    property_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(RoomType).order_by(RoomType.property_id, RoomType.name)
    if property_id is not None:
        q = q.filter_by(property_id=property_id)
    if is_active is not None:
        q = q.filter_by(is_active=is_active)
    return [_serialize_room_type(rt) for rt in q.all()]


@router.post("/room-types", status_code=201)
def create_room_type(
    body: RoomTypeCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    rt = RoomType(**body.model_dump())
    db.add(rt)
    db.commit()
    db.refresh(rt)
    log.info("Room type created", id=rt.id, name=rt.name)
    return _serialize_room_type(rt)


@router.put("/room-types/{room_type_id}")
def update_room_type(
    room_type_id: int,
    body: RoomTypeUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    rt = db.query(RoomType).filter_by(id=room_type_id).first()
    if not rt:
        raise HTTPException(status_code=404, detail="Room type not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(rt, field, value)
    db.commit()
    db.refresh(rt)
    return _serialize_room_type(rt)


@router.delete("/room-types/{room_type_id}", status_code=204)
def delete_room_type(
    room_type_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    rt = db.query(RoomType).filter_by(id=room_type_id).first()
    if not rt:
        raise HTTPException(status_code=404, detail="Room type not found")
    # Check if rooms are using this type
    room_count = db.query(Room).filter_by(room_type_id=room_type_id).count()
    if room_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete room type with {room_count} rooms. Deactivate it instead.",
        )
    db.delete(rt)
    db.commit()


# ---------------------------------------------------------------------------
# Room endpoints
# ---------------------------------------------------------------------------

@router.get("/rooms")
def list_rooms(
    property_id: Optional[int] = Query(None),
    room_type_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_online: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(Room).order_by(Room.property_id, Room.floor, Room.number, Room.name)
    if property_id is not None:
        q = q.filter_by(property_id=property_id)
    if room_type_id is not None:
        q = q.filter_by(room_type_id=room_type_id)
    if status is not None:
        q = q.filter_by(status=status)
    if is_active is not None:
        q = q.filter_by(is_active=is_active)
    if is_online is not None:
        q = q.filter_by(is_online=is_online)
    return [_serialize_room(r) for r in q.all()]


@router.post("/rooms", status_code=201)
def create_room(
    body: RoomCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    if body.status not in VALID_ROOM_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{body.status}'. Must be one of: {sorted(VALID_ROOM_STATUSES)}",
        )
    room = Room(**body.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    log.info("Room created", id=room.id, name=room.name)
    return _serialize_room(room)


@router.get("/rooms/{room_id}")
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    room = db.query(Room).filter_by(id=room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return _serialize_room(room)


@router.put("/rooms/{room_id}")
def update_room(
    room_id: int,
    body: RoomUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    room = db.query(Room).filter_by(id=room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    updates = body.model_dump(exclude_none=True)
    if "status" in updates and updates["status"] not in VALID_ROOM_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {sorted(VALID_ROOM_STATUSES)}",
        )
    for field, value in updates.items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return _serialize_room(room)


@router.delete("/rooms/{room_id}", status_code=204)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    room = db.query(Room).filter_by(id=room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    db.delete(room)
    db.commit()


@router.post("/rooms/{room_id}/status")
def update_room_status(
    room_id: int,
    body: RoomStatusUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Quick housekeeping status update (clean/dirty/maintenance/out_of_order)."""
    if body.status not in VALID_ROOM_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{body.status}'. Must be one of: {sorted(VALID_ROOM_STATUSES)}",
        )
    room = db.query(Room).filter_by(id=room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    old_status = room.status
    room.status = body.status
    db.commit()
    db.refresh(room)
    log.info("Room status updated", room_id=room_id, old=old_status, new=body.status)
    return _serialize_room(room)
