"""Price fetching endpoints — scrape price from product URLs."""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import get_current_user
from schemas.auth import UserResponse
from models.produtos_empresa import Produtos_empresa
from services.price_scraper import fetch_price_from_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/price", tags=["price"])


class FetchPriceRequest(BaseModel):
    produto_id: int
    empresa_id: int


class FetchPriceResponse(BaseModel):
    produto_id: int
    old_price: Optional[float] = None
    new_price: Optional[float] = None
    source: str
    updated: bool
    link_produto: Optional[str] = None


class BulkFetchPriceRequest(BaseModel):
    empresa_id: int
    produto_ids: Optional[List[int]] = None  # None = all products with link_produto


class BulkFetchPriceResponse(BaseModel):
    total: int
    updated: int
    failed: int
    results: List[FetchPriceResponse]


@router.post("/fetch-from-url", response_model=FetchPriceResponse)
async def fetch_price_from_product_url(
    data: FetchPriceRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch current price from the product's website URL and update in DB."""
    stmt = select(Produtos_empresa).where(
        and_(
            Produtos_empresa.id == data.produto_id,
            Produtos_empresa.empresa_id == data.empresa_id,
            Produtos_empresa.user_id == str(current_user.id),
        )
    )
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    if not product.link_produto:
        return FetchPriceResponse(
            produto_id=data.produto_id,
            old_price=product.preco,
            new_price=None,
            source="Produto sem link cadastrado",
            updated=False,
            link_produto=None,
        )

    old_price = product.preco
    new_price, source = await fetch_price_from_url(product.link_produto)

    updated = False
    if new_price is not None and new_price != old_price:
        product.preco = new_price
        await db.commit()
        await db.refresh(product)
        updated = True
        logger.info(f"Price updated for product {data.produto_id}: {old_price} -> {new_price} (source: {source})")

    return FetchPriceResponse(
        produto_id=data.produto_id,
        old_price=old_price,
        new_price=new_price,
        source=source,
        updated=updated,
        link_produto=product.link_produto,
    )


@router.post("/bulk-fetch", response_model=BulkFetchPriceResponse)
async def bulk_fetch_prices(
    data: BulkFetchPriceRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch prices from URLs for multiple products (or all with links)."""
    conditions = [
        Produtos_empresa.empresa_id == data.empresa_id,
        Produtos_empresa.user_id == str(current_user.id),
        Produtos_empresa.link_produto != None,
        Produtos_empresa.link_produto != "",
    ]
    if data.produto_ids:
        conditions.append(Produtos_empresa.id.in_(data.produto_ids))

    stmt = select(Produtos_empresa).where(and_(*conditions)).limit(50)
    result = await db.execute(stmt)
    products = result.scalars().all()

    results: List[FetchPriceResponse] = []
    updated_count = 0
    failed_count = 0

    for product in products:
        try:
            old_price = product.preco
            new_price, source = await fetch_price_from_url(product.link_produto)

            was_updated = False
            if new_price is not None and new_price != old_price:
                product.preco = new_price
                was_updated = True
                updated_count += 1

            results.append(FetchPriceResponse(
                produto_id=product.id,
                old_price=old_price,
                new_price=new_price,
                source=source,
                updated=was_updated,
                link_produto=product.link_produto,
            ))

            if not new_price:
                failed_count += 1

        except Exception as e:
            logger.error(f"Error fetching price for product {product.id}: {e}")
            results.append(FetchPriceResponse(
                produto_id=product.id,
                old_price=product.preco,
                new_price=None,
                source=f"Erro: {str(e)}",
                updated=False,
                link_produto=product.link_produto,
            ))
            failed_count += 1

    if updated_count > 0:
        await db.commit()

    return BulkFetchPriceResponse(
        total=len(products),
        updated=updated_count,
        failed=failed_count,
        results=results,
    )