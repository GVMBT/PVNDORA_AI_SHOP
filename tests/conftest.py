"""Pytest configuration and fixtures"""
import os
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Generator

# Set test environment variables
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test_key")
os.environ.setdefault("TELEGRAM_TOKEN", "test_token")
os.environ.setdefault("GEMINI_API_KEY", "test_gemini_key")
os.environ.setdefault("ADMIN_API_KEY", "test_admin_key")
os.environ.setdefault("CRON_SECRET", "test_cron_secret")


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    client = Mock()
    
    # Mock table operations
    table_mock = Mock()
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.or_.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.gte.return_value = table_mock
    table_mock.lte.return_value = table_mock
    table_mock.lt.return_value = table_mock
    table_mock.ilike.return_value = table_mock
    
    client.table.return_value = table_mock
    client.rpc.return_value = table_mock
    
    return client


@pytest.fixture
def mock_database(mock_supabase_client):
    """Mock database instance"""
    from src.services.database import Database
    
    db = Database()
    db.client = mock_supabase_client
    return db


@pytest.fixture
def sample_user():
    """Sample user data"""
    return {
        "id": "user-123",
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "language_code": "ru",
        "balance": 0.0,
        "referrer_id": None,
        "personal_ref_percent": 20,
        "is_admin": False,
        "is_banned": False,
        "warnings_count": 0,
        "do_not_disturb": False,
        "last_activity_at": "2025-01-01T00:00:00Z",
        "created_at": "2025-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_product():
    """Sample product data"""
    return {
        "id": "product-123",
        "name": "ChatGPT Plus",
        "description": "Premium AI assistant",
        "price": 300.0,
        "type": "shared",
        "status": "active",
        "warranty_hours": 24,
        "instructions": "Use VPN",
        "terms": "No refunds",
        "supplier_id": None,
        "stock_count": 5
    }


@pytest.fixture
def sample_order():
    """Sample order data"""
    return {
        "id": "order-123",
        "user_id": "user-123",
        "product_id": "product-123",
        "stock_item_id": "stock-123",
        "amount": 300.0,
        "original_price": 300.0,
        "discount_percent": 0,
        "status": "completed",
        "payment_method": "aaio",
        "expires_at": None,
        "delivered_at": "2025-01-01T00:00:00Z",
        "refund_requested": False,
        "created_at": "2025-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_bot():
    """Mock Telegram bot"""
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=Mock(username="test_bot"))
    bot.send_message = AsyncMock()
    bot.send_chat_action = AsyncMock()
    bot.get_file = AsyncMock()
    bot.download_file = AsyncMock()
    return bot


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini AI client"""
    client = Mock()
    
    # Mock response
    mock_response = Mock()
    mock_response.text = "Test response"
    mock_response.candidates = [Mock()]
    mock_response.candidates[0].content = Mock()
    mock_response.candidates[0].content.parts = []
    
    client.models.generate_content = AsyncMock(return_value=mock_response)
    
    return client

