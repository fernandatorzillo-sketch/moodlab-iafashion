import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.curated_look_items import Curated_look_itemsService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/curated_look_items", tags=["curated_look_items"])


# ---------- Pydantic Schemas ----------
class Curated_look_itemsData(BaseModel):
    """Entity data schema (for create/update)"""
    look_id: int
    produto_id: int
    ordem: int = None
    obrigatorio: bool = None


class Curated_look_itemsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    look_id: Optional[int] = None
    produto_id: Optional[int] = None
    ordem: Optional[int] = None
    obrigatorio: Optional[bool] = None


class Curated_look_itemsResponse(BaseModel):
    """Entity response schema"""
    id: int
    look_id: int
    produto_id: int
    ordem: Optional[int] = None
    obrigatorio: Optional[bool] = None
    user_id: str

    class Config:
        from_attributes = True


class Curated_look_itemsListResponse(BaseModel):
    """List response schema"""
    items: List[Curated_look_itemsResponse]
    total: int
    skip: int
    limit: int


class Curated_look_itemsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Curated_look_itemsData]


class Curated_look_itemsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Curated_look_itemsUpdateData


class Curated_look_itemsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Curated_look_itemsBatchUpdateItem]


class Curated_look_itemsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Curated_look_itemsListResponse)
async def query_curated_look_itemss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query curated_look_itemss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying curated_look_itemss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Curated_look_itemsService(db)
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
        logger.debug(f"Found {result['total']} curated_look_itemss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying curated_look_itemss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Curated_look_itemsListResponse)
async def query_curated_look_itemss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query curated_look_itemss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying curated_look_itemss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Curated_look_itemsService(db)
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
        logger.debug(f"Found {result['total']} curated_look_itemss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying curated_look_itemss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Curated_look_itemsResponse)
async def get_curated_look_items(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single curated_look_items by ID (user can only see their own records)"""
    logger.debug(f"Fetching curated_look_items with id: {id}, fields={fields}")
    
    service = Curated_look_itemsService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Curated_look_items with id {id} not found")
            raise HTTPException(status_code=404, detail="Curated_look_items not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching curated_look_items {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Curated_look_itemsResponse, status_code=201)
async def create_curated_look_items(
    data: Curated_look_itemsData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new curated_look_items"""
    logger.debug(f"Creating new curated_look_items with data: {data}")
    
    service = Curated_look_itemsService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create curated_look_items")
        
        logger.info(f"Curated_look_items created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating curated_look_items: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating curated_look_items: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Curated_look_itemsResponse], status_code=201)
async def create_curated_look_itemss_batch(
    request: Curated_look_itemsBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple curated_look_itemss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} curated_look_itemss")
    
    service = Curated_look_itemsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} curated_look_itemss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Curated_look_itemsResponse])
async def update_curated_look_itemss_batch(
    request: Curated_look_itemsBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple curated_look_itemss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} curated_look_itemss")
    
    service = Curated_look_itemsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} curated_look_itemss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Curated_look_itemsResponse)
async def update_curated_look_items(
    id: int,
    data: Curated_look_itemsUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing curated_look_items (requires ownership)"""
    logger.debug(f"Updating curated_look_items {id} with data: {data}")

    service = Curated_look_itemsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Curated_look_items with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Curated_look_items not found")
        
        logger.info(f"Curated_look_items {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating curated_look_items {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating curated_look_items {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_curated_look_itemss_batch(
    request: Curated_look_itemsBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple curated_look_itemss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} curated_look_itemss")
    
    service = Curated_look_itemsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} curated_look_itemss successfully")
        return {"message": f"Successfully deleted {deleted_count} curated_look_itemss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_curated_look_items(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single curated_look_items by ID (requires ownership)"""
    logger.debug(f"Deleting curated_look_items with id: {id}")
    
    service = Curated_look_itemsService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Curated_look_items with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Curated_look_items not found")
        
        logger.info(f"Curated_look_items {id} deleted successfully")
        return {"message": "Curated_look_items deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting curated_look_items {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")