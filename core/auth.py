"""
Unified Authentication Module

All authentication functions for API endpoints.
Used by both api/index.py and core/routers/*.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING
from fastapi import Header, HTTPException, Depends

if TYPE_CHECKING:
    from src.utils.validators import TelegramUser

# Lazy imports to avoid circular dependencies
_database = None
_telegram_token = None

# In-memory session store for web access
_web_sessions = {}


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


def create_web_session(user_id: str, telegram_id: int, username: str, is_admin: bool) -> str:
    """Create a new web session and return the token."""
    session_token = secrets.token_urlsafe(32)
    _web_sessions[session_token] = {
        "user_id": str(user_id),
        "telegram_id": telegram_id,
        "username": username,
        "is_admin": is_admin,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    }
    return session_token


def verify_web_session_token(token: str) -> dict | None:
    """Verify a web session token and return session data."""
    session = _web_sessions.get(token)
    
    if not session:
        return None
    
    # Check expiration
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        del _web_sessions[token]
        return None
        
    return session


async def verify_telegram_auth(
    authorization: str = Header(None, alias="Authorization"),
    x_init_data: str = Header(None, alias="X-Init-Data")
) -> "TelegramUser":
    """
    Verify Telegram Mini App authentication (hybrid mode).
    Accepts either:
    - Authorization: Bearer <session_token> (for web login)
    - Authorization: tma <initData> (for Telegram Mini App)
    - X-Init-Data: <initData> (for Telegram Mini App)
    
    Returns TelegramUser object (Pydantic model with .id, .first_name, etc.)
    """
    from src.utils.validators import validate_telegram_init_data, extract_user_from_init_data, TelegramUser
    
    # Try Bearer token first (web session)
    if authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            session_token = parts[1]
            session = verify_web_session_token(session_token)
            if session:
                return TelegramUser(
                    id=session["telegram_id"],
                    first_name=session.get("username", "User"),
                    username=session.get("username"),
                    language_code="en"
                )
    
    init_data = None
    
    # Try X-Init-Data header (Telegram Mini App)
    if x_init_data:
        init_data = x_init_data
    # Fallback to Authorization header (Telegram Mini App)
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

