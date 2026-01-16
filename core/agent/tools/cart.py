"""Cart Tools for Shop Agent.

Shopping cart management: add, remove, update, promo codes.
"""

import contextlib

from langchain_core.tools import tool

from core.logging import get_logger

from .base import get_db, get_user_context

logger = get_logger(__name__)


@tool
async def get_user_cart() -> dict:
    """Get user's shopping cart.
    ALWAYS call this before mentioning cart contents.
    Uses telegram_id from context.

    Returns:
        Cart with items and totals in user's currency

    """
    try:
        from core.cart import get_cart_manager
        from core.db import get_redis
        from core.services.currency import get_currency_service

        ctx = get_user_context()
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(ctx.telegram_id)

        if not cart or not cart.items:
            return {"success": True, "empty": True, "items": [], "total": 0.0}

        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency

        total_converted: float = float(cart.total)
        if target_currency != "USD":
            with contextlib.suppress(Exception):
                total_converted = currency_service.convert_price(cart.total, target_currency)

        return {
            "success": True,
            "empty": False,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                }
                for item in cart.items
            ],
            "total": total_converted,
            "total_usd": cart.total,
            "total_formatted": currency_service.format_price(total_converted, target_currency),
            "currency": target_currency,
            "promo_code": cart.promo_code,
        }
    except Exception as e:
        logger.exception("get_user_cart error")
        return {"success": False, "error": str(e)}


@tool
async def add_to_cart(product_id: str, quantity: int = 1) -> dict:
    """Add product to user's cart.
    Uses telegram_id from context.

    Args:
        product_id: Product UUID
        quantity: How many to add (default 1)

    Returns:
        Updated cart info

    """
    try:
        from core.cart import get_cart_manager
        from core.db import get_redis
        from core.services.currency import get_currency_service

        db = get_db()
        ctx = get_user_context()
        product = await db.get_product_by_id(product_id)
        if not product:
            return {"success": False, "error": "Product not found"}

        stock_count = await db.get_available_stock_count(product_id)

        cart_manager = get_cart_manager()
        cart = await cart_manager.add_item(
            user_telegram_id=ctx.telegram_id,
            product_id=product_id,
            product_name=product.name,
            quantity=quantity,
            available_stock=stock_count,
            unit_price=product.price,
            discount_percent=0,
        )

        redis = get_redis()
        currency_service = get_currency_service(redis)
        total_converted: float = float(cart.total)
        if ctx.currency != "USD":
            with contextlib.suppress(Exception):
                total_converted = currency_service.convert_price(cart.total, ctx.currency)

        total_formatted = currency_service.format_price(total_converted, ctx.currency)

        return {
            "success": True,
            "product_name": product.name,
            "quantity": quantity,
            "cart_total": total_converted,
            "cart_total_formatted": total_formatted,
            "message": f"Added {product.name} to cart",
        }
    except Exception as e:
        logger.exception("add_to_cart error")
        return {"success": False, "error": str(e)}


@tool
async def remove_from_cart(product_id: str) -> dict:
    """Remove product from cart.
    Uses telegram_id from context.

    Args:
        product_id: Product UUID to remove

    Returns:
        Updated cart info

    """
    try:
        from core.cart import get_cart_manager
        from core.db import get_redis
        from core.services.currency import get_currency_service

        ctx = get_user_context()
        cart_manager = get_cart_manager()

        cart = await cart_manager.remove_item(ctx.telegram_id, product_id)

        if cart is None or not cart.items:
            return {"success": True, "empty": True, "message": "Корзина теперь пуста"}

        redis = get_redis()
        currency_service = get_currency_service(redis)

        if ctx.currency != "USD":
            total_display = currency_service.convert_price(float(cart.total), ctx.currency)
        else:
            total_display = float(cart.total)

        return {
            "success": True,
            "empty": False,
            "items_count": len(cart.items),
            "total": total_display,
            "total_formatted": currency_service.format_price(total_display, ctx.currency),
            "message": "Товар удалён из корзины",
        }
    except Exception as e:
        logger.exception("remove_from_cart error")
        return {"success": False, "error": str(e)}


@tool
async def update_cart_quantity(product_id: str, quantity: int) -> dict:
    """Update quantity of product in cart.
    Uses telegram_id from context.

    Args:
        product_id: Product UUID
        quantity: New quantity (0 = remove)

    Returns:
        Updated cart info

    """
    try:
        from core.cart import get_cart_manager
        from core.db import get_redis
        from core.services.currency import get_currency_service

        ctx = get_user_context()
        db = get_db()
        cart_manager = get_cart_manager()

        available_stock = await db.get_available_stock_count(product_id)

        cart = await cart_manager.update_item_quantity(
            ctx.telegram_id,
            product_id,
            quantity,
            available_stock,
        )

        if cart is None or not cart.items:
            return {"success": True, "empty": True, "message": "Корзина теперь пуста"}

        redis = get_redis()
        currency_service = get_currency_service(redis)

        if ctx.currency != "USD":
            total_display = currency_service.convert_price(float(cart.total), ctx.currency)
        else:
            total_display = float(cart.total)

        return {
            "success": True,
            "empty": False,
            "items_count": len(cart.items),
            "total": total_display,
            "total_formatted": currency_service.format_price(total_display, ctx.currency),
            "message": "Количество обновлено",
        }
    except Exception as e:
        logger.exception("update_cart_quantity error")
        return {"success": False, "error": str(e)}


@tool
async def clear_cart() -> dict:
    """Clear user's shopping cart.
    Uses telegram_id from context.

    Returns:
        Confirmation

    """
    try:
        from core.cart import get_cart_manager

        ctx = get_user_context()
        cart_manager = get_cart_manager()
        await cart_manager.clear_cart(ctx.telegram_id)
        return {"success": True, "message": "Cart cleared"}
    except Exception as e:
        logger.exception("clear_cart error")
        return {"success": False, "error": str(e)}


@tool
async def apply_promo_code(code: str) -> dict:
    """Apply promo code to cart.
    Uses telegram_id from context.

    Supports both cart-wide and product-specific promo codes:
    - If promo.product_id is NULL: applies to entire cart
    - If promo.product_id is set: applies only to that product in cart

    Args:
        code: Promo code

    Returns:
        Discount info

    """
    try:
        ctx = get_user_context()
        db = get_db()
        promo = await db.validate_promo_code(code)

        if not promo:
            return {"success": False, "valid": False, "message": "Invalid or expired promo code"}

        product_id = promo.get("product_id")  # NULL = cart-wide, NOT NULL = product-specific

        # For product-specific promos, verify product is in cart
        if product_id:
            from core.cart import get_cart_manager

            cart_manager = get_cart_manager()
            cart = await cart_manager.get_cart(ctx.telegram_id)
            if cart is None:
                return {"success": False, "valid": False, "message": "Cart is empty"}

            # Check if product is in cart
            product_in_cart = any(item.product_id == product_id for item in cart.items)
            if not product_in_cart:
                return {
                    "success": False,
                    "valid": False,
                    "message": f"Promo code is valid only for product {product_id}, which is not in your cart",
                }

        from core.cart import get_cart_manager

        cart_manager = get_cart_manager()
        try:
            cart = await cart_manager.apply_promo_code(
                ctx.telegram_id,
                code,
                promo["discount_percent"],
                product_id=product_id,  # Pass product_id (can be None for cart-wide)
            )
        except ValueError as e:
            return {"success": False, "valid": False, "message": str(e)}

        if cart is None:
            return {"success": False, "valid": False, "message": "Cart is empty"}

        message = f"Promo code applied! {promo['discount_percent']}% discount"
        if product_id:
            message += f" (applied to product {product_id})"
        else:
            message += " (applied to entire cart)"

        return {
            "success": True,
            "valid": True,
            "code": code.upper(),
            "discount_percent": promo["discount_percent"],
            "product_id": product_id,  # NULL = cart-wide, NOT NULL = product-specific
            "message": message,
        }
    except Exception as e:
        logger.exception("apply_promo_code error")
        return {"success": False, "error": str(e)}
