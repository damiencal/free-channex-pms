"""Tax Types API.

Routes:
  GET    /api/tax-types           — list tax types (filter by property_id)
  POST   /api/tax-types           — create tax type
  GET    /api/tax-types/{id}      — get tax type
  PUT    /api/tax-types/{id}      — update tax type
  DELETE /api/tax-types/{id}      — delete (soft) tax type
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.tax_type import TaxType

log = structlog.get_logger()
router = APIRouter(prefix="/api/tax-types", tags=["taxes"])


def _serialize(tt: TaxType) -> dict:
    return {
        "id": tt.id,
        "property_id": tt.property_id,
        "name": tt.name,
        "rate": str(tt.rate),
        "is_inclusive": tt.is_inclusive,
        "is_flat": tt.is_flat,
        "flat_amount": str(tt.flat_amount) if tt.flat_amount is not None else None,
        "is_active": tt.is_active,
        "created_at": tt.created_at.isoformat(),
        "updated_at": tt.updated_at.isoformat(),
    }


class TaxTypeCreate(BaseModel):
    property_id: Optional[int] = None
    name: str
    rate: Decimal = Decimal("0")
    is_inclusive: bool = False
    is_flat: bool = False
    flat_amount: Optional[Decimal] = None
    is_active: bool = True


class TaxTypeUpdate(BaseModel):
    name: Optional[str] = None
    rate: Optional[Decimal] = None
    is_inclusive: Optional[bool] = None
    is_flat: Optional[bool] = None
    flat_amount: Optional[Decimal] = None
    is_active: Optional[bool] = None


@router.get("")
def list_tax_types(
    property_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(TaxType).order_by(TaxType.name)
    if property_id is not None:
        q = q.filter(
            (TaxType.property_id == property_id) | (TaxType.property_id.is_(None))
        )
    if is_active is not None:
        q = q.filter_by(is_active=is_active)
    return [_serialize(tt) for tt in q.all()]


@router.post("", status_code=201)
def create_tax_type(
    body: TaxTypeCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    tt = TaxType(**body.model_dump())
    db.add(tt)
    db.commit()
    db.refresh(tt)
    return _serialize(tt)


@router.get("/{tax_type_id}")
def get_tax_type(
    tax_type_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    tt = db.query(TaxType).filter_by(id=tax_type_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail="Tax type not found")
    return _serialize(tt)


@router.put("/{tax_type_id}")
def update_tax_type(
    tax_type_id: int,
    body: TaxTypeUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    tt = db.query(TaxType).filter_by(id=tax_type_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail="Tax type not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(tt, field, value)
    db.commit()
    db.refresh(tt)
    return _serialize(tt)


@router.delete("/{tax_type_id}", status_code=204)
def delete_tax_type(
    tax_type_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    tt = db.query(TaxType).filter_by(id=tax_type_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail="Tax type not found")
    tt.is_active = False
    db.commit()
