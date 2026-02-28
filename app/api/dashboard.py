"""Dashboard API endpoints.

Purpose-built aggregation endpoints for the frontend dashboard. These endpoints
combine data from multiple models (bookings, journal entries, compliance,
communication) into dashboard-ready responses — something the existing granular
report endpoints are not suited for.

Endpoints:
  GET /api/dashboard/properties   — All properties with id, slug, display_name
  GET /api/dashboard/metrics      — YTD financials with YoY comparison
  GET /api/dashboard/bookings     — Bookings for calendar view with property info
  GET /api/dashboard/occupancy    — Per-property 12-month occupancy rates
  GET /api/dashboard/actions      — Pending resort forms, messages, unreconciled

All monetary amounts returned as strings (2 decimal places).
All dates returned as ISO format strings.
All endpoints accept an optional property_id query parameter to filter by property.
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.account import Account
from app.models.booking import Booking
from app.models.communication_log import CommunicationLog
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.models.property import Property
from app.models.resort_submission import ResortSubmission

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# GET /api/dashboard/properties
# ---------------------------------------------------------------------------


@router.get("/properties")
def get_properties(db: Session = Depends(get_db)) -> list[dict]:
    """Return all properties with id, slug, and display_name.

    No property_id filter — always returns all properties (used to populate
    property selectors in the dashboard UI).

    Returns:
        List of {id, slug, display_name} dicts.
    """
    properties = db.query(Property).order_by(Property.id).all()
    return [
        {
            "id": p.id,
            "slug": p.slug,
            "display_name": p.display_name,
        }
        for p in properties
    ]


# ---------------------------------------------------------------------------
# Shared helper: compute YTD/monthly financial sums
# ---------------------------------------------------------------------------


def _sum_journal_lines(
    db: Session,
    account_type: str,
    start_date: date,
    end_date: date,
    property_id: Optional[int],
) -> Decimal:
    """Sum journal lines for accounts of a given type within a date range.

    Args:
        db: SQLAlchemy session.
        account_type: "revenue" or "expense".
        start_date: Inclusive start date.
        end_date: Inclusive end date.
        property_id: Optional property filter (None = all properties).

    Returns:
        Raw sum of JournalLine.amount (signed: revenue lines are negative credits,
        expense lines are positive debits).
    """
    q = (
        db.query(func.coalesce(func.sum(JournalLine.amount), Decimal("0")))
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .join(Account, Account.id == JournalLine.account_id)
        .filter(Account.account_type == account_type)
        .filter(JournalEntry.entry_date >= start_date)
        .filter(JournalEntry.entry_date <= end_date)
    )
    if property_id is not None:
        q = q.filter(JournalEntry.property_id == property_id)
    result = q.scalar()
    return result if result is not None else Decimal("0")


def _count_pending_actions(db: Session, property_id: Optional[int]) -> int:
    """Count total pending actions across all three sources.

    Used by the metrics endpoint to populate the actions_count badge.

    Sources:
      1. ResortSubmission: status='pending' and (is_urgent OR check_in within 7 days)
      2. CommunicationLog: status='pending' and message_type in ('welcome', 'pre_arrival')
      3. Booking: reconciliation_status='unmatched' and net_amount > 0

    Args:
        db: SQLAlchemy session.
        property_id: Optional property filter.

    Returns:
        Integer count of pending actions.
    """
    today = date.today()
    seven_days = today + timedelta(days=7)

    # Source 1: Pending resort submissions (urgent or within 7 days)
    rs_q = (
        db.query(func.count(ResortSubmission.id))
        .join(Booking, Booking.id == ResortSubmission.booking_id)
        .filter(ResortSubmission.status == "pending")
        .filter(
            (ResortSubmission.is_urgent == True)  # noqa: E712
            | (Booking.check_in_date <= seven_days)
        )
    )
    if property_id is not None:
        rs_q = rs_q.filter(Booking.property_id == property_id)
    rs_count = rs_q.scalar() or 0

    # Source 2: Pending VRBO/RVshare messages
    cl_q = (
        db.query(func.count(CommunicationLog.id))
        .join(Booking, Booking.id == CommunicationLog.booking_id)
        .filter(CommunicationLog.status == "pending")
        .filter(CommunicationLog.message_type.in_(["welcome", "pre_arrival"]))
    )
    if property_id is not None:
        cl_q = cl_q.filter(Booking.property_id == property_id)
    cl_count = cl_q.scalar() or 0

    # Source 3: Unreconciled bookings (actual revenue, not fee-only rows)
    bk_q = (
        db.query(func.count(Booking.id))
        .filter(Booking.reconciliation_status == "unmatched")
        .filter(Booking.net_amount > 0)
    )
    if property_id is not None:
        bk_q = bk_q.filter(Booking.property_id == property_id)
    bk_count = bk_q.scalar() or 0

    return rs_count + cl_count + bk_count


# ---------------------------------------------------------------------------
# GET /api/dashboard/metrics
# ---------------------------------------------------------------------------


@router.get("/metrics")
def get_metrics(
    property_id: Optional[int] = Query(default=None, description="Filter by property ID"),
    db: Session = Depends(get_db),
) -> dict:
    """Return YTD financial metrics with YoY comparison for the dashboard stat cards.

    Aggregates journal line data for the current year-to-date and the same
    period one year prior for year-over-year comparison.

    Sign convention (from accounting module):
      - Revenue accounts: credits stored as negative -> negate for display (positive)
      - Expense accounts: debits stored as positive -> display as-is

    Args:
        property_id: Optional property filter.
        db: SQLAlchemy session.

    Returns:
        Dict with ytd_revenue, ytd_expenses, current_month_profit,
        yoy_revenue_change, yoy_expense_change, and actions_count.
    """
    today = date.today()

    # --- YTD range (Jan 1 through today) ---
    ytd_start = date(today.year, 1, 1)
    ytd_end = today

    # --- Prior-year same-period range ---
    prior_ytd_start = date(today.year - 1, 1, 1)
    prior_ytd_end = date(today.year - 1, today.month, today.day)

    # --- Current month range ---
    month_start = date(today.year, today.month, 1)
    month_end = today

    # Revenue sums (raw negative credits -> negate for positive display)
    ytd_rev_raw = _sum_journal_lines(db, "revenue", ytd_start, ytd_end, property_id)
    ytd_revenue = -ytd_rev_raw  # negate: credits are negative

    prior_rev_raw = _sum_journal_lines(db, "revenue", prior_ytd_start, prior_ytd_end, property_id)
    prior_revenue = -prior_rev_raw

    month_rev_raw = _sum_journal_lines(db, "revenue", month_start, month_end, property_id)
    month_revenue = -month_rev_raw

    # Expense sums (positive debits -> display as-is)
    ytd_exp = _sum_journal_lines(db, "expense", ytd_start, ytd_end, property_id)
    prior_exp = _sum_journal_lines(db, "expense", prior_ytd_start, prior_ytd_end, property_id)
    month_exp = _sum_journal_lines(db, "expense", month_start, month_end, property_id)

    # --- Current month profit ---
    current_month_profit = month_revenue - month_exp

    # --- YoY percentage changes ---
    def _yoy_change(current: Decimal, prior: Decimal) -> Optional[str]:
        """Compute YoY percentage change string, or None if no prior-year data."""
        if prior == Decimal("0"):
            return None
        pct = ((current - prior) / prior) * 100
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.1f}%"

    yoy_revenue_change = _yoy_change(ytd_revenue, prior_revenue)
    yoy_expense_change = _yoy_change(ytd_exp, prior_exp)

    # --- Pending actions count (for badge) ---
    actions_count = _count_pending_actions(db, property_id)

    return {
        "ytd_revenue": f"{ytd_revenue:.2f}",
        "ytd_expenses": f"{ytd_exp:.2f}",
        "current_month_profit": f"{current_month_profit:.2f}",
        "yoy_revenue_change": yoy_revenue_change,
        "yoy_expense_change": yoy_expense_change,
        "actions_count": actions_count,
    }


# ---------------------------------------------------------------------------
# GET /api/dashboard/bookings
# ---------------------------------------------------------------------------


@router.get("/bookings")
def get_bookings(
    property_id: Optional[int] = Query(default=None, description="Filter by property ID"),
    start_date: Optional[date] = Query(
        default=None, description="Range start — returns bookings overlapping this range"
    ),
    end_date: Optional[date] = Query(
        default=None, description="Range end — returns bookings overlapping this range"
    ),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return bookings with property info for the calendar view.

    Date filtering uses overlap semantics: a booking overlaps the range if
    check_in_date <= end_date AND check_out_date >= start_date.

    Capped at 500 results (ordered by check_in_date DESC) so the calendar
    gets all visible bookings without pagination overhead.

    Args:
        property_id: Optional property filter.
        start_date: Optional range start (requires end_date to filter).
        end_date: Optional range end (requires start_date to filter).
        db: SQLAlchemy session.

    Returns:
        List of booking dicts with property slug and display_name joined.
    """
    q = (
        db.query(Booking, Property)
        .join(Property, Property.id == Booking.property_id)
        .order_by(Booking.check_in_date.desc())
    )

    if property_id is not None:
        q = q.filter(Booking.property_id == property_id)

    # Overlap filter: booking overlaps range if check_in <= range_end AND check_out >= range_start
    if start_date is not None and end_date is not None:
        q = q.filter(Booking.check_in_date <= end_date)
        q = q.filter(Booking.check_out_date >= start_date)
    elif start_date is not None:
        q = q.filter(Booking.check_out_date >= start_date)
    elif end_date is not None:
        q = q.filter(Booking.check_in_date <= end_date)

    rows = q.limit(500).all()

    return [
        {
            "id": booking.id,
            "platform": booking.platform,
            "platform_booking_id": booking.platform_booking_id,
            "guest_name": booking.guest_name,
            "check_in_date": booking.check_in_date.isoformat(),
            "check_out_date": booking.check_out_date.isoformat(),
            "net_amount": f"{booking.net_amount:.2f}",
            "property_slug": prop.slug,
            "property_display_name": prop.display_name,
        }
        for booking, prop in rows
    ]


# ---------------------------------------------------------------------------
# GET /api/dashboard/occupancy
# ---------------------------------------------------------------------------


@router.get("/occupancy")
def get_occupancy(
    property_id: Optional[int] = Query(default=None, description="Filter by property ID"),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return per-property occupancy rates for the last 12 calendar months.

    Occupancy is computed server-side in Python for clarity. Each month shows:
      - occupied_nights: nights a booking covers within that calendar month
      - total_nights: total days in that calendar month
      - occupancy_rate: occupied_nights / total_nights (rounded to 4 decimal places)

    Partial-month overlaps are handled correctly: a booking spanning month
    boundaries contributes only the nights within each month.

    Args:
        property_id: Optional property filter.
        db: SQLAlchemy session.

    Returns:
        List of per-property dicts, each with a 12-element months list.
    """
    today = date.today()

    # Build list of last 12 calendar months (most recent first for the window query,
    # but returned chronologically in the response)
    months: list[tuple[int, int]] = []
    year = today.year
    month = today.month
    for _ in range(12):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()  # chronological order

    # Compute the query range for bookings: start of earliest month to today
    earliest_year, earliest_month = months[0]
    window_start = date(earliest_year, earliest_month, 1)
    window_end = today

    # Query properties to iterate over
    prop_q = db.query(Property).order_by(Property.id)
    if property_id is not None:
        prop_q = prop_q.filter(Property.id == property_id)
    properties = prop_q.all()

    result = []

    for prop in properties:
        # Fetch all bookings for this property that overlap the window
        bookings = (
            db.query(Booking)
            .filter(Booking.property_id == prop.id)
            .filter(Booking.check_in_date <= window_end)
            .filter(Booking.check_out_date >= window_start)
            .all()
        )

        month_data = []
        for yr, mo in months:
            # Month boundaries
            _, last_day_of_month = calendar.monthrange(yr, mo)
            month_start = date(yr, mo, 1)
            month_end = date(yr, mo, last_day_of_month)
            total_nights = last_day_of_month

            # Occupied nights: sum of overlap between each booking and this month
            occupied_nights = 0
            for bk in bookings:
                overlap_start = max(bk.check_in_date, month_start)
                overlap_end = min(bk.check_out_date, month_end)
                if overlap_start < overlap_end:
                    occupied_nights += (overlap_end - overlap_start).days

            occupancy_rate = round(occupied_nights / total_nights, 4) if total_nights > 0 else 0.0

            month_data.append(
                {
                    "year": yr,
                    "month": mo,
                    "occupied_nights": occupied_nights,
                    "total_nights": total_nights,
                    "occupancy_rate": occupancy_rate,
                }
            )

        result.append(
            {
                "property_slug": prop.slug,
                "property_display_name": prop.display_name,
                "months": month_data,
            }
        )

    return result


# ---------------------------------------------------------------------------
# GET /api/dashboard/actions
# ---------------------------------------------------------------------------


@router.get("/actions")
def get_actions(
    property_id: Optional[int] = Query(default=None, description="Filter by property ID"),
    db: Session = Depends(get_db),
) -> dict:
    """Return pending action items from three sources, sorted by urgency.

    Sources and inclusion criteria:
      1. Resort forms: ResortSubmission with status='pending' and
         (is_urgent=True OR check_in_date within 7 days).
      2. VRBO/RVshare messages: CommunicationLog with status='pending' and
         message_type in ('welcome', 'pre_arrival').
      3. Unreconciled bookings: Booking with reconciliation_status='unmatched'
         and net_amount > 0 (excludes fee-only rows).

    Sort order: resort forms (days_to_checkin ASC) → messages (scheduled_for
    ASC) → unreconciled (check_in_date DESC).

    Args:
        property_id: Optional property filter.
        db: SQLAlchemy session.

    Returns:
        Dict with 'actions' (list) and 'total' (integer count).
    """
    today = date.today()
    seven_days = today + timedelta(days=7)

    actions: list[dict] = []

    # ------------------------------------------------------------------
    # Source 1: Pending resort submissions
    # ------------------------------------------------------------------
    rs_q = (
        db.query(ResortSubmission, Booking, Property)
        .join(Booking, Booking.id == ResortSubmission.booking_id)
        .join(Property, Property.id == Booking.property_id)
        .filter(ResortSubmission.status == "pending")
        .filter(
            (ResortSubmission.is_urgent == True)  # noqa: E712
            | (Booking.check_in_date <= seven_days)
        )
    )
    if property_id is not None:
        rs_q = rs_q.filter(Booking.property_id == property_id)

    for submission, booking, prop in rs_q.all():
        days_to_checkin = (booking.check_in_date - today).days
        actions.append(
            {
                "type": "resort_form",
                "booking_id": booking.id,
                "guest_name": booking.guest_name,
                "check_in_date": booking.check_in_date.isoformat(),
                "property_slug": prop.slug,
                "urgency": days_to_checkin,
                "submission_id": submission.id,
                # Sort key for ordering within group
                "_sort_key": days_to_checkin,
                "_group": 0,
            }
        )

    # ------------------------------------------------------------------
    # Source 2: Pending VRBO/RVshare messages
    # ------------------------------------------------------------------
    cl_q = (
        db.query(CommunicationLog, Booking, Property)
        .join(Booking, Booking.id == CommunicationLog.booking_id)
        .join(Property, Property.id == Booking.property_id)
        .filter(CommunicationLog.status == "pending")
        .filter(CommunicationLog.message_type.in_(["welcome", "pre_arrival"]))
    )
    if property_id is not None:
        cl_q = cl_q.filter(Booking.property_id == property_id)

    for log, booking, prop in cl_q.all():
        # scheduled_for may be None for welcome messages
        scheduled_for_str = log.scheduled_for.isoformat() if log.scheduled_for else None
        # Use a large sort key for None (puts unscheduled last within message group)
        sort_key = log.scheduled_for.timestamp() if log.scheduled_for else float("inf")
        actions.append(
            {
                "type": "vrbo_message",
                "booking_id": booking.id,
                "guest_name": booking.guest_name,
                "message_type": log.message_type,
                "scheduled_for": scheduled_for_str,
                "property_slug": prop.slug,
                "log_id": log.id,
                "_sort_key": sort_key,
                "_group": 1,
            }
        )

    # ------------------------------------------------------------------
    # Source 3: Unreconciled bookings
    # ------------------------------------------------------------------
    bk_q = (
        db.query(Booking, Property)
        .join(Property, Property.id == Booking.property_id)
        .filter(Booking.reconciliation_status == "unmatched")
        .filter(Booking.net_amount > 0)
    )
    if property_id is not None:
        bk_q = bk_q.filter(Booking.property_id == property_id)

    for booking, prop in bk_q.all():
        # Sort unreconciled by check_in_date DESC — most recent first
        # Negate the date ordinal so that higher (more recent) dates sort first
        sort_key = -booking.check_in_date.toordinal()
        actions.append(
            {
                "type": "unreconciled",
                "booking_id": booking.id,
                "platform": booking.platform,
                "guest_name": booking.guest_name,
                "net_amount": f"{booking.net_amount:.2f}",
                "check_in_date": booking.check_in_date.isoformat(),
                "property_slug": prop.slug,
                "_sort_key": sort_key,
                "_group": 2,
            }
        )

    # ------------------------------------------------------------------
    # Sort: group 0 (resort) → group 1 (messages) → group 2 (unreconciled)
    # Within each group, sort by _sort_key
    # ------------------------------------------------------------------
    actions.sort(key=lambda a: (a["_group"], a["_sort_key"]))

    # Strip internal sort fields before returning
    clean_actions = []
    for action in actions:
        clean = {k: v for k, v in action.items() if not k.startswith("_")}
        clean_actions.append(clean)

    return {
        "actions": clean_actions,
        "total": len(clean_actions),
    }
