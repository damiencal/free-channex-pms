"""Revenue Estimator API — project monthly/annual income for unlisted properties.

This is a "what-if" tool that uses internal comparable data to estimate
potential revenue for a new listing or an address under consideration.

Endpoint:
  POST /api/estimator/analyze
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db

router = APIRouter(prefix="/api/estimator", tags=["estimator"])


class EstimatorRequest(BaseModel):
    bedrooms: int
    property_type: str = "house"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    amenities: list[str] = []
    months_ahead: int = 12

    @field_validator("bedrooms")
    @classmethod
    def bedrooms_range(cls, v: int) -> int:
        if not 0 <= v <= 20:
            raise ValueError("bedrooms must be between 0 and 20")
        return v

    @field_validator("months_ahead")
    @classmethod
    def months_range(cls, v: int) -> int:
        if not 1 <= v <= 24:
            raise ValueError("months_ahead must be between 1 and 24")
        return v


@router.post("/analyze")
async def estimate_revenue(
    payload: EstimatorRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_auth),
) -> dict:
    """Estimate potential revenue for a new or hypothetical listing.

    Uses internal comparable properties to project ADR, occupancy, and revenue.
    Confidence level is based on the number of comparable data points available.
    """
    from app.pricing.estimator import estimate_revenue as _estimate

    result = _estimate(
        db=db,
        bedrooms=payload.bedrooms,
        property_type=payload.property_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        amenities=payload.amenities,
        months_ahead=payload.months_ahead,
    )
    return result
