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
    if authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            session_token = parts[1]
            session = verify_web_session_token(session_token)
            if session:
                # Get user language from database
                language_code = "en"
                try:
                    db = get_database()
                    db_user = await db.get_user_by_telegram_id(session["telegram_id"])
                    if db_user:
                        # OPTIMIZATION: Cache db_user in ContextVar to avoid duplicate queries
                        # Cache db_user for this request (lazy import to avoid circular dependency)
                        from .dependencies import _cache_db_user

                        _cache_db_user(session["telegram_id"], db_user)
                        if db_user.language_code:
                            language_code = db_user.language_code
                except Exception as e:
                    logger.warning(f"Failed to get user language from DB: {e}")

                user = TelegramUser(
                    id=session["telegram_id"],
                    first_name=session.get("username", "User"),
                    username=session.get("username"),
                    language_code=language_code,
                )

                # Update user activity with debounce (fire-and-forget, non-blocking)
                try:
                    from core.routers.webapp.middleware import update_user_activity_with_debounce

                    update_user_activity_with_debounce(user.id)
                except Exception as e:
                    # Non-fatal - activity tracking shouldn't break authentication
                    logger.debug(f"Failed to schedule activity update: {e}")

                return user
            # If Bearer token is invalid and no X-Init-Data, raise error
            if not x_init_data:
                raise HTTPException(status_code=401, detail="Invalid session token")

    init_data = None

    # Try X-Init-Data header (Telegram Mini App)
    if x_init_data:
        init_data = x_init_data
    # Fallback to Authorization header (Telegram Mini App) - only if not Bearer
    elif authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "tma":
            init_data = parts[1]
        # Don't try raw authorization as initData - it will fail validation

    if not init_data:
        raise HTTPException(status_code=401, detail="No authorization header")

    token = _get_telegram_token()
    if not validate_telegram_init_data(init_data, token):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    user = extract_user_from_init_data(init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Could not extract user")

    # Update user's photo_url if provided
    if user.photo_url:
        try:
            db = get_database()
            await db.update_user_photo(user.id, user.photo_url)
        except Exception as e:
            logger.warning(f"Failed to update user photo: {e}")

    # Update user activity with debounce (fire-and-forget, non-blocking)
    try:
        from core.routers.webapp.middleware import update_user_activity_with_debounce

        update_user_activity_with_debounce(user.id)
    except Exception as e:
        # Non-fatal - activity tracking shouldn't break authentication
        logger.debug(f"Failed to schedule activity update: {e}")

    return user


async def verify_admin(user: TelegramUser = Depends(verify_telegram_auth)):
    """
    Verify that user is an admin (via Telegram initData).
    Returns db_user object if admin.

    OPTIMIZATION: Uses Redis cache to avoid duplicate DB queries
    when multiple admin endpoints are called in parallel.
    Cache stores: "0" for non-admin, or UUID for admin.
    Cache TTL: 60 seconds.
    """
    from core.db import get_redis

    redis = None
    cache_key = f"user:admin:{user.id}"

    try:
        redis = get_redis()
        # Check Redis cache first (TTL 60s)
        # Cache value: "0" = not admin, UUID string = admin with that user ID
        cached = await redis.get(cache_key)
        if cached and cached != "0":
            # User is admin (cached) - return object with UUID from cache
            # Some endpoints use admin.id for logging
            return type(
                "AdminUser",
                (),
                {"id": cached, "telegram_id": user.id, "is_admin": True},  # UUID stored in cache
            )()
        if cached == "0":
            # User is NOT admin (cached) - raise immediately, don't fall through
            raise HTTPException(status_code=403, detail="Admin access required")
    except HTTPException:
        # Re-raise HTTP exceptions (including cached denials)
        raise
    except (ValueError, ImportError):
        # Redis not available - fall through to DB check
        pass
    except Exception as e:
        # Only Redis errors - log and fall through to DB check
        logger.debug(f"Redis cache check failed: {e}")

    # Cache miss or error - check DB
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user or not db_user.is_admin:
        # Cache negative result
        if redis:
            try:
                await redis.set(cache_key, "0", ex=60)
            except Exception:
                pass
        raise HTTPException(status_code=403, detail="Admin access required")

    # Cache positive result (store UUID for endpoints that need admin.id)
    if redis:
        try:
            await redis.set(cache_key, str(db_user.id), ex=60)
        except Exception:
            pass

    return db_user
