"""
WebApp Auth Router

Web authentication via Telegram Login Widget for desktop/web access.
"""
import os
import hmac
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException

from src.services.database import get_database
from .models import TelegramLoginData, SessionTokenRequest

router = APIRouter(tags=["webapp-auth"])

# Session tokens for web login (in-memory for simplicity, use Redis in production)
_web_sessions = {}


def verify_telegram_login_hash(data: dict, bot_token: str) -> bool:
    """Verify Telegram Login Widget data using HMAC-SHA256."""
    check_hash = data.pop('hash', None)
    if not check_hash:
        return False
    
    # Create data-check-string
    data_items = sorted(data.items())
    data_check_string = '\n'.join(f"{k}={v}" for k, v in data_items if v is not None)
    
    # Create secret key (SHA256 of bot token)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    # Calculate HMAC-SHA256
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated_hash, check_hash)


@router.post("/auth/telegram-login")
async def telegram_login_widget_auth(data: TelegramLoginData):
    """
    Authenticate user via Telegram Login Widget (for desktop/web access).
    
    Verifies the hash using bot token and creates a session.
    Only admins can access the web panel.
    """
    bot_token = os.environ.get("TELEGRAM_TOKEN", "")
    
    # Convert to dict for verification
    auth_data = {
        "id": data.id,
        "first_name": data.first_name,
        "auth_date": data.auth_date,
        "hash": data.hash
    }
    if data.last_name:
        auth_data["last_name"] = data.last_name
    if data.username:
        auth_data["username"] = data.username
    if data.photo_url:
        auth_data["photo_url"] = data.photo_url
    
    # Verify hash
    if not verify_telegram_login_hash(auth_data.copy(), bot_token):
        raise HTTPException(status_code=401, detail="Invalid authentication data")
    
    # Check auth_date (not older than 1 hour)
    auth_time = datetime.fromtimestamp(data.auth_date, tz=timezone.utc)
    if datetime.now(timezone.utc) - auth_time > timedelta(hours=1):
        raise HTTPException(status_code=401, detail="Authentication data expired")
    
    # Get or create user
    db = get_database()
    db_user = await db.get_user_by_telegram_id(data.id)
    
    if not db_user:
        # Create new user
        db_user = await db.create_user(
            telegram_id=data.id,
            username=data.username,
            first_name=data.first_name,
            language_code="en"
        )
    
    # Check if admin (required for web access)
    if not db_user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Web access is only available for administrators. Please use the Telegram Mini App."
        )
    
    # Create session token
    session_token = secrets.token_urlsafe(32)
    _web_sessions[session_token] = {
        "user_id": str(db_user.id),
        "telegram_id": data.id,
        "username": data.username,
        "is_admin": db_user.is_admin,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    }
    
    return {
        "session_token": session_token,
        "user": {
            "id": data.id,
            "username": data.username,
            "first_name": data.first_name,
            "is_admin": db_user.is_admin
        }
    }


@router.post("/auth/verify-session")
async def verify_web_session(data: SessionTokenRequest):
    """Verify a web session token."""
    session = _web_sessions.get(data.session_token)
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiration
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        del _web_sessions[data.session_token]
        raise HTTPException(status_code=401, detail="Session expired")
    
    return {
        "valid": True,
        "user": {
            "telegram_id": session["telegram_id"],
            "username": session["username"],
            "is_admin": session["is_admin"]
        }
    }
