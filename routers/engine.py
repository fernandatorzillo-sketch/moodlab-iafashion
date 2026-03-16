import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import get_current_user
from schemas.auth import UserResponse
from services.engine_service import EngineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/engine", tags=["engine"])


# --- Request/Response Models ---

class SearchResponse(BaseModel):
    items: list
    total: int
    skip: int
    limit: int


class RecommendationRequest(BaseModel):
    empresa_id: int
    cliente_id: Optional[int] = None
    ocasiao: Optional[str] = None
    limit: int = 5


class OutfitRequest(BaseModel):
    empresa_id: int
    cliente_id: Optional[int] = None
    ocasiao: str = "casual"


class ClosetRequest(BaseModel):
    empresa_id: int
    cliente_id: int


class ApproveRecommendationRequest(BaseModel):
    log_id: int
    aprovado: bool
    feedback: Optional[str] = None


# --- Endpoints ---

@router.get("/search", response_model=SearchResponse)
async def search_products(
    empresa_id: int = Query(...),
    query: str = Query(""),
    categoria: str = Query(""),
    ocasiao: str = Query(""),
    tags: str = Query(""),
    limit: int = Query(20),
    skip: int = Query(0),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search products by text, category, occasion, tags"""
    try:
        service = EngineService(db)
        return await service.search_products(
            empresa_id=empresa_id,
            user_id=str(current_user.id),
            query=query,
            categoria=categoria,
            ocasiao=ocasiao,
            tags=tags,
            limit=limit,
            skip=skip,
        )
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations")
async def get_recommendations(
    data: RecommendationRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-powered hybrid recommendations"""
    try:
        service = EngineService(db)
        return await service.generate_recommendations(
            empresa_id=data.empresa_id,
            user_id=str(current_user.id),
            cliente_id=data.cliente_id,
            ocasiao=data.ocasiao,
            limit=data.limit,
        )
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outfits")
async def generate_outfit(
    data: OutfitRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a complete outfit from closet + catalog"""
    try:
        service = EngineService(db)
        return await service.generate_outfit(
            empresa_id=data.empresa_id,
            user_id=str(current_user.id),
            cliente_id=data.cliente_id,
            ocasiao=data.ocasiao,
        )
    except Exception as e:
        logger.error(f"Outfit generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/customer-closet")
async def get_customer_closet(
    data: ClosetRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get customer closet with full product details"""
    try:
        service = EngineService(db)
        return await service.get_customer_closet(
            empresa_id=data.empresa_id,
            cliente_id=data.cliente_id,
            user_id=str(current_user.id),
        )
    except Exception as e:
        logger.error(f"Closet error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics")
async def get_analytics(
    empresa_id: int = Query(...),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recommendation analytics for AI learning dashboard"""
    try:
        service = EngineService(db)
        return await service.get_recommendation_analytics(
            empresa_id=empresa_id,
            user_id=str(current_user.id),
        )
    except Exception as e:
        logger.error(f"Analytics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve-recommendation")
async def approve_recommendation(
    data: ApproveRecommendationRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a recommendation (brand feedback)"""
    from sqlalchemy import select as sa_select
    from models.recommendation_logs import Recommendation_logs
    try:
        stmt = sa_select(Recommendation_logs).where(
            Recommendation_logs.id == data.log_id,
            Recommendation_logs.user_id == str(current_user.id),
        )
        result = await db.execute(stmt)
        log = result.scalar_one_or_none()
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        log.aprovado_marca = data.aprovado
        if data.feedback:
            log.feedback = data.feedback
        await db.commit()
        return {"status": "ok", "aprovado": data.aprovado}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approve error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))