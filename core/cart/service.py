"""Cart manager service using Redis storage."""
import json
import logging
from typing import Optional
from datetime import datetime

from src.services.money import to_decimal
from .models import CartItem, Cart
from .storage import get_redis, RedisKeys, TTL

logger = logging.getLogger(__name__)


class CartManager:
    """
    Manages shopping carts in Redis.
    
    Features:
    - Auto-split items into instant (in stock) vs prepaid (on demand)
    - 24-hour TTL for abandoned carts
    - Promo code support
    """
    
    def __init__(self):
        self._redis = None  # Lazy initialization
    
    @property
    def redis(self):
        """Get Redis client (lazy initialization)."""
        if self._redis is None:
            try:
                self._redis = get_redis()
            except ValueError as e:
                raise ValueError(f"Redis not available: {e}. Check UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN environment variables.")
        return self._redis
    
    async def get_cart(self, user_telegram_id: int) -> Optional[Cart]:
        """Get user's cart from Redis."""
        try:
            key = RedisKeys.cart_key(user_telegram_id)
            data = await self.redis.get(key)
            
            if not data:
                return None
            
            try:
                return Cart.from_dict(json.loads(data))
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                # Corrupted data - clear it and return None
                logger.warning(f"Corrupted cart data for user {user_telegram_id}: {e}")
                await self.redis.delete(key)
                return None
        except Exception as e:
            logger.error(f"Failed to get cart from Redis: {e}")
            raise ValueError(f"Cart service unavailable: {str(e)}")
    
    async def save_cart(self, cart: Cart) -> bool:
        """Save cart to Redis with TTL."""
        try:
            key = RedisKeys.cart_key(cart.user_telegram_id)
            cart.updated_at = datetime.utcnow().isoformat()
            
            await self.redis.set(
                key,
                json.dumps(cart.to_dict()),
                ex=TTL.CART
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save cart to Redis: {e}")
            raise ValueError(f"Cart service unavailable: {str(e)}")
    
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
        """Add item to cart with auto-split for instant vs prepaid."""
        # Validate inputs
        if not product_id or not isinstance(product_id, str):
            raise ValueError("product_id must be a non-empty string")
        if not product_name or not isinstance(product_name, str):
            raise ValueError("product_name must be a non-empty string")
        if not isinstance(quantity, int) or quantity < 1:
            raise ValueError("quantity must be a positive integer")
        if not isinstance(available_stock, int) or available_stock < 0:
            raise ValueError("available_stock must be a non-negative integer")
        if not isinstance(unit_price, (int, float)) or unit_price < 0:
            raise ValueError("unit_price must be a non-negative number")
        if not isinstance(discount_percent, (int, float)) or discount_percent < 0 or discount_percent > 100:
            raise ValueError("discount_percent must be between 0 and 100")
        
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
            existing_item.instant_quantity = min(existing_item.quantity, available_stock)
            existing_item.prepaid_quantity = max(0, existing_item.quantity - available_stock)
            existing_item.discount_percent = to_decimal(discount_percent)
            existing_item.unit_price = to_decimal(unit_price)
        else:
            # Add new item
            item = CartItem(
                product_id=product_id,
                product_name=product_name,
                quantity=quantity,
                instant_quantity=instant_qty,
                prepaid_quantity=prepaid_qty,
                unit_price=to_decimal(unit_price),
                discount_percent=to_decimal(discount_percent),
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
        """Update item quantity in cart."""
        if not isinstance(new_quantity, int) or new_quantity < 0:
            raise ValueError("new_quantity must be a non-negative integer")
        if not isinstance(available_stock, int) or available_stock < 0:
            raise ValueError("available_stock must be a non-negative integer")
        
        try:
            cart = await self.get_cart(user_telegram_id)
            if cart is None:
                return None
            
            if new_quantity <= 0:
                cart.items = [item for item in cart.items if item.product_id != product_id]
            else:
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
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update cart item quantity: {e}")
            raise ValueError(f"Cart service unavailable: {str(e)}")
    
    async def remove_item(
        self,
        user_telegram_id: int,
        product_id: str
    ) -> Optional[Cart]:
        """Remove item from cart."""
        return await self.update_item_quantity(user_telegram_id, product_id, 0, 0)
    
    async def apply_promo_code(
        self,
        user_telegram_id: int,
        promo_code: str,
        discount_percent: float
    ) -> Optional[Cart]:
        """Apply promo code to cart."""
        cart = await self.get_cart(user_telegram_id)
        if cart is None:
            return None
        
        cart.promo_code = promo_code
        cart.promo_discount_percent = to_decimal(discount_percent)
        
        await self.save_cart(cart)
        return cart
    
    async def remove_promo_code(self, user_telegram_id: int) -> Optional[Cart]:
        """Remove promo code from cart."""
        cart = await self.get_cart(user_telegram_id)
        if cart is None:
            return None
        
        cart.promo_code = None
        cart.promo_discount_percent = to_decimal(0)
        
        await self.save_cart(cart)
        return cart
    
    async def clear_cart(self, user_telegram_id: int) -> bool:
        """Clear user's cart."""
        try:
            key = RedisKeys.cart_key(user_telegram_id)
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to clear cart from Redis: {e}")
            raise ValueError(f"Cart service unavailable: {str(e)}")
    
    async def get_cart_summary(self, user_telegram_id: int) -> dict:
        """Get cart summary for AI context."""
        try:
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
                        "unit_price": float(item.final_price),
                        "total": float(item.total_price)
                    }
                    for item in cart.items
                ],
                "subtotal": float(cart.subtotal),
                "promo_code": cart.promo_code,
                "promo_discount": float(cart.promo_discount_percent),
                "total": float(cart.total),
                "instant_total": float(cart.instant_total),
                "prepaid_total": float(cart.prepaid_total)
            }
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to get cart summary: {e}")
            raise ValueError(f"Cart service unavailable: {str(e)}")


# Singleton instance
_cart_manager: Optional[CartManager] = None


def get_cart_manager() -> CartManager:
    """Get CartManager singleton."""
    global _cart_manager
    if _cart_manager is None:
        _cart_manager = CartManager()
    return _cart_manager

