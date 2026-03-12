"""Price recommendation engine — the HLP (Hyper Local Pulse) algorithm.

Generates pricing recommendations for a property over a date range.
The algorithm:
  1. Fetch base price from active RatePlan
  2. Compute demand score from demand engine
  3. Apply demand-driven price adjustment (controlled by sensitivity setting)
  4. Apply time-to-arrival factors (last-minute discount / early-bird discount)
  5. Apply weekend markup
  6. Detect orphan days (isolated gaps) and apply fill discount
  7. Apply event calendar modifier directly
  8. Clamp to pricing rule min/max
  9. Compute confidence score
  10. Compute min-stay recommendation (gap-filling intelligence)

Results are upserted into price_recommendations with status='pending'.
Previously accepted/rejected recommendations are not regenerated.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import structlog
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.price_recommendation import PriceRecommendation
from app.models.pricing_rule import PricingRule
from app.models.rate_plan import RatePlan
from app.pricing.demand import calculate_confidence, calculate_demand_score
from app.pricing.providers import InternalMarketDataProvider, MarketDataProvider

log = structlog.get_logger()


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _get_base_price(
    db: Session, property_id: int, pricing_rule: PricingRule
) -> Decimal:
    """Fetch the base price anchor for recommendation generation."""
    # Find the primary active rate plan for the property
    plan = (
        db.query(RatePlan)
        .filter(
            RatePlan.property_id == property_id,
            RatePlan.is_active.is_(True),
            RatePlan.parent_rate_plan_id.is_(None),  # Top-level plan only
        )
        .order_by(RatePlan.id)
        .first()
    )
    if plan and plan.base_rate and plan.base_rate > 0:
        return plan.base_rate

    # Fallback: average of all rate plans
    plans = (
        db.query(RatePlan)
        .filter(RatePlan.property_id == property_id, RatePlan.is_active.is_(True))
        .all()
    )
    if plans:
        avg = statistics.mean(float(p.base_rate) for p in plans if p.base_rate)
        return _round2(Decimal(str(avg)))

    return Decimal("150.00")


def _detect_orphan_day(
    db: Session,
    property_id: int,
    target_date: date,
    window: int = 2,
) -> bool:
    """Detect if the target date is an isolated gap (orphan day) between bookings.

    An orphan day is a 1–N night gap that is unlikely to be booked because
    it's wedged between two existing reservations. Applying a discount to
    orphan days increases their fill probability.

    window: max gap size to consider an "orphan" (default: 2 nights)
    """
    # Find the nearest checkout before target_date
    checkout_before = (
        db.query(Booking.check_out_date)
        .filter(
            Booking.property_id == property_id,
            Booking.check_out_date <= target_date,
            Booking.check_out_date >= target_date - timedelta(days=window + 1),
            Booking.booking_state.notin_(["cancelled", "no_show"]),
        )
        .order_by(Booking.check_out_date.desc())
        .first()
    )

    if not checkout_before:
        return False

    # Find the nearest checkin after target_date
    checkin_after = (
        db.query(Booking.check_in_date)
        .filter(
            Booking.property_id == property_id,
            Booking.check_in_date > target_date,
            Booking.check_in_date <= target_date + timedelta(days=window + 1),
            Booking.booking_state.notin_(["cancelled", "no_show"]),
        )
        .order_by(Booking.check_in_date)
        .first()
    )

    if not checkin_after:
        return False

    # Gap between the two bookings
    gap_nights = (checkin_after[0] - checkout_before[0]).days
    return 0 < gap_nights <= window


def _recommend_min_stay(
    db: Session,
    property_id: int,
    target_date: date,
    pricing_rule: PricingRule,
    demand_score: Decimal,
) -> Optional[int]:
    """Recommend optimal minimum stay based on demand and gap analysis.

    Logic:
    - High demand (score > 0.7): increase min stay to 2 to capture multi-night bookings
    - Orphan day detected: reduce to 1 to maximize fill probability
    - Low demand (score < 0.3): reduce to 1 to accept any booking
    - Otherwise: use pricing rule default or 2 for weekends
    """
    is_orphan = _detect_orphan_day(db, property_id, target_date)

    if is_orphan:
        return 1  # Must accept short stays to fill the gap

    if demand_score > Decimal("0.70"):
        return pricing_rule.min_stay_default if pricing_rule.min_stay_default else 2

    if demand_score < Decimal("0.35"):
        return 1

    # Weekend minimum
    if target_date.weekday() in (4, 5):  # Friday/Saturday
        return 2

    return pricing_rule.min_stay_default or 1


def generate_recommendations(
    db: Session,
    property_id: int,
    start_date: date,
    end_date: date,
    provider: Optional[MarketDataProvider] = None,
) -> list[PriceRecommendation]:
    """Generate or refresh price recommendations for a date range.

    Existing 'accepted' or 'rejected' recommendations are skipped.
    'pending' recommendations are refreshed (overwritten) with latest signals.
    Past-date ('expired') status is set for dates already passed.

    Returns the list of upserted PriceRecommendation objects.
    """
    if provider is None:
        provider = InternalMarketDataProvider(db)

    # Fetch or create pricing rule for this property
    pricing_rule = (
        db.query(PricingRule).filter(PricingRule.property_id == property_id).first()
    )
    if pricing_rule is None:
        pricing_rule = PricingRule(property_id=property_id)
        db.add(pricing_rule)
        db.flush()

    if not pricing_rule.is_active:
        log.info("Pricing rules inactive, skipping generation", property_id=property_id)
        return []

    base_price = _get_base_price(db, property_id, pricing_rule)
    confidence = calculate_confidence(provider, property_id)

    today = date.today()
    results: list[PriceRecommendation] = []

    current_date = start_date
    while current_date < end_date:
        # Skip past dates
        if current_date < today:
            current_date += timedelta(days=1)
            continue

        # Don't regenerate accepted/rejected decisions
        existing = (
            db.query(PriceRecommendation)
            .filter(
                PriceRecommendation.property_id == property_id,
                PriceRecommendation.date == current_date,
            )
            .first()
        )
        if existing and existing.status in ("accepted", "rejected"):
            results.append(existing)
            current_date += timedelta(days=1)
            continue

        # --- Compute demand signals ---
        demand_score, seasonal_factor, event_factor, dow_score = calculate_demand_score(
            db, provider, property_id, current_date
        )

        # --- Apply adjustments ---
        price = base_price

        # Demand adjustment: sensitivity controls how strongly demand moves price
        # demand_score = 0.5 → no change; 1.0 → +sensitivity% increase; 0.0 → -sensitivity%
        sensitivity = float(pricing_rule.demand_sensitivity)
        demand_adj = (float(demand_score) - 0.5) * 2 * sensitivity  # -1.0 to +1.0
        demand_factor = Decimal(str(round(1.0 + demand_adj * 0.5, 4)))  # Max ±50%
        price = price * demand_factor

        # Seasonal / event
        price = price * seasonal_factor * event_factor

        # Weekend markup
        is_weekend = current_date.weekday() in (4, 5)  # Friday or Saturday
        weekend_factor = Decimal("1.0")
        if is_weekend and pricing_rule.weekend_markup_pct > 0:
            weekend_factor = Decimal("1.0") + (
                pricing_rule.weekend_markup_pct / Decimal("100")
            )
            price = price * weekend_factor

        # Time-to-arrival adjustments
        days_out = (current_date - today).days
        last_minute_factor = Decimal("1.0")
        early_bird_factor = Decimal("1.0")

        if days_out <= pricing_rule.last_minute_window_days:
            discount = pricing_rule.last_minute_discount_pct / Decimal("100")
            last_minute_factor = Decimal("1.0") - discount
            price = price * last_minute_factor
        elif days_out >= pricing_rule.early_bird_window_days:
            discount = pricing_rule.early_bird_discount_pct / Decimal("100")
            early_bird_factor = Decimal("1.0") - discount
            price = price * early_bird_factor

        # Orphan day discount
        is_orphan = _detect_orphan_day(db, property_id, current_date)
        if is_orphan and pricing_rule.orphan_day_discount_pct > 0:
            orphan_discount = pricing_rule.orphan_day_discount_pct / Decimal("100")
            price = price * (Decimal("1.0") - orphan_discount)

        # Clamp to min/max
        if pricing_rule.min_price and price < pricing_rule.min_price:
            price = pricing_rule.min_price
        if pricing_rule.max_price and price > pricing_rule.max_price:
            price = pricing_rule.max_price

        price = _round2(price)

        # Min-stay recommendation
        recommended_min_stay = _recommend_min_stay(
            db, property_id, current_date, pricing_rule, demand_score
        )

        # Upsert recommendation
        if existing:
            existing.recommended_price = price
            existing.recommended_min_stay = recommended_min_stay
            existing.base_price = base_price
            existing.demand_score = demand_score
            existing.supply_score = Decimal(
                "0.500"
            )  # Placeholder for future supply signal
            existing.seasonal_factor = seasonal_factor
            existing.event_factor = event_factor
            existing.weekend_factor = weekend_factor
            existing.last_minute_factor = last_minute_factor
            existing.early_bird_factor = early_bird_factor
            existing.confidence = confidence
            existing.status = "pending"
            results.append(existing)
        else:
            rec = PriceRecommendation(
                property_id=property_id,
                date=current_date,
                recommended_price=price,
                recommended_min_stay=recommended_min_stay,
                base_price=base_price,
                demand_score=demand_score,
                supply_score=Decimal("0.500"),
                seasonal_factor=seasonal_factor,
                event_factor=event_factor,
                weekend_factor=weekend_factor,
                last_minute_factor=last_minute_factor,
                early_bird_factor=early_bird_factor,
                confidence=confidence,
                status="pending",
            )
            db.add(rec)
            results.append(rec)

        current_date += timedelta(days=1)

    db.commit()
    log.info(
        "Price recommendations generated",
        property_id=property_id,
        count=len(results),
        date_range=f"{start_date}–{end_date}",
    )
    return results


def expire_past_recommendations(db: Session) -> int:
    """Mark all past-date pending recommendations as expired.

    Called nightly before new generation to clean up stale entries.
    Returns count of expired records.
    """
    today = date.today()
    count = (
        db.query(PriceRecommendation)
        .filter(
            PriceRecommendation.date < today,
            PriceRecommendation.status == "pending",
        )
        .update({"status": "expired"})
    )
    db.commit()
    return count
