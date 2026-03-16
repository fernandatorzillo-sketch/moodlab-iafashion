import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.itens_pedido import Itens_pedidoService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/itens_pedido", tags=["itens_pedido"])


# ---------- Pydantic Schemas ----------
class Itens_pedidoData(BaseModel):
    """Entity data schema (for create/update)"""
    pedido_id: int
    produto_id: int
    sku: str = None
    quantidade: int = None
    preco_unitario: float = None
    tamanho: str = None


class Itens_pedidoUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    pedido_id: Optional[int] = None
    produto_id: Optional[int] = None
    sku: Optional[str] = None
    quantidade: Optional[int] = None
    preco_unitario: Optional[float] = None
    tamanho: Optional[str] = None


class Itens_pedidoResponse(BaseModel):
    """Entity response schema"""
    id: int
    pedido_id: int
    produto_id: int
    sku: Optional[str] = None
    quantidade: Optional[int] = None
    preco_unitario: Optional[float] = None
    tamanho: Optional[str] = None
    user_id: str

    class Config:
        from_attributes = True


class Itens_pedidoListResponse(BaseModel):
    """List response schema"""
    items: List[Itens_pedidoResponse]
    total: int
    skip: int
    limit: int


class Itens_pedidoBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Itens_pedidoData]


class Itens_pedidoBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Itens_pedidoUpdateData


class Itens_pedidoBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Itens_pedidoBatchUpdateItem]


class Itens_pedidoBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Itens_pedidoListResponse)
async def query_itens_pedidos(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query itens_pedidos with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying itens_pedidos: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Itens_pedidoService(db)
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
        logger.debug(f"Found {result['total']} itens_pedidos")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying itens_pedidos: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Itens_pedidoListResponse)
async def query_itens_pedidos_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query itens_pedidos with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying itens_pedidos: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Itens_pedidoService(db)
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
        logger.debug(f"Found {result['total']} itens_pedidos")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying itens_pedidos: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Itens_pedidoResponse)
async def get_itens_pedido(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single itens_pedido by ID (user can only see their own records)"""
    logger.debug(f"Fetching itens_pedido with id: {id}, fields={fields}")
    
    service = Itens_pedidoService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Itens_pedido with id {id} not found")
            raise HTTPException(status_code=404, detail="Itens_pedido not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching itens_pedido {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Itens_pedidoResponse, status_code=201)
async def create_itens_pedido(
    data: Itens_pedidoData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new itens_pedido"""
    logger.debug(f"Creating new itens_pedido with data: {data}")
    
    service = Itens_pedidoService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create itens_pedido")
        
        logger.info(f"Itens_pedido created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating itens_pedido: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating itens_pedido: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Itens_pedidoResponse], status_code=201)
async def create_itens_pedidos_batch(
    request: Itens_pedidoBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple itens_pedidos in a single request"""
    logger.debug(f"Batch creating {len(request.items)} itens_pedidos")
    
    service = Itens_pedidoService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} itens_pedidos successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Itens_pedidoResponse])
async def update_itens_pedidos_batch(
    request: Itens_pedidoBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple itens_pedidos in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} itens_pedidos")
    
    service = Itens_pedidoService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} itens_pedidos successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Itens_pedidoResponse)
async def update_itens_pedido(
    id: int,
    data: Itens_pedidoUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing itens_pedido (requires ownership)"""
    logger.debug(f"Updating itens_pedido {id} with data: {data}")

    service = Itens_pedidoService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Itens_pedido with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Itens_pedido not found")
        
        logger.info(f"Itens_pedido {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating itens_pedido {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating itens_pedido {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_itens_pedidos_batch(
    request: Itens_pedidoBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple itens_pedidos by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} itens_pedidos")
    
    service = Itens_pedidoService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} itens_pedidos successfully")
        return {"message": f"Successfully deleted {deleted_count} itens_pedidos", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_itens_pedido(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single itens_pedido by ID (requires ownership)"""
    logger.debug(f"Deleting itens_pedido with id: {id}")
    
    service = Itens_pedidoService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Itens_pedido with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Itens_pedido not found")
        
        logger.info(f"Itens_pedido {id} deleted successfully")
        return {"message": "Itens_pedido deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting itens_pedido {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")