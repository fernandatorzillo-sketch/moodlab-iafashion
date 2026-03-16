import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.closet_cliente import Closet_clienteService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/closet_cliente", tags=["closet_cliente"])


# ---------- Pydantic Schemas ----------
class Closet_clienteData(BaseModel):
    """Entity data schema (for create/update)"""
    empresa_id: int
    cliente_id: int
    produto_id: int
    origem: str = None
    data_entrada: Optional[datetime] = None


class Closet_clienteUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    empresa_id: Optional[int] = None
    cliente_id: Optional[int] = None
    produto_id: Optional[int] = None
    origem: Optional[str] = None
    data_entrada: Optional[datetime] = None


class Closet_clienteResponse(BaseModel):
    """Entity response schema"""
    id: int
    empresa_id: int
    cliente_id: int
    produto_id: int
    origem: Optional[str] = None
    data_entrada: Optional[datetime] = None
    user_id: str

    class Config:
        from_attributes = True


class Closet_clienteListResponse(BaseModel):
    """List response schema"""
    items: List[Closet_clienteResponse]
    total: int
    skip: int
    limit: int


class Closet_clienteBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Closet_clienteData]


class Closet_clienteBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Closet_clienteUpdateData


class Closet_clienteBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Closet_clienteBatchUpdateItem]


class Closet_clienteBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Closet_clienteListResponse)
async def query_closet_clientes(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query closet_clientes with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying closet_clientes: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Closet_clienteService(db)
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
        logger.debug(f"Found {result['total']} closet_clientes")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying closet_clientes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Closet_clienteListResponse)
async def query_closet_clientes_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query closet_clientes with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying closet_clientes: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Closet_clienteService(db)
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
        logger.debug(f"Found {result['total']} closet_clientes")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying closet_clientes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Closet_clienteResponse)
async def get_closet_cliente(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single closet_cliente by ID (user can only see their own records)"""
    logger.debug(f"Fetching closet_cliente with id: {id}, fields={fields}")
    
    service = Closet_clienteService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Closet_cliente with id {id} not found")
            raise HTTPException(status_code=404, detail="Closet_cliente not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching closet_cliente {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Closet_clienteResponse, status_code=201)
async def create_closet_cliente(
    data: Closet_clienteData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new closet_cliente"""
    logger.debug(f"Creating new closet_cliente with data: {data}")
    
    service = Closet_clienteService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create closet_cliente")
        
        logger.info(f"Closet_cliente created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating closet_cliente: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating closet_cliente: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Closet_clienteResponse], status_code=201)
async def create_closet_clientes_batch(
    request: Closet_clienteBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple closet_clientes in a single request"""
    logger.debug(f"Batch creating {len(request.items)} closet_clientes")
    
    service = Closet_clienteService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} closet_clientes successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Closet_clienteResponse])
async def update_closet_clientes_batch(
    request: Closet_clienteBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple closet_clientes in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} closet_clientes")
    
    service = Closet_clienteService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} closet_clientes successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Closet_clienteResponse)
async def update_closet_cliente(
    id: int,
    data: Closet_clienteUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing closet_cliente (requires ownership)"""
    logger.debug(f"Updating closet_cliente {id} with data: {data}")

    service = Closet_clienteService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Closet_cliente with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Closet_cliente not found")
        
        logger.info(f"Closet_cliente {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating closet_cliente {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating closet_cliente {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_closet_clientes_batch(
    request: Closet_clienteBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple closet_clientes by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} closet_clientes")
    
    service = Closet_clienteService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} closet_clientes successfully")
        return {"message": f"Successfully deleted {deleted_count} closet_clientes", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_closet_cliente(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single closet_cliente by ID (requires ownership)"""
    logger.debug(f"Deleting closet_cliente with id: {id}")
    
    service = Closet_clienteService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Closet_cliente with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Closet_cliente not found")
        
        logger.info(f"Closet_cliente {id} deleted successfully")
        return {"message": "Closet_cliente deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting closet_cliente {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")