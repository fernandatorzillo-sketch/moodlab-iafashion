import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.customer_closet_service import CustomerClosetService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/customer-closet", tags=["customer-closet"])


class EmailLookupRequest(BaseModel):
    email: str


class RecommendationRequest(BaseModel):
    email: str
    ocasiao: Optional[str] = None
    limit: int = 6


@router.post("/lookup")
async def lookup_customer(
    data: EmailLookupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: look up customer by email and return closet data."""
    try:
        service = CustomerClosetService(db)
        result = await service.lookup_by_email(data.email)
        return result
    except Exception as e:
        logger.error(f"Customer lookup error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations")
async def get_customer_recommendations(
    data: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: get AI recommendations for a customer by email."""
    try:
        service = CustomerClosetService(db)
        result = await service.get_recommendations_for_customer(
            email=data.email,
            ocasiao=data.ocasiao,
            limit=data.limit,
        )
        if result.get("error"):
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))