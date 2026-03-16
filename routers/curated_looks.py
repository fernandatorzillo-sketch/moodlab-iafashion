import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.curated_looks import Curated_looksService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/curated_looks", tags=["curated_looks"])


# ---------- Pydantic Schemas ----------
class Curated_looksData(BaseModel):
    """Entity data schema (for create/update)"""
    empresa_id: int
    nome: str
    ocasiao: str = None
    estilo: str = None
    descricao_editorial: str = None
    observacoes_marca: str = None
    tags: str = None
    prioridade: int = None
    ativo: bool = None
    tipo: str = None
    created_at: Optional[datetime] = None


class Curated_looksUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    empresa_id: Optional[int] = None
    nome: Optional[str] = None
    ocasiao: Optional[str] = None
    estilo: Optional[str] = None
    descricao_editorial: Optional[str] = None
    observacoes_marca: Optional[str] = None
    tags: Optional[str] = None
    prioridade: Optional[int] = None
    ativo: Optional[bool] = None
    tipo: Optional[str] = None
    created_at: Optional[datetime] = None


class Curated_looksResponse(BaseModel):
    """Entity response schema"""
    id: int
    empresa_id: int
    nome: str
    ocasiao: Optional[str] = None
    estilo: Optional[str] = None
    descricao_editorial: Optional[str] = None
    observacoes_marca: Optional[str] = None
    tags: Optional[str] = None
    prioridade: Optional[int] = None
    ativo: Optional[bool] = None
    tipo: Optional[str] = None
    created_at: Optional[datetime] = None
    user_id: str

    class Config:
        from_attributes = True


class Curated_looksListResponse(BaseModel):
    """List response schema"""
    items: List[Curated_looksResponse]
    total: int
    skip: int
    limit: int


class Curated_looksBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Curated_looksData]


class Curated_looksBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Curated_looksUpdateData


class Curated_looksBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Curated_looksBatchUpdateItem]


class Curated_looksBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Curated_looksListResponse)
async def query_curated_lookss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query curated_lookss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying curated_lookss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Curated_looksService(db)
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
        logger.debug(f"Found {result['total']} curated_lookss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying curated_lookss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Curated_looksListResponse)
async def query_curated_lookss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query curated_lookss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying curated_lookss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Curated_looksService(db)
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
        logger.debug(f"Found {result['total']} curated_lookss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying curated_lookss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Curated_looksResponse)
async def get_curated_looks(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single curated_looks by ID (user can only see their own records)"""
    logger.debug(f"Fetching curated_looks with id: {id}, fields={fields}")
    
    service = Curated_looksService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Curated_looks with id {id} not found")
            raise HTTPException(status_code=404, detail="Curated_looks not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching curated_looks {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Curated_looksResponse, status_code=201)
async def create_curated_looks(
    data: Curated_looksData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new curated_looks"""
    logger.debug(f"Creating new curated_looks with data: {data}")
    
    service = Curated_looksService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create curated_looks")
        
        logger.info(f"Curated_looks created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating curated_looks: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating curated_looks: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Curated_looksResponse], status_code=201)
async def create_curated_lookss_batch(
    request: Curated_looksBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple curated_lookss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} curated_lookss")
    
    service = Curated_looksService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} curated_lookss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Curated_looksResponse])
async def update_curated_lookss_batch(
    request: Curated_looksBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple curated_lookss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} curated_lookss")
    
    service = Curated_looksService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} curated_lookss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Curated_looksResponse)
async def update_curated_looks(
    id: int,
    data: Curated_looksUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing curated_looks (requires ownership)"""
    logger.debug(f"Updating curated_looks {id} with data: {data}")

    service = Curated_looksService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Curated_looks with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Curated_looks not found")
        
        logger.info(f"Curated_looks {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating curated_looks {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating curated_looks {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_curated_lookss_batch(
    request: Curated_looksBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple curated_lookss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} curated_lookss")
    
    service = Curated_looksService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} curated_lookss successfully")
        return {"message": f"Successfully deleted {deleted_count} curated_lookss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_curated_looks(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single curated_looks by ID (requires ownership)"""
    logger.debug(f"Deleting curated_looks with id: {id}")
    
    service = Curated_looksService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Curated_looks with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Curated_looks not found")
        
        logger.info(f"Curated_looks {id} deleted successfully")
        return {"message": "Curated_looks deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting curated_looks {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")