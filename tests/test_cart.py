"""
Tests for Cart Manager
"""

import pytest
from datetime import datetime
from core.cart import CartItem, Cart, CartManager


class TestCartItem:
    """Tests for CartItem dataclass."""
    
    def test_create_cart_item(self):
        """Test creating a cart item."""
        item = CartItem(
            product_id="prod-123",
            product_name="ChatGPT Plus",
            quantity=2,
            instant_quantity=1,
            prepaid_quantity=1,
            unit_price=299.0,
            discount_percent=10.0
        )
        
        assert item.product_id == "prod-123"
        assert item.quantity == 2
        assert item.added_at != ""
    
    def test_final_price_calculation(self):
        """Test final price after discount."""
        item = CartItem(
            product_id="prod-123",
            product_name="Test",
            quantity=1,
            instant_quantity=1,
            prepaid_quantity=0,
            unit_price=100.0,
            discount_percent=20.0
        )
        
        assert item.final_price == 80.0
    
    def test_total_price_calculation(self):
        """Test total price for quantity."""
        item = CartItem(
            product_id="prod-123",
            product_name="Test",
            quantity=3,
            instant_quantity=2,
            prepaid_quantity=1,
            unit_price=100.0,
            discount_percent=10.0
        )
        
        # 100 * 0.9 * 3 = 270
        assert item.total_price == 270.0
    
    def test_to_dict(self):
        """Test serialization to dict."""
        item = CartItem(
            product_id="prod-123",
            product_name="Test",
            quantity=1,
            instant_quantity=1,
            prepaid_quantity=0,
            unit_price=100.0
        )
        
        data = item.to_dict()
        assert data["product_id"] == "prod-123"
        assert "added_at" in data
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "product_id": "prod-123",
            "product_name": "Test",
            "quantity": 1,
            "instant_quantity": 1,
            "prepaid_quantity": 0,
            "unit_price": 100.0,
            "discount_percent": 0.0,
            "added_at": "2024-01-01T00:00:00"
        }
        
        item = CartItem.from_dict(data)
        assert item.product_id == "prod-123"


class TestCart:
    """Tests for Cart dataclass."""
    
    def test_create_empty_cart(self):
        """Test creating an empty cart."""
        cart = Cart(user_telegram_id=123456, items=[])
        
        assert cart.user_telegram_id == 123456
        assert cart.total_items == 0
        assert cart.total == 0
    
    def test_cart_with_items(self):
        """Test cart with multiple items."""
        items = [
            CartItem(
                product_id="prod-1",
                product_name="Product 1",
                quantity=2,
                instant_quantity=2,
                prepaid_quantity=0,
                unit_price=100.0
            ),
            CartItem(
                product_id="prod-2",
                product_name="Product 2",
                quantity=1,
                instant_quantity=0,
                prepaid_quantity=1,
                unit_price=200.0
            )
        ]
        
        cart = Cart(user_telegram_id=123456, items=items)
        
        assert cart.total_items == 3
        assert cart.subtotal == 400.0  # 200 + 200
        assert cart.instant_total == 200.0  # 2 * 100
        assert cart.prepaid_total == 200.0  # 1 * 200
    
    def test_cart_with_promo(self):
        """Test cart with promo code."""
        items = [
            CartItem(
                product_id="prod-1",
                product_name="Product 1",
                quantity=1,
                instant_quantity=1,
                prepaid_quantity=0,
                unit_price=100.0
            )
        ]
        
        cart = Cart(
            user_telegram_id=123456,
            items=items,
            promo_code="SAVE10",
            promo_discount_percent=10.0
        )
        
        assert cart.subtotal == 100.0
        assert cart.total == 90.0  # 10% off
    
    def test_cart_serialization(self):
        """Test cart serialization and deserialization."""
        items = [
            CartItem(
                product_id="prod-1",
                product_name="Test",
                quantity=1,
                instant_quantity=1,
                prepaid_quantity=0,
                unit_price=100.0
            )
        ]
        
        cart = Cart(user_telegram_id=123456, items=items)
        data = cart.to_dict()
        
        restored = Cart.from_dict(data)
        
        assert restored.user_telegram_id == 123456
        assert len(restored.items) == 1
        assert restored.items[0].product_id == "prod-1"

