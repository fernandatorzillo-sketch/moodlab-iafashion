import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import get_current_user
from schemas.auth import UserResponse
from services.import_service import ImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/import", tags=["import"])


class ProcessCsvRequest(BaseModel):
    empresa_id: int
    entity_type: str
    field_mapping: Dict[str, str]
    rows: List[Dict[str, Any]]


class ProcessCsvResponse(BaseModel):
    success: int
    errors: List[str]
    closet_synced: int = 0
    stock_deducted: int = 0


class SyncClosetRequest(BaseModel):
    empresa_id: int


class SyncClosetResponse(BaseModel):
    new_entries: int


class CleanupRequest(BaseModel):
    empresa_id: int


class CleanupResponse(BaseModel):
    clientes_removed: int = 0
    clientes_kept: int = 0
    pedidos_linked: int = 0
    itens_fixed: int = 0
    email_populated: int = 0
    duplicates_removed: int = 0
    closet_synced: int = 0
    messages: List[str] = []


class HealthRequest(BaseModel):
    empresa_id: int


class HealthResponse(BaseModel):
    total_clientes: int = 0
    total_produtos: int = 0
    total_pedidos: int = 0
    total_itens_pedido: int = 0
    total_closet: int = 0
    corrupted_clientes: int = 0
    unlinked_pedidos: int = 0
    orphan_itens: int = 0
    health_score: int = 0


@router.post("/process-csv", response_model=ProcessCsvResponse)
async def process_csv(
    data: ProcessCsvRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process CSV data and import into the specified entity table. Auto-syncs closet when importing pedidos."""
    logger.info(f"Processing CSV import: entity={data.entity_type}, empresa={data.empresa_id}, rows={len(data.rows)}")
    try:
        service = ImportService(db)
        result = await service.process_csv_rows(
            empresa_id=data.empresa_id,
            entity_type=data.entity_type,
            field_mapping=data.field_mapping,
            rows=data.rows,
            user_id=str(current_user.id),
            auto_sync_closet=True,
        )
        return result
    except Exception as e:
        logger.error(f"CSV import error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/sync-closet", response_model=SyncClosetResponse)
async def sync_closet(
    data: SyncClosetRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync closet entries from completed orders"""
    logger.info(f"Syncing closet for empresa={data.empresa_id}")
    try:
        service = ImportService(db)
        result = await service.sync_closet(
            empresa_id=data.empresa_id,
            user_id=str(current_user.id),
        )
        return result
    except Exception as e:
        logger.error(f"Closet sync error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/cleanup-data", response_model=CleanupResponse)
async def cleanup_data(
    data: CleanupRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clean up corrupted data: deduplicate clients, fix relationships, populate email_cliente."""
    logger.info(f"Cleaning up data for empresa={data.empresa_id}")
    try:
        service = ImportService(db)
        result = await service.cleanup_data(
            empresa_id=data.empresa_id,
            user_id=str(current_user.id),
        )
        return result
    except Exception as e:
        logger.error(f"Data cleanup error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.post("/data-health", response_model=HealthResponse)
async def data_health(
    data: HealthRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get data health metrics for monitoring."""
    logger.info(f"Getting data health for empresa={data.empresa_id}")
    try:
        service = ImportService(db)
        result = await service.get_data_health(
            empresa_id=data.empresa_id,
            user_id=str(current_user.id),
        )
        return result
    except Exception as e:
        logger.error(f"Data health error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")