import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.itens_pedido import Itens_pedido

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Itens_pedidoService:
    """Service layer for Itens_pedido operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Itens_pedido]:
        """Create a new itens_pedido"""
        try:
            if user_id:
                data['user_id'] = user_id
            obj = Itens_pedido(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created itens_pedido with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating itens_pedido: {str(e)}")
            raise

    async def check_ownership(self, obj_id: int, user_id: str) -> bool:
        """Check if user owns this record"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            return obj is not None
        except Exception as e:
            logger.error(f"Error checking ownership for itens_pedido {obj_id}: {str(e)}")
            return False

    async def get_by_id(self, obj_id: int, user_id: Optional[str] = None) -> Optional[Itens_pedido]:
        """Get itens_pedido by ID (user can only see their own records)"""
        try:
            query = select(Itens_pedido).where(Itens_pedido.id == obj_id)
            if user_id:
                query = query.where(Itens_pedido.user_id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching itens_pedido {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        user_id: Optional[str] = None,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of itens_pedidos (user can only see their own records)"""
        try:
            query = select(Itens_pedido)
            count_query = select(func.count(Itens_pedido.id))
            
            if user_id:
                query = query.where(Itens_pedido.user_id == user_id)
                count_query = count_query.where(Itens_pedido.user_id == user_id)
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Itens_pedido, field):
                        query = query.where(getattr(Itens_pedido, field) == value)
                        count_query = count_query.where(getattr(Itens_pedido, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Itens_pedido, field_name):
                        query = query.order_by(getattr(Itens_pedido, field_name).desc())
                else:
                    if hasattr(Itens_pedido, sort):
                        query = query.order_by(getattr(Itens_pedido, sort))
            else:
                query = query.order_by(Itens_pedido.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching itens_pedido list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Itens_pedido]:
        """Update itens_pedido (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Itens_pedido {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key) and key != 'user_id':
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated itens_pedido {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating itens_pedido {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int, user_id: Optional[str] = None) -> bool:
        """Delete itens_pedido (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Itens_pedido {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted itens_pedido {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting itens_pedido {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Itens_pedido]:
        """Get itens_pedido by any field"""
        try:
            if not hasattr(Itens_pedido, field_name):
                raise ValueError(f"Field {field_name} does not exist on Itens_pedido")
            result = await self.db.execute(
                select(Itens_pedido).where(getattr(Itens_pedido, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching itens_pedido by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Itens_pedido]:
        """Get list of itens_pedidos filtered by field"""
        try:
            if not hasattr(Itens_pedido, field_name):
                raise ValueError(f"Field {field_name} does not exist on Itens_pedido")
            result = await self.db.execute(
                select(Itens_pedido)
                .where(getattr(Itens_pedido, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Itens_pedido.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching itens_pedidos by {field_name}: {str(e)}")
            raise