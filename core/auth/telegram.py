"""Telegram Mini App authentication and admin checks."""
import os
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Header, HTTPException, Depends

from src.utils.validators import validate_telegram_init_data, extract_user_from_init_data, TelegramUser
from src.services.database import get_database
from .session import verify_web_session_token

logger = logging.getLogger(__name__)

_telegram_token: Optional[str] = None


def _get_telegram_token() -> str:
    """Get Telegram token (cached)."""
    global _telegram_token
    if _telegram_token is None:
        _telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    return _telegram_token


async def verify_telegram_auth(
    authorization: str = Header(None, alias="Authorization"),
    x_init_data: str = Header(None, alias="X-Init-Data")
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
                    if db_user and db_user.language_code:
                        language_code = db_user.language_code
                except Exception as e:
                    logger.warning(f"Failed to get user language from DB: {e}")
                
                return TelegramUser(
                    id=session["telegram_id"],
                    first_name=session.get("username", "User"),
                    username=session.get("username"),
                    language_code=language_code
                )
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
    
    return user


async def verify_admin(user: TelegramUser = Depends(verify_telegram_auth)):
    """
    Verify that user is an admin (via Telegram initData).
    Returns db_user object if admin.
    """
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    
    if not db_user or not db_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return db_user

