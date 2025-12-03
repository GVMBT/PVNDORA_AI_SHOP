"""
Unified Authentication Module

All authentication functions for API endpoints.
Used by both api/index.py and core/routers/*.
"""

import os
from typing import TYPE_CHECKING
from fastapi import Header, HTTPException, Depends

if TYPE_CHECKING:
    from src.utils.validators import TelegramUser

# Lazy imports to avoid circular dependencies
_database = None
_telegram_token = None


def _get_database():
    """Lazy load database to avoid import issues"""
    global _database
    if _database is None:
        from src.services.database import get_database
        _database = get_database()
    return _database


def _get_telegram_token():
    """Get Telegram token (cached)"""
    global _telegram_token
    if _telegram_token is None:
        _telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    return _telegram_token


async def verify_telegram_auth(
    authorization: str = Header(None, alias="Authorization"),
    x_init_data: str = Header(None, alias="X-Init-Data")
) -> "TelegramUser":
    """
    Verify Telegram Mini App authentication.
    Accepts either:
    - Authorization: tma <initData>
    - X-Init-Data: <initData>
    
    Returns TelegramUser object (Pydantic model with .id, .first_name, etc.)
    """
    from src.utils.validators import validate_telegram_init_data, extract_user_from_init_data, TelegramUser
    
    init_data = None
    
    # Try X-Init-Data header first (frontend sends this)
    if x_init_data:
        init_data = x_init_data
    # Fallback to Authorization header
    elif authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "tma":
            init_data = parts[1]
        else:
            init_data = authorization  # Try raw value
    
    if not init_data:
        raise HTTPException(status_code=401, detail="No authorization header")
    
    # For development/testing - allow bypass with special token
    if init_data == "dev_bypass" and os.environ.get("DEBUG") == "true":
        return TelegramUser(id=339469894, first_name="Test", language_code="ru")
    
    token = _get_telegram_token()
    if not validate_telegram_init_data(init_data, token):
        raise HTTPException(status_code=401, detail="Invalid initData signature")
    
    user = extract_user_from_init_data(init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Could not extract user")
    
    return user


async def verify_admin(user: "TelegramUser" = Depends(verify_telegram_auth)):
    """
    Verify that user is an admin (via Telegram initData).
    
    Use for Mini App admin endpoints.
    Returns db_user object if admin.
    """
    db = _get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    
    if not db_user or not db_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return db_user


async def verify_cron_secret(
    authorization: str = Header(None, alias="Authorization")
):
    """
    Verify CRON_SECRET for scheduled jobs and internal workers.
    
    Use for cron endpoints and QStash workers.
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    
    if not cron_secret:
        raise HTTPException(status_code=500, detail="CRON_SECRET not configured")
    
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid CRON_SECRET")
    
    return True


# Type aliases for FastAPI Depends
AdminUser = object   # Database user object with is_admin=True

