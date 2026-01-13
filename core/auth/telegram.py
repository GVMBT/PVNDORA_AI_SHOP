"""Telegram Mini App authentication and admin checks."""

import logging
import os

from fastapi import Depends, Header, HTTPException

from core.services.database import get_database
from core.utils.validators import (
    TelegramUser,
    extract_user_from_init_data,
    validate_telegram_init_data,
)

from .session import verify_web_session_token

logger = logging.getLogger(__name__)

_telegram_token: str | None = None


def _get_telegram_token() -> str:
    """Get Telegram token (cached)."""
    global _telegram_token
    if _telegram_token is None:
        _telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    return _telegram_token


async def _get_user_language_from_db(telegram_id: int) -> str:
    """Get user language from DB and cache user (reduces cognitive complexity)."""
    language_code = "en"
    try:
        db = get_database()
        db_user = await db.get_user_by_telegram_id(telegram_id)
        if db_user:
            from .dependencies import _cache_db_user

            _cache_db_user(telegram_id, db_user)
            if db_user.language_code:
                language_code = db_user.language_code
    except Exception as e:
        logger.warning(f"Failed to get user language from DB: {e}")
    return language_code


def _update_user_activity(user_id: int) -> None:
    """Update user activity with debounce (fire-and-forget, reduces cognitive complexity)."""
    try:
        from core.routers.webapp.middleware import update_user_activity_with_debounce

        update_user_activity_with_debounce(user_id)
    except Exception as e:
        logger.debug(f"Failed to schedule activity update: {e}")


async def _verify_bearer_token(session_token: str) -> TelegramUser | None:
    """Verify Bearer token and return user if valid (reduces cognitive complexity)."""
    session = verify_web_session_token(session_token)
    if not session:
        return None

    language_code = await _get_user_language_from_db(session["telegram_id"])

    user = TelegramUser(
        id=session["telegram_id"],
        first_name=session.get("username", "User"),
        username=session.get("username"),
        language_code=language_code,
    )
    _update_user_activity(user.id)
    return user


def _extract_init_data(authorization: str | None, x_init_data: str | None) -> str | None:
    """Extract initData from headers (reduces cognitive complexity)."""
    if x_init_data:
        return x_init_data

    if authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "tma":
            return parts[1]

    return None


# Helper: Try Bearer token authentication (reduces cognitive complexity)
async def _try_bearer_auth(authorization: str, x_init_data: str | None) -> TelegramUser | None:
    """Try to authenticate using Bearer token, return user if successful."""
    if not authorization:
        return None

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    user = await _verify_bearer_token(parts[1])
    if user:
        return user

    # If Bearer token is invalid and no X-Init-Data, raise error
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Invalid session token")

    return None


# Helper: Verify and extract user from initData (reduces cognitive complexity)
async def _verify_and_extract_user_from_init_data(
    init_data: str,
) -> TelegramUser:
    """Verify initData signature and extract user."""
    token = _get_telegram_token()
    if not validate_telegram_init_data(init_data, token):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    extracted_user = extract_user_from_init_data(init_data)
    if not extracted_user:
        raise HTTPException(status_code=401, detail="Could not extract user")

    return extracted_user


# Helper: Update user photo if provided (reduces cognitive complexity)
async def _update_user_photo_if_provided(user: TelegramUser) -> None:
    """Update user's photo URL if provided in initData."""
    if not user.photo_url:
        return

    try:
        db = get_database()
        await db.update_user_photo(user.id, user.photo_url)
    except Exception as e:
        logger.warning(f"Failed to update user photo: {e}")


async def verify_telegram_auth(
    authorization: str = Header(None, alias="Authorization"),
    x_init_data: str = Header(None, alias="X-Init-Data"),
) -> TelegramUser:
    """
    Verify Telegram Mini App authentication (hybrid mode).
    Accepts either:
    - Authorization: Bearer <session_token> (for web login)
    - Authorization: tma <initData> (for Telegram Mini App)
    - X-Init-Data: <initData> (for Telegram Mini App)
    """
    # Try Bearer token first (web session)
    bearer_user = await _try_bearer_auth(authorization, x_init_data)
    if bearer_user:
        return bearer_user

    # Try TMA initData
    init_data = _extract_init_data(authorization, x_init_data)
    if not init_data:
        raise HTTPException(status_code=401, detail="No authorization header")

    extracted_user = await _verify_and_extract_user_from_init_data(init_data)

    # Update user's photo_url if provided
    await _update_user_photo_if_provided(extracted_user)

    _update_user_activity(extracted_user.id)
    return extracted_user


# Helper to get Redis client (reduces cognitive complexity)
def _get_redis_client():
    """Get Redis client, return None if unavailable."""
    try:
        from core.db import get_redis

        return get_redis()
    except (ValueError, ImportError):
        return None


# Helper to check cache (reduces cognitive complexity)
async def _check_admin_cache(redis, cache_key: str, user_id: int):
    """Check Redis cache for admin status, return cached result or None."""
    try:
        cached = await redis.get(cache_key)
        if cached and cached != "0":
            # User is admin (cached)
            return type(
                "AdminUser",
                (),
                {"id": cached, "telegram_id": user_id, "is_admin": True},
            )()
        if cached == "0":
            # User is NOT admin (cached)
            raise HTTPException(status_code=403, detail="Admin access required")
    except HTTPException:
        raise
    except Exception as e:
        logger.debug("Redis cache check failed: %s", e)
    return None


# Helper to cache admin result (reduces cognitive complexity)
async def _cache_admin_result(redis, cache_key: str, is_admin: bool, admin_id: str | None = None):
    """Cache admin verification result."""
    if not redis:
        return
    try:
        value = str(admin_id) if is_admin and admin_id else "0"
        await redis.set(cache_key, value, ex=60)
    except Exception:
        pass


async def verify_admin(user: TelegramUser = Depends(verify_telegram_auth)):
    """
    Verify that user is an admin (via Telegram initData).
    Returns db_user object if admin.

    OPTIMIZATION: Uses Redis cache to avoid duplicate DB queries
    when multiple admin endpoints are called in parallel.
    Cache stores: "0" for non-admin, or UUID for admin.
    Cache TTL: 60 seconds.
    """
    cache_key = f"user:admin:{user.id}"
    redis = _get_redis_client()

    # Check cache first
    if redis:
        cached_result = await _check_admin_cache(redis, cache_key, user.id)
        if cached_result:
            return cached_result

    # Cache miss or error - check DB
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user or not db_user.is_admin:
        await _cache_admin_result(redis, cache_key, False)
        raise HTTPException(status_code=403, detail="Admin access required")

    # Cache positive result
    await _cache_admin_result(redis, cache_key, True, str(db_user.id))
    return db_user
