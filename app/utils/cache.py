"""
Cache abstraction with Redis support and in-memory fallback.
"""
import pickle
import time
from typing import Any, Optional

from app.core.config import get_settings

settings = get_settings()


class InMemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self):
        self._data: dict[str, tuple[Any, Optional[float]]] = {}

    def get(self, key: str) -> Any:
        if key not in self._data:
            return None
        value, expiry = self._data[key]
        if expiry is not None and time.time() > expiry:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expiry = time.time() + ttl if ttl is not None else None
        self._data[key] = (value, expiry)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    async def close(self) -> None:
        pass


class RedisCache:
    """Redis-backed cache using pickle for Python object support."""

    def __init__(self, redis_url: str):
        import redis as redis_lib
        self._client = redis_lib.from_url(redis_url, decode_responses=False)
        self._client.ping()

    def get(self, key: str) -> Any:
        data = self._client.get(key)
        if data is None:
            return None
        return pickle.loads(data)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        data = pickle.dumps(value)
        if ttl is not None:
            self._client.setex(key, ttl, data)
        else:
            self._client.set(key, data)

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def clear(self) -> None:
        self._client.flushdb()

    async def close(self) -> None:
        self._client.close()


class Cache:
    """
    Unified cache interface.
    Uses Redis if REDIS_URL is configured and reachable; otherwise falls back
    to an in-memory dictionary.
    """

    def __init__(self):
        self._backend: Any = InMemoryCache()
        self._backend_name = "in-memory"

        if settings.REDIS_URL:
            try:
                self._backend = RedisCache(settings.REDIS_URL)
                self._backend_name = "redis"
            except Exception as e:
                print(f"Redis cache unavailable ({e}). Using in-memory cache.")
                self._backend = InMemoryCache()
                self._backend_name = "in-memory"

    def get(self, key: str) -> Any:
        return self._backend.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._backend.set(key, value, ttl)

    def delete(self, key: str) -> None:
        self._backend.delete(key)

    def clear(self) -> None:
        self._backend.clear()

    async def close(self) -> None:
        await self._backend.close()

    @property
    def backend_name(self) -> str:
        return self._backend_name


_cache_instance: Optional[Cache] = None


def get_cache() -> Cache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = Cache()
    return _cache_instance
