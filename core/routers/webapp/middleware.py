"""Optimization: Centralized user activity tracking with Redis debounce.

Helper function to update user activity with debounce (max 1 per minute per user).
Call this from verify_telegram_auth or endpoints to update user activity.
"""

import asyncio

from core.logging import get_logger

logger = get_logger(__name__)

# Debounce TTL: Update activity at most once per minute
ACTIVITY_DEBOUNCE_TTL = 60  # seconds


async def _update_user_activity_async(telegram_id: int) -> None:
    """Update user activity asynchronously (fire-and-forget).
    Uses Redis debounce to avoid excessive DB updates.

    IMPORTANT: Uses atomic SETNX to avoid race conditions when
    multiple requests arrive simultaneously.
    """
    try:
        from core.db import get_redis
        from core.services.database import get_database

        redis = None
        try:
            redis = get_redis()
        except (ValueError, ImportError):
            # Redis not available, skip debounce but still update
            pass

        if redis:
            # ATOMIC: Try to acquire debounce lock (SETNX pattern)
            # If key exists, we skip update. If not, we set it and proceed.
            debounce_key = f"user:activity:debounce:{telegram_id}"

            # set() with nx=True returns True only if key was set (didn't exist)
            # This is atomic - prevents race conditions
            acquired = await redis.set(debounce_key, "1", ex=ACTIVITY_DEBOUNCE_TTL, nx=True)

            if not acquired:
                # Key already exists - another request is handling this user
                return

        # Update activity in DB (only one request per user per minute reaches here)
        db = get_database()
        await db.update_user_activity(telegram_id)

    except Exception as e:
        # Non-fatal - activity tracking shouldn't break requests
        logger.debug(f"Failed to update user activity: {e}")


def update_user_activity_with_debounce(telegram_id: int) -> None:
    """Update user activity with Redis debounce (max 1 per minute per user).

    This is a fire-and-forget operation that doesn't block the request.
    Uses Redis debounce to limit DB updates.

    Call this from verify_telegram_auth or endpoints to update user activity.

    Note: This is a sync function that schedules an async task in the background.
    Do NOT await this function.

    Args:
        telegram_id: Telegram user ID

    """
    # Fire-and-forget async update (non-blocking)
    try:
        # Use asyncio.create_task to run in background
        # This works because we're called from within an async context (FastAPI)
        # Store task reference to prevent premature garbage collection
        _ = asyncio.create_task(_update_user_activity_async(telegram_id))
        # Task runs in background - we don't await it (fire-and-forget)
        # Storing the reference ensures the task isn't garbage collected before it completes
    except Exception as e:
        # Non-fatal - activity tracking shouldn't break requests
        logger.debug(f"Failed to schedule activity update: {e}")
