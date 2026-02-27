"""Ingestion API endpoints.

Exposes all ingestion functionality via HTTP:
  - POST /ingestion/airbnb/upload    — Airbnb CSV upload
  - POST /ingestion/vrbo/upload      — VRBO CSV upload
  - POST /ingestion/mercury/upload   — Mercury bank CSV upload
  - POST /ingestion/rvshare/entry    — RVshare manual booking entry
  - GET  /ingestion/history          — Import run history
  - GET  /ingestion/bookings         — Unified bookings list
  - GET  /ingestion/bank-transactions — Bank transactions list

All upload endpoints validate that the file extension is .csv and delegate
to the normalizer. ValueError from the normalizer is returned as HTTP 422.
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.ingestion import normalizer
from app.ingestion.adapters import airbnb as airbnb_adapter
from app.ingestion.adapters import mercury as mercury_adapter
from app.ingestion.adapters import vrbo as vrbo_adapter
from app.ingestion.schemas import RVshareEntryRequest
from app.models.bank_transaction import BankTransaction
from app.models.booking import Booking
from app.models.import_run import ImportRun
from app.models.property import Property

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


# ---------------------------------------------------------------------------
# Upload endpoints
# ---------------------------------------------------------------------------


@router.post("/airbnb/upload")
async def upload_airbnb_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """Upload an Airbnb Transaction History CSV.

    Parses the CSV, groups rows by Confirmation Code, upserts bookings,
    archives the raw file, and records an ImportRun.

    Returns:
        Dict with platform, filename, inserted, updated, skipped counts.

    Raises:
        HTTPException 422: On wrong file extension, header mismatch, or row errors.
    """
    _require_csv_extension(file.filename)
    raw_bytes = await file.read()
    try:
        result = normalizer.ingest_csv(raw_bytes, file.filename, "airbnb", airbnb_adapter, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.post("/vrbo/upload")
async def upload_vrbo_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """Upload a VRBO Payments Report CSV.

    Parses the CSV, groups rows by Reservation ID, upserts bookings,
    archives the raw file, and records an ImportRun.

    Returns:
        Dict with platform, filename, inserted, updated, skipped counts.

    Raises:
        HTTPException 422: On wrong file extension, header mismatch, or row errors.
    """
    _require_csv_extension(file.filename)
    raw_bytes = await file.read()
    try:
        result = normalizer.ingest_csv(raw_bytes, file.filename, "vrbo", vrbo_adapter, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.post("/mercury/upload")
async def upload_mercury_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """Upload a Mercury bank transaction CSV.

    Parses the CSV, upserts bank transactions using a composite dedup key,
    archives the raw file, and records an ImportRun.

    Returns:
        Dict with platform, filename, inserted, updated, skipped counts.

    Raises:
        HTTPException 422: On wrong file extension, header mismatch, or row errors.
    """
    _require_csv_extension(file.filename)
    raw_bytes = await file.read()
    try:
        result = normalizer.ingest_bank_csv(raw_bytes, file.filename, mercury_adapter, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


# ---------------------------------------------------------------------------
# Manual entry endpoint
# ---------------------------------------------------------------------------


@router.post("/rvshare/entry")
def create_rvshare_booking(
    entry: RVshareEntryRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Manually enter an RVshare booking.

    RVshare does not export CSVs in the same format as Airbnb/VRBO.
    Operators submit bookings as JSON via this endpoint.

    Returns:
        Dict with platform, filename, inserted, updated, skipped counts.

    Raises:
        HTTPException 422: If the property_slug is not found in the database.
    """
    try:
        result = normalizer.create_manual_booking(entry, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


# ---------------------------------------------------------------------------
# Query endpoints
# ---------------------------------------------------------------------------


@router.get("/history")
def get_import_history(
    platform: Optional[str] = Query(default=None, description="Filter by platform (airbnb, vrbo, mercury, rvshare)"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return import run history, newest first.

    Args:
        platform: Optional platform filter.
        limit:    Maximum number of results (default 50, max 500).

    Returns:
        List of dicts with id, platform, filename, inserted_count,
        updated_count, skipped_count, imported_at.
    """
    stmt = select(ImportRun).order_by(desc(ImportRun.imported_at)).limit(limit)
    if platform is not None:
        stmt = stmt.where(ImportRun.platform == platform)

    runs = db.execute(stmt).scalars().all()
    return [
        {
            "id": run.id,
            "platform": run.platform,
            "filename": run.filename,
            "inserted_count": run.inserted_count,
            "updated_count": run.updated_count,
            "skipped_count": run.skipped_count,
            "imported_at": run.imported_at.isoformat() if run.imported_at else None,
        }
        for run in runs
    ]


@router.get("/bookings")
def get_bookings(
    platform: Optional[str] = Query(default=None, description="Filter by platform (airbnb, vrbo, rvshare)"),
    property_slug: Optional[str] = Query(default=None, description="Filter by property slug"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return unified booking list, newest check-in first.

    Args:
        platform:      Optional platform filter.
        property_slug: Optional property slug filter.
        limit:         Maximum number of results (default 100, max 1000).
        offset:        Number of results to skip for pagination (default 0).

    Returns:
        List of dicts with platform, confirmation_code, guest_name,
        check_in_date, check_out_date, net_amount, property_slug.
    """
    stmt = (
        select(Booking, Property.slug.label("prop_slug"))
        .join(Property, Booking.property_id == Property.id)
        .order_by(desc(Booking.check_in_date))
        .limit(limit)
        .offset(offset)
    )
    if platform is not None:
        stmt = stmt.where(Booking.platform == platform)
    if property_slug is not None:
        stmt = stmt.where(Property.slug == property_slug)

    rows = db.execute(stmt).all()
    return [
        {
            "platform": booking.platform,
            "confirmation_code": booking.platform_booking_id,
            "guest_name": booking.guest_name,
            "check_in_date": booking.check_in_date.isoformat() if booking.check_in_date else None,
            "check_out_date": booking.check_out_date.isoformat() if booking.check_out_date else None,
            "net_amount": str(booking.net_amount),
            "property_slug": prop_slug,
        }
        for booking, prop_slug in rows
    ]


@router.get("/bank-transactions")
def get_bank_transactions(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return bank transactions list, newest first.

    Args:
        limit:  Maximum number of results (default 100, max 1000).
        offset: Number of results to skip for pagination (default 0).

    Returns:
        List of dicts with transaction_id, date, description, amount.
    """
    stmt = (
        select(BankTransaction)
        .order_by(desc(BankTransaction.date))
        .limit(limit)
        .offset(offset)
    )
    txns = db.execute(stmt).scalars().all()
    return [
        {
            "transaction_id": txn.transaction_id,
            "date": txn.date.isoformat() if txn.date else None,
            "description": txn.description,
            "amount": str(txn.amount),
        }
        for txn in txns
    ]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _require_csv_extension(filename: Optional[str]) -> None:
    """Raise HTTP 422 if the uploaded file does not have a .csv extension.

    Args:
        filename: Original filename from the upload (may be None).

    Raises:
        HTTPException 422: If filename is missing or does not end with .csv.
    """
    if not filename or not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422,
            detail=f"File must have a .csv extension. Got: {filename!r}",
        )
