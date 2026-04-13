import os
import time
from typing import Any

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))

_cache: dict[str, dict[str, Any]] = {}


def get_cache(key: str):
    item = _cache.get(key)
    if not item:
        return None

    if time.time() > item["expires_at"]:
        _cache.pop(key, None)
        return None

    return item["value"]


def set_cache(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS):
    _cache[key] = {
        "value": value,
        "expires_at": time.time() + ttl,
    }


def delete_cache(key: str):
    _cache.pop(key, None)