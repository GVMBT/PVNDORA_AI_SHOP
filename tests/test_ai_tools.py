"""Tests for AI tools execution"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.ai.tools import execute_tool, TOOLS


@pytest.fixture
def mock_db():
    """Mock database for tools"""
    db = Mock()
    
    # Mock product
    product = Mock()
    product.id = "product-123"
    product.name = "ChatGPT Plus"
    product.price = 300.0
    product.stock_count = 5
    product.description = "Premium AI"
    product.type = "shared"
    product.warranty_hours = 24
    product.instructions = "Use VPN"
    
    db.get_product_by_id = AsyncMock(return_value=product)
    db.search_products = AsyncMock(return_value=[product])
    db.get_products = AsyncMock(return_value=[product])
    db.get_product_rating = AsyncMock(return_value={"average": 4.5, "count": 10})
    db.add_to_waitlist = AsyncMock()
    db.get_user_orders = AsyncMock(return_value=[])
    db.get_faq = AsyncMock(return_value=[])
    db.validate_promo_code = AsyncMock(return_value={"discount_percent": 20})
    db.get_wishlist = AsyncMock(return_value=[])
    db.get_order_by_id = AsyncMock(return_value=Mock(
        id="order-123",
        user_id="user-123",
        product_id="product-123",
        amount=300.0,
        status="completed",
        refund_requested=False
    ))
    
    # Mock Supabase client operations
    db.client = Mock()
    db.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    db.client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "ticket-123"}]
    db.client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "order-123"}]
    
    return db


@pytest.mark.asyncio
async def test_check_product_availability_found(mock_db):
    """Test checking product availability when found"""
    result = await execute_tool(
        "check_product_availability",
        {"product_name": "ChatGPT"},
        "user-123",
        mock_db
    )
    
    assert result["found"] is True
    assert result["product_id"] == "product-123"
    assert result["in_stock"] is True


@pytest.mark.asyncio
async def test_check_product_availability_not_found(mock_db):
    """Test checking product availability when not found"""
    mock_db.search_products = AsyncMock(return_value=[])
    
    result = await execute_tool(
        "check_product_availability",
        {"product_name": "NonExistent"},
        "user-123",
        mock_db
    )
    
    assert result["found"] is False


@pytest.mark.asyncio
async def test_get_product_details(mock_db):
    """Test getting product details"""
    result = await execute_tool(
        "get_product_details",
        {"product_id": "product-123"},
        "user-123",
        mock_db
    )
    
    assert result["found"] is True
    assert result["name"] == "ChatGPT Plus"
    assert result["price"] == 300.0
    assert result["rating"] == 4.5


@pytest.mark.asyncio
async def test_search_products(mock_db):
    """Test searching products"""
    result = await execute_tool(
        "search_products",
        {"query": "AI assistant"},
        "user-123",
        mock_db
    )
    
    assert result["count"] > 0
    assert len(result["products"]) > 0
    assert result["products"][0]["name"] == "ChatGPT Plus"


@pytest.mark.asyncio
async def test_create_purchase_intent(mock_db):
    """Test creating purchase intent"""
    result = await execute_tool(
        "create_purchase_intent",
        {"product_id": "product-123"},
        "user-123",
        mock_db
    )
    
    assert result["success"] is True
    assert result["product_id"] == "product-123"
    assert result["action"] == "show_payment_button"


@pytest.mark.asyncio
async def test_create_purchase_intent_out_of_stock(mock_db):
    """Test purchase intent when out of stock"""
    mock_db.get_product_by_id = AsyncMock(return_value=Mock(
        id="product-123",
        name="Test",
        stock_count=0
    ))
    
    result = await execute_tool(
        "create_purchase_intent",
        {"product_id": "product-123"},
        "user-123",
        mock_db
    )
    
    assert result["success"] is False
    assert "not available" in result["reason"].lower()


@pytest.mark.asyncio
async def test_add_to_waitlist(mock_db):
    """Test adding to waitlist"""
    result = await execute_tool(
        "add_to_waitlist",
        {"product_name": "ChatGPT Plus"},
        "user-123",
        mock_db
    )
    
    assert result["success"] is True
    mock_db.add_to_waitlist.assert_called_once()


@pytest.mark.asyncio
async def test_add_to_wishlist_new_item(mock_db):
    """Test adding new item to wishlist"""
    # Mock: item doesn't exist
    with patch('asyncio.to_thread') as mock_thread:
        mock_thread.return_value = Mock(data=[])  # First check - not exists
        mock_thread.return_value = Mock(data=[{"id": "wish-123"}])  # Upsert result
        
        result = await execute_tool(
            "add_to_wishlist",
            {"product_id": "product-123"},
            "user-123",
            mock_db
        )
        
        assert result["success"] is True
        assert "Added to wishlist" in result["message"]


@pytest.mark.asyncio
async def test_add_to_wishlist_already_exists(mock_db):
    """Test adding item that already exists to wishlist"""
    with patch('asyncio.to_thread') as mock_thread:
        # Mock: item already exists
        mock_thread.return_value = Mock(data=[{"id": "wish-123"}])
        
        result = await execute_tool(
            "add_to_wishlist",
            {"product_id": "product-123"},
            "user-123",
            mock_db
        )
        
        assert result["success"] is False
        assert "Already in wishlist" in result["reason"]


@pytest.mark.asyncio
async def test_apply_promo_code_valid(mock_db):
    """Test applying valid promo code"""
    result = await execute_tool(
        "apply_promo_code",
        {"code": "TEST20"},
        "user-123",
        mock_db
    )
    
    assert result["valid"] is True
    assert result["discount_percent"] == 20


@pytest.mark.asyncio
async def test_apply_promo_code_invalid(mock_db):
    """Test applying invalid promo code"""
    mock_db.validate_promo_code = AsyncMock(return_value=None)
    
    result = await execute_tool(
        "apply_promo_code",
        {"code": "INVALID"},
        "user-123",
        mock_db
    )
    
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_get_referral_info(mock_db):
    """Test getting referral info"""
    with patch('asyncio.to_thread') as mock_thread:
        mock_thread.side_effect = [
            Mock(data=[{"telegram_id": 123456789, "balance": 100.0, "personal_ref_percent": 20}]),
            Mock(count=5)
        ]
        
        result = await execute_tool(
            "get_referral_info",
            {},
            "user-123",
            mock_db
        )
        
        assert result["success"] is True
        assert "ref_123456789" in result["referral_link"]
        assert result["total_referrals"] == 5


@pytest.mark.asyncio
async def test_get_user_orders(mock_db):
    """Test getting user orders"""
    order = Mock()
    order.id = "order-123"
    order.product_id = "product-123"
    order.amount = 300.0
    order.status = "completed"
    order.created_at = None
    order.expires_at = None
    
    mock_db.get_user_orders = AsyncMock(return_value=[order])
    
    result = await execute_tool(
        "get_user_orders",
        {"limit": 5},
        "user-123",
        mock_db
    )
    
    assert result["count"] == 1
    assert len(result["orders"]) == 1


@pytest.mark.asyncio
async def test_request_refund(mock_db):
    """Test requesting refund"""
    with patch('asyncio.to_thread') as mock_thread:
        mock_thread.side_effect = [
            Mock(data=[{"id": "ticket-123"}]),
            Mock()  # Order update
        ]
        
        result = await execute_tool(
            "request_refund",
            {"order_id": "order-123", "reason": "Not working"},
            "user-123",
            mock_db
        )
        
        assert result["success"] is True
        assert "submitted for review" in result["message"]


@pytest.mark.asyncio
async def test_request_refund_already_requested(mock_db):
    """Test requesting refund when already requested"""
    mock_db.get_order_by_id = AsyncMock(return_value=Mock(
        id="order-123",
        user_id="user-123",
        refund_requested=True
    ))
    
    result = await execute_tool(
        "request_refund",
        {"order_id": "order-123", "reason": "Test"},
        "user-123",
        mock_db
    )
    
    assert result["success"] is False
    assert "already requested" in result["reason"].lower()


@pytest.mark.asyncio
async def test_get_catalog(mock_db):
    """Test getting full catalog"""
    result = await execute_tool(
        "get_catalog",
        {},
        "user-123",
        mock_db
    )
    
    assert result["count"] > 0
    assert len(result["products"]) > 0


@pytest.mark.asyncio
async def test_compare_products(mock_db):
    """Test comparing products"""
    result = await execute_tool(
        "compare_products",
        {"product_names": ["ChatGPT Plus", "Claude Pro"]},
        "user-123",
        mock_db
    )
    
    assert "products" in result
    assert len(result["products"]) > 0


@pytest.mark.asyncio
async def test_create_support_ticket(mock_db):
    """Test creating support ticket"""
    with patch('asyncio.to_thread') as mock_thread:
        mock_thread.return_value = Mock()
        
        result = await execute_tool(
            "create_support_ticket",
            {"issue_description": "Product not working", "order_id": "order-123"},
            "user-123",
            mock_db
        )
        
        assert result["success"] is True
        assert "Support ticket created" in result["message"]

