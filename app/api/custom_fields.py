"""Custom Fields API.

Supports admin-defined fields attached to bookings or guests.

Routes:
  GET    /api/custom-fields                  — list field definitions
  POST   /api/custom-fields                  — create field definition
  GET    /api/custom-fields/{id}             — get definition
  PUT    /api/custom-fields/{id}             — update definition
  DELETE /api/custom-fields/{id}             — soft delete definition

  GET    /api/custom-fields/values           — get all field values for an entity
  POST   /api/custom-fields/values           — set (upsert) a field value
  DELETE /api/custom-fields/values/{id}      — delete a field value
"""

from __future__ import annotations

import json
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.custom_field import CustomFieldDefinition, CustomFieldValue

log = structlog.get_logger()
router = APIRouter(prefix="/api/custom-fields", tags=["custom-fields"])

VALID_FIELD_TYPES = {"text", "number", "date", "select", "checkbox", "textarea"}
VALID_ENTITY_TYPES = {"booking", "guest"}


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_def(cfd: CustomFieldDefinition) -> dict:
    options = None
    if cfd.options:
        try:
            options = json.loads(cfd.options) if isinstance(cfd.options, str) else cfd.options
        except (ValueError, TypeError):
            options = cfd.options
    return {
        "id": cfd.id,
        "property_id": cfd.property_id,
        "entity_type": cfd.entity_type,
        "name": cfd.name,
        "label": cfd.label,
        "field_type": cfd.field_type,
        "options": options,
        "is_required": cfd.is_required,
        "sort_order": cfd.sort_order,
        "is_active": cfd.is_active,
        "created_at": cfd.created_at.isoformat(),
    }


def _serialize_value(cfv: CustomFieldValue) -> dict:
    return {
        "id": cfv.id,
        "field_id": cfv.field_id,
        "entity_type": cfv.entity_type,
        "entity_id": cfv.entity_id,
        "value": cfv.value,
        "updated_at": cfv.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FieldDefCreate(BaseModel):
    property_id: Optional[int] = None
    entity_type: str
    name: str
    label: str
    field_type: str = "text"
    options: Optional[list] = None
    is_required: bool = False
    sort_order: int = 0
    is_active: bool = True


class FieldDefUpdate(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    field_type: Optional[str] = None
    options: Optional[list] = None
    is_required: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class FieldValueUpsert(BaseModel):
    field_id: int
    entity_type: str
    entity_id: int
    value: Optional[str] = None


# ---------------------------------------------------------------------------
# Definition endpoints
# ---------------------------------------------------------------------------

@router.get("")
def list_field_definitions(
    property_id: Optional[int] = Query(None),
    entity_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(CustomFieldDefinition).order_by(
        CustomFieldDefinition.entity_type, CustomFieldDefinition.sort_order
    )
    if property_id is not None:
        q = q.filter(
            (CustomFieldDefinition.property_id == property_id)
            | (CustomFieldDefinition.property_id.is_(None))
        )
    if entity_type is not None:
        q = q.filter_by(entity_type=entity_type)
    if is_active is not None:
        q = q.filter_by(is_active=is_active)
    return [_serialize_def(cfd) for cfd in q.all()]


@router.post("", status_code=201)
def create_field_definition(
    body: FieldDefCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    if body.entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=422, detail=f"entity_type must be one of {sorted(VALID_ENTITY_TYPES)}")
    if body.field_type not in VALID_FIELD_TYPES:
        raise HTTPException(status_code=422, detail=f"field_type must be one of {sorted(VALID_FIELD_TYPES)}")

    data = body.model_dump()
    if data.get("options") is not None:
        data["options"] = json.dumps(data["options"])

    cfd = CustomFieldDefinition(**data)
    db.add(cfd)
    db.commit()
    db.refresh(cfd)
    return _serialize_def(cfd)


@router.get("/values")
def get_entity_values(
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    """Return all custom field values for a specific entity (e.g. a booking or guest)."""
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=422, detail=f"entity_type must be one of {sorted(VALID_ENTITY_TYPES)}")
    values = (
        db.query(CustomFieldValue)
        .filter_by(entity_type=entity_type, entity_id=entity_id)
        .all()
    )
    return [_serialize_value(v) for v in values]


@router.get("/{field_id}")
def get_field_definition(
    field_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    cfd = db.query(CustomFieldDefinition).filter_by(id=field_id).first()
    if not cfd:
        raise HTTPException(status_code=404, detail="Custom field definition not found")
    return _serialize_def(cfd)


@router.put("/{field_id}")
def update_field_definition(
    field_id: int,
    body: FieldDefUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    cfd = db.query(CustomFieldDefinition).filter_by(id=field_id).first()
    if not cfd:
        raise HTTPException(status_code=404, detail="Custom field definition not found")
    updates = body.model_dump(exclude_none=True)
    if "field_type" in updates and updates["field_type"] not in VALID_FIELD_TYPES:
        raise HTTPException(status_code=422, detail=f"field_type must be one of {sorted(VALID_FIELD_TYPES)}")
    if "options" in updates:
        updates["options"] = json.dumps(updates["options"])
    for field, value in updates.items():
        setattr(cfd, field, value)
    db.commit()
    db.refresh(cfd)
    return _serialize_def(cfd)


@router.delete("/{field_id}", status_code=204)
def delete_field_definition(
    field_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    cfd = db.query(CustomFieldDefinition).filter_by(id=field_id).first()
    if not cfd:
        raise HTTPException(status_code=404, detail="Custom field definition not found")
    cfd.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Value endpoints
# ---------------------------------------------------------------------------

@router.post("/values", status_code=200)
def upsert_field_value(
    body: FieldValueUpsert,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Create or update the value of a custom field for a given entity."""
    if body.entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=422, detail=f"entity_type must be one of {sorted(VALID_ENTITY_TYPES)}")

    cfd = db.query(CustomFieldDefinition).filter_by(id=body.field_id).first()
    if not cfd:
        raise HTTPException(status_code=404, detail="Custom field definition not found")

    existing = (
        db.query(CustomFieldValue)
        .filter_by(
            field_id=body.field_id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
        )
        .first()
    )
    if existing:
        existing.value = body.value
        db.commit()
        db.refresh(existing)
        return _serialize_value(existing)
    else:
        cfv = CustomFieldValue(
            field_id=body.field_id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            value=body.value,
        )
        db.add(cfv)
        db.commit()
        db.refresh(cfv)
        return _serialize_value(cfv)


@router.delete("/values/{value_id}", status_code=204)
def delete_field_value(
    value_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    cfv = db.query(CustomFieldValue).filter_by(id=value_id).first()
    if not cfv:
        raise HTTPException(status_code=404, detail="Custom field value not found")
    db.delete(cfv)
    db.commit()
