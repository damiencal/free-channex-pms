"""Compliance API endpoints.

Exposes resort booking form submission management:
  - GET  /compliance/submissions           — List all submissions with status + urgency
  - POST /compliance/submit/{booking_id}   — Manually trigger submission for a booking
  - POST /compliance/confirm/{booking_id}  — Mark as confirmed (n8n webhook)
  - POST /compliance/approve/{submission_id} — Approve preview-mode submission and send
  - POST /compliance/process-pending       — Batch-process all pending auto-submit submissions
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.compliance.submission import process_booking_submission, should_auto_submit
from app.config import get_config
from app.db import get_db
from app.models.booking import Booking
from app.models.property import Property
from app.models.resort_submission import ResortSubmission

router = APIRouter(prefix="/compliance", tags=["compliance"])


# ---------------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------------


@router.get("/submissions")
def list_submissions(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: pending, submitted, confirmed",
    ),
    urgent_only: bool = Query(
        default=False,
        description="Only show urgent submissions",
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return resort form submissions with booking details.

    Includes: submission status, urgency flag, confirmation attachment status,
    guest name, check-in date, property slug, and timestamps.

    Args:
        status: Optional filter by submission status.
        urgent_only: If true, only return submissions flagged as urgent.
        limit: Max results (default 100).
        offset: Pagination offset.

    Returns:
        List of submission dicts with booking and property details.
    """
    stmt = (
        select(ResortSubmission, Booking, Property.slug.label("prop_slug"))
        .join(Booking, ResortSubmission.booking_id == Booking.id)
        .join(Property, Booking.property_id == Property.id)
        .order_by(desc(ResortSubmission.created_at))
        .limit(limit)
        .offset(offset)
    )

    if status is not None:
        stmt = stmt.where(ResortSubmission.status == status)
    if urgent_only:
        stmt = stmt.where(ResortSubmission.is_urgent == True)  # noqa: E712

    rows = db.execute(stmt).all()
    return [
        {
            "submission_id": sub.id,
            "booking_id": sub.booking_id,
            "status": sub.status,
            "is_urgent": sub.is_urgent,
            "submitted_automatically": sub.submitted_automatically,
            "confirmation_attached": sub.confirmation_attached,
            "email_sent_at": sub.email_sent_at.isoformat() if sub.email_sent_at else None,
            "confirmed_at": sub.confirmed_at.isoformat() if sub.confirmed_at else None,
            "error_message": sub.error_message,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
            "guest_name": booking.guest_name,
            "platform_booking_id": booking.platform_booking_id,
            "platform": booking.platform,
            "check_in_date": booking.check_in_date.isoformat() if booking.check_in_date else None,
            "check_out_date": booking.check_out_date.isoformat() if booking.check_out_date else None,
            "property_slug": prop_slug,
        }
        for sub, booking, prop_slug in rows
    ]


# ---------------------------------------------------------------------------
# Batch endpoint — MUST be before /{param} routes to avoid route conflicts
# ---------------------------------------------------------------------------


@router.post("/process-pending")
async def process_pending_submissions(
    db: Session = Depends(get_db),
) -> dict:
    """Process all pending submissions eligible for auto-submit.

    Finds all submissions with status='pending' and processes each one.
    Respects preview mode — only processes if auto-submit threshold is met.

    Returns:
        Dict with processed count and per-submission results.
    """
    config = get_config()

    if not should_auto_submit(db, config.auto_submit_threshold):
        return {
            "action": "preview_mode_active",
            "message": (
                f"Auto-submit threshold ({config.auto_submit_threshold}) not yet reached. "
                "Use POST /compliance/approve/{id} to approve individual submissions."
            ),
            "processed": 0,
        }

    # Find all pending submissions
    pending = db.execute(
        select(ResortSubmission).where(ResortSubmission.status == "pending")
    ).scalars().all()

    if not pending:
        return {"action": "none_pending", "processed": 0}

    results = []
    for submission in pending:
        result = await process_booking_submission(submission.booking_id, db)
        results.append({
            "booking_id": submission.booking_id,
            "submission_id": submission.id,
            **result,
        })

    submitted_count = sum(1 for r in results if r.get("action") == "submitted")
    failed_count = sum(1 for r in results if r.get("action") == "failed")

    return {
        "action": "batch_processed",
        "processed": len(results),
        "submitted": submitted_count,
        "failed": failed_count,
        "results": results,
    }


# ---------------------------------------------------------------------------
# Path-param endpoints — after fixed-path routes
# ---------------------------------------------------------------------------


@router.post("/submit/{booking_id}")
async def submit_booking(
    booking_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Trigger resort form submission for a specific booking.

    Fills the PDF form, sends the email with retry, and updates the
    submission status. If in preview mode, this endpoint processes the
    submission regardless (operator-initiated = manual override).

    Args:
        booking_id: ID of the booking to submit.

    Returns:
        Dict with action (submitted/failed/already_exists) and details.

    Raises:
        HTTPException 404: If booking not found.
    """
    result = await process_booking_submission(booking_id, db)
    if result.get("action") == "error":
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/confirm/{booking_id}")
def confirm_submission(
    booking_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Mark a resort submission as confirmed (n8n webhook endpoint).

    Called by n8n when the Campspot automated confirmation email is received
    (from do-not-reply@campspot.com, subject contains "Reservation Confirmation").

    Idempotent — confirming an already-confirmed submission returns success.

    Args:
        booking_id: ID of the booking whose submission to confirm.

    Returns:
        Dict with status and booking_id.

    Raises:
        HTTPException 404: If no submission exists for this booking.
    """
    submission = db.execute(
        select(ResortSubmission).where(ResortSubmission.booking_id == booking_id)
    ).scalar_one_or_none()

    if submission is None:
        raise HTTPException(
            status_code=404,
            detail=f"No submission found for booking {booking_id}",
        )

    if submission.status == "confirmed":
        return {"status": "already_confirmed", "booking_id": booking_id}

    submission.status = "confirmed"
    submission.confirmed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "confirmed", "booking_id": booking_id}


@router.post("/approve/{submission_id}")
async def approve_submission(
    submission_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Approve a preview-mode submission and trigger email send.

    Preview mode creates submissions with submitted_automatically=False and
    status='pending'. This endpoint approves the submission and triggers the
    full send pipeline (fill PDF, send email).

    Args:
        submission_id: ID of the submission to approve.

    Returns:
        Dict with action and submission details.

    Raises:
        HTTPException 404: If submission not found.
        HTTPException 409: If submission is not in pending/preview state.
    """
    submission = db.get(ResortSubmission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=404,
            detail=f"Submission {submission_id} not found",
        )

    if submission.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Submission {submission_id} is '{submission.status}', not 'pending'",
        )

    # Process the submission (fill PDF + send email)
    result = await process_booking_submission(submission.booking_id, db)
    return result
