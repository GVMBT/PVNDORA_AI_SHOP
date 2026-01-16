"""Database Module - Supabase and Redis Clients.

This module provides:
- Redis client for FSM, carts, leaderboards
- Re-exports from core.services.database for Supabase access

For Supabase access, use:
    from core.services.database import get_database, init_database

For Redis access:
    from core.db import get_redis
"""

import os
import warnings
from typing import TYPE_CHECKING, Any

# Re-export Supabase access from unified database module
from core.services.database import (
    close_database,
    get_database,
    get_database_async,
    init_database,
    is_database_initialized,
)

__all__ = [
    "TTL",
    "RedisKeys",
    "close_database",
    # Supabase
    "get_database",
    "get_database_async",
    # Redis
    "get_redis",
    "get_redis_sync",
    "init_database",
    "is_database_initialized",
]

# For type-checkers only
if TYPE_CHECKING:  # pragma: no cover
    from upstash_redis import Redis as RedisType
    from upstash_redis.asyncio import Redis as AsyncRedisType
else:
    RedisType = object
    AsyncRedisType = object

try:
    from upstash_redis import Redis
    from upstash_redis.asyncio import Redis as AsyncRedis
except ImportError:
    # Runtime fallback: lightweight REST client (get/set/delete) for Upstash
    Redis = None  # type: ignore
    AsyncRedis = None  # type: ignore
    warnings.warn(
        "upstash_redis not installed. Falling back to lightweight REST client.",
        ImportWarning,
        stacklevel=2,
    )
    import httpx

    class AsyncRedisFallback:
        """Minimal async Redis client using Upstash REST (get/set/delete only)."""

        def __init__(self, url: str, token: str) -> None:
            self.url = url.rstrip("/")
            self.token = token
            self._client: httpx.AsyncClient | None = None

        @property
        def client(self) -> httpx.AsyncClient:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    base_url=self.url,
                    headers={"Authorization": f"Bearer {self.token}"},
                )
            return self._client

        async def get(self, key: str) -> Any:
            resp = await self.client.get(f"/get/{key}")
            resp.raise_for_status()
            data = resp.json()
            return data.get("result")

        async def set(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> bool:
            """SET key value with optional EX (expiration) and NX (only if not exists).

            Returns:
                True if key was set, False if NX was True and key already exists

            """
            params: dict[str, Any] = {}
            if ex is not None:
                params["EX"] = ex
            if nx:
                params["NX"] = ""  # Upstash REST API: NX without value
            resp = await self.client.post(f"/set/{key}/{value}", params=params)
            resp.raise_for_status()
            result = resp.json().get("result")
            # NX returns None if key exists, "OK" if set
            if nx:
                return bool(result == "OK")
            return True

        async def setex(self, key: str, seconds: int, value: str) -> bool:
            """SET with expiration in seconds."""
            return await self.set(key, value, ex=seconds)

        async def delete(self, key: str) -> bool:
            # Upstash REST API requires POST for DEL command, not HTTP DELETE
            resp = await self.client.post(f"/del/{key}")
            resp.raise_for_status()
            return True

    # Use fallback for both sync/async interfaces
    AsyncRedis = AsyncRedisFallback  # type: ignore
    Redis = AsyncRedisFallback  # type: ignore


# Upstash Redis - standard env var names per docs
UPSTASH_REDIS_REST_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")


# Redis singleton instances
_redis_client: AsyncRedis | None = None
_sync_redis_client: Redis | None = None


def get_redis() -> AsyncRedis:
    """Get async Upstash Redis client (singleton).

    Uses standard Upstash env var names:
    - UPSTASH_REDIS_REST_URL
    - UPSTASH_REDIS_REST_TOKEN

    Used for:
    - FSM storage (aiogram)
    - Cart management
    - Leaderboards (sorted sets)
    - Rate limiting
    - Currency cache
    """
    global _redis_client

    if _redis_client is None:
        if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
            msg = "UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set"
            raise ValueError(msg)
        if AsyncRedis is None:
            msg = "upstash_redis is not installed in the runtime environment"
            raise ImportError(msg)
        _redis_client = AsyncRedis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)

    return _redis_client


def get_redis_sync() -> Redis:
    """Get sync Upstash Redis client (singleton).
    Use only when async is not available.
    """
    global _sync_redis_client

    if _sync_redis_client is None:
        if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
            msg = "UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set"
            raise ValueError(msg)
        if Redis is None:
            msg = "upstash_redis is not installed in the runtime environment"
            raise ImportError(msg)
        _sync_redis_client = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)

    return _sync_redis_client


# Redis key prefixes for organization
class RedisKeys:
    """Redis key prefixes for different data types."""

    # Cart storage
    CART = "cart:"  # cart:{user_telegram_id}

    # FSM storage (aiogram)
    FSM_STATE = "fsm:state:"  # fsm:state:{user_id}:{chat_id}
    FSM_DATA = "fsm:data:"  # fsm:data:{user_id}:{chat_id}

    # Leaderboard
    LEADERBOARD_SAVINGS = "leaderboard:savings"  # Sorted set

    # Rate limiting for notifications
    USER_NOTIFICATION = "notify:"  # notify:{user_id}:{type}

    # Currency cache
    CURRENCY_RATES = "currency:rates"  # Hash with rates

    # Session/temp data
    TEMP = "temp:"  # temp:{key}

    @staticmethod
    def cart_key(user_telegram_id: int) -> str:
        return f"{RedisKeys.CART}{user_telegram_id}"

    @staticmethod
    def notification_key(user_id: int, notification_type: str) -> str:
        return f"{RedisKeys.USER_NOTIFICATION}{user_id}:{notification_type}"


# TTL constants (in seconds)
class TTL:
    """Time-to-live constants for Redis keys."""

    CART = 86400  # 24 hours
    CURRENCY_CACHE = 3600  # 1 hour
    TEMP_DATA = 900  # 15 minutes
    RATE_LIMIT_REENGAGEMENT = 259200  # 72 hours
