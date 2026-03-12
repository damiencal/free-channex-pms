"""Metrics API endpoints.

Endpoints:
  GET /api/metrics/realtime          — real-time operational statistics for today
  GET /api/metrics/monthly-reports   — month-by-month income/expense/booking summary
  GET /api/metrics/income-expenses   — flat ledger of income and expense entries
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models.booking import Booking
from app.models.expense import Expense
from app.models.property import Property

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


# ── Realtime ──────────────────────────────────────────────────────────────────


@router.get("/realtime")
def get_realtime_stats(
    property_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
):
    today = date.today()

    def bq(extra_filters=""):
        base = "SELECT COUNT(*) FROM bookings b WHERE b.booking_state != 'cancelled'"
        if property_id:
            base += f" AND b.property_id = {property_id}"
        return base + extra_filters

    check_ins_today = (
        db.execute(text(bq(" AND b.check_in_date = :d")), {"d": today}).scalar() or 0
    )

    check_outs_today = (
        db.execute(text(bq(" AND b.check_out_date = :d")), {"d": today}).scalar() or 0
    )

    in_stay = (
        db.execute(
            text(bq(" AND b.check_in_date <= :d AND b.check_out_date > :d")),
            {"d": today},
        ).scalar()
        or 0
    )

    # Count active (non-cancelled) bookings created today
    bookings_today = (
        db.execute(text(bq(" AND DATE(b.created_at) = :d")), {"d": today}).scalar() or 0
    )

    # Cancelled today (updated_at today & booking_state = cancelled)
    cancelled_q = "SELECT COUNT(*) FROM bookings WHERE booking_state = 'cancelled' AND DATE(updated_at) = :d"
    if property_id:
        cancelled_q += f" AND property_id = {property_id}"
    cancelled_today = db.execute(text(cancelled_q), {"d": today}).scalar() or 0

    # Tasks today
    tasks_q = "SELECT COUNT(*) FROM cleaning_tasks WHERE scheduled_date = :d"
    if property_id:
        tasks_q += f" AND property_id = {property_id}"
    tasks_today = db.execute(text(tasks_q), {"d": today}).scalar() or 0

    # Property count
    prop_q = "SELECT COUNT(*) FROM properties"
    if property_id:
        total_properties = 1
    else:
        total_properties = db.execute(text(prop_q)).scalar() or 1

    vacant = max(0, total_properties - in_stay)
    occupancy_rate = (
        round((in_stay / total_properties) * 100, 1) if total_properties else 0.0
    )

    return {
        "check_ins_today": int(check_ins_today),
        "check_outs_today": int(check_outs_today),
        "in_stay": int(in_stay),
        "vacant": int(vacant),
        "occupancy_rate": occupancy_rate,
        "total_properties": int(total_properties),
        "inquiries_today": 0,
        "bookings_today": int(bookings_today),
        "cancelled_today": int(cancelled_today),
        "tasks_today": int(tasks_today),
    }


# ── Monthly reports ───────────────────────────────────────────────────────────


@router.get("/monthly-reports")
def get_monthly_reports(
    property_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
):
    """Return month-by-month summary from portfolio_metrics table.

    Falls back to computing directly from bookings + expenses if no portfolio
    metrics are stored yet.
    """
    # Try portfolio_metrics first (computed by nightly job)
    prop_filter = "AND property_id = :pid" if property_id else ""
    rows = db.execute(
        text(f"""
            SELECT
                TO_CHAR(metric_date, 'YYYY-MM')  AS month,
                SUM(booking_count)               AS reservations,
                SUM(revenue)                     AS total_income,
                SUM(expenses)                    AS total_expense,
                MAX(computed_at)                 AS generated_at
            FROM portfolio_metrics
            WHERE 1=1 {prop_filter}
            GROUP BY TO_CHAR(metric_date, 'YYYY-MM')
            ORDER BY month DESC
            LIMIT 24
        """),
        {"pid": property_id} if property_id else {},
    ).fetchall()

    if rows:
        result = []
        for r in rows:
            income = float(r.total_income or 0)
            expense = float(r.total_expense or 0)
            result.append(
                {
                    "month": r.month,
                    "reservations": int(r.reservations or 0),
                    "total_income": round(income, 2),
                    "total_expense": round(expense, 2),
                    "net_profit": round(income - expense, 2),
                    "generated_at": r.generated_at.isoformat()
                    if r.generated_at
                    else None,
                }
            )
        return result

    # Fallback: compute from bookings + expenses directly
    booking_filter = "AND b.property_id = :pid" if property_id else ""
    expense_filter = "AND e.property_id = :pid" if property_id else ""
    params: dict = {"pid": property_id} if property_id else {}

    booking_rows = db.execute(
        text(f"""
            SELECT
                TO_CHAR(b.check_in_date, 'YYYY-MM') AS month,
                COUNT(*)                             AS reservations,
                COALESCE(SUM(b.net_amount), 0)       AS total_income
            FROM bookings b
            WHERE b.booking_state != 'cancelled'
                AND b.check_in_date IS NOT NULL
                {booking_filter}
            GROUP BY TO_CHAR(b.check_in_date, 'YYYY-MM')
        """),
        params,
    ).fetchall()

    expense_rows = db.execute(
        text(f"""
            SELECT
                TO_CHAR(e.expense_date, 'YYYY-MM') AS month,
                COALESCE(SUM(e.amount), 0)          AS total_expense
            FROM expenses e
            WHERE e.expense_date IS NOT NULL
                {expense_filter}
            GROUP BY TO_CHAR(e.expense_date, 'YYYY-MM')
        """),
        params,
    ).fetchall()

    expense_by_month = {r.month: float(r.total_expense) for r in expense_rows}

    months_seen: dict = {}
    for r in booking_rows:
        months_seen[r.month] = {
            "month": r.month,
            "reservations": int(r.reservations),
            "total_income": round(float(r.total_income), 2),
            "total_expense": round(expense_by_month.get(r.month, 0.0), 2),
            "net_profit": 0.0,
            "generated_at": None,
        }

    for m in months_seen:
        months_seen[m]["net_profit"] = round(
            months_seen[m]["total_income"] - months_seen[m]["total_expense"], 2
        )

    return sorted(months_seen.values(), key=lambda x: x["month"], reverse=True)[:24]


# ── Income & Expenses ─────────────────────────────────────────────────────────


@router.get("/income-expenses")
def get_income_expenses(
    property_id: Optional[int] = Query(None),
    month: Optional[str] = Query(None, description="YYYY-MM"),
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
):
    """Return a flat list of income (bookings) and expense entries for the period."""
    params: dict = {}
    prop_filter = ""
    if property_id:
        prop_filter = "AND property_id = :pid"
        params["pid"] = property_id

    month_booking_filter = ""
    month_expense_filter = ""
    if month:
        params["month_start"] = f"{month}-01"
        params["month_end"] = f"{month}-01"
        month_booking_filter = "AND TO_CHAR(check_in_date, 'YYYY-MM') = TO_CHAR(CAST(:month_start AS DATE), 'YYYY-MM')"
        month_expense_filter = "AND TO_CHAR(expense_date, 'YYYY-MM') = TO_CHAR(CAST(:month_start AS DATE), 'YYYY-MM')"

    # Income rows from bookings
    income_rows = db.execute(
        text(f"""
            SELECT
                b.id,
                b.guest_name                     AS item,
                b.net_amount                     AS amount,
                b.platform                       AS payment_method,
                b.platform                       AS channel,
                b.check_in_date::text            AS time,
                'system'                         AS operator,
                b.id                             AS reservation_id,
                p.display_name                   AS property_name,
                b.notes                          AS note
            FROM bookings b
            LEFT JOIN properties p ON p.id = b.property_id
            WHERE b.booking_state != 'cancelled'
                AND b.net_amount > 0
                {prop_filter}
                {month_booking_filter}
            ORDER BY b.check_in_date DESC
            LIMIT 100
        """),
        params,
    ).fetchall()

    # Expense rows
    expense_rows = db.execute(
        text(f"""
            SELECT
                e.id,
                COALESCE(e.description, e.category) AS item,
                e.amount,
                'expense'                           AS payment_method,
                e.category                          AS channel,
                e.expense_date::text                AS time,
                COALESCE(e.vendor, 'system')        AS operator,
                NULL                                AS reservation_id,
                p.display_name                      AS property_name,
                e.description                       AS note
            FROM expenses e
            LEFT JOIN properties p ON p.id = e.property_id
            WHERE 1=1
                {prop_filter.replace("property_id", "e.property_id")}
                {month_expense_filter.replace("expense_date", "e.expense_date")}
            ORDER BY e.expense_date DESC
            LIMIT 100
        """),
        params,
    ).fetchall()

    result = []
    for r in income_rows:
        result.append(
            {
                "id": r.id,
                "item": r.item or "Booking",
                "amount": float(r.amount or 0),
                "payment_method": r.payment_method or "direct",
                "channel": r.channel,
                "time": r.time or "",
                "operator": r.operator,
                "reservation_id": r.reservation_id,
                "property_name": r.property_name,
                "note": r.note,
            }
        )
    for r in expense_rows:
        result.append(
            {
                "id": -r.id,  # negative to avoid ID collisions with income rows
                "item": r.item or "Expense",
                "amount": -float(r.amount or 0),  # negative = expense
                "payment_method": r.payment_method,
                "channel": r.channel,
                "time": r.time or "",
                "operator": r.operator,
                "reservation_id": None,
                "property_name": r.property_name,
                "note": r.note,
            }
        )

    # Sort combined list by time desc
    result.sort(key=lambda x: x["time"], reverse=True)
    return result
