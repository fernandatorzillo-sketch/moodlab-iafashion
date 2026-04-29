from sqlalchemy import text

from services.closet_db import AsyncSessionLocal
from services.look_engine import build_looks
from services.recommendation_service import get_customer_recommendations

SITE_BASE = "https://www.aguadecoco.com.br"


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def build_email_like(email: str) -> str:
    return f"{normalize_email(email)}%"


def safe_url(url: str | None) -> str | None:
    if not url:
        return None

    url = str(url).strip()

    if url.startswith("http"):
        return url

    if url.startswith("/"):
        return f"{SITE_BASE}{url}"

    return f"{SITE_BASE}/{url}"


def slugify(value: str | None) -> str:
    value = str(value or "").strip().lower()

    replacements = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "õ": "o", "ô": "o",
        "ú": "u",
        "ç": "c",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    chars = []
    for char in value:
        if char.isalnum():
            chars.append(char)
        elif char in [" ", "-", "_", "/"]:
            chars.append("-")

    slug = "".join(chars)

    while "--" in slug:
        slug = slug.replace("--", "-")

    return slug.strip("-")


def build_product_url(name: str | None, product_id: str | None, url: str | None) -> str:
    fixed = safe_url(url)
    if fixed:
        return fixed

    if name:
        slug = slugify(name)
        if slug:
            return f"{SITE_BASE}/{slug}/p"

    if product_id:
        return f"{SITE_BASE}/busca?fq=productId:{product_id}"

    return SITE_BASE


def infer_product_type(name: str | None) -> str | None:
    text = str(name or "").strip().lower()

    if any(x in text for x in ["biquini", "biquíni", "sutiã", "sutia", "calcinha"]):
        return "biquini"

    if any(x in text for x in ["maiô", "maio"]):
        return "maio"

    if "vestido" in text:
        return "vestido"

    if any(x in text for x in ["saída", "saida", "pareô", "pareo"]):
        return "saida"

    if any(x in text for x in ["short", "calça", "calca", "pantalona", "saia"]):
        return "bottom"

    if any(x in text for x in ["camisa", "camiseta", "blusa", "top", "cropped"]):
        return "top"

    if any(x in text for x in ["bolsa", "sandália", "sandalia", "chapéu", "chapeu"]):
        return "acessorio"

    return None


def infer_department(name: str | None, category: str | None) -> str | None:
    text = f"{name or ''} {category or ''}".lower()

    home_terms = [
        "bandeja",
        "copo",
        "taça",
        "taca",
        "vaso",
        "prato",
        "guardanapo",
        "mesa",
        "home",
        "casa",
    ]

    if any(term in text for term in home_terms):
        return "casa"

    return "feminino"


async def get_customer_closet_payload(email: str) -> dict:
    email = normalize_email(email)
    email_like = build_email_like(email)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    oi.sku_id,
                    MAX(oi.product_id) AS product_id,
                    MAX(oi.ref_id) AS ref_id,
                    MAX(oi.name) AS name,

                    MAX(COALESCE(oi.category, cp_by_product.category, cp_by_sku.category)) AS category,
                    MAX(COALESCE(oi.department, cp_by_product.department, cp_by_sku.department)) AS department,
                    MAX(COALESCE(oi.brand, cp_by_product.brand, cp_by_sku.brand)) AS brand,

                    MAX(COALESCE(oi.image_url, cp_by_product.image_url, cp_by_sku.image_url)) AS image_url,
                    MAX(COALESCE(oi.product_url, cp_by_product.product_url, cp_by_sku.product_url)) AS product_url,

                    MAX(COALESCE(cp_by_product.product_type, cp_by_sku.product_type)) AS product_type,
                    MAX(COALESCE(cp_by_product.occasion, cp_by_sku.occasion)) AS occasion,
                    MAX(COALESCE(cp_by_product.print_name, cp_by_sku.print_name)) AS estamparia,
                    MAX(COALESCE(cp_by_product.color, cp_by_sku.color)) AS color,
                    MAX(COALESCE(cp_by_product.size, cp_by_sku.size)) AS size,
                    MAX(COALESCE(cp_by_product.collection, cp_by_sku.collection)) AS collection,

                    COUNT(DISTINCT oi.order_id) AS purchase_count,
                    COALESCE(SUM(oi.quantity), 0) AS quantity,
                    COALESCE(SUM(oi.total_value), 0) AS total_spent,
                    MAX(o.creation_date) AS last_purchase_at

                FROM order_items oi

                LEFT JOIN orders o
                    ON o.order_id = oi.order_id

                LEFT JOIN catalog_products cp_by_product
                    ON cp_by_product.product_id = oi.product_id

                LEFT JOIN catalog_products cp_by_sku
                    ON cp_by_sku.sku_id = oi.sku_id

                WHERE
                    LOWER(oi.email) LIKE LOWER(:email_like)
                    AND COALESCE(LOWER(o.status), '') NOT IN ('canceled', 'cancelado')

                GROUP BY
                    oi.sku_id

                ORDER BY
                    MAX(o.creation_date) DESC NULLS LAST
                """
            ),
            {"email_like": email_like},
        )

        rows = result.mappings().all()

    closet_payload = []

    for row in rows:
        name = row.get("name")
        product_id = row.get("product_id")

        category = row.get("category") or infer_product_type(name)
        product_type = row.get("product_type") or infer_product_type(name)
        department = row.get("department") or infer_department(name, category)

        image_url = row.get("image_url") or ""

        product_url = build_product_url(
            name=name,
            product_id=product_id,
            url=row.get("product_url"),
        )

        closet_payload.append(
            {
                "id": product_id or row.get("sku_id"),
                "sku": row.get("sku_id"),
                "sku_id": row.get("sku_id"),
                "product_id": product_id,
                "produto_id": product_id,
                "ref_id": row.get("ref_id"),

                "nome": name,
                "name": name,

                "categoria": category,
                "category": category,

                "departamento": department,
                "department": department,

                "brand": row.get("brand"),

                "tipo_produto": product_type,
                "product_type": product_type,

                "occasion": row.get("occasion"),
                "ocasiao": row.get("occasion"),

                "estamparia": row.get("estamparia"),

                "cor": row.get("color"),
                "color": row.get("color"),

                "tamanho": row.get("size"),
                "size": row.get("size"),

                "colecao": row.get("collection"),
                "collection": row.get("collection"),

                "imagem_url": image_url,
                "image_url": image_url,

                "link_produto": product_url,
                "product_url": product_url,
                "url": product_url,

                "purchase_count": int(row.get("purchase_count") or 0),
                "quantity": int(row.get("quantity") or 0),
                "total_spent": float(row.get("total_spent") or 0),
                "last_purchase_at": (
                    row.get("last_purchase_at").isoformat()
                    if row.get("last_purchase_at")
                    else None
                ),
            }
        )

    looks = build_looks(closet_payload)

    recommendations = await get_customer_recommendations(
        email=email_like,
        limit=12,
    )

    return {
        "found": len(closet_payload) > 0,
        "customer": {
            "name": email.split("@")[0],
            "email": email,
        },
        "cliente": {
            "nome": email.split("@")[0],
            "email": email,
        },
        "closet": closet_payload,
        "closet_products": closet_payload,
        "looks": looks,
        "recommendations": recommendations,
        "debug": {
            "email_original": email,
            "email_like": email_like,
            "closet_count": len(closet_payload),
            "looks_count": len(looks),
            "recommendation_count": len(recommendations),
            "source": "order_items + orders + catalog_products by product_id and sku_id",
        },
    }