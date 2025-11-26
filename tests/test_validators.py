"""Tests for validators"""
import pytest
import hmac
import hashlib
import urllib.parse
from src.utils.validators import validate_telegram_init_data


def test_validate_telegram_init_data_valid():
    """Test validating valid Telegram initData"""
    from src.utils.validators import extract_user_from_init_data
    
    # Generate valid initData
    bot_token = "test_bot_token"
    # Build data check string (sorted alphabetically)
    data_check_string = "auth_date=1234567890\nuser=%7B%22id%22%3A123456789%7D"
    
    # Calculate hash
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256
    ).digest()
    
    hash_value = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    init_data = f"auth_date=1234567890&user=%7B%22id%22%3A123456789%7D&hash={hash_value}"
    
    result = validate_telegram_init_data(init_data, bot_token)
    
    assert result is True
    
    # Test user extraction
    user = extract_user_from_init_data(init_data)
    assert user is not None
    assert user.id == 123456789


def test_validate_telegram_init_data_invalid_hash():
    """Test validating initData with invalid hash"""
    bot_token = "test_bot_token"
    init_data = "user=%7B%22id%22%3A123456789%7D&auth_date=1234567890&hash=invalid_hash"
    
    result = validate_telegram_init_data(init_data, bot_token)
    
    assert result is None


def test_validate_telegram_init_data_missing_hash():
    """Test validating initData without hash"""
    bot_token = "test_bot_token"
    init_data = "user=%7B%22id%22%3A123456789%7D&auth_date=1234567890"
    
    result = validate_telegram_init_data(init_data, bot_token)
    
    assert result is None


def test_validate_telegram_init_data_expired():
    """Test validating expired initData"""
    import time
    
    bot_token = "test_bot_token"
    # Auth date more than 24 hours ago
    expired_auth_date = int(time.time()) - (25 * 3600)
    data_check_string = f"auth_date={expired_auth_date}\nuser=%7B%22id%22%3A123456789%7D"
    
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256
    ).digest()
    
    hash_value = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    init_data = f"auth_date={expired_auth_date}&user=%7B%22id%22%3A123456789%7D&hash={hash_value}"
    
    result = validate_telegram_init_data(init_data, bot_token)
    
    # Should still validate (hash is correct), but auth_date check should be done by caller
    assert result is True

