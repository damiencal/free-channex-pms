"""Booking Sites CRUD API."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from app.auth import require_auth
from app.db import get_db

router = APIRouter(prefix="/api/booking-sites", tags=["booking-sites"])


class BookingSitePayload(BaseModel):
    name: str
    type: str = "hosted"
    domain: Optional[str] = None
    custom_domain: Optional[str] = None
    hero_title: Optional[str] = None
    hero_subtitle: Optional[str] = None
    site_logo_url: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None


class ListingUpdatePayload(BaseModel):
    is_visible: Optional[bool] = None
    sort_order: Optional[int] = None


def _row_to_dict(row) -> dict:
    return dict(row._mapping)


@router.get("")
def list_booking_sites(
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    rows = db.execute(
        text("SELECT * FROM booking_sites ORDER BY created_at DESC")
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.post("", status_code=201)
def create_booking_site(
    payload: BookingSitePayload,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    row = db.execute(
        text("""
            INSERT INTO booking_sites (name, type, domain, custom_domain, hero_title,
                hero_subtitle, site_logo_url, contact_phone, contact_email,
                seo_title, seo_description, seo_keywords)
            VALUES (:name, :type, :domain, :custom_domain, :hero_title,
                :hero_subtitle, :site_logo_url, :contact_phone, :contact_email,
                :seo_title, :seo_description, :seo_keywords)
            RETURNING *
        """),
        payload.model_dump(),
    ).fetchone()
    db.commit()
    return _row_to_dict(row)


@router.get("/{site_id}")
def get_booking_site(
    site_id: int,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    row = db.execute(
        text("SELECT * FROM booking_sites WHERE id = :id"), {"id": site_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking site not found")
    return _row_to_dict(row)


@router.put("/{site_id}")
def update_booking_site(
    site_id: int,
    payload: BookingSitePayload,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    data = payload.model_dump()
    data["id"] = site_id
    row = db.execute(
        text("""
            UPDATE booking_sites SET name=:name, type=:type, domain=:domain,
                custom_domain=:custom_domain, hero_title=:hero_title,
                hero_subtitle=:hero_subtitle, site_logo_url=:site_logo_url,
                contact_phone=:contact_phone, contact_email=:contact_email,
                seo_title=:seo_title, seo_description=:seo_description,
                seo_keywords=:seo_keywords, updated_at=now()
            WHERE id=:id RETURNING *
        """),
        data,
    ).fetchone()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Booking site not found")
    return _row_to_dict(row)


@router.post("/{site_id}/publish")
def publish_booking_site(
    site_id: int,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    row = db.execute(
        text(
            "UPDATE booking_sites SET is_published=true, updated_at=now() WHERE id=:id RETURNING *"
        ),
        {"id": site_id},
    ).fetchone()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Booking site not found")
    return _row_to_dict(row)


@router.post("/{site_id}/unpublish")
def unpublish_booking_site(
    site_id: int,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    row = db.execute(
        text(
            "UPDATE booking_sites SET is_published=false, updated_at=now() WHERE id=:id RETURNING *"
        ),
        {"id": site_id},
    ).fetchone()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Booking site not found")
    return _row_to_dict(row)


@router.delete("/{site_id}", status_code=204)
def delete_booking_site(
    site_id: int,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    db.execute(text("DELETE FROM booking_sites WHERE id=:id"), {"id": site_id})
    db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sync_listing_count(db, site_id: int) -> None:
    """Update the denormalized listing_count on booking_sites."""
    db.execute(
        text("""
            UPDATE booking_sites
            SET listing_count = (
                SELECT COUNT(*) FROM booking_site_listings WHERE site_id = :site_id
            )
            WHERE id = :site_id
        """),
        {"site_id": site_id},
    )


def _seed_listings_from_channex(db, site_id: int) -> None:
    """Auto-create listings for all properties that have a Channex mapping."""
    db.execute(
        text("""
            INSERT INTO booking_site_listings (site_id, property_id, sort_order, is_visible)
            SELECT :site_id, p.id, ROW_NUMBER() OVER (ORDER BY p.display_name) - 1, true
            FROM properties p
            INNER JOIN channex_properties cp ON cp.property_id = p.id
            WHERE p.is_active = true
            ON CONFLICT (site_id, property_id) DO NOTHING
        """),
        {"site_id": site_id},
    )
    _sync_listing_count(db, site_id)


# ---------------------------------------------------------------------------
# Listings sub-resource
# ---------------------------------------------------------------------------

@router.get("/{site_id}/listings")
def list_site_listings(
    site_id: int,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    """Return listings for a booking site, auto-seeding from Channex properties if none exist."""
    # Verify site exists
    site = db.execute(
        text("SELECT id FROM booking_sites WHERE id = :id"), {"id": site_id}
    ).fetchone()
    if not site:
        raise HTTPException(status_code=404, detail="Booking site not found")

    # Check for existing listings
    existing = db.execute(
        text("SELECT COUNT(*) FROM booking_site_listings WHERE site_id = :site_id"),
        {"site_id": site_id},
    ).scalar()

    if existing == 0:
        # Auto-seed from Channex-linked properties
        _seed_listings_from_channex(db, site_id)
        db.commit()

    rows = db.execute(
        text("""
            SELECT bsl.id, bsl.site_id, bsl.property_id, bsl.sort_order, bsl.is_visible,
                   p.display_name, p.slug, p.bedrooms, p.bathrooms, p.max_guests,
                   p.property_type, p.address, p.city, p.country
            FROM booking_site_listings bsl
            JOIN properties p ON p.id = bsl.property_id
            WHERE bsl.site_id = :site_id
            ORDER BY bsl.sort_order, p.display_name
        """),
        {"site_id": site_id},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


@router.patch("/{site_id}/listings/{listing_id}")
def update_site_listing(
    site_id: int,
    listing_id: int,
    payload: ListingUpdatePayload,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    """Update visibility or sort order of a listing."""
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = ", ".join(f"{k}=:{k}" for k in updates)
    updates["listing_id"] = listing_id
    updates["site_id"] = site_id

    row = db.execute(
        text(f"UPDATE booking_site_listings SET {set_clauses} WHERE id=:listing_id AND site_id=:site_id RETURNING *"),
        updates,
    ).fetchone()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found")
    return dict(row._mapping)


@router.delete("/{site_id}/listings/{listing_id}", status_code=204)
def delete_site_listing(
    site_id: int,
    listing_id: int,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    """Remove a property from a booking site."""
    db.execute(
        text("DELETE FROM booking_site_listings WHERE id=:id AND site_id=:site_id"),
        {"id": listing_id, "site_id": site_id},
    )
    _sync_listing_count(db, site_id)
    db.commit()

