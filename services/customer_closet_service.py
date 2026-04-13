import json
import os

from services.cache_service import get_cache, set_cache


BASE_PATH = "data_models"


def load_json(file_name):
    path = os.path.join(BASE_PATH, file_name)

    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_email(email):
    return str(email or "").strip().lower()


def get_customer_data(email):
    data = load_json("closet_cliente.json")

    for item in data:
        if normalize_email(item.get("email")) == email:
            return item

    return None


def get_style(email):
    data = load_json("style_preferences.json")

    for item in data:
        if normalize_email(item.get("user_id")) == email:
            return item

    return {}


def get_recommendations(email):
    data = load_json("outfit_recommendation.json")

    return [
        r for r in data
        if normalize_email(r.get("user_id")) == email
    ]


def get_customer_closet(email):
    email = normalize_email(email)
    cache_key = f"closet:{email}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    customer = get_customer_data(email)
    style = get_style(email)
    recommendations = get_recommendations(email)

    closet_products = customer.get("closet_products", []) if customer else []

    response = {
        "customer": {
            "email": email,
            "name": customer.get("name") if customer else "",
            "style": style,
        },
        "closet": closet_products,
        "recommendations": recommendations,
        "meta": {
            "total_skus": len(closet_products),
            "total_recommendations": len(recommendations),
        }
    }

    set_cache(cache_key, response)

    return response