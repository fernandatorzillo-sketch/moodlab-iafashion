"""Stock management service — handles inventory deduction on purchase events."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.produtos_empresa import Produtos_empresa
from models.pedidos import Pedidos
from models.itens_pedido import Itens_pedido

logger = logging.getLogger(__name__)

# Order statuses that trigger stock deduction
PURCHASE_STATUSES = {"pago", "enviado", "entregue", "completo", "completed", "delivered", "paid", "shipped"}


class StockService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def deduct_stock(
        self, empresa_id: int, user_id: str,
        sku: str, quantidade: int,
    ) -> Dict[str, Any]:
        """Deduct stock for a single product by SKU."""
        stmt = select(Produtos_empresa).where(
            and_(
                Produtos_empresa.empresa_id == empresa_id,
                Produtos_empresa.user_id == user_id,
                Produtos_empresa.sku == sku,
            )
        )
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            return {"success": False, "error": f"Produto SKU '{sku}' não encontrado", "sku": sku}

        old_stock = product.estoque or 0
        new_stock = max(0, old_stock - quantidade)
        product.estoque = new_stock

        # Deactivate product if stock reaches 0
        if new_stock <= 0:
            product.ativo = False
            logger.info(f"Product {sku} deactivated — out of stock")

        await self.db.flush()

        return {
            "success": True,
            "sku": sku,
            "produto_id": product.id,
            "nome": product.nome,
            "old_stock": old_stock,
            "new_stock": new_stock,
            "quantidade_deduzida": quantidade,
            "esgotado": new_stock <= 0,
        }

    async def process_order_stock(
        self, empresa_id: int, user_id: str, pedido_id: int,
    ) -> Dict[str, Any]:
        """Process stock deduction for all items in an order."""
        # Get order
        order_stmt = select(Pedidos).where(
            and_(
                Pedidos.id == pedido_id,
                Pedidos.empresa_id == empresa_id,
                Pedidos.user_id == user_id,
            )
        )
        order_result = await self.db.execute(order_stmt)
        order = order_result.scalar_one_or_none()

        if not order:
            return {"success": False, "error": "Pedido não encontrado", "deductions": []}

        # Check if order status triggers stock deduction
        status = (order.status or "").lower().strip()
        if status not in PURCHASE_STATUSES:
            return {
                "success": False,
                "error": f"Status '{order.status}' não é um evento de compra",
                "deductions": [],
            }

        # Get order items
        items_stmt = select(Itens_pedido).where(
            and_(
                Itens_pedido.pedido_id == pedido_id,
                Itens_pedido.user_id == user_id,
            )
        )
        items_result = await self.db.execute(items_stmt)
        items = items_result.scalars().all()

        deductions = []
        for item in items:
            sku = item.sku
            quantidade = item.quantidade or 1

            if not sku:
                # Try to find by produto_id
                if item.produto_id:
                    prod_stmt = select(Produtos_empresa).where(Produtos_empresa.id == item.produto_id)
                    prod_result = await self.db.execute(prod_stmt)
                    prod = prod_result.scalar_one_or_none()
                    if prod:
                        sku = prod.sku

            if sku:
                result = await self.deduct_stock(empresa_id, user_id, sku, quantidade)
                deductions.append(result)
            else:
                deductions.append({
                    "success": False,
                    "error": "Item sem SKU ou produto_id",
                    "sku": None,
                })

        await self.db.commit()

        successful = sum(1 for d in deductions if d.get("success"))
        out_of_stock = sum(1 for d in deductions if d.get("esgotado"))

        return {
            "success": True,
            "pedido_id": pedido_id,
            "numero_pedido": order.numero_pedido,
            "total_items": len(items),
            "deductions_ok": successful,
            "deductions_failed": len(deductions) - successful,
            "produtos_esgotados": out_of_stock,
            "deductions": deductions,
        }

    async def process_orders_by_status(
        self, empresa_id: int, user_id: str,
    ) -> Dict[str, Any]:
        """Process stock deduction for all orders with purchase status that haven't been processed yet."""
        # Get orders with purchase statuses
        stmt = select(Pedidos).where(
            and_(
                Pedidos.empresa_id == empresa_id,
                Pedidos.user_id == user_id,
                Pedidos.status.in_(list(PURCHASE_STATUSES)),
            )
        )
        result = await self.db.execute(stmt)
        orders = result.scalars().all()

        total_deductions = 0
        total_out_of_stock = 0
        processed_orders = 0

        for order in orders:
            order_result = await self.process_order_stock(empresa_id, user_id, order.id)
            if order_result.get("success"):
                processed_orders += 1
                total_deductions += order_result.get("deductions_ok", 0)
                total_out_of_stock += order_result.get("produtos_esgotados", 0)

        return {
            "processed_orders": processed_orders,
            "total_deductions": total_deductions,
            "produtos_esgotados": total_out_of_stock,
        }

    async def get_stock_summary(
        self, empresa_id: int, user_id: str,
    ) -> Dict[str, Any]:
        """Get stock summary for the company."""
        base_cond = [
            Produtos_empresa.empresa_id == empresa_id,
            Produtos_empresa.user_id == user_id,
        ]

        # Total products
        total_stmt = select(func.count()).select_from(Produtos_empresa).where(and_(*base_cond))
        total_result = await self.db.execute(total_stmt)
        total = total_result.scalar() or 0

        # Out of stock
        oos_stmt = select(func.count()).select_from(Produtos_empresa).where(
            and_(*base_cond, Produtos_empresa.estoque != None, Produtos_empresa.estoque <= 0)
        )
        oos_result = await self.db.execute(oos_stmt)
        out_of_stock = oos_result.scalar() or 0

        # Low stock (1-5)
        low_stmt = select(func.count()).select_from(Produtos_empresa).where(
            and_(*base_cond, Produtos_empresa.estoque != None, Produtos_empresa.estoque > 0, Produtos_empresa.estoque <= 5)
        )
        low_result = await self.db.execute(low_stmt)
        low_stock = low_result.scalar() or 0

        # In stock
        in_stock = total - out_of_stock

        # Products without stock info
        no_info_stmt = select(func.count()).select_from(Produtos_empresa).where(
            and_(*base_cond, Produtos_empresa.estoque.is_(None))
        )
        no_info_result = await self.db.execute(no_info_stmt)
        no_stock_info = no_info_result.scalar() or 0

        # Out of stock product details
        oos_products_stmt = (
            select(Produtos_empresa)
            .where(and_(*base_cond, Produtos_empresa.estoque != None, Produtos_empresa.estoque <= 0))
            .limit(20)
        )
        oos_products_result = await self.db.execute(oos_products_stmt)
        oos_products = [
            {"id": p.id, "sku": p.sku, "nome": p.nome, "estoque": p.estoque, "preco": p.preco}
            for p in oos_products_result.scalars().all()
        ]

        # Low stock product details
        low_products_stmt = (
            select(Produtos_empresa)
            .where(and_(*base_cond, Produtos_empresa.estoque != None, Produtos_empresa.estoque > 0, Produtos_empresa.estoque <= 5))
            .limit(20)
        )
        low_products_result = await self.db.execute(low_products_stmt)
        low_products = [
            {"id": p.id, "sku": p.sku, "nome": p.nome, "estoque": p.estoque, "preco": p.preco}
            for p in low_products_result.scalars().all()
        ]

        return {
            "total_produtos": total,
            "em_estoque": in_stock,
            "fora_estoque": out_of_stock,
            "estoque_baixo": low_stock,
            "sem_info_estoque": no_stock_info,
            "produtos_esgotados": oos_products,
            "produtos_estoque_baixo": low_products,
        }