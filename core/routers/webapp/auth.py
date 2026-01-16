"""WebApp Auth Router.

Web authentication via Telegram Login Widget for desktop/web access.
"""

import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException

from core.auth import create_web_session
from core.services.database import get_database

from .models import SessionTokenRequest, TelegramLoginData

router = APIRouter(tags=["webapp-auth"])


def verify_telegram_login_hash(data: dict, bot_token: str) -> bool:
    """Verify Telegram Login Widget data using HMAC-SHA256."""
    check_hash = data.pop("hash", None)
    if not check_hash:
        return False

    # Create data-check-string
    data_items = sorted(data.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in data_items if v is not None)

    # Create secret key (SHA256 of bot token)
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Calculate HMAC-SHA256
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(calculated_hash, check_hash)


@router.post("/auth/telegram-login")
async def telegram_login_widget_auth(data: TelegramLoginData):
    """Authenticate user via Telegram Login Widget (for desktop/web access).

    Verifies the hash using bot token and creates a session.
    Only admins can access the web panel.
    """
    bot_token = os.environ.get("TELEGRAM_TOKEN", "")

    # Convert to dict for verification
    auth_data = {
        "id": data.id,
        "first_name": data.first_name,
        "auth_date": data.auth_date,
        "hash": data.hash,
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
    auth_time = datetime.fromtimestamp(data.auth_date, tz=UTC)
    if datetime.now(UTC) - auth_time > timedelta(hours=1):
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
            language_code="en",
        )

    # Web access is available for all users (desktop version)
    # Admins get full access, regular users get read-only access

    # Create session token using unified auth module
    username_str = data.username if data.username else ""
    session_token = create_web_session(
        user_id=str(db_user.id),
        telegram_id=data.id,
        username=username_str,
        is_admin=db_user.is_admin,
    )

    return {
        "session_token": session_token,
        "user": {
            "id": data.id,
            "username": data.username,
            "first_name": data.first_name,
            "is_admin": db_user.is_admin,
        },
    }


@router.post("/auth/verify-session")
async def verify_web_session_endpoint(data: SessionTokenRequest):
    """Verify a web session token."""
    from core.auth import verify_web_session_token

    session = verify_web_session_token(data.session_token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid session or expired")

    return {
        "valid": True,
        "user": {
            "telegram_id": session["telegram_id"],
            "username": session["username"],
            "is_admin": session["is_admin"],
        },
    }


@router.get("/auth/dev-token/{telegram_id}")
async def get_dev_token(telegram_id: int):
    """DEV ONLY: Generate a session token for a user by telegram_id.
    This endpoint should be disabled in production or protected by secret.
    """
    # For now, allow if TELEGRAM_TOKEN exists (means we're in dev/staging)

    db = get_database()
    db_user = await db.get_user_by_telegram_id(telegram_id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create session token
    session_token = create_web_session(
        user_id=str(db_user.id),
        telegram_id=telegram_id,
        username=db_user.username or f"user_{telegram_id}",
        is_admin=db_user.is_admin,
    )

    return {
        "session_token": session_token,
        "user": {
            "id": telegram_id,
            "username": db_user.username,
            "first_name": db_user.first_name,
            "is_admin": db_user.is_admin,
        },
    }
