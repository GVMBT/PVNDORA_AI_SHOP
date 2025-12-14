"""Cart-related tool handlers."""
import asyncio
from typing import Dict, Any

from .helpers import get_user_telegram_id, create_error_response, resolve_product_id
from core.logging import get_logger

logger = get_logger(__name__)


async def handle_get_user_cart(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Get user's shopping cart with all items."""
    try:
        from core.cart import get_cart_manager
        
        telegram_id = await get_user_telegram_id(user_id, db)
        if not telegram_id:
            return {"success": False, "reason": "User not found"}
        
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(telegram_id)
        
        if not cart:
            return {
                "success": True,
                "empty": True,
                "items": [],
                "total": 0.0
            }
        
        return {
            "success": True,
            "empty": False,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "instant_quantity": item.instant_quantity,
                    "prepaid_quantity": item.prepaid_quantity,
                    "unit_price": item.unit_price,
                    "discount_percent": item.discount_percent,
                    "total_price": item.total_price
                }
                for item in cart.items
            ],
            "instant_total": cart.instant_total,
            "prepaid_total": cart.prepaid_total,
            "subtotal": cart.subtotal,
            "total": cart.total,
            "promo_code": cart.promo_code,
            "promo_discount_percent": cart.promo_discount_percent
        }
    except Exception as e:
        logger.error(f"get_user_cart failed: {e}", exc_info=True)
        return create_error_response(e, "Failed to retrieve cart.")


async def handle_add_to_cart(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Add a product to user's shopping cart."""
    try:
        from core.cart import get_cart_manager
        
        product_id_or_name = arguments.get("product_id", "")
        quantity = arguments.get("quantity", 1)
        
        if quantity < 1:
            return {"success": False, "reason": "Quantity must be at least 1"}
        
        resolved_id, error = await resolve_product_id(product_id_or_name, db)
        if error:
            return {"success": False, "reason": error}
        
        product_id = resolved_id
        product = await db.get_product_by_id(product_id)
        if not product:
            return {"success": False, "reason": "Product not found"}
        
        # Get available stock with discounts
        stock_result = await asyncio.to_thread(
            lambda: db.client.table("available_stock_with_discounts").select(
                "*"
            ).eq("product_id", product_id).limit(1).execute()
        )
        
        available_stock = len(stock_result.data) if stock_result.data else 0
        discount_percent = stock_result.data[0].get("discount_percent", 0) if stock_result.data else 0
        
        telegram_id = await get_user_telegram_id(user_id, db)
        if not telegram_id:
            return {"success": False, "reason": "User not found"}
        
        cart_manager = get_cart_manager()
        
        cart = await cart_manager.add_item(
            user_telegram_id=telegram_id,
            product_id=product_id,
            product_name=product.name,
            quantity=quantity,
            available_stock=available_stock,
            unit_price=product.price,
            discount_percent=discount_percent
        )
        
        added_item = next(
            (item for item in cart.items if item.product_id == product_id),
            None
        )
        
        return {
            "success": True,
            "product_id": product_id,
            "product_name": product.name,
            "quantity": quantity,
            "instant_quantity": added_item.instant_quantity if added_item else 0,
            "prepaid_quantity": added_item.prepaid_quantity if added_item else 0,
            "unit_price": product.price,
            "discount_percent": discount_percent,
            "cart_total": cart.total,
            "message": f"Added {product.name} to cart"
        }
    except Exception as e:
        logger.error(f"add_to_cart failed: {e}")
        return create_error_response(e, "Failed to add to cart.")


async def handle_update_cart(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Update shopping cart: change quantity or remove item."""
    try:
        from core.cart import get_cart_manager
        
        operation = arguments.get("operation")
        product_id = arguments.get("product_id")
        quantity = arguments.get("quantity")
        
        telegram_id = await get_user_telegram_id(user_id, db)
        if not telegram_id:
            return {"success": False, "reason": "User not found"}
        
        cart_manager = get_cart_manager()
        
        if operation == "clear":
            await cart_manager.clear_cart(telegram_id)
            return {
                "success": True,
                "message": "Cart cleared",
                "cart_total": 0.0
            }
        
        elif operation == "remove_item":
            if not product_id:
                return {"success": False, "reason": "product_id required for remove_item"}
            
            cart = await cart_manager.remove_item(telegram_id, product_id)
            if cart:
                return {
                    "success": True,
                    "message": "Item removed from cart",
                    "cart_total": cart.total
                }
            return {"success": False, "reason": "Item not found in cart"}
        
        elif operation == "update_quantity":
            if not product_id or quantity is None:
                return {"success": False, "reason": "product_id and quantity required"}
            
            if quantity < 0:
                return {"success": False, "reason": "Quantity cannot be negative"}
            
            product = await db.get_product_by_id(product_id)
            if not product:
                return {"success": False, "reason": "Product not found"}
            
            stock_result = await asyncio.to_thread(
                lambda: db.client.table("available_stock_with_discounts").select(
                    "*"
                ).eq("product_id", product_id).limit(1).execute()
            )
            available_stock = len(stock_result.data) if stock_result.data else 0
            
            if quantity == 0:
                cart = await cart_manager.remove_item(telegram_id, product_id)
            else:
                cart = await cart_manager.update_item_quantity(
                    telegram_id, product_id, quantity, available_stock
                )
            
            if cart:
                return {
                    "success": True,
                    "message": "Cart updated",
                    "cart_total": cart.total
                }
            return {"success": False, "reason": "Cart not found"}
        
        else:
            return {"success": False, "reason": f"Unknown operation: {operation}"}
            
    except Exception as e:
        logger.error(f"update_cart failed: {e}", exc_info=True)
        return create_error_response(e, "Failed to update cart.")


# Export handlers mapping
CART_HANDLERS = {
    "get_user_cart": handle_get_user_cart,
    "add_to_cart": handle_add_to_cart,
    "update_cart": handle_update_cart,
}

