import requests


class VtexClient:
    def __init__(self, account_name, environment, app_key, app_token):
        self.base_url = f"https://{account_name}.{environment}.com.br"
        self.headers = {
            "X-VTEX-API-AppKey": app_key,
            "X-VTEX-API-AppToken": app_token,
            "Content-Type": "application/json",
        }

    def get_orders(self):
        url = f"{self.base_url}/api/oms/pvt/orders"
        response = requests.get(url, headers=self.headers, timeout=30)
        return {
            "url": url,
            "status_code": response.status_code,
            "body": response.text,
        }

    def get_products(self):
        url = f"{self.base_url}/api/catalog_system/pvt/products/GetProductAndSkuIds"
        response = requests.get(url, headers=self.headers, timeout=30)
        return {
            "url": url,
            "status_code": response.status_code,
            "body": response.text,
        }