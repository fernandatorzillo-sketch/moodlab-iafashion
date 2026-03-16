"""Price scraper service — extracts current price from product URLs.

Strategy (in order):
1. JSON-LD structured data (schema.org Product)
2. Open Graph meta tags (og:price:amount, product:price:amount)
3. Meta tag "price" / "twitter:data1"
4. Regex fallback for common price patterns (R$ X.XXX,XX)
"""
import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 15.0

# Common user-agent to avoid bot blocking
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _parse_price_string(raw: str) -> Optional[float]:
    """Normalize a price string like 'R$ 389,90' or '389.90' to float."""
    if not raw:
        return None
    # Remove currency symbols, spaces, non-breaking spaces
    cleaned = re.sub(r"[R$€£¥\s\u00a0]", "", raw.strip())
    if not cleaned:
        return None
    # Brazilian format: 1.234,56 → 1234.56
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        value = float(cleaned)
        return value if value > 0 else None
    except (ValueError, TypeError):
        return None


def _extract_json_ld_price(html: str) -> Optional[float]:
    """Extract price from JSON-LD structured data."""
    import json as json_mod
    pattern = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
    for match in pattern.finditer(html):
        try:
            data = json_mod.loads(match.group(1))
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    # Direct Product
                    if item.get("@type") in ("Product", "IndividualProduct"):
                        offers = item.get("offers", {})
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        price = offers.get("price") or offers.get("lowPrice")
                        if price is not None:
                            return _parse_price_string(str(price))
                    # @graph array
                    if "@graph" in item:
                        for node in item["@graph"]:
                            if isinstance(node, dict) and node.get("@type") in ("Product", "IndividualProduct"):
                                offers = node.get("offers", {})
                                if isinstance(offers, list):
                                    offers = offers[0] if offers else {}
                                price = offers.get("price") or offers.get("lowPrice")
                                if price is not None:
                                    return _parse_price_string(str(price))
        except Exception:
            continue
    return None


def _extract_meta_price(html: str) -> Optional[float]:
    """Extract price from meta tags (og:price, product:price, etc.)."""
    meta_patterns = [
        r'<meta[^>]*property=["\'](?:og:price:amount|product:price:amount)["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\'](?:og:price:amount|product:price:amount)["\']',
        r'<meta[^>]*name=["\'](?:price|twitter:data1)["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\'](?:price|twitter:data1)["\']',
    ]
    for pattern in meta_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            price = _parse_price_string(match.group(1))
            if price is not None:
                return price
    return None


def _extract_regex_price(html: str) -> Optional[float]:
    """Fallback: find price patterns like R$ 389,90 in HTML."""
    # Look for R$ followed by a number
    patterns = [
        r'R\$\s*([\d.,]+)',
        r'"price"\s*:\s*"?([\d.,]+)"?',
        r'"preco"\s*:\s*"?([\d.,]+)"?',
        r'data-price=["\']?([\d.,]+)',
        r'class=["\'][^"\']*price[^"\']*["\'][^>]*>\s*R?\$?\s*([\d.,]+)',
    ]
    prices = []
    for pattern in patterns:
        for match in re.finditer(pattern, html, re.IGNORECASE):
            price = _parse_price_string(match.group(1))
            if price and 1.0 < price < 100000.0:  # reasonable price range
                prices.append(price)
    if prices:
        # Return the most common price (mode)
        from collections import Counter
        counter = Counter(prices)
        return counter.most_common(1)[0][0]
    return None


async def fetch_price_from_url(url: str) -> Tuple[Optional[float], str]:
    """
    Fetch the current price from a product URL.

    Returns:
        Tuple of (price or None, source description)
    """
    if not url or not url.startswith(("http://", "https://")):
        return None, "URL inválida"

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return None, "URL inválida"
    except Exception:
        return None, "URL inválida"

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers=HEADERS,
        ) as http_client:
            response = await http_client.get(url)
            response.raise_for_status()
            html = response.text

        # Strategy 1: JSON-LD
        price = _extract_json_ld_price(html)
        if price is not None:
            return price, "json-ld"

        # Strategy 2: Meta tags
        price = _extract_meta_price(html)
        if price is not None:
            return price, "meta-tag"

        # Strategy 3: Regex fallback
        price = _extract_regex_price(html)
        if price is not None:
            return price, "regex"

        return None, "Preço não encontrado na página"

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching price from {url}")
        return None, "Timeout ao acessar a página"
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error {e.response.status_code} fetching {url}")
        return None, f"Erro HTTP {e.response.status_code}"
    except Exception as e:
        logger.error(f"Error fetching price from {url}: {e}")
        return None, f"Erro: {str(e)}"