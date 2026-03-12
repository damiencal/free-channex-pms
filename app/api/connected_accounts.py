"""
Connected Accounts API
=======================
CRUD endpoints for Channex API token connections stored in the
``channex_connections`` database table.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import text

from app.auth import require_auth
from app.db import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mask_token(token: str) -> str:
    """Return "****<last-4>" to avoid exposing the full token."""
    if len(token) <= 4:
        return "****"
    return "****" + token[-4:]


def _row_to_account(row: dict) -> dict:
    return {
        "id": row["id"],
        "channel": "channex",
        "account_name": row["name"],
        "status": row["status"],
        "listing_count": row["listing_count"],
        "api_token_hint": _mask_token(row["api_token"]),
        "last_synced_at": row["last_synced_at"].isoformat()
        if row.get("last_synced_at")
        else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
    }


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CreateConnectionRequest(BaseModel):
    name: str
    api_token: str


# ---------------------------------------------------------------------------
# Endpoints: /api/connected-accounts
# ---------------------------------------------------------------------------


@router.get("/api/connected-accounts")
async def list_connected_accounts(
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    rows = (
        db.execute(text("SELECT * FROM channex_connections ORDER BY created_at DESC"))
        .mappings()
        .all()
    )
    return [_row_to_account(dict(r)) for r in rows]


@router.post("/api/connected-accounts", status_code=201)
async def create_connected_account(
    payload: CreateConnectionRequest,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    name = payload.name.strip()
    token = payload.api_token.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if not token:
        raise HTTPException(status_code=422, detail="API token is required")

    # Test the token with the Channex API before saving
    try:
        from app.channex.client import ChannexClient

        async with ChannexClient(api_key=token) as client:
            result = await client.get("/properties", params={"pagination[limit]": 1})
        listing_count = len(result.get("data", []))
        status = "active"
    except Exception:
        # Store the connection even if the test fails, but mark as error
        listing_count = 0
        status = "error"

    row = (
        db.execute(
            text("""
            INSERT INTO channex_connections (name, api_token, status, listing_count)
            VALUES (:name, :token, :status, :listing_count)
            RETURNING *
        """),
            {
                "name": name,
                "token": token,
                "status": status,
                "listing_count": listing_count,
            },
        )
        .mappings()
        .fetchone()
    )
    db.commit()
    return _row_to_account(dict(row))


@router.delete("/api/connected-accounts/{connection_id}", status_code=204)
async def delete_connected_account(
    connection_id: int,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    result = db.execute(
        text("DELETE FROM channex_connections WHERE id = :id RETURNING id"),
        {"id": connection_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Connection not found")
    return Response(status_code=204)


@router.post("/api/connected-accounts/{connection_id}/test")
async def test_connected_account(
    connection_id: int,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    row = (
        db.execute(
            text("SELECT * FROM channex_connections WHERE id = :id"),
            {"id": connection_id},
        )
        .mappings()
        .fetchone()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")

    token = row["api_token"]
    try:
        from app.channex.client import ChannexClient

        async with ChannexClient(api_key=token) as client:
            result = await client.get("/properties", params={"pagination[limit]": 1})
        listing_count = len(result.get("data", []))
        new_status = "active"
        message = "Connection is working."
    except Exception as exc:
        listing_count = 0
        new_status = "error"
        message = f"Connection failed: {exc}"

    db.execute(
        text("""
            UPDATE channex_connections
            SET status = :status, listing_count = :count, updated_at = NOW()
            WHERE id = :id
        """),
        {"status": new_status, "count": listing_count, "id": connection_id},
    )
    db.commit()
    return {"status": new_status, "message": message, "listing_count": listing_count}


@router.post("/api/connected-accounts/{connection_id}/sync")
async def sync_connected_account(
    connection_id: int,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    row = (
        db.execute(
            text("SELECT * FROM channex_connections WHERE id = :id"),
            {"id": connection_id},
        )
        .mappings()
        .fetchone()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")

    token = row["api_token"]
    try:
        from app.channex.client import ChannexClient

        async with ChannexClient(api_key=token) as client:
            result = await client.get("/properties", params={"pagination[limit]": 100})
        properties = result.get("data", [])
        synced = len(properties)

        # Upsert properties into channex_properties table
        for prop in properties:
            attrs = prop.get("attributes", {})
            channex_id = prop.get("id")
            if not channex_id:
                continue
            db.execute(
                text("""
                    INSERT INTO channex_properties
                        (channex_id, title, currency, timezone, is_active)
                    VALUES (:channex_id, :title, :currency, :timezone, true)
                    ON CONFLICT (channex_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        currency = EXCLUDED.currency,
                        timezone = EXCLUDED.timezone,
                        is_active = true
                """),
                {
                    "channex_id": channex_id,
                    "title": attrs.get("title", ""),
                    "currency": attrs.get("currency", "USD"),
                    "timezone": attrs.get("timezone", "UTC"),
                },
            )

        db.execute(
            text("""
                UPDATE channex_connections
                SET status = 'active', listing_count = :count,
                    last_synced_at = NOW(), updated_at = NOW()
                WHERE id = :id
            """),
            {"count": synced, "id": connection_id},
        )
        db.commit()
        return {"synced": synced, "status": "active"}
    except Exception as exc:
        db.execute(
            text(
                "UPDATE channex_connections SET status='error', updated_at=NOW() WHERE id=:id"
            ),
            {"id": connection_id},
        )
        db.commit()
        raise HTTPException(status_code=502, detail=f"Sync failed: {exc}")


# ---------------------------------------------------------------------------
# Endpoints: /api/linked-listings
# ---------------------------------------------------------------------------


@router.get("/api/linked-listings")
async def list_linked_listings(
    property_id: int | None = None,
    db=Depends(get_db),
    _user=Depends(require_auth),
):
    if property_id:
        rows = (
            db.execute(
                text("""
                SELECT cp.id, cp.property_id, 0 AS account_id,
                       'channex' AS channel, cp.channex_property_name AS listing_name,
                       NULL AS rate_plan, 1 AS inventory,
                       (cp.property_id IS NOT NULL) AS is_linked
                FROM channex_properties cp
                WHERE cp.property_id = :pid
            """),
                {"pid": property_id},
            )
            .mappings()
            .all()
        )
    else:
        rows = (
            db.execute(
                text("""
                SELECT cp.id, cp.property_id,
                       0 AS account_id,
                       'channex' AS channel, cp.channex_property_name AS listing_name,
                       NULL AS rate_plan, 1 AS inventory,
                       (cp.property_id IS NOT NULL) AS is_linked
                FROM channex_properties cp
                ORDER BY cp.channex_property_name
            """),
            )
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]
