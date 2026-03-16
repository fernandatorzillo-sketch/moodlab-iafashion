import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.recommendation_logs import Recommendation_logsService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/recommendation_logs", tags=["recommendation_logs"])


# ---------- Pydantic Schemas ----------
class Recommendation_logsData(BaseModel):
    """Entity data schema (for create/update)"""
    empresa_id: int
    cliente_id: int = None
    look_id: int = None
    produtos_recomendados: str = None
    ocasiao: str = None
    fonte: str = None
    clicado: bool = None
    aprovado_marca: bool = None
    feedback: str = None
    created_at: Optional[datetime] = None


class Recommendation_logsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    empresa_id: Optional[int] = None
    cliente_id: Optional[int] = None
    look_id: Optional[int] = None
    produtos_recomendados: Optional[str] = None
    ocasiao: Optional[str] = None
    fonte: Optional[str] = None
    clicado: Optional[bool] = None
    aprovado_marca: Optional[bool] = None
    feedback: Optional[str] = None
    created_at: Optional[datetime] = None


class Recommendation_logsResponse(BaseModel):
    """Entity response schema"""
    id: int
    empresa_id: int
    cliente_id: Optional[int] = None
    look_id: Optional[int] = None
    produtos_recomendados: Optional[str] = None
    ocasiao: Optional[str] = None
    fonte: Optional[str] = None
    clicado: Optional[bool] = None
    aprovado_marca: Optional[bool] = None
    feedback: Optional[str] = None
    created_at: Optional[datetime] = None
    user_id: str

    class Config:
        from_attributes = True


class Recommendation_logsListResponse(BaseModel):
    """List response schema"""
    items: List[Recommendation_logsResponse]
    total: int
    skip: int
    limit: int


class Recommendation_logsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Recommendation_logsData]


class Recommendation_logsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Recommendation_logsUpdateData


class Recommendation_logsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Recommendation_logsBatchUpdateItem]


class Recommendation_logsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Recommendation_logsListResponse)
async def query_recommendation_logss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query recommendation_logss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying recommendation_logss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Recommendation_logsService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")
        
        result = await service.get_list(
            skip=skip, 
            limit=limit,
            query_dict=query_dict,
            sort=sort,
            user_id=str(current_user.id),
        )
        logger.debug(f"Found {result['total']} recommendation_logss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying recommendation_logss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Recommendation_logsListResponse)
async def query_recommendation_logss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query recommendation_logss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying recommendation_logss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Recommendation_logsService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")

        result = await service.get_list(
            skip=skip,
            limit=limit,
            query_dict=query_dict,
            sort=sort
        )
        logger.debug(f"Found {result['total']} recommendation_logss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying recommendation_logss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Recommendation_logsResponse)
async def get_recommendation_logs(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single recommendation_logs by ID (user can only see their own records)"""
    logger.debug(f"Fetching recommendation_logs with id: {id}, fields={fields}")
    
    service = Recommendation_logsService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Recommendation_logs with id {id} not found")
            raise HTTPException(status_code=404, detail="Recommendation_logs not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching recommendation_logs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Recommendation_logsResponse, status_code=201)
async def create_recommendation_logs(
    data: Recommendation_logsData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new recommendation_logs"""
    logger.debug(f"Creating new recommendation_logs with data: {data}")
    
    service = Recommendation_logsService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create recommendation_logs")
        
        logger.info(f"Recommendation_logs created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating recommendation_logs: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating recommendation_logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Recommendation_logsResponse], status_code=201)
async def create_recommendation_logss_batch(
    request: Recommendation_logsBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple recommendation_logss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} recommendation_logss")
    
    service = Recommendation_logsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} recommendation_logss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Recommendation_logsResponse])
async def update_recommendation_logss_batch(
    request: Recommendation_logsBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple recommendation_logss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} recommendation_logss")
    
    service = Recommendation_logsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} recommendation_logss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Recommendation_logsResponse)
async def update_recommendation_logs(
    id: int,
    data: Recommendation_logsUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing recommendation_logs (requires ownership)"""
    logger.debug(f"Updating recommendation_logs {id} with data: {data}")

    service = Recommendation_logsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Recommendation_logs with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Recommendation_logs not found")
        
        logger.info(f"Recommendation_logs {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating recommendation_logs {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating recommendation_logs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_recommendation_logss_batch(
    request: Recommendation_logsBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple recommendation_logss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} recommendation_logss")
    
    service = Recommendation_logsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} recommendation_logss successfully")
        return {"message": f"Successfully deleted {deleted_count} recommendation_logss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_recommendation_logs(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single recommendation_logs by ID (requires ownership)"""
    logger.debug(f"Deleting recommendation_logs with id: {id}")
    
    service = Recommendation_logsService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Recommendation_logs with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Recommendation_logs not found")
        
        logger.info(f"Recommendation_logs {id} deleted successfully")
        return {"message": "Recommendation_logs deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting recommendation_logs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")