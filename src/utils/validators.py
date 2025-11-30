"""Telegram WebApp initData Validation"""
import hmac
import hashlib
import json
from urllib.parse import parse_qs, unquote
from typing import Optional
from pydantic import BaseModel


class TelegramUser(BaseModel):
    """Telegram user data from initData"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = "en"
    is_premium: Optional[bool] = False


def validate_telegram_init_data(init_data: str, bot_token: str) -> bool:
    """
    Validate Telegram Mini App initData using HMAC-SHA256.
    
    Args:
        init_data: The initData string from Telegram WebApp
        bot_token: The bot token for HMAC verification
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parsed = parse_qs(init_data)
        
        # Extract hash
        received_hash = parsed.pop('hash', [None])[0]
        if not received_hash:
            return False
        
        # Build data check string (sorted alphabetically)
        data_check_parts = []
        for key in sorted(parsed.keys()):
            value = parsed[key][0]
            data_check_parts.append(f"{key}={value}")
        
        data_check_string = '\n'.join(data_check_parts)
        
        # Calculate secret key: HMAC-SHA256(bot_token, "WebAppData")
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(calculated_hash, received_hash)
    except Exception:
        return False


def extract_user_from_init_data(init_data: str) -> Optional[TelegramUser]:
    """
    Extract user information from validated initData.
    
    Args:
        init_data: The initData string from Telegram WebApp
        
    Returns:
        TelegramUser object or None if parsing fails
    """
    try:
        parsed = parse_qs(init_data)
        user_json = parsed.get('user', [None])[0]
        
        if not user_json:
            return None
        
        user_data = json.loads(unquote(user_json))
        return TelegramUser(**user_data)
    except Exception:
        return None


def get_init_data_param(init_data: str, param: str) -> Optional[str]:
    """
    Get a specific parameter from initData.
    
    Args:
        init_data: The initData string
        param: Parameter name to extract
        
    Returns:
        Parameter value or None
    """
    try:
        parsed = parse_qs(init_data)
        return parsed.get(param, [None])[0]
    except Exception:
        return None

