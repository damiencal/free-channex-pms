"""Channex.io reviews service.

Fetches guest reviews from Channex and syncs them to the local
``channex_reviews`` table. Also provides a function for submitting
host responses back to Channex.

After ``respond_to_review`` succeeds, the local record is updated:
  - ``status`` set to ``"responded"``
  - ``response_text`` populated
  - ``responded_at`` stamped
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.channex.client import ChannexClient
from app.models.channex_review import ChannexReview

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


async def list_reviews(
    client: ChannexClient,
    since: datetime | None = None,
    channex_property_id: str | None = None,
) -> list[dict]:
    """Fetch reviews from Channex, optionally filtered by time or property.

    Returns a flat list of review dicts with all attributes merged.
    """
    params: dict = {}
    if since:
        params["inserted_at[gte]"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    if channex_property_id:
        params["property_id"] = channex_property_id

    raw_items = await client.paginate("/reviews", params=params)
    reviews = []
    for item in raw_items:
        if isinstance(item, dict):
            attrs = item.get("attributes", item)
            attrs["id"] = item.get("id", attrs.get("id", ""))
            reviews.append(attrs)
    return reviews


async def respond_to_review(
    client: ChannexClient,
    db: Session,
    channex_review_id: str,
    response_text: str,
) -> dict:
    """Submit a host response to a Channex review.

    Calls the Channex API, then updates the local ``channex_reviews`` row.

    Returns the API response dict.
    """
    result = await client.post(
        f"/reviews/{channex_review_id}/responses",
        json={"review_response": {"response": response_text}},
    )

    # Update local record
    now = datetime.now(timezone.utc)
    row = (
        db.query(ChannexReview)
        .filter_by(channex_review_id=channex_review_id)
        .first()
    )
    if row:
        row.status = "responded"
        row.response_text = response_text
        row.responded_at = now
        db.commit()

    log.info("channex_review_responded", review_id=channex_review_id)
    return result


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def sync_reviews_to_db(
    db: Session,
    reviews: list[dict],
    local_booking_map: dict[str, int] | None = None,
    local_property_map: dict[str, int | None] | None = None,
) -> dict[str, int]:
    """Upsert a list of Channex reviews into ``channex_reviews``.

    Does NOT overwrite ``status``, ``response_text``, or ``responded_at``
    if the local record is already ``status='responded'``, to prevent losing
    operator-submitted responses during re-sync.

    Args:
        db: SQLAlchemy session.
        reviews: List of Channex review dicts.
        local_booking_map: Optional ``{channex_booking_id: local_booking.id}`` map.
        local_property_map: Optional ``{channex_booking_id: property_id}`` map.

    Returns:
        ``{"upserted": N, "skipped": N}``.
    """
    upserted = skipped = 0

    for rev in reviews:
        rev_id = str(rev.get("id") or rev.get("review_id") or "")
        if not rev_id:
            skipped += 1
            continue

        channex_booking_id = str(rev.get("booking_id") or rev.get("reservation_id") or "")
        guest_name = str(rev.get("reviewer_name") or rev.get("guest_name") or "")
        rating_raw = rev.get("rating") or rev.get("overall_rating")
        try:
            rating: int | None = int(rating_raw) if rating_raw is not None else None
        except (ValueError, TypeError):
            rating = None

        review_text = str(rev.get("body") or rev.get("review") or rev.get("text") or "")

        reviewed_at_raw = rev.get("reviewed_at") or rev.get("inserted_at") or rev.get("created_at")
        reviewed_at: datetime | None = None
        if reviewed_at_raw:
            try:
                reviewed_at = datetime.fromisoformat(
                    str(reviewed_at_raw).replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Check if already responded — don't overwrite response on re-sync
        existing = (
            db.query(ChannexReview).filter_by(channex_review_id=rev_id).first()
        )
        already_responded = existing and existing.status == "responded"

        local_booking_id: int | None = None
        local_property_id: int | None = None
        if local_booking_map and channex_booking_id:
            local_booking_id = local_booking_map.get(channex_booking_id)
        if local_property_map and channex_booking_id:
            local_property_id = local_property_map.get(channex_booking_id)

        if already_responded:
            # Only update non-response fields
            if existing:
                existing.guest_name = guest_name
                existing.rating = rating
                existing.review_text = review_text
                existing.reviewed_at = reviewed_at
                if local_booking_id:
                    existing.booking_id = local_booking_id
                if local_property_id:
                    existing.property_id = local_property_id
            upserted += 1
            continue

        stmt = (
            pg_insert(ChannexReview)
            .values(
                channex_review_id=rev_id,
                channex_booking_id=channex_booking_id or None,
                booking_id=local_booking_id,
                property_id=local_property_id,
                guest_name=guest_name,
                rating=rating,
                review_text=review_text,
                status="new",
                response_text=None,
                reviewed_at=reviewed_at,
                responded_at=None,
            )
            .on_conflict_do_update(
                index_elements=["channex_review_id"],
                set_={
                    "guest_name": guest_name,
                    "rating": rating,
                    "review_text": review_text,
                    "reviewed_at": reviewed_at,
                    "booking_id": local_booking_id,
                    "property_id": local_property_id,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        )
        try:
            db.execute(stmt)
            upserted += 1
        except Exception as exc:
            log.warning("channex_review_sync_failed", rev_id=rev_id, error=str(exc))
            skipped += 1

    db.commit()
    log.info("channex_reviews_synced", upserted=upserted, skipped=skipped)
    return {"upserted": upserted, "skipped": skipped}


async def sync_all_reviews(
    db: Session,
    client: ChannexClient,
    since: datetime | None = None,
) -> dict[str, int]:
    """Pull all reviews from Channex and sync to DB."""
    reviews = await list_reviews(client, since=since)
    return sync_reviews_to_db(db, reviews)
