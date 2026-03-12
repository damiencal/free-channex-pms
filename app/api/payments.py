"""Payments API.

Routes:
  GET    /api/payments               — list payments (filter by invoice_id/booking_id)
  POST   /api/payments               — record a payment
  GET    /api/payments/{id}          — get payment
  DELETE /api/payments/{id}          — record refund (creates negative amount payment)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.invoice import Invoice
from app.models.payment import Payment

log = structlog.get_logger()
router = APIRouter(prefix="/api/payments", tags=["payments"])


def _serialize(p: Payment) -> dict:
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


def _recalculate_invoice(inv: Invoice, db: Session) -> None:
    from decimal import Decimal as D

    payments = db.query(Payment).filter_by(invoice_id=inv.id).all()
    amount_paid = sum(D(str(p.amount)) for p in payments)
    balance = D(str(inv.total)) - amount_paid
    inv.amount_paid = amount_paid
    inv.balance = balance
    if balance <= 0 and D(str(inv.total)) > 0:
        inv.status = "paid"
    elif amount_paid > 0 and balance > 0:
        inv.status = "partially_paid"
    elif amount_paid <= 0:
        inv.status = "open"


VALID_METHODS = {"cash", "credit_card", "debit_card", "bank_transfer", "check", "other"}


class PaymentCreate(BaseModel):
    invoice_id: int
    booking_id: Optional[int] = None
    amount: Decimal
    payment_method: str = "cash"
    reference: Optional[str] = None
    notes: Optional[str] = None
    payment_date: Optional[date] = None


@router.get("")
def list_payments(
    invoice_id: Optional[int] = Query(None),
    booking_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> list[dict]:
    q = db.query(Payment).order_by(Payment.payment_date.desc())
    if invoice_id is not None:
        q = q.filter_by(invoice_id=invoice_id)
    if booking_id is not None:
        q = q.filter_by(booking_id=booking_id)
    return [_serialize(p) for p in q.all()]


@router.post("", status_code=201)
def record_payment(
    body: PaymentCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    if body.payment_method not in VALID_METHODS:
        raise HTTPException(
            status_code=422,
            detail=f"payment_method must be one of {sorted(VALID_METHODS)}",
        )
    inv = db.query(Invoice).filter_by(id=body.invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status == "void":
        raise HTTPException(
            status_code=400, detail="Cannot add payments to a voided invoice"
        )

    payment = Payment(
        invoice_id=body.invoice_id,
        booking_id=body.booking_id,
        amount=body.amount,
        payment_method=body.payment_method,
        reference=body.reference,
        notes=body.notes,
        payment_date=body.payment_date or date.today(),
    )
    db.add(payment)
    db.flush()
    _recalculate_invoice(inv, db)
    db.commit()
    db.refresh(payment)
    log.info("Payment recorded", id=payment.id, amount=str(payment.amount))
    return _serialize(payment)


@router.get("/{payment_id}")
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    p = db.query(Payment).filter_by(id=payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Payment not found")
    return _serialize(p)


@router.delete("/{payment_id}", status_code=201)
def refund_payment(
    payment_id: int,
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Create a refund by recording a negative-amount payment against the same invoice."""
    original = db.query(Payment).filter_by(id=payment_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Payment not found")
    inv = db.query(Invoice).filter_by(id=original.invoice_id).first()
    if inv and inv.status == "void":
        raise HTTPException(status_code=400, detail="Cannot refund a voided invoice")

    refund = Payment(
        invoice_id=original.invoice_id,
        booking_id=original.booking_id,
        amount=-abs(original.amount),
        payment_method=original.payment_method,
        reference=f"REFUND/{original.id}",
        notes=notes or f"Refund for payment #{original.id}",
        payment_date=date.today(),
    )
    db.add(refund)
    db.flush()
    if inv:
        _recalculate_invoice(inv, db)
    db.commit()
    db.refresh(refund)
    log.info("Refund recorded", id=refund.id, original_payment_id=payment_id)
    return _serialize(refund)
