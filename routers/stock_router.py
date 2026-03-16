"""Stock management endpoints — deduct inventory on purchase events."""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import get_current_user
from schemas.auth import UserResponse
from services.stock_service import StockService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])


class DeductStockRequest(BaseModel):
    empresa_id: int
    sku: str
    quantidade: int = 1


class ProcessOrderRequest(BaseModel):
    empresa_id: int
    pedido_id: int


class ProcessAllOrdersRequest(BaseModel):
    empresa_id: int


@router.post("/deduct")
async def deduct_stock(
    data: DeductStockRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually deduct stock for a product by SKU."""
    try:
        service = StockService(db)
        result = await service.deduct_stock(
            empresa_id=data.empresa_id,
            user_id=str(current_user.id),
            sku=data.sku,
            quantidade=data.quantidade,
        )
        await db.commit()
        return result
    except Exception as e:
        logger.error(f"Stock deduction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-order")
async def process_order_stock(
    data: ProcessOrderRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process stock deduction for all items in a specific order."""
    try:
        service = StockService(db)
        return await service.process_order_stock(
            empresa_id=data.empresa_id,
            user_id=str(current_user.id),
            pedido_id=data.pedido_id,
        )
    except Exception as e:
        logger.error(f"Order stock processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-all-orders")
async def process_all_orders(
    data: ProcessAllOrdersRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process stock deduction for all orders with purchase status."""
    try:
        service = StockService(db)
        return await service.process_orders_by_status(
            empresa_id=data.empresa_id,
            user_id=str(current_user.id),
        )
    except Exception as e:
        logger.error(f"Bulk order stock processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_stock_summary(
    empresa_id: int = Query(...),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get stock summary with out-of-stock and low-stock alerts."""
    try:
        service = StockService(db)
        return await service.get_stock_summary(
            empresa_id=empresa_id,
            user_id=str(current_user.id),
        )
    except Exception as e:
        logger.error(f"Stock summary error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))