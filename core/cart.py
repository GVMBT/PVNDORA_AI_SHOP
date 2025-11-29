"""
Cart Manager - Redis-based Shopping Cart

Manages shopping carts in Redis with:
- Auto-split for instant vs prepaid items
- TTL of 24 hours
- CRUD operations
"""

import json
from typing import Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

from core.db import get_redis, RedisKeys, TTL


@dataclass
class CartItem:
    """Single item in the cart."""
    product_id: str
    product_name: str
    quantity: int
    instant_quantity: int  # Available in stock
    prepaid_quantity: int  # Needs to be ordered
    unit_price: float
    discount_percent: float = 0.0
    added_at: str = ""
    
    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.utcnow().isoformat()
    
    @property
    def final_price(self) -> float:
        """Calculate price after discount."""
        return self.unit_price * (1 - self.discount_percent / 100)
    
    @property
    def total_price(self) -> float:
        """Total price for all units."""
        return self.final_price * self.quantity
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "CartItem":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Cart:
    """Shopping cart containing multiple items."""
    user_telegram_id: int
    items: List[CartItem]
    promo_code: Optional[str] = None
    promo_discount_percent: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        now = datetime.utcnow().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
    
    @property
    def total_items(self) -> int:
        """Total number of items in cart."""
        return sum(item.quantity for item in self.items)
    
    @property
    def instant_total(self) -> float:
        """Total for items available instantly."""
        return sum(item.final_price * item.instant_quantity for item in self.items)
    
    @property
    def prepaid_total(self) -> float:
        """Total for items that need to be ordered."""
        return sum(item.final_price * item.prepaid_quantity for item in self.items)
    
    @property
    def subtotal(self) -> float:
        """Subtotal before promo code."""
        return sum(item.total_price for item in self.items)
    
    @property
    def total(self) -> float:
        """Final total after promo code discount."""
        if self.promo_discount_percent > 0:
            return self.subtotal * (1 - self.promo_discount_percent / 100)
        return self.subtotal
    
    def to_dict(self) -> dict:
        """Convert to dictionary for Redis storage."""
        return {
            "user_telegram_id": self.user_telegram_id,
            "items": [item.to_dict() for item in self.items],
            "promo_code": self.promo_code,
            "promo_discount_percent": self.promo_discount_percent,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Cart":
        """Create from dictionary."""
        items = [CartItem.from_dict(item) for item in data.get("items", [])]
        return cls(
            user_telegram_id=data["user_telegram_id"],
            items=items,
            promo_code=data.get("promo_code"),
            promo_discount_percent=data.get("promo_discount_percent", 0.0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )


class CartManager:
    """
    Manages shopping carts in Redis.
    
    Features:
    - Auto-split items into instant (in stock) vs prepaid (on demand)
    - 24-hour TTL for abandoned carts
    - Promo code support
    
    Usage:
        manager = CartManager()
        cart = await manager.get_cart(user_telegram_id)
        await manager.add_item(user_telegram_id, item)
        await manager.clear_cart(user_telegram_id)
    """
    
    def __init__(self):
        self.redis = get_redis()
    
    async def get_cart(self, user_telegram_id: int) -> Optional[Cart]:
        """
        Get user's cart from Redis.
        
        Args:
            user_telegram_id: Telegram user ID
        
        Returns:
            Cart object or None if empty
        """
        key = RedisKeys.cart_key(user_telegram_id)
        data = await self.redis.get(key)
        
        if not data:
            return None
        
        return Cart.from_dict(json.loads(data))
    
    async def save_cart(self, cart: Cart) -> bool:
        """
        Save cart to Redis with TTL.
        
        Args:
            cart: Cart object to save
        
        Returns:
            True if saved successfully
        """
        key = RedisKeys.cart_key(cart.user_telegram_id)
        cart.updated_at = datetime.utcnow().isoformat()
        
        await self.redis.set(
            key,
            json.dumps(cart.to_dict()),
            ex=TTL.CART
        )
        return True
    
    async def add_item(
        self,
        user_telegram_id: int,
        product_id: str,
        product_name: str,
        quantity: int,
        available_stock: int,
        unit_price: float,
        discount_percent: float = 0.0
    ) -> Cart:
        """
        Add item to cart with auto-split for instant vs prepaid.
        
        Args:
            user_telegram_id: Telegram user ID
            product_id: Product UUID
            product_name: Product name for display
            quantity: Requested quantity
            available_stock: Currently available in stock
            unit_price: Price per unit
            discount_percent: Discount percentage
        
        Returns:
            Updated cart
        """
        cart = await self.get_cart(user_telegram_id)
        
        if cart is None:
            cart = Cart(user_telegram_id=user_telegram_id, items=[])
        
        # Calculate split
        instant_qty = min(quantity, available_stock)
        prepaid_qty = max(0, quantity - available_stock)
        
        # Check if product already in cart
        existing_item = next(
            (item for item in cart.items if item.product_id == product_id),
            None
        )
        
        if existing_item:
            # Update existing item
            existing_item.quantity += quantity
            existing_item.instant_quantity = min(
                existing_item.quantity,
                available_stock
            )
            existing_item.prepaid_quantity = max(
                0,
                existing_item.quantity - available_stock
            )
            existing_item.discount_percent = discount_percent
        else:
            # Add new item
            item = CartItem(
                product_id=product_id,
                product_name=product_name,
                quantity=quantity,
                instant_quantity=instant_qty,
                prepaid_quantity=prepaid_qty,
                unit_price=unit_price,
                discount_percent=discount_percent
            )
            cart.items.append(item)
        
        await self.save_cart(cart)
        return cart
    
    async def update_item_quantity(
        self,
        user_telegram_id: int,
        product_id: str,
        new_quantity: int,
        available_stock: int
    ) -> Optional[Cart]:
        """
        Update item quantity in cart.
        
        Args:
            user_telegram_id: Telegram user ID
            product_id: Product to update
            new_quantity: New quantity (0 to remove)
            available_stock: Currently available
        
        Returns:
            Updated cart or None if cart doesn't exist
        """
        cart = await self.get_cart(user_telegram_id)
        
        if cart is None:
            return None
        
        if new_quantity <= 0:
            # Remove item
            cart.items = [
                item for item in cart.items 
                if item.product_id != product_id
            ]
        else:
            # Update quantity
            for item in cart.items:
                if item.product_id == product_id:
                    item.quantity = new_quantity
                    item.instant_quantity = min(new_quantity, available_stock)
                    item.prepaid_quantity = max(0, new_quantity - available_stock)
                    break
        
        if cart.items:
            await self.save_cart(cart)
        else:
            await self.clear_cart(user_telegram_id)
        
        return cart
    
    async def remove_item(
        self,
        user_telegram_id: int,
        product_id: str
    ) -> Optional[Cart]:
        """
        Remove item from cart.
        
        Args:
            user_telegram_id: Telegram user ID
            product_id: Product to remove
        
        Returns:
            Updated cart or None
        """
        return await self.update_item_quantity(
            user_telegram_id, product_id, 0, 0
        )
    
    async def apply_promo_code(
        self,
        user_telegram_id: int,
        promo_code: str,
        discount_percent: float
    ) -> Optional[Cart]:
        """
        Apply promo code to cart.
        
        Args:
            user_telegram_id: Telegram user ID
            promo_code: Promo code string
            discount_percent: Discount percentage
        
        Returns:
            Updated cart or None
        """
        cart = await self.get_cart(user_telegram_id)
        
        if cart is None:
            return None
        
        cart.promo_code = promo_code
        cart.promo_discount_percent = discount_percent
        
        await self.save_cart(cart)
        return cart
    
    async def remove_promo_code(self, user_telegram_id: int) -> Optional[Cart]:
        """Remove promo code from cart."""
        cart = await self.get_cart(user_telegram_id)
        
        if cart is None:
            return None
        
        cart.promo_code = None
        cart.promo_discount_percent = 0.0
        
        await self.save_cart(cart)
        return cart
    
    async def clear_cart(self, user_telegram_id: int) -> bool:
        """
        Clear user's cart.
        
        Args:
            user_telegram_id: Telegram user ID
        
        Returns:
            True if cleared
        """
        key = RedisKeys.cart_key(user_telegram_id)
        await self.redis.delete(key)
        return True
    
    async def get_cart_summary(self, user_telegram_id: int) -> dict:
        """
        Get cart summary for AI context.
        
        Returns:
            Dictionary with cart summary or empty cart info
        """
        cart = await self.get_cart(user_telegram_id)
        
        if cart is None or not cart.items:
            return {
                "is_empty": True,
                "total_items": 0,
                "subtotal": 0,
                "total": 0
            }
        
        return {
            "is_empty": False,
            "total_items": cart.total_items,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "instant": item.instant_quantity,
                    "prepaid": item.prepaid_quantity,
                    "unit_price": item.final_price,
                    "total": item.total_price
                }
                for item in cart.items
            ],
            "subtotal": cart.subtotal,
            "promo_code": cart.promo_code,
            "promo_discount": cart.promo_discount_percent,
            "total": cart.total,
            "instant_total": cart.instant_total,
            "prepaid_total": cart.prepaid_total
        }


# Singleton instance
_cart_manager: Optional[CartManager] = None


def get_cart_manager() -> CartManager:
    """Get CartManager singleton."""
    global _cart_manager
    if _cart_manager is None:
        _cart_manager = CartManager()
    return _cart_manager

