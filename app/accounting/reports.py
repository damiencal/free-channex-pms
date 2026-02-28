"""Financial report generators and shared helpers.

This module contains:
- resolve_period(): shared date-range resolver for all report endpoints
- Category constants for bank transaction categorization
- Report generator functions (added by plans 04-02 and 04-03)
"""
import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.accounting.expenses import EXPENSE_CATEGORIES
from app.models.account import Account
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.models.property import Property

# Non-expense categories for bank transactions that don't appear on P&L
NON_EXPENSE_CATEGORIES = [
    "owner_deposit",
    "loan_payment",
    "transfer",
    "personal",
]

# All valid categories for bank transaction categorization
ALL_CATEGORIES = EXPENSE_CATEGORIES + NON_EXPENSE_CATEGORIES


def resolve_period(
    start_date: date | None = None,
    end_date: date | None = None,
    month: int | None = None,
    quarter: str | None = None,  # "Q1", "Q2", "Q3", "Q4"
    year: int | None = None,
    ytd: bool = False,
) -> tuple[date, date]:
    """Resolve a reporting period into a (start_date, end_date) tuple.

    Resolution priority (first match wins):
    1. start_date + end_date: returned directly after validation
    2. month + year: first and last day of that calendar month
    3. quarter + year: first and last day of that quarter
    4. year alone: Jan 1 - Dec 31 of that year
    5. ytd=True: Jan 1 of current year through today
    6. No match: raises ValueError

    Args:
        start_date: Explicit period start (requires end_date).
        end_date: Explicit period end (requires start_date).
        month: Calendar month (1-12). Requires year.
        quarter: One of "Q1", "Q2", "Q3", "Q4" (case-insensitive). Requires year.
        year: Calendar year (e.g., 2026).
        ytd: If True, return Jan 1 of current year through today.

    Returns:
        Tuple of (start_date, end_date) as datetime.date objects.

    Raises:
        ValueError: If parameters are invalid or insufficient to determine a period.
    """
    # 1. Explicit start_date and end_date
    if start_date is not None and end_date is not None:
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date")
        return (start_date, end_date)

    # 2. month + year
    if month is not None:
        if year is None:
            raise ValueError("month requires year")
        last_day = calendar.monthrange(year, month)[1]
        return (date(year, month, 1), date(year, month, last_day))

    # 3. quarter + year
    if quarter is not None:
        if year is None:
            raise ValueError("quarter requires year")
        q_upper = quarter.upper()
        _QUARTER_MONTHS = {
            "Q1": (1, 3),
            "Q2": (4, 6),
            "Q3": (7, 9),
            "Q4": (10, 12),
        }
        if q_upper not in _QUARTER_MONTHS:
            raise ValueError(f"Invalid quarter: {quarter}. Use Q1, Q2, Q3, or Q4.")
        start_month, end_month = _QUARTER_MONTHS[q_upper]
        last_day = calendar.monthrange(year, end_month)[1]
        return (date(year, start_month, 1), date(year, end_month, last_day))

    # 4. year alone
    if year is not None:
        return (date(year, 1, 1), date(year, 12, 31))

    # 5. year-to-date
    if ytd:
        today = date.today()
        return (date(today.year, 1, 1), today)

    # 6. No valid period specified
    raise ValueError(
        "No valid period specified. Provide start_date/end_date, month+year, "
        "quarter+year, year, or ytd=True."
    )


def generate_pl(
    db: Session,
    start_date: date,
    end_date: date,
    breakdown: str = "combined",  # "combined" or "property"
) -> dict:
    """Generate a Profit & Loss report for the given date range.

    Queries journal_lines to compute:
    - Revenue by platform (airbnb, vrbo, rvshare) with per-month rows per platform
    - Expenses by category name

    Revenue journal lines are credits (negative amounts in journal_lines). They are
    negated here so that positive numbers appear in the P&L for display.

    Args:
        db: SQLAlchemy session.
        start_date: Inclusive start of the reporting period.
        end_date: Inclusive end of the reporting period.
        breakdown: "combined" (default) or "property" for per-property columns.

    Returns:
        Dict with period, breakdown, revenue, expenses, and net_income (combined mode)
        or period, breakdown, properties, and combined (property mode).
    """
    # ------------------------------------------------------------------
    # 1. Query revenue lines (booking_payout source_type, revenue accounts)
    # ------------------------------------------------------------------
    # Group by: property_id, source_id (to extract platform), year, month
    revenue_rows = (
        db.query(
            JournalEntry.property_id,
            JournalEntry.source_id,
            func.extract("year", JournalEntry.entry_date).label("year"),
            func.extract("month", JournalEntry.entry_date).label("month"),
            func.sum(JournalLine.amount).label("amount"),
        )
        .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .join(Account, Account.id == JournalLine.account_id)
        .filter(Account.account_type == "revenue")
        .filter(JournalEntry.entry_date >= start_date)
        .filter(JournalEntry.entry_date <= end_date)
        .filter(JournalEntry.source_type == "booking_payout")
        .group_by(
            JournalEntry.property_id,
            JournalEntry.source_id,
            func.extract("year", JournalEntry.entry_date),
            func.extract("month", JournalEntry.entry_date),
        )
        .all()
    )

    # ------------------------------------------------------------------
    # 2. Query expense lines (all source types, expense accounts)
    # ------------------------------------------------------------------
    # Group by: property_id, account name (= category)
    expense_rows = (
        db.query(
            JournalEntry.property_id,
            Account.name.label("category"),
            func.sum(JournalLine.amount).label("amount"),
        )
        .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .join(Account, Account.id == JournalLine.account_id)
        .filter(Account.account_type == "expense")
        .filter(JournalEntry.entry_date >= start_date)
        .filter(JournalEntry.entry_date <= end_date)
        .group_by(JournalEntry.property_id, Account.name)
        .all()
    )

    # ------------------------------------------------------------------
    # 3. Fetch all active properties
    # ------------------------------------------------------------------
    properties = db.query(Property).order_by(Property.id).all()
    property_count = len(properties)

    # ------------------------------------------------------------------
    # 4. Organise revenue data into nested structure
    # ------------------------------------------------------------------
    # revenue_data[property_id or None][platform][(year, month)] = total_amount
    # Revenue lines are credits (negative). Negate so display values are positive.
    revenue_data: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))

    for row in revenue_rows:
        # Extract platform from source_id: "booking_payout:{platform}:{booking_id}"
        platform = row.source_id.split(":")[1]
        # Negate: credits are negative in journal_lines; positive = revenue earned
        amount = -(row.amount)
        year_int = int(row.year)
        month_int = int(row.month)
        revenue_data[row.property_id][platform][(year_int, month_int)] += amount

    # ------------------------------------------------------------------
    # 5. Organise expense data
    # ------------------------------------------------------------------
    # expense_data[property_id or None][category] = total_amount
    # Expenses are debits (positive). Show as-is.
    expense_data: dict = defaultdict(lambda: defaultdict(Decimal))

    for row in expense_rows:
        expense_data[row.property_id][row.category] += row.amount

    # ------------------------------------------------------------------
    # 6. Helper: build platform revenue dict (combined across all properties)
    # ------------------------------------------------------------------

    def _build_platform_revenue(rev_map: dict) -> dict:
        """Build by_platform dict with months list and subtotal from a platform->month->amount map."""
        by_platform: dict = {}
        total = Decimal("0")
        for platform, month_map in rev_map.items():
            months_sorted = sorted(month_map.keys())  # sorted (year, month) tuples
            months_list = [
                {
                    "month": f"{yr:04d}-{mo:02d}",
                    "amount": str(month_map[(yr, mo)]),
                }
                for yr, mo in months_sorted
            ]
            subtotal = sum(month_map.values(), Decimal("0"))
            by_platform[platform] = {
                "months": months_list,
                "subtotal": str(subtotal),
            }
            total += subtotal
        return by_platform, total

    def _merge_platform_revenue(list_of_rev_data: list) -> tuple[dict, Decimal]:
        """Merge multiple property revenue dicts into a single platform->month->amount map."""
        merged: dict = defaultdict(lambda: defaultdict(Decimal))
        for rev_map in list_of_rev_data:
            for platform, month_map in rev_map.items():
                for ym, amt in month_map.items():
                    merged[platform][ym] += amt
        return _build_platform_revenue(merged)

    def _build_expense_totals(cat_map: dict) -> tuple[dict, Decimal]:
        """Build by_category dict with totals from a category->amount map."""
        by_category = {cat: str(amt) for cat, amt in sorted(cat_map.items())}
        total = sum(cat_map.values(), Decimal("0"))
        return by_category, total

    def _merge_expense_totals(list_of_cat_maps: list) -> tuple[dict, Decimal]:
        """Merge multiple category maps into a single category->amount map (uses full amounts)."""
        merged: dict = defaultdict(Decimal)
        for cat_map in list_of_cat_maps:
            for cat, amt in cat_map.items():
                merged[cat] += amt
        return _build_expense_totals(merged)

    # ------------------------------------------------------------------
    # 7. Build response
    # ------------------------------------------------------------------
    period_dict = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    if breakdown == "combined":
        # Merge revenue from all properties (keyed by property_id incl. None)
        all_rev_maps = list(revenue_data.values())
        by_platform, revenue_total = _merge_platform_revenue(all_rev_maps)

        # Merge expenses from all properties (including shared expenses at full value)
        all_exp_maps = list(expense_data.values())
        by_category, expense_total = _merge_expense_totals(all_exp_maps)

        net_income = revenue_total - expense_total

        return {
            "period": period_dict,
            "breakdown": "combined",
            "revenue": {
                "by_platform": by_platform,
                "total": str(revenue_total),
            },
            "expenses": {
                "by_category": by_category,
                "total": str(expense_total),
            },
            "net_income": str(net_income),
        }

    else:  # breakdown == "property"
        # Build per-property sections
        property_sections: dict = {}

        # Shared expense categories (property_id == None) to allocate 1/N per property
        shared_exp_map = dict(expense_data.get(None, {}))

        for prop in properties:
            # Revenue for this property
            prop_rev_map = dict(revenue_data.get(prop.id, {}))
            by_platform, prop_rev_total = _build_platform_revenue(prop_rev_map)

            # Property-specific expenses
            prop_exp_map = dict(expense_data.get(prop.id, {}))

            # Add allocated share of shared expenses (1/N)
            if property_count > 0:
                for cat, shared_amt in shared_exp_map.items():
                    allocated = shared_amt / property_count
                    prop_exp_map[cat] = prop_exp_map.get(cat, Decimal("0")) + allocated

            by_category, prop_exp_total = _build_expense_totals(prop_exp_map)
            prop_net = prop_rev_total - prop_exp_total

            property_sections[prop.display_name] = {
                "property_id": prop.id,
                "revenue": {
                    "by_platform": by_platform,
                    "total": str(prop_rev_total),
                },
                "expenses": {
                    "by_category": by_category,
                    "total": str(prop_exp_total),
                },
                "net_income": str(prop_net),
            }

        # Combined totals: full amounts (not per-property sums) to avoid double-counting shared expenses
        all_rev_maps = list(revenue_data.values())
        comb_by_platform, comb_rev_total = _merge_platform_revenue(all_rev_maps)

        # Combined expenses: use all expense data directly (shared expenses counted once)
        all_exp_maps = list(expense_data.values())
        comb_by_category, comb_exp_total = _merge_expense_totals(all_exp_maps)
        comb_net = comb_rev_total - comb_exp_total

        return {
            "period": period_dict,
            "breakdown": "property",
            "properties": property_sections,
            "combined": {
                "revenue": {
                    "by_platform": comb_by_platform,
                    "total": str(comb_rev_total),
                },
                "expenses": {
                    "by_category": comb_by_category,
                    "total": str(comb_exp_total),
                },
                "net_income": str(comb_net),
            },
        }
