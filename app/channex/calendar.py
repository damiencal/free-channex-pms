"""Channex.io calendar service — availability and rate management.

Provides read and write access to per-property ARI (Availability, Rates,
and Inventory) data via the Channex API.

Key concepts:
  - Availability is managed per room type (``room_type_id``).
  - Rates are managed per rate plan (``rate_plan_id``).
  - The Channex ARI endpoints accept batch payloads with date ranges.

Rate limiting is handled by the shared ``ChannexClient`` semaphore.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


from app.channex.client import ChannexClient


# ---------------------------------------------------------------------------
# Request schemas (dataclasses used — no Pydantic dependency here)
# ---------------------------------------------------------------------------


@dataclass
class AvailabilityUpdate:
    """A single availability update for a room type over a date range."""

    room_type_id: str
    date_from: date
    date_to: date
    availability: int | None = None
    """Number of available units. None = no change."""
    min_stay_arrival: int | None = None
    """Minimum stay (nights) — applies on arrival date."""
    max_stay: int | None = None
    """Maximum stay (nights)."""
    closed_to_arrival: bool | None = None
    """Block arrivals on these dates."""
    closed_to_departure: bool | None = None
    """Block departures on these dates."""
    stop_sell: bool | None = None
    """Stop selling (close availability entirely)."""


@dataclass
class RateUpdate:
    """A single rate update for a rate plan over a date range."""

    rate_plan_id: str
    date_from: date
    date_to: date
    rate: float | None = None
    """Nightly rate in the property currency. None = no change."""


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


async def get_availability(
    client: ChannexClient,
    channex_property_id: str,
    date_from: date,
    date_to: date,
) -> dict:
    """Fetch availability for all room types of a Channex property.

    Returns the raw Channex response dict which contains per-room-type
    availability indexed by date string ('YYYY-MM-DD').
    """
    return await client.get(
        "/availability",
        params={
            "property_id": channex_property_id,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
    )


async def update_availability(
    client: ChannexClient,
    updates: list[AvailabilityUpdate],
) -> dict:
    """Push availability updates to Channex.

    Accepts a list of ``AvailabilityUpdate`` items; builds the Channex
    ``PUT /availability`` batch payload.

    Returns the raw Channex API response.
    """
    values = []
    for u in updates:
        entry: dict = {
            "room_type_id": u.room_type_id,
            "date_from": u.date_from.isoformat(),
            "date_to": u.date_to.isoformat(),
        }
        if u.availability is not None:
            entry["availability"] = u.availability
        if u.min_stay_arrival is not None:
            entry["min_stay_arrival"] = u.min_stay_arrival
        if u.max_stay is not None:
            entry["max_stay"] = u.max_stay
        if u.closed_to_arrival is not None:
            entry["closed_to_arrival"] = u.closed_to_arrival
        if u.closed_to_departure is not None:
            entry["closed_to_departure"] = u.closed_to_departure
        if u.stop_sell is not None:
            entry["stop_sell"] = u.stop_sell
        values.append(entry)

    return await client.put("/availability", json={"values": values})


# ---------------------------------------------------------------------------
# Rate plans
# ---------------------------------------------------------------------------


async def get_rate_plans(
    client: ChannexClient,
    channex_property_id: str,
) -> list[dict]:
    """List all rate plans for a Channex property."""
    raw = await client.paginate(
        "/rate_plans",
        params={"property_id": channex_property_id},
    )
    plans = []
    for item in raw:
        if isinstance(item, dict):
            attrs = item.get("attributes", item)
            attrs["id"] = item.get("id", attrs.get("id", ""))
            plans.append(attrs)
    return plans


async def get_rates(
    client: ChannexClient,
    channex_property_id: str,
    date_from: date,
    date_to: date,
) -> dict:
    """Fetch rates for all rate plans of a Channex property over a date range.

    Returns the raw Channex response dict indexed by rate_plan_id → date.
    """
    return await client.get(
        "/rates",
        params={
            "property_id": channex_property_id,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
    )


async def update_rates(
    client: ChannexClient,
    updates: list[RateUpdate],
) -> dict:
    """Push rate updates to Channex.

    Accepts a list of ``RateUpdate`` items; builds the Channex
    ``PUT /rates`` batch payload.

    Returns the raw Channex API response.
    """
    values = []
    for u in updates:
        if u.rate is None:
            continue
        values.append({
            "rate_plan_id": u.rate_plan_id,
            "date_from": u.date_from.isoformat(),
            "date_to": u.date_to.isoformat(),
            "rate": u.rate,
        })

    return await client.put("/rates", json={"values": values})


# ---------------------------------------------------------------------------
# Room types
# ---------------------------------------------------------------------------


async def get_room_types(
    client: ChannexClient,
    channex_property_id: str,
) -> list[dict]:
    """List all room types for a Channex property."""
    raw = await client.paginate(
        "/room_types",
        params={"property_id": channex_property_id},
    )
    room_types = []
    for item in raw:
        if isinstance(item, dict):
            attrs = item.get("attributes", item)
            attrs["id"] = item.get("id", attrs.get("id", ""))
            room_types.append(attrs)
    return room_types
