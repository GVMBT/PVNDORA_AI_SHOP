"""
Optimization: Centralized user activity tracking with Redis debounce.

Helper function to update user activity with debounce (max 1 per minute per user).
Call this from verify_telegram_auth or endpoints to update user activity.
"""
import asyncio
from core.logging import get_logger

logger = get_logger(__name__)

# Debounce TTL: Update activity at most once per minute
ACTIVITY_DEBOUNCE_TTL = 60  # seconds


async def _update_user_activity_async(telegram_id: int) -> None:
    """
    Update user activity asynchronously (fire-and-forget).
    Uses Redis debounce to avoid excessive DB updates.
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
            # Check if we've updated recently (debounce)
            debounce_key = f"user:activity:debounce:{telegram_id}"
            is_recently_updated = await redis.get(debounce_key)
            
            if is_recently_updated:
                # Already updated recently, skip
                return
        
        # Update activity in DB
        db = get_database()
        await db.update_user_activity(telegram_id)
        
        # Set debounce flag
        if redis:
            await redis.set(debounce_key, "1", ex=ACTIVITY_DEBOUNCE_TTL)
        
    except Exception as e:
        # Non-fatal - activity tracking shouldn't break requests
        logger.debug(f"Failed to update user activity: {e}")


def update_user_activity_with_debounce(telegram_id: int) -> None:
    """
    Update user activity with Redis debounce (max 1 per minute per user).
    
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
        asyncio.create_task(_update_user_activity_async(telegram_id))
    except Exception as e:
        # Non-fatal - activity tracking shouldn't break requests
        logger.debug(f"Failed to schedule activity update: {e}")
