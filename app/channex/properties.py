"""Channex.io property service.

Fetches properties from the Channex API and syncs them to the local
``channex_properties`` table, linking each to a local ``Property`` row.

Matching strategy (in order of preference):
  1. Explicit ``channex_property_id`` set in the per-property YAML config.
  2. Case-insensitive display_name match between Channex and local properties.
  3. If neither matches, the ``property_id`` FK is left NULL — operator must
     map it manually by editing config or using the admin UI.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.channex.client import ChannexClient
from app.config import get_config
from app.models.channex_property import ChannexProperty
from app.models.property import Property

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


async def list_properties(client: ChannexClient) -> list[dict]:
    """Fetch all Channex properties the API key has access to.

    Paginates through all pages and returns a flat list of raw Channex
    property dicts (JSON:API ``attributes`` content).
    """
    raw_items = await client.paginate("/properties")
    properties = []
    for item in raw_items:
        if isinstance(item, dict):
            attrs = item.get("attributes", item)
            attrs["id"] = item.get("id", attrs.get("id", ""))
            properties.append(attrs)
    return properties


async def get_property(client: ChannexClient, channex_property_id: str) -> dict:
    """Fetch a single Channex property by its UUID."""
    raw = await client.get(f"/properties/{channex_property_id}")
    if isinstance(raw, dict):
        attrs = raw.get("attributes", raw)
        attrs["id"] = raw.get("id", attrs.get("id", ""))
        return attrs
    return raw


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


async def sync_properties(db: Session, client: ChannexClient) -> dict[str, int]:
    """Pull all Channex properties and upsert into ``channex_properties``.

    Returns a summary dict with counts: ``{"upserted": N, "linked": N, "unlinked": N}``.
    """
    config = get_config()
    channex_props = await list_properties(client)

    # Build lookup maps for the two matching strategies
    # Strategy 1: explicit channex_property_id in per-property YAML
    explicit_map: dict[str, int] = {}  # channex_uuid -> local property_id
    for prop_cfg in config.properties:
        if prop_cfg.channex_property_id:
            local = db.query(Property).filter_by(slug=prop_cfg.slug).first()
            if local:
                explicit_map[prop_cfg.channex_property_id] = local.id

    # Strategy 2: display name (case-insensitive)
    all_local = db.query(Property).all()
    name_map: dict[str, int] = {
        p.display_name.lower().strip(): p.id for p in all_local
    }

    upserted = linked = unlinked = 0

    for cprop in channex_props:
        channex_id = str(cprop.get("id", ""))
        if not channex_id:
            continue

        channex_name = str(cprop.get("title") or cprop.get("name") or "")
        group_id = str(cprop.get("property_group_id") or cprop.get("group_id") or "")

        # Resolve local property_id
        local_id: int | None = explicit_map.get(channex_id)
        if local_id is None:
            local_id = name_map.get(channex_name.lower().strip())

        existing = (
            db.query(ChannexProperty)
            .filter_by(channex_property_id=channex_id)
            .first()
        )
        now = datetime.now(timezone.utc)

        if existing:
            existing.channex_property_name = channex_name
            existing.channex_group_id = group_id or existing.channex_group_id
            existing.synced_at = now
            if local_id is not None:
                existing.property_id = local_id
        else:
            db.add(
                ChannexProperty(
                    channex_property_id=channex_id,
                    channex_property_name=channex_name,
                    channex_group_id=group_id or None,
                    property_id=local_id,
                    synced_at=now,
                )
            )

        upserted += 1
        if local_id is not None:
            linked += 1
        else:
            unlinked += 1
            log.warning(
                "channex_property_unlinked",
                channex_id=channex_id,
                channex_name=channex_name,
                hint="Set channex_property_id in your property YAML or match display_name",
            )

    db.commit()
    log.info(
        "channex_properties_synced",
        upserted=upserted,
        linked=linked,
        unlinked=unlinked,
    )
    return {"upserted": upserted, "linked": linked, "unlinked": unlinked}


def resolve_local_property_id(
    db: Session, channex_property_id: str
) -> int | None:
    """Look up the local property FK for a given Channex property UUID.

    Returns ``None`` if the Channex property hasn't been synced or isn't linked yet.
    """
    row = (
        db.query(ChannexProperty)
        .filter_by(channex_property_id=channex_property_id)
        .first()
    )
    return row.property_id if row else None
