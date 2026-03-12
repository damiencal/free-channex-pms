"""Invoice / Folio Management API.

Routes (authenticated):
  GET    /api/invoices                     — list invoices by property/booking
  POST   /api/invoices                     — create invoice for a booking
  GET    /api/invoices/{id}               — get invoice with line items + payments
  PUT    /api/invoices/{id}               — update notes / status
  POST   /api/invoices/{id}/void          — void the invoice
  POST   /api/invoices/{id}/items         — add a line item
  DELETE /api/invoice-items/{id}          — remove a line item

Public (no auth):
  GET    /public/invoice/{token}          — guest-facing invoice view (read-only)
"""

from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.booking import Booking
from app.models.invoice import Invoice, InvoiceItem
from app.models.payment import Payment
from app.models.tax_type import TaxType

log = structlog.get_logger()
router = APIRouter(tags=["invoices"])
public_router = APIRouter(tags=["public"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_invoice_number(db: Session) -> str:
    """Produce a unique invoice number like INV-20250101-0001."""
    prefix = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-"
    # Find the highest existing number with this prefix
    existing = (
        db.query(Invoice.invoice_number)
        .filter(Invoice.invoice_number.like(f"{prefix}%"))
        .all()
    )
    seq = len(existing) + 1
    return f"{prefix}{seq:04d}"


def _recalculate_invoice(invoice: Invoice, db: Session) -> None:
    """Recompute subtotal, tax_amount, total and balance from line items + payments."""
    items = db.query(InvoiceItem).filter_by(invoice_id=invoice.id).all()
    subtotal = sum(Decimal(str(i.amount)) for i in items if i.item_type != "tax")
    tax_total = sum(Decimal(str(i.tax_amount or 0)) for i in items)
    total = sum(Decimal(str(i.amount)) for i in items)
    payments = db.query(Payment).filter_by(invoice_id=invoice.id).all()
    amount_paid = sum(Decimal(str(p.amount)) for p in payments)
    balance = total - amount_paid

    invoice.subtotal = subtotal
    invoice.tax_amount = tax_total
    invoice.total = total
    invoice.amount_paid = amount_paid
    invoice.balance = balance
    if balance <= 0 and total > 0:
        invoice.status = "paid"
    elif amount_paid > 0:
        invoice.status = "partially_paid"


def _serialize_item(item: InvoiceItem) -> dict:
    return {
        "id": item.id,
        "invoice_id": item.invoice_id,
        "item_type": item.item_type,
        "description": item.description,
        "quantity": str(item.quantity),
        "unit_price": str(item.unit_price),
        "amount": str(item.amount),
        "tax_type_id": item.tax_type_id,
        "tax_amount": str(item.tax_amount) if item.tax_amount else "0.00",
        "created_at": item.created_at.isoformat(),
    }


def _serialize_payment(p: Payment) -> dict:
    return {
        "id": p.id,
        "invoice_id": p.invoice_id,
        "booking_id": p.booking_id,
        "amount": str(p.amount),
        "payment_method": p.payment_method,
        "reference": p.reference,
        "notes": p.notes,
        "payment_date": p.payment_date.isoformat(),
        "created_at": p.created_at.isoformat(),
    }


def _serialize_invoice(inv: Invoice, db: Session, include_items: bool = False) -> dict:
    data = {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "booking_id": inv.booking_id,
        "property_id": inv.property_id,
        "guest_id": inv.guest_id,
        "guest_name": inv.guest_name,
        "guest_email": inv.guest_email,
        "status": inv.status,
        "subtotal": str(inv.subtotal),
        "tax_amount": str(inv.tax_amount),
        "total": str(inv.total),
        "amount_paid": str(inv.amount_paid),
        "balance": str(inv.balance),
        "notes": inv.notes,
        "created_at": inv.created_at.isoformat(),
        "updated_at": inv.updated_at.isoformat(),
    }
    if include_items:
        items = db.query(InvoiceItem).filter_by(invoice_id=inv.id).all()
        payments = db.query(Payment).filter_by(invoice_id=inv.id).all()
        data["items"] = [_serialize_item(i) for i in items]
        data["payments"] = [_serialize_payment(p) for p in payments]
    return data


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class InvoiceCreate(BaseModel):
    booking_id: Optional[int] = None
    property_id: int
    guest_id: Optional[int] = None
    guest_name: str
    guest_email: Optional[str] = None
    notes: Optional[str] = None


class InvoiceUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[str] = None


class InvoiceItemCreate(BaseModel):
    item_type: str = "room_charge"
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal
    tax_type_id: Optional[int] = None


VALID_ITEM_TYPES = {"room_charge", "extra", "tax", "discount", "service_charge"}
VALID_STATUSES = {"open", "paid", "void", "partially_paid"}


# ---------------------------------------------------------------------------
# Invoice endpoints
# ---------------------------------------------------------------------------


@router.get("/api/invoices")
def list_invoices(
    property_id: Optional[int] = Query(None),
    booking_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(Invoice).order_by(Invoice.created_at.desc())
    if property_id is not None:
        q = q.filter_by(property_id=property_id)
    if booking_id is not None:
        q = q.filter_by(booking_id=booking_id)
    if status is not None:
        q = q.filter_by(status=status)
    return [_serialize_invoice(inv, db) for inv in q.all()]


@router.post("/api/invoices", status_code=201)
def create_invoice(
    body: InvoiceCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    if body.booking_id is not None:
        booking = db.query(Booking).filter_by(id=body.booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

    invoice_number = _generate_invoice_number(db)
    public_token = secrets.token_urlsafe(24)

    inv = Invoice(
        invoice_number=invoice_number,
        public_token=public_token,
        booking_id=body.booking_id,
        property_id=body.property_id,
        guest_id=body.guest_id,
        guest_name=body.guest_name,
        guest_email=body.guest_email,
        notes=body.notes,
        status="open",
        subtotal=Decimal("0"),
        tax_amount=Decimal("0"),
        total=Decimal("0"),
        amount_paid=Decimal("0"),
        balance=Decimal("0"),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    log.info("Invoice created", id=inv.id, invoice_number=invoice_number)
    return _serialize_invoice(inv, db, include_items=True)


@router.get("/api/invoices/{invoice_id}")
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    inv = db.query(Invoice).filter_by(id=invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _serialize_invoice(inv, db, include_items=True)


@router.put("/api/invoices/{invoice_id}")
def update_invoice(
    invoice_id: int,
    body: InvoiceUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    inv = db.query(Invoice).filter_by(id=invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status == "void":
        raise HTTPException(status_code=400, detail="Cannot modify a voided invoice")
    updates = body.model_dump(exclude_none=True)
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(
            status_code=422, detail=f"status must be one of {sorted(VALID_STATUSES)}"
        )
    for field, value in updates.items():
        setattr(inv, field, value)
    db.commit()
    db.refresh(inv)
    return _serialize_invoice(inv, db, include_items=True)


@router.post("/api/invoices/{invoice_id}/void", status_code=200)
def void_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    inv = db.query(Invoice).filter_by(id=invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status == "void":
        raise HTTPException(status_code=400, detail="Invoice is already voided")
    inv.status = "void"
    db.commit()
    db.refresh(inv)
    log.info("Invoice voided", id=inv.id)
    return _serialize_invoice(inv, db, include_items=True)


@router.post("/api/invoices/{invoice_id}/items", status_code=201)
def add_invoice_item(
    invoice_id: int,
    body: InvoiceItemCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    inv = db.query(Invoice).filter_by(id=invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status == "void":
        raise HTTPException(
            status_code=400, detail="Cannot add items to a voided invoice"
        )
    if body.item_type not in VALID_ITEM_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"item_type must be one of {sorted(VALID_ITEM_TYPES)}",
        )

    amount = body.unit_price * body.quantity
    tax_amount = Decimal("0")

    if body.tax_type_id:
        tax_type = db.query(TaxType).filter_by(id=body.tax_type_id).first()
        if tax_type and not tax_type.is_inclusive:
            tax_amount = (
                tax_type.flat_amount if tax_type.is_flat else amount * tax_type.rate
            )

    item = InvoiceItem(
        invoice_id=invoice_id,
        item_type=body.item_type,
        description=body.description,
        quantity=body.quantity,
        unit_price=body.unit_price,
        amount=amount + tax_amount,
        tax_type_id=body.tax_type_id,
        tax_amount=tax_amount,
    )
    db.add(item)
    db.flush()
    _recalculate_invoice(inv, db)
    db.commit()
    db.refresh(item)
    return _serialize_item(item)


@router.delete("/api/invoice-items/{item_id}", status_code=204)
def remove_invoice_item(
    item_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> None:
    item = db.query(InvoiceItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Invoice item not found")
    inv = db.query(Invoice).filter_by(id=item.invoice_id).first()
    if inv and inv.status == "void":
        raise HTTPException(status_code=400, detail="Cannot modify a voided invoice")
    db.delete(item)
    db.flush()
    if inv:
        _recalculate_invoice(inv, db)
    db.commit()


# ---------------------------------------------------------------------------
# Public guest-facing invoice view (no auth required)
# ---------------------------------------------------------------------------


@public_router.get("/public/invoice/{token}")
def public_invoice_view(
    token: str,
    db: Session = Depends(get_db),
) -> dict:
    if not token or len(token) < 16:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv = db.query(Invoice).filter_by(public_token=token).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _serialize_invoice(inv, db, include_items=True)
