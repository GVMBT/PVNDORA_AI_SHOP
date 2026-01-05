"""
LangChain Tools for Shop Agent

Complete toolset covering all app functionality:
- Catalog & Search
- Cart Management  
- Orders & Credentials
- User Profile & Referrals
- Wishlist & Waitlist
- Support & FAQ

User context (user_id, telegram_id, language, currency) is auto-injected
via set_user_context() before each agent call.
"""
import asyncio
from typing import Optional
from dataclasses import dataclass

from langchain_core.tools import tool

from core.logging import get_logger

logger = get_logger(__name__)

# Global DB instance - set during agent initialization
_db = None


# Global user context - set before each agent call
@dataclass
class _UserContext:
    user_id: str = ""
    telegram_id: int = 0
    language: str = "en"
    currency: str = "USD"

_user_ctx = _UserContext()


def set_db(db):
    """Set the database instance for tools."""
    global _db
    _db = db


def get_db():
    """Get the database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call set_db() first.")
    return _db


def set_user_context(user_id: str, telegram_id: int, language: str, currency: str):
    """Set user context for all tools. Called by agent before each chat."""
    global _user_ctx
    _user_ctx = _UserContext(
        user_id=user_id,
        telegram_id=telegram_id,
        language=language,
        currency=currency
    )
    logger.debug(f"User context set: {_user_ctx}")


def get_user_context() -> _UserContext:
    """Get current user context."""
    return _user_ctx


# =============================================================================
# CATALOG TOOLS
# =============================================================================

@tool
async def get_catalog() -> dict:
    """
    Get full product catalog with prices and availability.
    Prices are automatically converted to user's currency (from context).
    
    Returns:
        List of all active products with stock status and prices in user's currency
    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service
        
        db = get_db()
        ctx = get_user_context()
        products = await db.get_products(status="active")
        
        # Use context currency (set by agent)
        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency
        
        logger.info(f"get_catalog: using context currency={target_currency}")
        
        result_products = []
        for p in products:
            price_usd = float(p.price or 0)
            
            # Convert price
            if target_currency != "USD":
                try:
                    price_converted = await currency_service.convert_price(price_usd, target_currency)
                except Exception:
                    price_converted = price_usd
            else:
                price_converted = price_usd
            
            price_formatted = currency_service.format_price(price_converted, target_currency)
            
            result_products.append({
                "id": p.id,
                "name": p.name,
                "price": price_converted,
                "price_usd": price_usd,
                "currency": target_currency,
                "price_formatted": price_formatted,
                "in_stock": p.stock_count > 0,
                "stock_count": p.stock_count,
                "status": p.status,
            })
        
        return {
            "success": True,
            "count": len(result_products),
            "currency": target_currency,
            "products": result_products
        }
    except Exception as e:
        logger.error(f"get_catalog error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def search_products(query: str) -> dict:
    """
    Search products by name or description.
    Use when user asks about specific products.
    Prices are automatically converted to user's currency.
    
    Args:
        query: Search query (product name, category, etc.)
        
    Returns:
        Matching products with prices in user's currency
    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service
        
        db = get_db()
        ctx = get_user_context()
        products = await db.search_products(query)
        
        # Use context currency
        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency
        
        logger.info(f"search_products: query='{query}', currency={target_currency}")
        
        result_products = []
        for p in products:
            price_usd = float(p.price or 0)
            
            # Convert price
            if target_currency != "USD":
                try:
                    price_converted = await currency_service.convert_price(price_usd, target_currency)
                except Exception as e:
                    logger.error(f"Currency conversion failed: {e}")
                    price_converted = price_usd
            else:
                price_converted = price_usd
            
            price_formatted = currency_service.format_price(price_converted, target_currency)
            
            result_products.append({
                "id": p.id,
                "name": p.name,
                "price": price_converted,
                "price_usd": price_usd,
                "price_formatted": price_formatted,
                "currency": target_currency,
                "in_stock": p.stock_count > 0,
                "stock_count": p.stock_count,
            })
        
        return {
            "success": True,
            "count": len(result_products),
            "currency": target_currency,
            "products": result_products
        }
    except Exception as e:
        logger.error(f"search_products error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_product_details(product_id: str) -> dict:
    """
    Get detailed info about a specific product.
    Prices are automatically converted to user's currency.
    
    Args:
        product_id: Product UUID
        
    Returns:
        Full product details including description, pricing, availability
    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service
        
        db = get_db()
        ctx = get_user_context()
        product = await db.get_product_by_id(product_id)
        if not product:
            return {"success": False, "error": "Product not found"}
        
        # Use context currency
        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency
        
        price_usd = float(product.price or 0)
        
        if target_currency != "USD":
            try:
                price_converted = await currency_service.convert_price(price_usd, target_currency)
            except Exception:
                price_converted = price_usd
        else:
            price_converted = price_usd
        
        price_formatted = currency_service.format_price(price_converted, target_currency)
        
        # Availability message based on language
        is_russian = ctx.language in ["ru", "be", "kk"]
        if product.stock_count > 0:
            availability = f"В наличии ({product.stock_count} шт), мгновенная доставка" if is_russian else f"In stock ({product.stock_count}), instant delivery"
        else:
            hours = getattr(product, 'fulfillment_time_hours', 48) or 48
            availability = f"Предзаказ, доставка {hours}ч" if is_russian else f"Preorder, delivery in {hours}h"
        
        warranty_hours = getattr(product, "warranty_hours", None)
        
        return {
            "success": True,
            "id": product.id,
            "name": product.name,
            "description": product.description or "",
            "price": price_converted,
            "price_usd": price_usd,
            "currency": target_currency,
            "price_formatted": price_formatted,
            "in_stock": product.stock_count > 0,
            "stock_count": product.stock_count,
            "availability": availability,
            "status": product.status,
            "warranty_hours": warranty_hours,
            "fulfillment_hours": getattr(product, "fulfillment_time_hours", 48),
            "categories": getattr(product, "categories", []),
        }
    except Exception as e:
        logger.error(f"get_product_details error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def check_product_availability(product_name: str) -> dict:
    """
    Check if a product is available for purchase.
    Use before adding to cart or purchasing.
    
    Args:
        product_name: Name or partial name of the product
        
    Returns:
        Availability info with price in user's currency
    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service
        
        db = get_db()
        ctx = get_user_context()
        products = await db.search_products(product_name)
        
        if not products:
            return {
                "success": False,
                "found": False,
                "message": f"Product '{product_name}' not found"
            }
        
        # Use context currency
        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency
        
        p = products[0]  # Best match
        price_usd = float(p.price or 0)
        
        # Convert price
        if target_currency != "USD":
            try:
                price_converted = await currency_service.convert_price(price_usd, target_currency)
            except Exception:
                price_converted = price_usd
        else:
            price_converted = price_usd
        
        price_formatted = currency_service.format_price(price_converted, target_currency)
        
        return {
            "success": True,
            "found": True,
            "product_id": p.id,
            "name": p.name,
            "price": price_converted,
            "price_usd": price_usd,
            "price_formatted": price_formatted,
            "currency": target_currency,
            "in_stock": p.stock_count > 0,
            "stock_count": p.stock_count,
            "status": p.status,
            "availability": "instant" if p.stock_count > 0 else "prepaid (24-48h)",
        }
    except Exception as e:
        logger.error(f"check_product_availability error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# CART TOOLS
# =============================================================================

@tool
async def get_user_cart() -> dict:
    """
    Get user's shopping cart.
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
        
        # Convert totals to user's currency
        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency
        
        total_converted = cart.total
        if target_currency != "USD":
            try:
                total_converted = await currency_service.convert_price(cart.total, target_currency)
            except Exception:
                pass
        
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
        logger.error(f"get_user_cart error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def add_to_cart(product_id: str, quantity: int = 1) -> dict:
    """
    Add product to user's cart.
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
        
        # Get stock info
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
        
        # Format total in user's currency
        redis = get_redis()
        currency_service = get_currency_service(redis)
        total_converted = cart.total
        if ctx.currency != "USD":
            try:
                total_converted = await currency_service.convert_price(cart.total, ctx.currency)
            except Exception:
                pass
        
        total_formatted = currency_service.format_price(total_converted, ctx.currency)
        
        return {
            "success": True,
            "product_name": product.name,
            "quantity": quantity,
            "cart_total": total_converted,
            "cart_total_formatted": total_formatted,
            "message": f"Added {product.name} to cart"
        }
    except Exception as e:
        logger.error(f"add_to_cart error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def clear_cart() -> dict:
    """
    Clear user's shopping cart.
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
        logger.error(f"clear_cart error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def apply_promo_code(code: str) -> dict:
    """
    Apply promo code to cart.
    Uses telegram_id from context.
    
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
        
        # Apply to cart
        from core.cart import get_cart_manager
        cart_manager = get_cart_manager()
        await cart_manager.apply_promo(ctx.telegram_id, code, promo["discount_percent"])
        
        return {
            "success": True,
            "valid": True,
            "code": code.upper(),
            "discount_percent": promo["discount_percent"],
            "message": f"Promo code applied! {promo['discount_percent']}% discount"
        }
    except Exception as e:
        logger.error(f"apply_promo_code error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# ORDER TOOLS
# =============================================================================

@tool
async def get_user_orders(limit: int = 5) -> dict:
    """
    Get user's order history.
    Use when user asks about their orders.
    Uses user_id from context.
    
    Args:
        limit: Max orders to return
        
    Returns:
        List of orders with status
    """
    try:
        ctx = get_user_context()
        db = get_db()
        orders = await db.get_user_orders(ctx.user_id, limit=limit)
        
        if not orders:
            return {"success": True, "count": 0, "orders": [], "message": "No orders found"}
        
        # Get order items for each order
        order_ids = [o.id for o in orders]
        all_items = await db.get_order_items_by_orders(order_ids)
        
        # Group items by order
        items_by_order = {}
        for item in all_items:
            oid = item["order_id"]
            if oid not in items_by_order:
                items_by_order[oid] = []
            items_by_order[oid].append(item)
        
        return {
            "success": True,
            "count": len(orders),
            "orders": [
                {
                    "id": o.id[:8],
                    "full_id": o.id,
                    "amount": o.amount,
                    "status": o.status,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                    "items": [
                        {
                            "product_name": it.get("product_name", "Unknown"),
                            "status": it.get("status", "unknown"),
                            "has_credentials": bool(it.get("delivery_content")),
                            "item_id": it.get("id", ""),
                        }
                        for it in items_by_order.get(o.id, [])
                    ]
                }
                for o in orders
            ]
        }
    except Exception as e:
        logger.error(f"get_user_orders error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_order_credentials(order_id_prefix: str) -> dict:
    """
    Get credentials/login data for a delivered order.
    Use when user asks for login/password from their order.
    Uses user_id from context.
    
    Args:
        order_id_prefix: First 8 characters of order ID (e.g. "c7e72095")
        
    Returns:
        Credentials for delivered items
    """
    try:
        ctx = get_user_context()
        db = get_db()
        
        # Find order by prefix
        orders = await db.get_user_orders(ctx.user_id, limit=20)
        order = next((o for o in orders if o.id.startswith(order_id_prefix)), None)
        
        if not order:
            return {
                "success": False,
                "error": f"Order {order_id_prefix} not found. Check order ID."
            }
        
        # Get order items with credentials
        items = await db.get_order_items_by_order(order.id)
        
        credentials = []
        for item in items:
            content = item.get("delivery_content")
            if content:
                credentials.append({
                    "product_name": item.get("product_name", "Product"),
                    "credentials": content,
                    "instructions": item.get("delivery_instructions", ""),
                })
        
        if not credentials:
            # Check order status
            if order.status in ("pending", "prepaid"):
                return {
                    "success": True,
                    "status": order.status,
                    "message": f"Order {order_id_prefix} is not yet delivered. Status: {order.status}",
                    "credentials": []
                }
            return {
                "success": True,
                "status": order.status,
                "message": f"No credentials found for order {order_id_prefix}",
                "credentials": []
            }
        
        return {
            "success": True,
            "order_id": order_id_prefix,
            "status": order.status,
            "credentials": credentials,
        }
    except Exception as e:
        logger.error(f"get_order_credentials error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def resend_order_credentials(order_id_prefix: str) -> dict:
    """
    Resend order credentials to user via Telegram.
    Use when user asks to resend/forward their login/password.
    Uses user_id and telegram_id from context.
    
    Args:
        order_id_prefix: First 8 characters of order ID
        
    Returns:
        Confirmation
    """
    try:
        from core.services.notifications import NotificationService
        
        ctx = get_user_context()
        # First get credentials
        db = get_db()
        orders = await db.get_user_orders(ctx.user_id, limit=20)
        order = next((o for o in orders if o.id.startswith(order_id_prefix)), None)
        
        if not order:
            return {"success": False, "error": f"Order {order_id_prefix} not found"}
        
        items = await db.get_order_items_by_order(order.id)
        
        credentials = []
        for item in items:
            content = item.get("delivery_content")
            if content:
                credentials.append(f"{item.get('product_name', 'Product')}:\n{content}")
        
        if not credentials:
            return {"success": False, "error": "No credentials to resend"}
        
        # Send via notification service
        notification = NotificationService()
        content_text = "\n\n".join(credentials)
        await notification.send_delivery(
            telegram_id=ctx.telegram_id,
            product_name=f"Заказ {order_id_prefix}",
            content=content_text
        )
        
        return {
            "success": True,
            "message": f"Credentials for order {order_id_prefix} sent to your Telegram"
        }
    except Exception as e:
        logger.error(f"resend_order_credentials error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# USER & PROFILE TOOLS
# =============================================================================

@tool
async def get_user_profile() -> dict:
    """
    Get user's full profile information.
    Loads thresholds from referral_settings, converts balance to user currency.
    Uses user_id and currency from context.
        
    Returns:
        Complete profile with balance, career level, stats
    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service
        
        ctx = get_user_context()
        db = get_db()
        
        # Load referral settings for thresholds
        settings_result = await asyncio.to_thread(
            lambda: db.client.table("referral_settings").select("*").limit(1).execute()
        )
        
        if settings_result.data:
            s = settings_result.data[0]
            threshold_l2 = float(s.get("level2_threshold_usd", 250) or 250)
            threshold_l3 = float(s.get("level3_threshold_usd", 1000) or 1000)
        else:
            threshold_l2, threshold_l3 = 250, 1000
        
        # Get user from DB
        result = await asyncio.to_thread(
            lambda: db.client.table("users").select("*").eq("id", ctx.user_id).single().execute()
        )
        
        if not result.data:
            return {"success": False, "error": "User not found"}
        
        user = result.data
        balance = float(user.get("balance", 0) or 0)
        turnover = float(user.get("turnover_usd", 0) or 0)
        total_saved = float(user.get("total_saved", 0) or 0)
        referral_earnings = float(user.get("total_referral_earnings", 0) or 0)
        
        # Determine career level based on DB thresholds
        line1_unlocked = user.get("level1_unlocked_at") is not None or user.get("referral_program_unlocked", False)
        line2_unlocked = turnover >= threshold_l2 or user.get("level2_unlocked_at") is not None
        line3_unlocked = turnover >= threshold_l3 or user.get("level3_unlocked_at") is not None
        
        if line3_unlocked:
            career_level = "ARCHITECT"
            next_level = None
            turnover_to_next = 0
        elif line2_unlocked:
            career_level = "OPERATOR"
            next_level = "ARCHITECT"
            turnover_to_next = max(0, threshold_l3 - turnover)
        elif line1_unlocked:
            career_level = "PROXY"
            next_level = "OPERATOR"
            turnover_to_next = max(0, threshold_l2 - turnover)
        else:
            career_level = "LOCKED"
            next_level = "PROXY (make first purchase)"
            turnover_to_next = 0
        
        # Count orders
        orders_result = await asyncio.to_thread(
            lambda: db.client.table("orders").select("id", count="exact").eq("user_id", ctx.user_id).execute()
        )
        orders_count = orders_result.count or 0
        
        # Use context currency
        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency
        
        # Balance is stored in USD, convert if needed
        if target_currency != "USD" and balance > 0:
            try:
                balance_converted = await currency_service.convert_price(balance, target_currency)
            except Exception:
                balance_converted = balance
        else:
            balance_converted = balance
        
        # Convert total_saved and referral_earnings to user currency for display
        if target_currency != "USD":
            try:
                total_saved_converted = await currency_service.convert_price(total_saved, target_currency)
                referral_earnings_converted = await currency_service.convert_price(referral_earnings, target_currency)
            except Exception:
                total_saved_converted = total_saved
                referral_earnings_converted = referral_earnings
        else:
            total_saved_converted = total_saved
            referral_earnings_converted = referral_earnings
        
        return {
            "success": True,
            "balance": balance_converted,
            "balance_usd": balance,
            "currency": target_currency,
            "balance_formatted": currency_service.format_price(balance_converted, target_currency),
            "career_level": career_level,
            "turnover_usd": turnover,
            "next_level": next_level,
            "turnover_to_next_usd": turnover_to_next,
            "total_saved": total_saved,
            "total_saved_formatted": currency_service.format_price(total_saved_converted, target_currency),
            "referral_earnings": referral_earnings,
            "referral_earnings_formatted": currency_service.format_price(referral_earnings_converted, target_currency),
            "orders_count": orders_count,
            "partner_mode": user.get("partner_mode", "commission"),
        }
    except Exception as e:
        logger.error(f"get_user_profile error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def get_referral_info() -> dict:
    """
    Get user's referral program info.
    Loads settings from database (referral_settings table).
    Uses user_id and telegram_id from context.
        
    Returns:
        Complete referral info with link, earnings, network stats
    """
    try:
        ctx = get_user_context()
        db = get_db()
        
        # Load referral settings from DB (dynamic, not hardcoded)
        settings_result = await asyncio.to_thread(
            lambda: db.client.table("referral_settings").select("*").limit(1).execute()
        )
        
        if settings_result.data:
            s = settings_result.data[0]
            threshold_l2 = float(s.get("level2_threshold_usd", 250) or 250)
            threshold_l3 = float(s.get("level3_threshold_usd", 1000) or 1000)
            commission_l1 = float(s.get("level1_commission_percent", 10) or 10)
            commission_l2 = float(s.get("level2_commission_percent", 7) or 7)
            commission_l3 = float(s.get("level3_commission_percent", 3) or 3)
        else:
            # Fallback defaults
            threshold_l2, threshold_l3 = 250, 1000
            commission_l1, commission_l2, commission_l3 = 10, 7, 3
        
        # Get user data
        result = await asyncio.to_thread(
            lambda: db.client.table("users").select(
                "balance, turnover_usd, total_referral_earnings, partner_mode, partner_discount_percent, "
                "level1_unlocked_at, level2_unlocked_at, level3_unlocked_at, referral_program_unlocked"
            ).eq("id", ctx.user_id).single().execute()
        )
        
        if not result.data:
            return {"success": False, "error": "User not found"}
        
        user = result.data
        turnover = float(user.get("turnover_usd", 0) or 0)
        earnings = float(user.get("total_referral_earnings", 0) or 0)
        
        # Determine career level based on thresholds from DB
        # PROXY = any purchase unlocks line 1
        # OPERATOR = turnover >= threshold_l2 unlocks line 2
        # ARCHITECT = turnover >= threshold_l3 unlocks line 3
        
        line1_unlocked = user.get("level1_unlocked_at") is not None or user.get("referral_program_unlocked", False)
        line2_unlocked = turnover >= threshold_l2 or user.get("level2_unlocked_at") is not None
        line3_unlocked = turnover >= threshold_l3 or user.get("level3_unlocked_at") is not None
        
        if line3_unlocked:
            career_level = "ARCHITECT"
            next_level = None
            turnover_to_next = 0
        elif line2_unlocked:
            career_level = "OPERATOR"
            next_level = "ARCHITECT"
            turnover_to_next = max(0, threshold_l3 - turnover)
        elif line1_unlocked:
            career_level = "PROXY"
            next_level = "OPERATOR"
            turnover_to_next = max(0, threshold_l2 - turnover)
        else:
            career_level = "LOCKED"
            next_level = "PROXY"
            turnover_to_next = 0  # Need first purchase
        
        # Count referrals by line
        network = {"line1": 0, "line2": 0, "line3": 0}
        
        # Line 1 - direct referrals
        l1 = await asyncio.to_thread(
            lambda: db.client.table("users").select("id", count="exact").eq("referrer_id", ctx.user_id).execute()
        )
        network["line1"] = l1.count or 0
        
        # Line 2 - referrals of referrals
        l1_ids = [u["id"] for u in (l1.data or [])]
        if l1_ids and line2_unlocked:
            l2 = await asyncio.to_thread(
                lambda ids=l1_ids: db.client.table("users").select("id", count="exact").in_("referrer_id", ids).execute()
            )
            network["line2"] = l2.count or 0
            
            # Line 3
            l2_ids = [u["id"] for u in (l2.data or [])]
            if l2_ids and line3_unlocked:
                l3 = await asyncio.to_thread(
                    lambda ids=l2_ids: db.client.table("users").select("id", count="exact").in_("referrer_id", ids).execute()
                )
                network["line3"] = l3.count or 0
        
        # Build active commissions based on unlocked lines
        active_commissions = {}
        if line1_unlocked:
            active_commissions["line1"] = commission_l1
        if line2_unlocked:
            active_commissions["line2"] = commission_l2
        if line3_unlocked:
            active_commissions["line3"] = commission_l3
        
        partner_mode = user.get("partner_mode", "commission")
        
        return {
            "success": True,
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{ctx.telegram_id}",
            "career_level": career_level,
            "line1_unlocked": line1_unlocked,
            "line2_unlocked": line2_unlocked,
            "line3_unlocked": line3_unlocked,
            "turnover_usd": turnover,
            "next_level": next_level,
            "turnover_to_next_usd": turnover_to_next,
            "thresholds": {"level2": threshold_l2, "level3": threshold_l3},
            "total_earnings": earnings,
            "network": network,
            "total_referrals": sum(network.values()),
            "active_commissions": active_commissions,
            "all_commissions": {"line1": commission_l1, "line2": commission_l2, "line3": commission_l3},
            "partner_mode": partner_mode,
            "discount_percent": user.get("partner_discount_percent", 0) if partner_mode == "discount" else 0,
            "balance": float(user.get("balance", 0) or 0),
        }
    except Exception as e:
        logger.error(f"get_referral_info error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =============================================================================
# WISHLIST & WAITLIST TOOLS
# =============================================================================

@tool
async def add_to_wishlist(product_id: str) -> dict:
    """
    Add product to user's wishlist (saved for later).
    Uses user_id from context.
    
    Args:
        product_id: Product UUID
        
    Returns:
        Confirmation
    """
    try:
        ctx = get_user_context()
        db = get_db()
        product = await db.get_product_by_id(product_id)
        if not product:
            return {"success": False, "error": "Product not found"}
        
        await db.add_to_wishlist(ctx.user_id, product_id)
        return {
            "success": True,
            "message": f"{product.name} added to wishlist"
        }
    except Exception as e:
        logger.error(f"add_to_wishlist error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_wishlist() -> dict:
    """
    Get user's wishlist.
    Uses user_id from context.
        
    Returns:
        List of saved products
    """
    try:
        ctx = get_user_context()
        db = get_db()
        products = await db.get_wishlist(ctx.user_id)
        
        return {
            "success": True,
            "count": len(products),
            "items": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                }
                for p in products
            ]
        }
    except Exception as e:
        logger.error(f"get_wishlist error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def add_to_waitlist(product_name: str) -> dict:
    """
    Add user to waitlist for coming_soon product.
    User will be notified when product becomes available.
    Uses user_id from context.
    
    Args:
        product_name: Product name
        
    Returns:
        Confirmation
    """
    try:
        ctx = get_user_context()
        db = get_db()
        await db.add_to_waitlist(ctx.user_id, product_name)
        return {
            "success": True,
            "message": f"Added to waitlist for {product_name}. You'll be notified when available."
        }
    except Exception as e:
        logger.error(f"add_to_waitlist error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# SUPPORT TOOLS
# =============================================================================

@tool
async def search_faq(question: str) -> dict:
    """
    Search FAQ for answer to common question.
    Use first before creating support ticket.
    Uses language from context.
    
    Args:
        question: User's question
        
    Returns:
        Matching FAQ entry if found
    """
    try:
        ctx = get_user_context()
        db = get_db()
        faq_entries = await db.get_faq(ctx.language)
        
        if not faq_entries:
            return {"success": True, "found": False}
        
        # Simple keyword matching
        question_lower = question.lower()
        for entry in faq_entries:
            q = entry.get("question", "").lower()
            if any(word in q for word in question_lower.split() if len(word) > 3):
                return {
                    "success": True,
                    "found": True,
                    "question": entry["question"],
                    "answer": entry["answer"],
                }
        
        return {"success": True, "found": False}
    except Exception as e:
        logger.error(f"search_faq error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def create_support_ticket(
    issue_type: str, 
    message: str, 
    order_id_prefix: Optional[str] = None,
    item_id: Optional[str] = None
) -> dict:
    """
    Create support ticket for user's issue.
    All tickets require manual review by admin/support.
    Uses user_id from context.
    
    IMPORTANT FOR REPLACEMENT TICKETS:
    - You MUST provide order_id_prefix for replacement/refund issues
    - You SHOULD provide item_id for account-specific problems
    
    Args:
        issue_type: Type of issue (replacement, refund, technical_issue, other)
        message: Issue description
        order_id_prefix: First 8 chars of related order ID (REQUIRED for replacement/refund)
        item_id: Specific order item ID (REQUIRED for account replacements)
        
    Returns:
        Ticket info with status
    """
    # Validate required params for replacement/refund
    if issue_type in ("replacement", "refund") and not order_id_prefix:
        return {
            "success": False,
            "error": "order_id_prefix required for replacement/refund tickets. First call get_user_orders to find the order, then ask user which one has the problem."
        }
    try:
        from datetime import datetime, timezone
        import re
        
        ctx = get_user_context()
        db = get_db()
        
        order_id = None
        warranty_status = "unknown"
        extracted_item_id = item_id
        
        # Extract item_id from message if not provided directly (format: "Item ID: <uuid>")
        if not extracted_item_id and ("Item ID:" in message or "item_id" in message.lower()):
            item_id_match = re.search(r'Item ID:\s*([a-f0-9\-]{36})', message, re.IGNORECASE)
            if item_id_match:
                extracted_item_id = item_id_match.group(1)
        
        # If order specified, find order and check warranty status (for info only)
        if order_id_prefix:
            orders = await db.get_user_orders(ctx.user_id, limit=20)
            order = next((o for o in orders if o.id.startswith(order_id_prefix)), None)
            
            if order:
                order_id = order.id
                
                # Check warranty status (informational only, no auto-approval)
                if extracted_item_id:
                    item_result = await asyncio.to_thread(
                        lambda: db.client.table("order_items")
                        .select("id, order_id, delivered_at, product_id")
                        .eq("id", extracted_item_id)
                        .eq("order_id", order_id)
                        .limit(1)
                        .execute()
                    )
                    if item_result.data:
                        item_data = item_result.data[0]
                        if item_data.get("delivered_at"):
                            item_delivered = datetime.fromisoformat(item_data["delivered_at"].replace("Z", "+00:00"))
                            now = datetime.now(timezone.utc)
                            days_since = (now - item_delivered).days
                            
                            # Get product warranty
                            product_result = await asyncio.to_thread(
                                lambda: db.client.table("products")
                                .select("name, warranty_hours")
                                .eq("id", item_data.get("product_id"))
                                .limit(1)
                                .execute()
                            )
                            if product_result.data:
                                product = product_result.data[0]
                                warranty_hours = product.get("warranty_hours", 168)
                                warranty_days = warranty_hours / 24
                                
                                if days_since <= warranty_days:
                                    warranty_status = "in_warranty"
                                else:
                                    warranty_status = "out_of_warranty"
                else:
                    # Order-level warranty check
                    items = await db.get_order_items_by_order(order.id)
                    
                    if items and order.created_at:
                        order_date = order.created_at
                        now = datetime.now(timezone.utc)
                        days_since = (now - order_date).days
                        
                        product_name = items[0].get("product_name", "").lower()
                        if "trial" in product_name or "7 дней" in product_name or "7 day" in product_name:
                            warranty_days = 1
                        else:
                            warranty_days = 14
                        
                        if days_since <= warranty_days:
                            warranty_status = "in_warranty"
                        else:
                            warranty_status = "out_of_warranty"
        
        # Create ticket via support domain - always with status "open"
        result = await db.support_domain.create_ticket(
            user_id=ctx.user_id,
            message=message,
            order_id=order_id,
            item_id=extracted_item_id,
            issue_type=issue_type
        )
        
        if not result.get("success"):
            return {"success": False, "error": result.get("reason", "Failed to create ticket")}
        
        ticket_id = result.get("ticket_id", "")
        ticket_id_short = ticket_id[:8] if ticket_id else None
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "ticket_id_short": ticket_id_short,
            "status": "open",
            "warranty_status": warranty_status,
            "message": f"Заявка #{ticket_id_short} создана. Наша команда поддержки рассмотрит её в ближайшее время."
        }
    except Exception as e:
        logger.error(f"create_support_ticket error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def request_refund(order_id: str, reason: str) -> dict:
    """
    Request refund for an order.
    Uses user_id from context.
    
    Args:
        order_id: Order ID (full or prefix)
        reason: Reason for refund
        
    Returns:
        Ticket ID for refund request
    """
    try:
        ctx = get_user_context()
        db = get_db()
        
        # Find order
        orders = await db.get_user_orders(ctx.user_id, limit=20)
        order = next((o for o in orders if o.id.startswith(order_id)), None)
        
        if not order:
            return {"success": False, "error": f"Order {order_id} not found"}
        
        # Create refund ticket
        result = await db.create_ticket(
            user_id=ctx.user_id,
            subject=f"Refund Request: {order_id[:8]}",
            message=f"Refund requested for order {order_id[:8]}. Reason: {reason}",
            order_id=order.id
        )
        
        return {
            "success": True,
            "ticket_id": result.get("id", "")[:8] if result else None,
            "message": f"Refund request created for order {order_id[:8]}. We'll review it soon."
        }
    except Exception as e:
        logger.error(f"request_refund error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# CHECKOUT TOOLS
# =============================================================================

@tool
async def checkout_cart(payment_method: str = "card") -> dict:
    """
    Create order from cart and get payment link.
    Use when user confirms they want to buy/purchase/order.
    
    CRITICAL: Call this when user says:
    - "купи", "оформи", "заказать", "оплатить"
    - "buy", "checkout", "order", "purchase"
    - "да" (after adding to cart)
    
    Args:
        payment_method: "card" (external payment) or "balance" (pay from internal balance)
        
    Returns:
        Order info with payment URL or confirmation
    """
    try:
        from core.cart import get_cart_manager
        from core.db import get_redis
        from core.services.currency import get_currency_service
        from datetime import datetime, timezone, timedelta
        
        ctx = get_user_context()
        db = get_db()
        cart_manager = get_cart_manager()
        
        # Get cart
        cart = await cart_manager.get_cart(ctx.telegram_id)
        if not cart or not cart.items:
            return {
                "success": False,
                "error": "Корзина пуста. Сначала добавь товары.",
                "action": "show_catalog"
            }
        
        # Get user from DB
        user_result = await asyncio.to_thread(
            lambda: db.client.table("users")
            .select("id, balance, preferred_currency, language_code")
            .eq("telegram_id", ctx.telegram_id)
            .single()
            .execute()
        )
        
        if not user_result.data:
            return {"success": False, "error": "User not found"}
        
        db_user = user_result.data
        user_id = db_user["id"]
        balance_usd = float(db_user.get("balance", 0) or 0)
        
        # Calculate cart total in USD
        cart_total_usd = float(cart.total)
        
        # Balance payment
        if payment_method == "balance":
            if balance_usd < cart_total_usd:
                # Format in user currency
                redis = get_redis()
                currency_service = get_currency_service(redis)
                
                if ctx.currency != "USD":
                    balance_display = await currency_service.convert_price(balance_usd, ctx.currency)
                    cart_display = await currency_service.convert_price(cart_total_usd, ctx.currency)
                else:
                    balance_display = balance_usd
                    cart_display = cart_total_usd
                
                return {
                    "success": False,
                    "error": "Недостаточно средств на балансе",
                    "balance": balance_display,
                    "cart_total": cart_display,
                    "shortage": cart_display - balance_display,
                    "message": f"Баланс: {currency_service.format_price(balance_display, ctx.currency)}, нужно: {currency_service.format_price(cart_display, ctx.currency)}. Используй оплату картой.",
                    "action": "suggest_card_payment"
                }
        
        # Create order in database
        payment_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        # Determine payment gateway
        import os
        payment_gateway = os.environ.get("DEFAULT_PAYMENT_GATEWAY", "rukassa")
        
        # Create order
        order_result = await asyncio.to_thread(
            lambda: db.client.table("orders").insert({
                "user_id": user_id,
                "amount": cart_total_usd,
                "original_price": float(cart.subtotal),
                "discount_percent": 0,
                "status": "pending",
                "payment_method": payment_method,
                "payment_gateway": payment_gateway if payment_method != "balance" else None,
                "user_telegram_id": ctx.telegram_id,
                "expires_at": payment_expires_at.isoformat(),
                "source_channel": "premium"
            }).execute()
        )
        
        if not order_result.data:
            return {"success": False, "error": "Failed to create order"}
        
        order = order_result.data[0]
        order_id = order["id"]
        
        # Create order items
        order_items = []
        for item in cart.items:
            # Get stock item if available
            stock_result = await asyncio.to_thread(
                lambda pid=item.product_id: db.client.table("stock_items")
                .select("id")
                .eq("product_id", pid)
                .eq("status", "available")
                .limit(1)
                .execute()
            )
            
            stock_item_id = stock_result.data[0]["id"] if stock_result.data else None
            
            order_items.append({
                "order_id": order_id,
                "product_id": item.product_id,
                "stock_item_id": stock_item_id,
                "quantity": item.quantity,
                "price": float(item.unit_price),
                "discount_percent": int(item.discount_percent),
                "fulfillment_type": "instant" if item.instant_quantity > 0 else "preorder",
                "status": "pending"
            })
        
        await asyncio.to_thread(
            lambda: db.client.table("order_items").insert(order_items).execute()
        )
        
        # Handle balance payment
        if payment_method == "balance":
            # Deduct from balance
            new_balance = balance_usd - cart_total_usd
            await asyncio.to_thread(
                lambda: db.client.table("users")
                .update({"balance": new_balance})
                .eq("id", user_id)
                .execute()
            )
            
            # Record balance transaction
            await asyncio.to_thread(
                lambda: db.client.table("balance_transactions").insert({
                    "user_id": user_id,
                    "type": "purchase",
                    "amount": -cart_total_usd,
                    "currency": "USD",
                    "balance_before": balance_usd,
                    "balance_after": new_balance,
                    "reference_type": "order",
                    "reference_id": order_id,
                    "status": "completed",
                    "description": f"Оплата заказа {order_id[:8]}"
                }).execute()
            )
            
            # Update order status to paid
            await asyncio.to_thread(
                lambda: db.client.table("orders")
                .update({"status": "paid"})
                .eq("id", order_id)
                .execute()
            )
            
            # Clear cart
            await cart_manager.clear_cart(ctx.telegram_id)
            
            # Format response in user currency
            redis = get_redis()
            currency_service = get_currency_service(redis)
            
            if ctx.currency != "USD":
                amount_display = await currency_service.convert_price(cart_total_usd, ctx.currency)
                new_balance_display = await currency_service.convert_price(new_balance, ctx.currency)
            else:
                amount_display = cart_total_usd
                new_balance_display = new_balance
            
            items_text = ", ".join([f"{item.product_name}" for item in cart.items])
            
            return {
                "success": True,
                "order_id": order_id[:8],
                "status": "paid",
                "payment_method": "balance",
                "amount": amount_display,
                "amount_formatted": currency_service.format_price(amount_display, ctx.currency),
                "new_balance": new_balance_display,
                "new_balance_formatted": currency_service.format_price(new_balance_display, ctx.currency),
                "items": items_text,
                "message": f"Заказ #{order_id[:8]} оплачен! Товар будет доставлен в течение нескольких минут.",
                "action": "order_paid"
            }
        
        # Card payment - create payment link
        from core.routers.deps import get_payment_service
        payment_service = get_payment_service()
        
        # Get payment URL
        try:
            payment_result = await payment_service.create_invoice(
                amount=cart_total_usd,
                order_id=order_id,
                description=f"PVNDORA Order #{order_id[:8]}",
                user_telegram_id=ctx.telegram_id
            )
            
            payment_url = payment_result.get("url") or payment_result.get("payment_url")
            payment_id = payment_result.get("id") or payment_result.get("payment_id")
            
            # Update order with payment info
            await asyncio.to_thread(
                lambda: db.client.table("orders")
                .update({
                    "payment_id": str(payment_id) if payment_id else None,
                    "payment_url": payment_url
                })
                .eq("id", order_id)
                .execute()
            )
            
            # Clear cart
            await cart_manager.clear_cart(ctx.telegram_id)
            
            # Format in user currency
            redis = get_redis()
            currency_service = get_currency_service(redis)
            
            if ctx.currency != "USD":
                amount_display = await currency_service.convert_price(cart_total_usd, ctx.currency)
            else:
                amount_display = cart_total_usd
            
            items_text = ", ".join([f"{item.product_name}" for item in cart.items])
            
            return {
                "success": True,
                "order_id": order_id[:8],
                "status": "pending",
                "payment_method": "card",
                "amount": amount_display,
                "amount_formatted": currency_service.format_price(amount_display, ctx.currency),
                "payment_url": payment_url,
                "items": items_text,
                "expires_in_minutes": 15,
                "message": f"Заказ #{order_id[:8]} создан! Оплати по ссылке в течение 15 минут.",
                "action": "show_payment_link"
            }
            
        except Exception as e:
            logger.error(f"Payment service error: {e}")
            # Cancel order if payment failed
            await asyncio.to_thread(
                lambda: db.client.table("orders")
                .update({"status": "cancelled"})
                .eq("id", order_id)
                .execute()
            )
            return {
                "success": False,
                "error": f"Ошибка платежного шлюза: {str(e)}",
                "action": "retry_payment"
            }
            
    except Exception as e:
        logger.error(f"checkout_cart error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def remove_from_cart(product_id: str) -> dict:
    """
    Remove product from cart.
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
            return {
                "success": True,
                "empty": True,
                "message": "Корзина теперь пуста"
            }
        
        # Format in user currency
        redis = get_redis()
        currency_service = get_currency_service(redis)
        
        if ctx.currency != "USD":
            total_display = await currency_service.convert_price(float(cart.total), ctx.currency)
        else:
            total_display = float(cart.total)
        
        return {
            "success": True,
            "empty": False,
            "items_count": len(cart.items),
            "total": total_display,
            "total_formatted": currency_service.format_price(total_display, ctx.currency),
            "message": "Товар удалён из корзины"
        }
    except Exception as e:
        logger.error(f"remove_from_cart error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def update_cart_quantity(product_id: str, quantity: int) -> dict:
    """
    Update quantity of product in cart.
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
        
        # Get available stock
        available_stock = await db.get_available_stock_count(product_id)
        
        cart = await cart_manager.update_item_quantity(
            ctx.telegram_id, 
            product_id, 
            quantity,
            available_stock
        )
        
        if cart is None or not cart.items:
            return {
                "success": True,
                "empty": True,
                "message": "Корзина теперь пуста"
            }
        
        # Format in user currency
        redis = get_redis()
        currency_service = get_currency_service(redis)
        
        if ctx.currency != "USD":
            total_display = await currency_service.convert_price(float(cart.total), ctx.currency)
        else:
            total_display = float(cart.total)
        
        return {
            "success": True,
            "empty": False,
            "items_count": len(cart.items),
            "total": total_display,
            "total_formatted": currency_service.format_price(total_display, ctx.currency),
            "message": "Количество обновлено"
        }
    except Exception as e:
        logger.error(f"update_cart_quantity error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_balance_history(limit: int = 10) -> dict:
    """
    Get user's balance transaction history.
    Shows deposits, purchases, referral earnings, cashback, etc.
    Uses user_id from context.
    
    Args:
        limit: Max transactions to return
        
    Returns:
        List of balance transactions
    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service
        
        ctx = get_user_context()
        db = get_db()
        
        result = await asyncio.to_thread(
            lambda: db.client.table("balance_transactions")
            .select("*")
            .eq("user_id", ctx.user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        if not result.data:
            return {
                "success": True,
                "count": 0,
                "transactions": [],
                "message": "Нет транзакций"
            }
        
        # Format in user currency
        redis = get_redis()
        currency_service = get_currency_service(redis)
        
        transactions = []
        for tx in result.data:
            amount_usd = float(tx.get("amount", 0))
            
            if ctx.currency != "USD":
                try:
                    amount_display = await currency_service.convert_price(abs(amount_usd), ctx.currency)
                except Exception:
                    amount_display = abs(amount_usd)
            else:
                amount_display = abs(amount_usd)
            
            sign = "+" if amount_usd > 0 else "-"
            
            # Type labels
            type_labels = {
                "referral_bonus": "Реферальный бонус",
                "purchase": "Покупка",
                "deposit": "Пополнение",
                "cashback": "Кэшбэк за отзыв",
                "refund": "Возврат",
                "withdrawal": "Вывод средств"
            }
            
            transactions.append({
                "type": tx.get("type"),
                "type_label": type_labels.get(tx.get("type"), tx.get("type")),
                "amount": amount_display,
                "amount_formatted": f"{sign}{currency_service.format_price(amount_display, ctx.currency)}",
                "description": tx.get("description", ""),
                "created_at": tx.get("created_at"),
            })
        
        return {
            "success": True,
            "count": len(transactions),
            "transactions": transactions
        }
    except Exception as e:
        logger.error(f"get_balance_history error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# BALANCE & PAYMENT TOOLS
# =============================================================================

@tool
async def pay_cart_from_balance() -> dict:
    """
    Pay for cart items using internal balance.
    Use when user says "оплати с баланса", "спиши с баланса", "pay from balance".
    Uses telegram_id and user_id from context.
        
    Returns:
        Instructions or confirmation
    """
    try:
        from core.cart import get_cart_manager
        
        ctx = get_user_context()
        db = get_db()
        
        # Get cart first
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(ctx.telegram_id)
        
        if not cart or not cart.items:
            return {"success": False, "error": "Корзина пуста. Сначала добавь товары."}
        
        # Check balance
        user_result = await asyncio.to_thread(
            lambda: db.client.table("users").select("balance, language_code, preferred_currency").eq("id", ctx.user_id).single().execute()
        )
        balance_usd = float(user_result.data.get("balance", 0) or 0) if user_result.data else 0
        
        # Use context currency
        user_currency = ctx.currency
        
        try:
            from core.db import get_redis
            from core.services.currency import get_currency_service
            redis = get_redis()
            currency_service = get_currency_service(redis)
            
            # Convert balance and cart total to user currency
            if user_currency != "USD":
                try:
                    balance = await currency_service.convert_price(balance_usd, user_currency)
                    cart_total = await currency_service.convert_price(cart.total, user_currency)
                except Exception:
                    balance = balance_usd
                    cart_total = cart.total
            else:
                balance = balance_usd
                cart_total = cart.total
        except Exception:
            # Fallback if currency service unavailable
            balance = balance_usd
            cart_total = cart.total
            user_currency = "USD"
            currency_service = None
        
        if balance < cart_total:
            # Format message with proper currency symbols
            if currency_service:
                try:
                    balance_formatted = currency_service.format_price(balance, user_currency)
                    cart_total_formatted = currency_service.format_price(cart_total, user_currency)
                    message = f"Баланс: {balance_formatted}, нужно: {cart_total_formatted}. Пополни баланс или оплати картой."
                except Exception:
                    message = f"Баланс: {balance:.0f}, нужно: {cart_total:.0f}. Пополни баланс или оплати картой."
            else:
                message = f"Баланс: {balance:.0f}, нужно: {cart_total:.0f}. Пополни баланс или оплати картой."
            
            return {
                "success": False,
                "error": "Недостаточно средств на балансе",
                "balance": balance,
                "cart_total": cart_total,
                "shortage": cart_total - balance,
                "message": message
            }
        
        # Balance is sufficient - direct user to checkout with balance option
        items_text = ", ".join([f"{item.product_name} x{item.quantity}" for item in cart.items])
        
        return {
            "success": True,
            "can_pay": True,
            "balance": balance,
            "cart_total": cart.total,
            "remaining_after": balance - cart.total,
            "items": items_text,
            "message": "Можно оплатить с баланса! Нажми Магазин → Корзина → выбери 'С баланса' и подтверди.",
            "instructions": "В корзине выбери способ оплаты 'С баланса' и нажми 'Оплатить'"
        }
        
    except Exception as e:
        logger.error(f"pay_cart_from_balance error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def remove_from_wishlist(product_id: str) -> dict:
    """
    Remove product from user's wishlist.
    Uses user_id from context.
    
    Args:
        product_id: Product UUID
        
    Returns:
        Confirmation
    """
    try:
        ctx = get_user_context()
        db = get_db()
        await db.remove_from_wishlist(ctx.user_id, product_id)
        return {"success": True, "message": "Removed from wishlist"}
    except Exception as e:
        logger.error(f"remove_from_wishlist error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# TOOL REGISTRY
# =============================================================================

def get_all_tools():
    """Get all available tools for the agent."""
    return [
        # Catalog
        get_catalog,
        search_products,
        get_product_details,
        check_product_availability,
        # Cart & Checkout
        get_user_cart,
        add_to_cart,
        remove_from_cart,
        update_cart_quantity,
        clear_cart,
        apply_promo_code,
        checkout_cart,  # CRITICAL: Creates order and returns payment link
        # Orders
        get_user_orders,
        get_order_credentials,
        resend_order_credentials,
        # User & Referrals
        get_user_profile,
        get_referral_info,
        get_balance_history,
        pay_cart_from_balance,
        # Wishlist & Waitlist
        add_to_wishlist,
        get_wishlist,
        remove_from_wishlist,
        add_to_waitlist,
        # Support
        search_faq,
        create_support_ticket,
        request_refund,
    ]
