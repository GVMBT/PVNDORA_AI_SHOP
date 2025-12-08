"""Web session utilities (in-memory)."""
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

_web_sessions: Dict[str, dict] = {}


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


def verify_web_session_token(token: str) -> Optional[dict]:
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

