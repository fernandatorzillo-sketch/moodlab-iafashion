import json
import os
import random

BASE_PATH = "data_models"


def load_products():
    path = os.path.join(BASE_PATH, "products_enriched.json")

    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_recommendations(customer):
    products = load_products()

    if not products:
        return []

    return random.sample(products, min(5, len(products)))