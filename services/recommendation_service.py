from services.catalog_service import get_full_catalog


def normalize(value):
    return str(value or "").strip().lower()


def extract_category(name):
    name = normalize(name)

    if "biquini" in name:
        return "biquini"
    if "maio" in name:
        return "maio"
    if "vestido" in name:
        return "vestido"
    if "short" in name:
        return "short"
    if "saia" in name:
        return "saia"
    if "blusa" in name or "top" in name:
        return "top"

    return "outros"


def extract_color(name):
    name = normalize(name)

    cores = ["preto", "branco", "off white", "verde", "azul", "rosa"]

    for cor in cores:
        if cor in name:
            return cor

    return "neutro"


def build_profile(closet):
    categories = []
    colors = []

    for item in closet:
        name = item.get("nome") or item.get("name")

        cat = extract_category(name)
        color = extract_color(name)

        categories.append(cat)
        colors.append(color)

    return {
        "categories": list(set(categories)),
        "colors": list(set(colors)),
    }


async def get_customer_recommendations(email: str, limit=12, **kwargs):
    from services.customer_closet_service import get_customer_closet_payload

    data = await get_customer_closet_payload(email)

    closet = data.get("closet", [])

    if not closet:
        return []

    profile = build_profile(closet)

    catalog = await get_full_catalog()

    results = []

    for product in catalog:
        name = product.get("name")

        product_cat = extract_category(name)
        product_color = extract_color(name)

        score = 0

        if product_cat in profile["categories"]:
            score += 2

        if product_color in profile["colors"]:
            score += 1

        if score >= 2:
            results.append({
                "product_id": product.get("product_id"),
                "name": name,
                "image_url": product.get("image_url"),
                "product_url": product.get("product_url"),
                "score": score,
                "reason": "Combina com seu estilo e compras anteriores",
            })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return results[:limit]