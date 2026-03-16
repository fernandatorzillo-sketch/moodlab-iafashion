import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.style_preferences import Style_preferencesService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/style_preferences", tags=["style_preferences"])


# ---------- Pydantic Schemas ----------
class Style_preferencesData(BaseModel):
    """Entity data schema (for create/update)"""
    preferred_colors: str = None
    preferred_styles: str = None
    preferred_occasions: str = None
    updated_at: Optional[datetime] = None


class Style_preferencesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    preferred_colors: Optional[str] = None
    preferred_styles: Optional[str] = None
    preferred_occasions: Optional[str] = None
    updated_at: Optional[datetime] = None


class Style_preferencesResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    preferred_colors: Optional[str] = None
    preferred_styles: Optional[str] = None
    preferred_occasions: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Style_preferencesListResponse(BaseModel):
    """List response schema"""
    items: List[Style_preferencesResponse]
    total: int
    skip: int
    limit: int


class Style_preferencesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Style_preferencesData]


class Style_preferencesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Style_preferencesUpdateData


class Style_preferencesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Style_preferencesBatchUpdateItem]


class Style_preferencesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Style_preferencesListResponse)
async def query_style_preferencess(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query style_preferencess with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying style_preferencess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Style_preferencesService(db)
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
        logger.debug(f"Found {result['total']} style_preferencess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying style_preferencess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Style_preferencesListResponse)
async def query_style_preferencess_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query style_preferencess with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying style_preferencess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Style_preferencesService(db)
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
        logger.debug(f"Found {result['total']} style_preferencess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying style_preferencess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Style_preferencesResponse)
async def get_style_preferences(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single style_preferences by ID (user can only see their own records)"""
    logger.debug(f"Fetching style_preferences with id: {id}, fields={fields}")
    
    service = Style_preferencesService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Style_preferences with id {id} not found")
            raise HTTPException(status_code=404, detail="Style_preferences not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching style_preferences {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Style_preferencesResponse, status_code=201)
async def create_style_preferences(
    data: Style_preferencesData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new style_preferences"""
    logger.debug(f"Creating new style_preferences with data: {data}")
    
    service = Style_preferencesService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create style_preferences")
        
        logger.info(f"Style_preferences created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating style_preferences: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating style_preferences: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Style_preferencesResponse], status_code=201)
async def create_style_preferencess_batch(
    request: Style_preferencesBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple style_preferencess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} style_preferencess")
    
    service = Style_preferencesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} style_preferencess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Style_preferencesResponse])
async def update_style_preferencess_batch(
    request: Style_preferencesBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple style_preferencess in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} style_preferencess")
    
    service = Style_preferencesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} style_preferencess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Style_preferencesResponse)
async def update_style_preferences(
    id: int,
    data: Style_preferencesUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing style_preferences (requires ownership)"""
    logger.debug(f"Updating style_preferences {id} with data: {data}")

    service = Style_preferencesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Style_preferences with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Style_preferences not found")
        
        logger.info(f"Style_preferences {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating style_preferences {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating style_preferences {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_style_preferencess_batch(
    request: Style_preferencesBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple style_preferencess by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} style_preferencess")
    
    service = Style_preferencesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} style_preferencess successfully")
        return {"message": f"Successfully deleted {deleted_count} style_preferencess", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_style_preferences(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single style_preferences by ID (requires ownership)"""
    logger.debug(f"Deleting style_preferences with id: {id}")
    
    service = Style_preferencesService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Style_preferences with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Style_preferences not found")
        
        logger.info(f"Style_preferences {id} deleted successfully")
        return {"message": "Style_preferences deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting style_preferences {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")