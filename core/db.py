"""
Database Module - Supabase and Redis Clients

Provides singleton instances of:
- Async Supabase client for PostgreSQL operations
- Sync Supabase client for non-async contexts
- Upstash Redis client for FSM, carts, leaderboards
"""

import os
from typing import Optional

from supabase import create_client, Client
from supabase._async.client import AsyncClient, create_client as acreate_client
try:
    from upstash_redis import Redis
    from upstash_redis.asyncio import Redis as AsyncRedis
except ImportError:
    # Runtime fallback: allow app to start even if dependency not present
    Redis = None  # type: ignore
    AsyncRedis = None  # type: ignore
    print("WARNING: upstash_redis not installed. Redis cache will be disabled.")


# Environment variables (Upstash uses REST_URL and REST_TOKEN)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# Upstash Redis - standard env var names per docs
UPSTASH_REDIS_REST_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")


# Singleton instances
_supabase_client: Optional[Client] = None
_async_supabase_client: Optional[AsyncClient] = None
_redis_client: Optional[AsyncRedis] = None
_sync_redis_client: Optional[Redis] = None


def get_supabase_sync() -> Client:
    """
    Get synchronous Supabase client (singleton).
    Use for sync contexts only.
    """
    global _supabase_client
    
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    return _supabase_client


async def get_supabase() -> AsyncClient:
    """
    Get async Supabase client (singleton).
    Preferred for all async operations.
    """
    global _async_supabase_client
    
    if _async_supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _async_supabase_client = await acreate_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    return _async_supabase_client


def get_redis() -> AsyncRedis:
    """
    Get async Upstash Redis client (singleton).
    
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
            raise ValueError("UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set")
        if AsyncRedis is None:
            raise ImportError("upstash_redis is not installed in the runtime environment")
        _redis_client = AsyncRedis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
    
    return _redis_client


def get_redis_sync() -> Redis:
    """
    Get sync Upstash Redis client (singleton).
    Use only when async is not available.
    """
    global _sync_redis_client
    
    if _sync_redis_client is None:
        if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
            raise ValueError("UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set")
        if Redis is None:
            raise ImportError("upstash_redis is not installed in the runtime environment")
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
