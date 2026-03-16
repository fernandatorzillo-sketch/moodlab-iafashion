import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.brand_settings import Brand_settingsService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/brand_settings", tags=["brand_settings"])


# ---------- Pydantic Schemas ----------
class Brand_settingsData(BaseModel):
    """Entity data schema (for create/update)"""
    empresa_id: int
    logo_url: str = None
    brand_name: str = None
    primary_color: str = None
    secondary_color: str = None
    background_color: str = None
    text_color: str = None
    font_family: str = None
    button_style: str = None
    border_radius: str = None
    display_mode: str = None
    tone_of_voice: str = None
    aesthetic_description: str = None
    module_name_closet: str = None
    module_name_looks: str = None
    module_name_recommendations: str = None
    banner_url: str = None


class Brand_settingsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    empresa_id: Optional[int] = None
    logo_url: Optional[str] = None
    brand_name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    font_family: Optional[str] = None
    button_style: Optional[str] = None
    border_radius: Optional[str] = None
    display_mode: Optional[str] = None
    tone_of_voice: Optional[str] = None
    aesthetic_description: Optional[str] = None
    module_name_closet: Optional[str] = None
    module_name_looks: Optional[str] = None
    module_name_recommendations: Optional[str] = None
    banner_url: Optional[str] = None


class Brand_settingsResponse(BaseModel):
    """Entity response schema"""
    id: int
    empresa_id: int
    logo_url: Optional[str] = None
    brand_name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    font_family: Optional[str] = None
    button_style: Optional[str] = None
    border_radius: Optional[str] = None
    display_mode: Optional[str] = None
    tone_of_voice: Optional[str] = None
    aesthetic_description: Optional[str] = None
    module_name_closet: Optional[str] = None
    module_name_looks: Optional[str] = None
    module_name_recommendations: Optional[str] = None
    banner_url: Optional[str] = None
    user_id: str

    class Config:
        from_attributes = True


class Brand_settingsListResponse(BaseModel):
    """List response schema"""
    items: List[Brand_settingsResponse]
    total: int
    skip: int
    limit: int


class Brand_settingsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Brand_settingsData]


class Brand_settingsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Brand_settingsUpdateData


class Brand_settingsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Brand_settingsBatchUpdateItem]


class Brand_settingsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Brand_settingsListResponse)
async def query_brand_settingss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query brand_settingss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying brand_settingss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Brand_settingsService(db)
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
        logger.debug(f"Found {result['total']} brand_settingss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying brand_settingss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Brand_settingsListResponse)
async def query_brand_settingss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query brand_settingss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying brand_settingss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Brand_settingsService(db)
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
        logger.debug(f"Found {result['total']} brand_settingss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying brand_settingss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Brand_settingsResponse)
async def get_brand_settings(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single brand_settings by ID (user can only see their own records)"""
    logger.debug(f"Fetching brand_settings with id: {id}, fields={fields}")
    
    service = Brand_settingsService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Brand_settings with id {id} not found")
            raise HTTPException(status_code=404, detail="Brand_settings not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching brand_settings {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Brand_settingsResponse, status_code=201)
async def create_brand_settings(
    data: Brand_settingsData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new brand_settings"""
    logger.debug(f"Creating new brand_settings with data: {data}")
    
    service = Brand_settingsService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create brand_settings")
        
        logger.info(f"Brand_settings created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating brand_settings: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating brand_settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Brand_settingsResponse], status_code=201)
async def create_brand_settingss_batch(
    request: Brand_settingsBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple brand_settingss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} brand_settingss")
    
    service = Brand_settingsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} brand_settingss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Brand_settingsResponse])
async def update_brand_settingss_batch(
    request: Brand_settingsBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple brand_settingss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} brand_settingss")
    
    service = Brand_settingsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} brand_settingss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Brand_settingsResponse)
async def update_brand_settings(
    id: int,
    data: Brand_settingsUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing brand_settings (requires ownership)"""
    logger.debug(f"Updating brand_settings {id} with data: {data}")

    service = Brand_settingsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Brand_settings with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Brand_settings not found")
        
        logger.info(f"Brand_settings {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating brand_settings {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating brand_settings {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_brand_settingss_batch(
    request: Brand_settingsBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple brand_settingss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} brand_settingss")
    
    service = Brand_settingsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} brand_settingss successfully")
        return {"message": f"Successfully deleted {deleted_count} brand_settingss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_brand_settings(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single brand_settings by ID (requires ownership)"""
    logger.debug(f"Deleting brand_settings with id: {id}")
    
    service = Brand_settingsService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Brand_settings with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Brand_settings not found")
        
        logger.info(f"Brand_settings {id} deleted successfully")
        return {"message": "Brand_settings deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting brand_settings {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")