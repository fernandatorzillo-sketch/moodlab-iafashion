from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.customer import Customer
from models.customer_closet_item import CustomerClosetItem
from services.closet_db import AsyncSessionLocal
from services.recommendation_service import get_customer_recommendations

def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def normalize(v) -> str:
    return str(v or "").strip().lower()


def fix_image_url(url: str) -> str:
    """
    Normaliza a URL da imagem VTEX.
    - Remove query string (?v=...)
    - URLs com dimensoes (728-1090): substitui por 500-500
    - URLs sem dimensoes (/ids/123/image.jpg): deixa como está
      (adicionar 500-500 quebraria essas URLs na VTEX)
    """
    if not url:
        return ""
    import re
    url = str(url).strip()
    # Remove query string
    url = re.sub(r'\?.*$', '', url)
    # Substitui dimensoes existentes por 500-500
    # Apenas quando JA tem dimensoes no path (ex: -728-1090)
    url = re.sub(
        r'(/arquivos/ids/[0-9]+)-[0-9]+-[0-9]+(/[^?#]+)',
        lambda m: m.group(1) + "-500-500" + m.group(2),
        url,
    )
    # URLs sem dimensoes (/ids/123456/image.jpg) ficam como estão
    return url


def fix_product_url(url: str) -> str:
    """
    Garante que a URL do produto aponta para o site de produção.
    """
    if not url:
        return ""
    url = str(url).strip()
    # Se a URL não tem domínio, adiciona o domínio correto
    if url.startswith("/"):
        return f"https://aguadecoco.com.br{url}"
    return url


async def _analyze_print_preference_async(closet_sku_ids: list) -> str:
    """
    Analisa print_name real (campo VTEX) das peças do closet.
    Valores: ESTAMPADO, LISO, LISO TRABALHADO
    """
    if not closet_sku_ids:
        return "misto"
    try:
        from sqlalchemy import select
        from models.catalog_product import CatalogProduct
        from services.closet_db import AsyncSessionLocal
        async with AsyncSessionLocal() as s:
            r = await s.execute(
                select(CatalogProduct.print_name)
                .where(CatalogProduct.sku_id.in_(closet_sku_ids[:30]))
            )
            prints = [normalize(row.print_name) for row in r.fetchall() if row.print_name]
    except Exception:
        return "misto"

    if not prints:
        return "misto"

    estampados = sum(1 for p in prints if "estampado" in p)
    lisos      = sum(1 for p in prints if "liso" in p)
    total = estampados + lisos
    if total == 0:
        return "misto"
    ratio = estampados / total
    if ratio >= 0.6:
        return "estampado"
    elif ratio <= 0.3:
        return "liso"
    return "misto"


def _analyze_print_preference(closet_items) -> str:
    """Versão síncrona — mantida para compatibilidade. Usa nome como aproximação."""
    estampados = lisos = 0
    for item in closet_items:
        name = (item.name or "").lower()
        if any(t in name for t in ["estampa","floral","listrad","tie dye","onça","onca",
                                    "floresta","folhagem","coqueiros","borboleta","espiral"]):
            estampados += 1
        else:
            lisos += 1
    total = estampados + lisos
    if total == 0: return "misto"
    ratio = estampados / total
    return "estampado" if ratio >= 0.6 else "liso" if ratio <= 0.3 else "misto"


async def get_customer_closet_payload(email: str) -> dict:
    email = normalize_email(email)

    if not email:
        return {
            "found": False,
            "customer": None,
            "closet": [],
            "looks": [],
            "recommendations": [],
            "debug": {
                "email": "",
                "closet_count": 0,
                "message": "E-mail vazio.",
            },
        }

    async with AsyncSessionLocal() as session:
        customer = await _get_customer(session, email)
        closet_items = await _get_customer_closet_items(session, email)

    # Analisa estamparia usando print_name real do catalog_products
    closet_sku_ids = [item.sku_id for item in closet_items if item.sku_id]
    estamparia_profile = await _analyze_print_preference_async(closet_sku_ids)

    recommendations = await get_customer_recommendations(
        email,
        print_preference=estamparia_profile,
    )

    customer_name = None
    if customer:
        customer_name = customer.full_name or customer.first_name or email.split("@")[0]
    else:
        customer_name = email.split("@")[0]

    # Departamentos que NÃO são moda — excluir do closet
    NON_FASHION_DEPTS = {"casa", "infantil", "kit", "kits", "utilidades", "mesa", "cama", "banho"}

    # Detecta gênero dominante do closet para filtrar itens masculinos
    all_names = " ".join((i.name or "") for i in closet_items).lower()
    all_cats  = " ".join((i.category or "") + " " + (i.department or "") for i in closet_items).lower()
    fem_signals  = all_names.count("biquíni") + all_names.count("biquini") + all_names.count("calcinha") + all_names.count("maiô") + all_cats.count("feminino")
    masc_signals = all_cats.count("masculino") + all_names.count("sunga")
    dominant_gender = "masculino" if masc_signals > fem_signals else "feminino"

    def is_fashion_item(item) -> bool:
        dept = (item.department or "").lower().strip()
        cat  = (item.category or "").lower().strip()
        name = (item.name or "").lower()
        # Exclui departamentos não-moda
        if dept in NON_FASHION_DEPTS:
            return False
        # Exclui itens sem nome ou nome genérico
        if not name or name == "produto":
            return False
        # Exclui itens claramente de casa pelo nome
        casa_terms = ["taça", "taca", "copo", "prato", "vaso", "vela", "toalha",
                      "almofada", "colcha", "lençol", "lenco", "porta", "quadro"]
        if any(t in name for t in casa_terms):
            return False
        # Exclui itens masculinos do closet feminino
        if dominant_gender == "feminino":
            is_masc_cat = "masculino" in dept or "masculino" in cat
            is_masc_name = any(t in name for t in [
                "sunga", "polo tricô", "polo trigo", "camisa polo masculin",
                "camiseta masculin", "short masculin", "bermuda masculin"
            ])
            if is_masc_cat or is_masc_name:
                return False
        return True

    fashion_items = [item for item in closet_items if is_fashion_item(item)]

    closet_payload = [
        {
            # IDs
            "id": item.product_id or item.sku_id,
            "sku_id": item.sku_id,
            "product_id": item.product_id,
            "ref_id": item.ref_id,

            # Nome
            "nome": item.name,
            "name": item.name,

            # Categoria
            "categoria": item.category,
            "category": item.category,

            # Departamento
            "departamento": item.department,
            "department": item.department,

            # Imagem — URL limpa sem ?v=
            "imagem_url": fix_image_url(item.image_url),
            "image_url": fix_image_url(item.image_url),

            # Link
            "link_produto": fix_product_url(item.product_url),
            "product_url": fix_product_url(item.product_url),
            "url": fix_product_url(item.product_url),

            # Outros campos
            "brand": item.brand,
            "cor": None,
            "color": None,
            "preco": None,
            "price": None,
            "purchase_count": item.purchase_count,
            "quantity": item.total_quantity,
            "total_spent": float(item.total_spent or 0),
            "last_purchase_at": item.last_purchase_at.isoformat() if item.last_purchase_at else None,
        }
        for item in fashion_items
    ]

    # Formata recomendações compatível com frontend VTEX
    recs_payload = [
        {
            "produto_id": r.get("product_id"),
            "sku_id": r.get("sku_id"),
            "ref_id": r.get("ref_id"),
            "nome": r.get("name"),
            "name": r.get("name"),
            "motivo": r.get("reason") or "Selecionado para você",
            "reason": r.get("reason") or "Selecionado para você",
            "score": r.get("score", 0),
            "imagem_url": fix_image_url(r.get("image_url", "")),
            "image_url": fix_image_url(r.get("image_url", "")),
            "link_produto": fix_product_url(r.get("url", "") or r.get("product_url", "")),
            "product_url": fix_product_url(r.get("url", "") or r.get("product_url", "")),
            "categoria": r.get("category"),
            "category": r.get("category"),
            "departamento": r.get("department"),
            "department": r.get("department"),
            "price": r.get("price"),
            "preco": r.get("price"),
        }
        for r in recommendations
    ]

    return {
        "found": len(closet_payload) > 0 or customer is not None,
        "customer": {
            "name": customer_name,
            "email": email,
        },
        "closet": closet_payload,
        "looks": [],
        "recommendations": recs_payload,
        "debug": {
            "email": email,
            "closet_count": len(closet_payload),
            "recommendation_count": len(recs_payload),
            "message": "Closet e recomendações lidos do banco consolidado.",
        },
    }


async def _get_customer(session: AsyncSession, email: str):
    result = await session.execute(
        select(Customer).where(Customer.email == email)
    )
    return result.scalar_one_or_none()


async def _get_customer_closet_items(session: AsyncSession, email: str):
    from models.catalog_product import CatalogProduct
    from sqlalchemy.orm import aliased

    result = await session.execute(
        select(CustomerClosetItem)
        .where(CustomerClosetItem.email == email)
        .order_by(CustomerClosetItem.last_purchase_at.desc().nullslast())
    )
    items = result.scalars().all()

    # Enriquece com imagem/url/category/department do catalog_products quando NULL
    sku_ids_null = [i.sku_id for i in items if i.sku_id and not i.image_url]
    if sku_ids_null:
        cp_result = await session.execute(
            select(
                CatalogProduct.sku_id,
                CatalogProduct.image_url,
                CatalogProduct.product_url,
                CatalogProduct.category,
                CatalogProduct.department,
            ).where(CatalogProduct.sku_id.in_(sku_ids_null))
        )
        cp_map = {row.sku_id: row for row in cp_result.fetchall()}
        for item in items:
            if item.sku_id in cp_map:
                cp = cp_map[item.sku_id]
                if not item.image_url and cp.image_url:
                    item.image_url = cp.image_url
                if not item.product_url and cp.product_url:
                    item.product_url = cp.product_url
                if not item.category and cp.category:
                    item.category = cp.category
                if not item.department and cp.department:
                    item.department = cp.department

    return items
