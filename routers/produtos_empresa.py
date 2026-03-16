import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.produtos_empresa import Produtos_empresaService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/produtos_empresa", tags=["produtos_empresa"])


# ---------- Pydantic Schemas ----------
class Produtos_empresaData(BaseModel):
    """Entity data schema (for create/update)"""
    empresa_id: int
    sku: str
    nome: str
    categoria: str = None
    subcategoria: str = None
    colecao: str = None
    cor: str = None
    modelagem: str = None
    tamanho: str = None
    preco: float = None
    estoque: int = None
    imagem_url: str = None
    link_produto: str = None
    ocasiao: str = None
    tags_estilo: str = None
    ativo: bool = None


class Produtos_empresaUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    empresa_id: Optional[int] = None
    sku: Optional[str] = None
    nome: Optional[str] = None
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    colecao: Optional[str] = None
    cor: Optional[str] = None
    modelagem: Optional[str] = None
    tamanho: Optional[str] = None
    preco: Optional[float] = None
    estoque: Optional[int] = None
    imagem_url: Optional[str] = None
    link_produto: Optional[str] = None
    ocasiao: Optional[str] = None
    tags_estilo: Optional[str] = None
    ativo: Optional[bool] = None


class Produtos_empresaResponse(BaseModel):
    """Entity response schema"""
    id: int
    empresa_id: int
    sku: str
    nome: str
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    colecao: Optional[str] = None
    cor: Optional[str] = None
    modelagem: Optional[str] = None
    tamanho: Optional[str] = None
    preco: Optional[float] = None
    estoque: Optional[int] = None
    imagem_url: Optional[str] = None
    link_produto: Optional[str] = None
    ocasiao: Optional[str] = None
    tags_estilo: Optional[str] = None
    ativo: Optional[bool] = None
    user_id: str

    class Config:
        from_attributes = True


class Produtos_empresaListResponse(BaseModel):
    """List response schema"""
    items: List[Produtos_empresaResponse]
    total: int
    skip: int
    limit: int


class Produtos_empresaBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Produtos_empresaData]


class Produtos_empresaBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Produtos_empresaUpdateData


class Produtos_empresaBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Produtos_empresaBatchUpdateItem]


class Produtos_empresaBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Produtos_empresaListResponse)
async def query_produtos_empresas(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query produtos_empresas with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying produtos_empresas: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Produtos_empresaService(db)
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
        logger.debug(f"Found {result['total']} produtos_empresas")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying produtos_empresas: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Produtos_empresaListResponse)
async def query_produtos_empresas_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query produtos_empresas with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying produtos_empresas: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Produtos_empresaService(db)
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
        logger.debug(f"Found {result['total']} produtos_empresas")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying produtos_empresas: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Produtos_empresaResponse)
async def get_produtos_empresa(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single produtos_empresa by ID (user can only see their own records)"""
    logger.debug(f"Fetching produtos_empresa with id: {id}, fields={fields}")
    
    service = Produtos_empresaService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Produtos_empresa with id {id} not found")
            raise HTTPException(status_code=404, detail="Produtos_empresa not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching produtos_empresa {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Produtos_empresaResponse, status_code=201)
async def create_produtos_empresa(
    data: Produtos_empresaData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new produtos_empresa"""
    logger.debug(f"Creating new produtos_empresa with data: {data}")
    
    service = Produtos_empresaService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create produtos_empresa")
        
        logger.info(f"Produtos_empresa created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating produtos_empresa: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating produtos_empresa: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Produtos_empresaResponse], status_code=201)
async def create_produtos_empresas_batch(
    request: Produtos_empresaBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple produtos_empresas in a single request"""
    logger.debug(f"Batch creating {len(request.items)} produtos_empresas")
    
    service = Produtos_empresaService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} produtos_empresas successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Produtos_empresaResponse])
async def update_produtos_empresas_batch(
    request: Produtos_empresaBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple produtos_empresas in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} produtos_empresas")
    
    service = Produtos_empresaService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} produtos_empresas successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Produtos_empresaResponse)
async def update_produtos_empresa(
    id: int,
    data: Produtos_empresaUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing produtos_empresa (requires ownership)"""
    logger.debug(f"Updating produtos_empresa {id} with data: {data}")

    service = Produtos_empresaService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Produtos_empresa with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Produtos_empresa not found")
        
        logger.info(f"Produtos_empresa {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating produtos_empresa {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating produtos_empresa {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_produtos_empresas_batch(
    request: Produtos_empresaBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple produtos_empresas by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} produtos_empresas")
    
    service = Produtos_empresaService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} produtos_empresas successfully")
        return {"message": f"Successfully deleted {deleted_count} produtos_empresas", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_produtos_empresa(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single produtos_empresa by ID (requires ownership)"""
    logger.debug(f"Deleting produtos_empresa with id: {id}")
    
    service = Produtos_empresaService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Produtos_empresa with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Produtos_empresa not found")
        
        logger.info(f"Produtos_empresa {id} deleted successfully")
        return {"message": "Produtos_empresa deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting produtos_empresa {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")