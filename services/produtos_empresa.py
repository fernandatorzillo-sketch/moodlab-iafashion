import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.produtos_empresa import Produtos_empresa

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Produtos_empresaService:
    """Service layer for Produtos_empresa operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Produtos_empresa]:
        """Create a new produtos_empresa"""
        try:
            if user_id:
                data['user_id'] = user_id
            obj = Produtos_empresa(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created produtos_empresa with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating produtos_empresa: {str(e)}")
            raise

    async def check_ownership(self, obj_id: int, user_id: str) -> bool:
        """Check if user owns this record"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            return obj is not None
        except Exception as e:
            logger.error(f"Error checking ownership for produtos_empresa {obj_id}: {str(e)}")
            return False

    async def get_by_id(self, obj_id: int, user_id: Optional[str] = None) -> Optional[Produtos_empresa]:
        """Get produtos_empresa by ID (user can only see their own records)"""
        try:
            query = select(Produtos_empresa).where(Produtos_empresa.id == obj_id)
            if user_id:
                query = query.where(Produtos_empresa.user_id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching produtos_empresa {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        user_id: Optional[str] = None,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of produtos_empresas (user can only see their own records)"""
        try:
            query = select(Produtos_empresa)
            count_query = select(func.count(Produtos_empresa.id))
            
            if user_id:
                query = query.where(Produtos_empresa.user_id == user_id)
                count_query = count_query.where(Produtos_empresa.user_id == user_id)
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Produtos_empresa, field):
                        query = query.where(getattr(Produtos_empresa, field) == value)
                        count_query = count_query.where(getattr(Produtos_empresa, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Produtos_empresa, field_name):
                        query = query.order_by(getattr(Produtos_empresa, field_name).desc())
                else:
                    if hasattr(Produtos_empresa, sort):
                        query = query.order_by(getattr(Produtos_empresa, sort))
            else:
                query = query.order_by(Produtos_empresa.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching produtos_empresa list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Produtos_empresa]:
        """Update produtos_empresa (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Produtos_empresa {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key) and key != 'user_id':
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated produtos_empresa {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating produtos_empresa {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int, user_id: Optional[str] = None) -> bool:
        """Delete produtos_empresa (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Produtos_empresa {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted produtos_empresa {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting produtos_empresa {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Produtos_empresa]:
        """Get produtos_empresa by any field"""
        try:
            if not hasattr(Produtos_empresa, field_name):
                raise ValueError(f"Field {field_name} does not exist on Produtos_empresa")
            result = await self.db.execute(
                select(Produtos_empresa).where(getattr(Produtos_empresa, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching produtos_empresa by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Produtos_empresa]:
        """Get list of produtos_empresas filtered by field"""
        try:
            if not hasattr(Produtos_empresa, field_name):
                raise ValueError(f"Field {field_name} does not exist on Produtos_empresa")
            result = await self.db.execute(
                select(Produtos_empresa)
                .where(getattr(Produtos_empresa, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Produtos_empresa.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching produtos_empresas by {field_name}: {str(e)}")
            raise