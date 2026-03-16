import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.clientes import ClientesService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/clientes", tags=["clientes"])


# ---------- Pydantic Schemas ----------
class ClientesData(BaseModel):
    """Entity data schema (for create/update)"""
    empresa_id: int
    nome: str
    email: str = None
    telefone: str = None
    genero: str = None
    cidade: str = None
    estado: str = None
    data_cadastro: Optional[datetime] = None
    estilo_resumo: str = None
    tamanho_top: str = None
    tamanho_bottom: str = None
    tamanho_dress: str = None


class ClientesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    empresa_id: Optional[int] = None
    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    genero: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    data_cadastro: Optional[datetime] = None
    estilo_resumo: Optional[str] = None
    tamanho_top: Optional[str] = None
    tamanho_bottom: Optional[str] = None
    tamanho_dress: Optional[str] = None


class ClientesResponse(BaseModel):
    """Entity response schema"""
    id: int
    empresa_id: int
    nome: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    genero: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    data_cadastro: Optional[datetime] = None
    estilo_resumo: Optional[str] = None
    tamanho_top: Optional[str] = None
    tamanho_bottom: Optional[str] = None
    tamanho_dress: Optional[str] = None
    user_id: str

    class Config:
        from_attributes = True


class ClientesListResponse(BaseModel):
    """List response schema"""
    items: List[ClientesResponse]
    total: int
    skip: int
    limit: int


class ClientesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[ClientesData]


class ClientesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: ClientesUpdateData


class ClientesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[ClientesBatchUpdateItem]


class ClientesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=ClientesListResponse)
async def query_clientess(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query clientess with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying clientess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = ClientesService(db)
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
        logger.debug(f"Found {result['total']} clientess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying clientess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=ClientesListResponse)
async def query_clientess_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query clientess with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying clientess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = ClientesService(db)
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
        logger.debug(f"Found {result['total']} clientess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying clientess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=ClientesResponse)
async def get_clientes(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single clientes by ID (user can only see their own records)"""
    logger.debug(f"Fetching clientes with id: {id}, fields={fields}")
    
    service = ClientesService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Clientes with id {id} not found")
            raise HTTPException(status_code=404, detail="Clientes not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching clientes {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=ClientesResponse, status_code=201)
async def create_clientes(
    data: ClientesData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new clientes"""
    logger.debug(f"Creating new clientes with data: {data}")
    
    service = ClientesService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create clientes")
        
        logger.info(f"Clientes created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating clientes: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating clientes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[ClientesResponse], status_code=201)
async def create_clientess_batch(
    request: ClientesBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple clientess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} clientess")
    
    service = ClientesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} clientess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[ClientesResponse])
async def update_clientess_batch(
    request: ClientesBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple clientess in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} clientess")
    
    service = ClientesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} clientess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=ClientesResponse)
async def update_clientes(
    id: int,
    data: ClientesUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing clientes (requires ownership)"""
    logger.debug(f"Updating clientes {id} with data: {data}")

    service = ClientesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Clientes with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Clientes not found")
        
        logger.info(f"Clientes {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating clientes {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating clientes {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_clientess_batch(
    request: ClientesBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple clientess by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} clientess")
    
    service = ClientesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} clientess successfully")
        return {"message": f"Successfully deleted {deleted_count} clientess", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_clientes(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single clientes by ID (requires ownership)"""
    logger.debug(f"Deleting clientes with id: {id}")
    
    service = ClientesService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Clientes with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Clientes not found")
        
        logger.info(f"Clientes {id} deleted successfully")
        return {"message": "Clientes deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting clientes {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")