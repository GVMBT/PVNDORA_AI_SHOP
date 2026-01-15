"""FastAPI Dependencies for User Context.

Provides cached db_user dependency to avoid duplicate DB queries
within the same request context.
"""

from contextvars import ContextVar

from fastapi import Depends, HTTPException

from core.auth.telegram import TelegramUser, verify_telegram_auth
from core.services.database import get_database
from core.services.models import User

# Context variable for caching db_user within a single request
_db_user_cache: ContextVar[dict[int, User] | None] = ContextVar("_db_user_cache", default=None)


def _get_db_user_cache() -> dict[int, User]:
    """Get or create db_user cache dict for current context."""
    cache = _db_user_cache.get()
    if cache is None:
        cache = {}
        _db_user_cache.set(cache)
    return cache


def _cache_db_user(telegram_id: int, db_user: User) -> None:
    """Cache db_user in current context (internal function for verify_telegram_auth)."""
    cache = _get_db_user_cache()
    cache[telegram_id] = db_user


async def get_db_user(user: TelegramUser = Depends(verify_telegram_auth)) -> User:
    """Get db_user from database with request-scoped caching.

    OPTIMIZATION: Caches db_user in ContextVar to avoid duplicate DB queries
    when multiple dependencies need db_user in the same request.

    Usage:
        @router.get("/profile")
        async def get_profile(db_user: User = Depends(get_db_user)):
            # Use db_user directly, no additional DB query needed
            ...
    """
    cache = _get_db_user_cache()

    # Check cache first
    if user.id in cache:
        return cache[user.id]

    # Fetch from DB
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Cache for this request
    cache[user.id] = db_user

    return db_user
