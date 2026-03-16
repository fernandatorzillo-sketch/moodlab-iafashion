import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.purchases import PurchasesService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/purchases", tags=["purchases"])


# ---------- Pydantic Schemas ----------
class PurchasesData(BaseModel):
    """Entity data schema (for create/update)"""
    product_id: int
    purchased_at: Optional[datetime] = None


class PurchasesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    product_id: Optional[int] = None
    purchased_at: Optional[datetime] = None


class PurchasesResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    product_id: int
    purchased_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PurchasesListResponse(BaseModel):
    """List response schema"""
    items: List[PurchasesResponse]
    total: int
    skip: int
    limit: int


class PurchasesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[PurchasesData]


class PurchasesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: PurchasesUpdateData


class PurchasesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[PurchasesBatchUpdateItem]


class PurchasesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=PurchasesListResponse)
async def query_purchasess(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query purchasess with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying purchasess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = PurchasesService(db)
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
        logger.debug(f"Found {result['total']} purchasess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying purchasess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=PurchasesListResponse)
async def query_purchasess_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query purchasess with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying purchasess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = PurchasesService(db)
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
        logger.debug(f"Found {result['total']} purchasess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying purchasess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=PurchasesResponse)
async def get_purchases(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single purchases by ID (user can only see their own records)"""
    logger.debug(f"Fetching purchases with id: {id}, fields={fields}")
    
    service = PurchasesService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Purchases with id {id} not found")
            raise HTTPException(status_code=404, detail="Purchases not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching purchases {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=PurchasesResponse, status_code=201)
async def create_purchases(
    data: PurchasesData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new purchases"""
    logger.debug(f"Creating new purchases with data: {data}")
    
    service = PurchasesService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create purchases")
        
        logger.info(f"Purchases created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating purchases: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating purchases: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[PurchasesResponse], status_code=201)
async def create_purchasess_batch(
    request: PurchasesBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple purchasess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} purchasess")
    
    service = PurchasesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} purchasess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[PurchasesResponse])
async def update_purchasess_batch(
    request: PurchasesBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple purchasess in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} purchasess")
    
    service = PurchasesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} purchasess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=PurchasesResponse)
async def update_purchases(
    id: int,
    data: PurchasesUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing purchases (requires ownership)"""
    logger.debug(f"Updating purchases {id} with data: {data}")

    service = PurchasesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Purchases with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Purchases not found")
        
        logger.info(f"Purchases {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating purchases {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating purchases {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_purchasess_batch(
    request: PurchasesBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple purchasess by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} purchasess")
    
    service = PurchasesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} purchasess successfully")
        return {"message": f"Successfully deleted {deleted_count} purchasess", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_purchases(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single purchases by ID (requires ownership)"""
    logger.debug(f"Deleting purchases with id: {id}")
    
    service = PurchasesService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Purchases with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Purchases not found")
        
        logger.info(f"Purchases {id} deleted successfully")
        return {"message": "Purchases deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting purchases {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")