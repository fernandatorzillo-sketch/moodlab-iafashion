import json
from pathlib import Path
import requests

def normalize_email(email):
    if not email:
        return None

    email = email.strip().lower()

    # caso VTEX traga sufixo técnico no final
    if ".ct.vtex.com.br" in email:
        if "@hotmail.com-" in email:
            return email.split("@hotmail.com-")[0] + "@hotmail.com"
        if "@gmail.com-" in email:
            return email.split("@gmail.com-")[0] + "@gmail.com"
        if "@terra.com.br-" in email:
            return email.split("@terra.com.br-")[0] + "@terra.com.br"
        if "@outlook.com-" in email:
            return email.split("@outlook.com-")[0] + "@outlook.com"
        if "@uol.com.br-" in email:
            return email.split("@uol.com.br-")[0] + "@uol.com.br"
        if "@icloud.com-" in email:
            return email.split("@icloud.com-")[0] + "@icloud.com"

    return email

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_MODELS_DIR = BASE_DIR / "data_models"


class VtexClient:
    def __init__(self, account_name, environment, app_key, app_token):
        self.base_url = f"https://{account_name}.{environment}.com.br"
        self.headers = {
            "X-VTEX-API-AppKey": app_key,
            "X-VTEX-API-AppToken": app_token,
            "Content-Type": "application/json",
        }

    def get_products_map(self):
        url = f"{self.base_url}/api/catalog_system/pvt/products/GetProductAndSkuIds"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_order_list(self):
        url = f"{self.base_url}/api/oms/pvt/orders"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_order_detail(self, order_id):
        url = f"{self.base_url}/api/oms/pvt/orders/{order_id}"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()


def save_json(filename, data):
    filepath = DATA_MODELS_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sync_products(client):
    raw = client.get_products_map()
    data = raw.get("data", {})

    products_output = []

    for product_id, sku_ids in data.items():
        products_output.append({
            "product_id": int(product_id),
            "sku_ids": sku_ids,
            "empresa_id": 1
        })

    save_json("products.json", products_output)
    print(f"✅ Produtos salvos: {len(products_output)}")


def sync_orders(client):
    raw = client.get_order_list()
    order_list = raw.get("list", [])

    pedidos_output = []
    itens_output = []

    for order in order_list:
        order_id = order.get("orderId")
        if not order_id:
            continue

        detail = client.get_order_detail(order_id)

        client_profile = detail.get("clientProfileData", {}) or {}
        items = detail.get("items", []) or []

        pedidos_output.append({
            "order_id": detail.get("orderId"),
            "creation_date": detail.get("creationDate"),
            "status": detail.get("status"),
            "client_email": normalize_email(client_profile.get("email")),
            "client_name": client_profile.get("firstName"),
            "total_value": detail.get("value"),
            "empresa_id": 1
        })

        for item in items:
            itens_output.append({
                "order_id": detail.get("orderId"),
                "sku_id": item.get("id"),
                "product_id": item.get("productId"),
                "name": item.get("name"),
                "quantity": item.get("quantity"),
                "selling_price": item.get("sellingPrice"),
                "empresa_id": 1
            })

    save_json("pedidos.json", pedidos_output)
    save_json("itens_pedido.json", itens_output)

    print(f"✅ Pedidos salvos: {len(pedidos_output)}")
    print(f"✅ Itens salvos: {len(itens_output)}")


if __name__ == "__main__":
    client = VtexClient(
        account_name="lojaaguadecoco",
        environment="vtexcommercestable",
        app_key="vtexappkey-lojaaguadecoco-PNVBLD",
        app_token="QHSZNPXVZKBDVWPBEIEXMJFDPZNQNHMKBUXNLYBRJNQOMNDTPTHNUCDKMWOKRFEJLUUEHUCAJNAXGPHKXNRASYAKXUIBGJREVNYHCFRLDBKUIUKFPSXZIUJOSMRVWEXP"
    )

    print("🔄 Sincronizando produtos...")
    sync_products(client)

    print("🔄 Sincronizando pedidos...")
    sync_orders(client)

    print("🚀 Sincronização concluída!")