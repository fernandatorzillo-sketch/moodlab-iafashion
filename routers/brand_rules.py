import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.brand_rules import Brand_rulesService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/brand_rules", tags=["brand_rules"])


# ---------- Pydantic Schemas ----------
class Brand_rulesData(BaseModel):
    """Entity data schema (for create/update)"""
    empresa_id: int
    rule_type: str
    rule_value: str = None
    descricao: str = None
    ativo: bool = None
    prioridade: int = None


class Brand_rulesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    empresa_id: Optional[int] = None
    rule_type: Optional[str] = None
    rule_value: Optional[str] = None
    descricao: Optional[str] = None
    ativo: Optional[bool] = None
    prioridade: Optional[int] = None


class Brand_rulesResponse(BaseModel):
    """Entity response schema"""
    id: int
    empresa_id: int
    rule_type: str
    rule_value: Optional[str] = None
    descricao: Optional[str] = None
    ativo: Optional[bool] = None
    prioridade: Optional[int] = None
    user_id: str

    class Config:
        from_attributes = True


class Brand_rulesListResponse(BaseModel):
    """List response schema"""
    items: List[Brand_rulesResponse]
    total: int
    skip: int
    limit: int


class Brand_rulesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Brand_rulesData]


class Brand_rulesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Brand_rulesUpdateData


class Brand_rulesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Brand_rulesBatchUpdateItem]


class Brand_rulesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Brand_rulesListResponse)
async def query_brand_ruless(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query brand_ruless with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying brand_ruless: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Brand_rulesService(db)
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
        logger.debug(f"Found {result['total']} brand_ruless")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying brand_ruless: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Brand_rulesListResponse)
async def query_brand_ruless_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query brand_ruless with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying brand_ruless: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Brand_rulesService(db)
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
        logger.debug(f"Found {result['total']} brand_ruless")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying brand_ruless: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Brand_rulesResponse)
async def get_brand_rules(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single brand_rules by ID (user can only see their own records)"""
    logger.debug(f"Fetching brand_rules with id: {id}, fields={fields}")
    
    service = Brand_rulesService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Brand_rules with id {id} not found")
            raise HTTPException(status_code=404, detail="Brand_rules not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching brand_rules {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Brand_rulesResponse, status_code=201)
async def create_brand_rules(
    data: Brand_rulesData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new brand_rules"""
    logger.debug(f"Creating new brand_rules with data: {data}")
    
    service = Brand_rulesService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create brand_rules")
        
        logger.info(f"Brand_rules created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating brand_rules: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating brand_rules: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Brand_rulesResponse], status_code=201)
async def create_brand_ruless_batch(
    request: Brand_rulesBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple brand_ruless in a single request"""
    logger.debug(f"Batch creating {len(request.items)} brand_ruless")
    
    service = Brand_rulesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} brand_ruless successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Brand_rulesResponse])
async def update_brand_ruless_batch(
    request: Brand_rulesBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple brand_ruless in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} brand_ruless")
    
    service = Brand_rulesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} brand_ruless successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Brand_rulesResponse)
async def update_brand_rules(
    id: int,
    data: Brand_rulesUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing brand_rules (requires ownership)"""
    logger.debug(f"Updating brand_rules {id} with data: {data}")

    service = Brand_rulesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Brand_rules with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Brand_rules not found")
        
        logger.info(f"Brand_rules {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating brand_rules {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating brand_rules {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_brand_ruless_batch(
    request: Brand_rulesBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple brand_ruless by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} brand_ruless")
    
    service = Brand_rulesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} brand_ruless successfully")
        return {"message": f"Successfully deleted {deleted_count} brand_ruless", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_brand_rules(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single brand_rules by ID (requires ownership)"""
    logger.debug(f"Deleting brand_rules with id: {id}")
    
    service = Brand_rulesService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Brand_rules with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Brand_rules not found")
        
        logger.info(f"Brand_rules {id} deleted successfully")
        return {"message": "Brand_rules deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting brand_rules {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")