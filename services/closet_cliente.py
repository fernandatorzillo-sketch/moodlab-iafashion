import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.closet_cliente import Closet_cliente

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Closet_clienteService:
    """Service layer for Closet_cliente operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Closet_cliente]:
        """Create a new closet_cliente"""
        try:
            if user_id:
                data['user_id'] = user_id
            obj = Closet_cliente(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created closet_cliente with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating closet_cliente: {str(e)}")
            raise

    async def check_ownership(self, obj_id: int, user_id: str) -> bool:
        """Check if user owns this record"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            return obj is not None
        except Exception as e:
            logger.error(f"Error checking ownership for closet_cliente {obj_id}: {str(e)}")
            return False

    async def get_by_id(self, obj_id: int, user_id: Optional[str] = None) -> Optional[Closet_cliente]:
        """Get closet_cliente by ID (user can only see their own records)"""
        try:
            query = select(Closet_cliente).where(Closet_cliente.id == obj_id)
            if user_id:
                query = query.where(Closet_cliente.user_id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching closet_cliente {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        user_id: Optional[str] = None,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of closet_clientes (user can only see their own records)"""
        try:
            query = select(Closet_cliente)
            count_query = select(func.count(Closet_cliente.id))
            
            if user_id:
                query = query.where(Closet_cliente.user_id == user_id)
                count_query = count_query.where(Closet_cliente.user_id == user_id)
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Closet_cliente, field):
                        query = query.where(getattr(Closet_cliente, field) == value)
                        count_query = count_query.where(getattr(Closet_cliente, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Closet_cliente, field_name):
                        query = query.order_by(getattr(Closet_cliente, field_name).desc())
                else:
                    if hasattr(Closet_cliente, sort):
                        query = query.order_by(getattr(Closet_cliente, sort))
            else:
                query = query.order_by(Closet_cliente.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching closet_cliente list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Closet_cliente]:
        """Update closet_cliente (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Closet_cliente {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key) and key != 'user_id':
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated closet_cliente {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating closet_cliente {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int, user_id: Optional[str] = None) -> bool:
        """Delete closet_cliente (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Closet_cliente {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted closet_cliente {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting closet_cliente {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Closet_cliente]:
        """Get closet_cliente by any field"""
        try:
            if not hasattr(Closet_cliente, field_name):
                raise ValueError(f"Field {field_name} does not exist on Closet_cliente")
            result = await self.db.execute(
                select(Closet_cliente).where(getattr(Closet_cliente, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching closet_cliente by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Closet_cliente]:
        """Get list of closet_clientes filtered by field"""
        try:
            if not hasattr(Closet_cliente, field_name):
                raise ValueError(f"Field {field_name} does not exist on Closet_cliente")
            result = await self.db.execute(
                select(Closet_cliente)
                .where(getattr(Closet_cliente, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Closet_cliente.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching closet_clientes by {field_name}: {str(e)}")
            raise