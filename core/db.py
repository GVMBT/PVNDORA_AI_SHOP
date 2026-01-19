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

        async def publish(self, channel: str, message: str) -> int:
            """Publish message to Redis channel (Pub/Sub).

            Args:
                channel: Channel name
                message: Message to publish

            Returns:
                Number of subscribers that received the message
            """
            # Upstash REST API: POST /publish/{channel} with body
            resp = await self.client.post(
                f"/publish/{channel}",
                content=message,
                headers={"Content-Type": "text/plain"},
            )
            resp.raise_for_status()
            result = resp.json().get("result", 0)
            return int(result) if result else 0

        async def xadd(
            self, stream_key: str, entry_id: str, fields: dict[str, str]
        ) -> str:
            """Add entry to Redis Stream (XADD command).

            Args:
                stream_key: Stream key name
                entry_id: Entry ID ("*" for auto-generate)
                fields: Dictionary of field-value pairs

            Returns:
                Entry ID

            Note: Signature matches upstash-redis library: xadd(name, id, data)
            """
            # Upstash REST API: POST /xadd/{stream_key}/{id} with fields as body
            # Format: {"field1": "value1", "field2": "value2"}
            resp = await self.client.post(
                f"/xadd/{stream_key}/{entry_id}",
                json=fields,
            )
            resp.raise_for_status()
            result = resp.json().get("result", "")
            return str(result) if result else entry_id

        async def xrange(
            self,
            stream_key: str,
            start: str = "-",
            end: str = "+",
            count: int | None = None,
        ) -> list[tuple[str, dict[str, str]]]:
            """Read entries from Redis Stream using XRANGE.

            Args:
                stream_key: Stream key name
                start: Start entry ID (use "-" for earliest, "(id" for exclusive)
                end: End entry ID (use "+" for latest)
                count: Maximum number of entries to return

            Returns:
                List of (entry_id, {field: value, ...}) tuples

            Note: Signature matches upstash-redis library (start/end instead of min/max)
            """
            # Build command parts for Upstash REST API
            # Format: /xrange/{key}/{start}/{end}[/COUNT/{count}]
            url = f"/xrange/{stream_key}/{start}/{end}"
            if count is not None:
                url += f"/COUNT/{count}"

            resp = await self.client.get(url)
            resp.raise_for_status()
            result = resp.json().get("result", [])

            # Parse result: [[entry_id, [field1, value1, ...]], ...]
            parsed: list[tuple[str, dict[str, str]]] = []
            if isinstance(result, list):
                for entry in result:
                    if isinstance(entry, list) and len(entry) >= 2:
                        entry_id = str(entry[0])
                        fields_list = entry[1] if isinstance(entry[1], list) else []
                        fields_dict: dict[str, str] = {}
                        # Convert [field1, value1, field2, value2, ...] to dict
                        for i in range(0, len(fields_list) - 1, 2):
                            fields_dict[str(fields_list[i])] = str(fields_list[i + 1])
                        parsed.append((entry_id, fields_dict))
            return parsed

        async def xread(
            self,
            streams: dict[str, str],
            count: int | None = None,
            block: int | None = None,
        ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
            """Read entries from Redis Streams (XREAD command).

            Args:
                streams: Dictionary mapping stream keys to entry IDs (e.g., {"stream1": "0"})
                count: Maximum number of entries per stream
                block: Block time in milliseconds (0 for non-blocking)

            Returns:
                List of (stream_key, [(entry_id, {field: value, ...}), ...]) tuples
            """
            # Upstash REST API: POST /xread with streams, count, block
            params: dict[str, Any] = {"streams": streams}
            if count is not None:
                params["count"] = count
            if block is not None:
                params["block"] = block

            resp = await self.client.post("/xread", json=params)
            resp.raise_for_status()
            result = resp.json().get("result", [])
            return self._parse_xread_result(result)

        def _parse_xread_result(
            self, result: Any
        ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
            """Parse XREAD result into structured format (reduces cognitive complexity).

            Args:
                result: Raw result from Redis XREAD

            Returns:
                List of (stream_key, [(entry_id, {field: value, ...}), ...]) tuples
            """
            parsed: list[tuple[str, list[tuple[str, dict[str, str]]]]] = []
            if not isinstance(result, list):
                return parsed

            for stream_data in result:
                if not isinstance(stream_data, list) or len(stream_data) < 2:
                    continue

                stream_key = str(stream_data[0])
                entries_raw = stream_data[1] if isinstance(stream_data[1], list) else []
                entries = self._parse_stream_entries(entries_raw)
                parsed.append((stream_key, entries))

            return parsed

        def _parse_stream_entries(
            self, entries_raw: list[Any]
        ) -> list[tuple[str, dict[str, str]]]:
            """Parse stream entries (reduces cognitive complexity).

            Args:
                entries_raw: Raw entries list from stream

            Returns:
                List of (entry_id, fields_dict) tuples
            """
            entries: list[tuple[str, dict[str, str]]] = []
            for entry_raw in entries_raw:
                if not isinstance(entry_raw, list) or len(entry_raw) < 2:
                    continue

                entry_id = str(entry_raw[0])
                fields_raw = entry_raw[1] if isinstance(entry_raw[1], list) else []
                fields = self._parse_entry_fields(fields_raw)
                entries.append((entry_id, fields))

            return entries

        def _parse_entry_fields(self, fields_raw: list[Any]) -> dict[str, str]:
            """Parse entry fields from [field, value, ...] to {field: value, ...}.

            Args:
                fields_raw: Raw fields list [field1, value1, field2, value2, ...]

            Returns:
                Dictionary mapping field names to values
            """
            fields: dict[str, str] = {}
            for i in range(0, len(fields_raw) - 1, 2):
                fields[str(fields_raw[i])] = str(fields_raw[i + 1])
            return fields

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
