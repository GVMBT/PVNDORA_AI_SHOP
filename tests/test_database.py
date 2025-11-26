"""Tests for database operations"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from src.services.database import Database, User, Product, Order


@pytest.mark.asyncio
async def test_get_user_by_telegram_id(mock_database, sample_user):
    """Test getting user by Telegram ID"""
    # Setup mock
    mock_database.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [sample_user]
    
    user = await mock_database.get_user_by_telegram_id(123456789)
    
    assert user is not None
    assert user.telegram_id == 123456789
    assert user.id == "user-123"


@pytest.mark.asyncio
async def test_get_user_not_found(mock_database):
    """Test getting non-existent user"""
    mock_database.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    user = await mock_database.get_user_by_telegram_id(999999)
    
    assert user is None


@pytest.mark.asyncio
async def test_create_user(mock_database, sample_user):
    """Test creating new user"""
    mock_database.client.table.return_value.insert.return_value.execute.return_value.data = [sample_user]
    
    user = await mock_database.create_user(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        language_code="ru"
    )
    
    assert user.telegram_id == 123456789
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_create_user_with_referrer(mock_database, sample_user):
    """Test creating user with referrer"""
    referrer_data = {**sample_user, "id": "referrer-123", "telegram_id": 987654321}
    
    # Mock referrer lookup
    mock_database.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [referrer_data]
    # Mock user creation
    mock_database.client.table.return_value.insert.return_value.execute.return_value.data = [{**sample_user, "referrer_id": "referrer-123"}]
    
    user = await mock_database.create_user(
        telegram_id=123456789,
        referrer_telegram_id=987654321
    )
    
    assert user.referrer_id == "referrer-123"


@pytest.mark.asyncio
async def test_get_product_by_id(mock_database, sample_product):
    """Test getting product by ID"""
    mock_database.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [sample_product]
    # Mock stock count
    mock_database.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": "stock-1"}, {"id": "stock-2"}]
    
    product = await mock_database.get_product_by_id("product-123")
    
    assert product is not None
    assert product.id == "product-123"
    assert product.name == "ChatGPT Plus"


@pytest.mark.asyncio
async def test_search_products(mock_database, sample_product):
    """Test searching products"""
    mock_database.client.table.return_value.select.return_value.or_.return_value.execute.return_value.data = [sample_product]
    # Mock stock count
    mock_database.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": "stock-1"}]
    
    products = await mock_database.search_products("ChatGPT")
    
    assert len(products) > 0
    assert products[0].name == "ChatGPT Plus"


@pytest.mark.asyncio
async def test_reserve_stock_item(mock_database):
    """Test reserving stock item with race condition handling"""
    # Mock stock item query
    mock_database.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": "stock-123", "is_sold": False}]
    # Mock update
    mock_database.client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "stock-123", "is_sold": True}]
    
    stock_item = await mock_database.reserve_stock_item("product-123")
    
    assert stock_item is not None
    assert stock_item.id == "stock-123"


@pytest.mark.asyncio
async def test_create_order(mock_database, sample_order):
    """Test creating order"""
    mock_database.client.table.return_value.insert.return_value.execute.return_value.data = [sample_order]
    
    order = await mock_database.create_order(
        user_id="user-123",
        product_id="product-123",
        stock_item_id="stock-123",
        amount=300.0
    )
    
    assert order.user_id == "user-123"
    assert order.amount == 300.0


@pytest.mark.asyncio
async def test_add_to_wishlist(mock_database):
    """Test adding to wishlist"""
    mock_database.client.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "wish-123"}]
    
    await mock_database.add_to_wishlist("user-123", "product-123")
    
    # Verify upsert was called
    mock_database.client.table.assert_called()


@pytest.mark.asyncio
async def test_validate_promo_code(mock_database):
    """Test promo code validation"""
    promo_data = {
        "id": "promo-123",
        "code": "TEST20",
        "discount_percent": 20,
        "expires_at": None,
        "usage_limit": None,
        "usage_count": 5,
        "is_active": True
    }
    
    mock_database.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [promo_data]
    
    promo = await mock_database.validate_promo_code("TEST20")
    
    assert promo is not None
    assert promo["discount_percent"] == 20


@pytest.mark.asyncio
async def test_validate_promo_code_expired(mock_database):
    """Test expired promo code"""
    expired_promo = {
        "code": "EXPIRED",
        "expires_at": "2024-01-01T00:00:00Z",
        "is_active": True
    }
    
    mock_database.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [expired_promo]
    
    promo = await mock_database.validate_promo_code("EXPIRED")
    
    assert promo is None  # Should be filtered out by date check


@pytest.mark.asyncio
async def test_get_chat_history(mock_database):
    """Test getting chat history"""
    history_data = [
        {"role": "user", "message": "Hello", "timestamp": "2025-01-01T00:00:00Z"},
        {"role": "assistant", "message": "Hi there!", "timestamp": "2025-01-01T00:01:00Z"}
    ]
    
    mock_database.client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = history_data
    
    history = await mock_database.get_chat_history("user-123", limit=10)
    
    assert len(history) == 2
    assert history[0]["role"] == "user"


@pytest.mark.asyncio
async def test_update_user_balance(mock_database):
    """Test updating user balance"""
    mock_database.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"balance": 100.0}]
    mock_database.client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"balance": 150.0}]
    
    await mock_database.update_user_balance("user-123", 50.0)
    
    # Verify update was called
    mock_database.client.table.assert_called()

