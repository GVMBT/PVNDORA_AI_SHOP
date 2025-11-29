"""
Tests for Pydantic models
"""

import pytest
from core.models import (
    AIResponse,
    ActionType,
    CartItemResponse,
    OrderStatus,
    OrderType,
    IntentType
)


class TestAIResponse:
    """Tests for AIResponse model."""
    
    def test_valid_response(self):
        """Test creating a valid AI response."""
        response = AIResponse(
            thought="User wants to buy ChatGPT",
            reply_text="I can help you with ChatGPT Plus!",
            action=ActionType.OFFER_PAYMENT,
            product_id="123e4567-e89b-12d3-a456-426614174000"
        )
        
        assert response.thought == "User wants to buy ChatGPT"
        assert response.action == ActionType.OFFER_PAYMENT
        assert response.requires_validation is False
    
    def test_default_action(self):
        """Test default action is NONE."""
        response = AIResponse(
            thought="General query",
            reply_text="Hello!"
        )
        
        assert response.action == ActionType.NONE
    
    def test_cart_items(self):
        """Test response with cart items."""
        cart_item = CartItemResponse(
            product_id="123",
            product_name="ChatGPT Plus",
            quantity=1,
            instant_quantity=1,
            prepaid_quantity=0,
            unit_price=299.0,
            discount_percent=10
        )
        
        response = AIResponse(
            thought="Adding to cart",
            reply_text="Added to cart!",
            action=ActionType.ADD_TO_CART,
            cart_items=[cart_item]
        )
        
        assert len(response.cart_items) == 1
        assert response.cart_items[0].product_name == "ChatGPT Plus"


class TestOrderModels:
    """Tests for order-related models."""
    
    def test_order_status_values(self):
        """Test order status enum values."""
        assert OrderStatus.PENDING == "pending"
        assert OrderStatus.DELIVERED == "delivered"
        assert OrderStatus.REFUNDED == "refunded"
    
    def test_order_type_values(self):
        """Test order type enum values."""
        assert OrderType.INSTANT == "instant"
        assert OrderType.PREPAID == "prepaid"


class TestIntentType:
    """Tests for intent classification."""
    
    def test_intent_types(self):
        """Test all intent types exist."""
        assert IntentType.DISCOVERY == "discovery"
        assert IntentType.PURCHASE == "purchase"
        assert IntentType.SUPPORT == "support"
        assert IntentType.COMPARISON == "comparison"
        assert IntentType.FAQ == "faq"


class TestCartItemResponse:
    """Tests for cart item model."""
    
    def test_valid_cart_item(self):
        """Test valid cart item creation."""
        item = CartItemResponse(
            product_id="abc-123",
            product_name="Test Product",
            quantity=2,
            instant_quantity=1,
            prepaid_quantity=1,
            unit_price=100.0
        )
        
        assert item.quantity == 2
        assert item.instant_quantity + item.prepaid_quantity == 2
    
    def test_cart_item_discount(self):
        """Test cart item with discount."""
        item = CartItemResponse(
            product_id="abc-123",
            product_name="Test Product",
            quantity=1,
            instant_quantity=1,
            prepaid_quantity=0,
            unit_price=100.0,
            discount_percent=20
        )
        
        assert item.discount_percent == 20
    
    def test_invalid_quantity(self):
        """Test that quantity must be positive."""
        with pytest.raises(ValueError):
            CartItemResponse(
                product_id="abc-123",
                product_name="Test",
                quantity=0,
                instant_quantity=0,
                prepaid_quantity=0,
                unit_price=100.0
            )

