"""Tests for validators"""
import pytest
import hmac
import hashlib
import urllib.parse
from src.utils.validators import validate_telegram_init_data


def test_validate_telegram_init_data_valid():
    """Test validating valid Telegram initData"""
    # Generate valid initData
    bot_token = "test_bot_token"
    data = "user=%7B%22id%22%3A123456789%7D&auth_date=1234567890"
    
    # Calculate hash
    secret_key = hmac.new(
        "WebAppData".encode(),
        bot_token.encode(),
        hashlib.sha256
    ).digest()
    
    hash_value = hmac.new(
        secret_key,
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    init_data = f"{data}&hash={hash_value}"
    
    result = validate_telegram_init_data(init_data, bot_token)
    
    assert result is not None
    assert result["user"]["id"] == 123456789


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
    data = f"user=%7B%22id%22%3A123456789%7D&auth_date={expired_auth_date}"
    
    secret_key = hmac.new(
        "WebAppData".encode(),
        bot_token.encode(),
        hashlib.sha256
    ).digest()
    
    hash_value = hmac.new(
        secret_key,
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    init_data = f"{data}&hash={hash_value}"
    
    result = validate_telegram_init_data(init_data, bot_token)
    
    # Should still validate but auth_date check should be done by caller
    assert result is not None

