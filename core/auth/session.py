"""Web session utilities (stateless, HMAC-signed)."""

import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any


def _get_secret() -> str:
    # Dedicated secret if present, otherwise fall back to TELEGRAM_TOKEN
    return os.environ.get("WEB_SESSION_SECRET") or os.environ.get("TELEGRAM_TOKEN", "")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_web_session(user_id: str, telegram_id: int, username: str, is_admin: bool) -> str:
    """
    Create a stateless HMAC-signed session token.
    Structure: base64url(payload).base64url(signature)
    """
    secret = _get_secret()
    if not secret:
        raise RuntimeError("WEB_SESSION_SECRET or TELEGRAM_TOKEN is required for web sessions")

    now = datetime.now(UTC)
    payload = {
        "user_id": str(user_id),
        "telegram_id": telegram_id,
        "username": username,
        "is_admin": is_admin,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=7)).timestamp()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{payload_b64}.{sig_b64}"


def verify_web_session_token(token: str) -> dict[str, Any] | None:
    """Verify HMAC-signed session token and return payload if valid and not expired."""
    secret = _get_secret()
    if not secret or not token or "." not in token:
        return None

    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected_sig = hmac.new(
            secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected_sig, _b64url_decode(sig_b64)):
            return None

        payload = json.loads(_b64url_decode(payload_b64))
        if not isinstance(payload, dict):
            return None
        exp_ts = payload.get("exp")
        if not exp_ts:
            return None
        if datetime.now(UTC).timestamp() > float(exp_ts):
            return None
        return payload
    except Exception:
        return None
