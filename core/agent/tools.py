"""
LangChain Tools for Shop Agent

Complete toolset covering all app functionality:
- Catalog & Search
- Cart Management  
- Orders & Credentials
- User Profile & Referrals
- Wishlist & Waitlist
- Support & FAQ
"""
import asyncio
from typing import Optional

from langchain_core.tools import tool

from core.logging import get_logger

logger = get_logger(__name__)

# Global DB instance - set during agent initialization
_db = None


def set_db(db):
    """Set the database instance for tools."""
    global _db
    _db = db


def get_db():
    """Get the database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call set_db() first.")
    return _db


# =============================================================================
# CATALOG TOOLS
# =============================================================================

@tool
async def get_catalog() -> dict:
    """
    Get full product catalog with prices and availability.
    Use when user asks what products are available.
    
    Returns:
        List of all active products with stock status
    """
    try:
        db = get_db()
        products = await db.get_products(status="active")
        return {
            "success": True,
            "count": len(products),
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "currency": getattr(p, "currency", "RUB") or "RUB",
                    "in_stock": p.stock_count > 0,
                    "stock_count": p.stock_count,
                    "status": p.status,
                }
                for p in products
            ]
        }
    except Exception as e:
        logger.error(f"get_catalog error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def search_products(query: str) -> dict:
    """
    Search products by name or description.
    Use when user asks about specific products.
    
    Args:
        query: Search query (product name, category, etc.)
        
    Returns:
        Matching products
    """
    try:
        db = get_db()
        products = await db.search_products(query)
        return {
            "success": True,
            "count": len(products),
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "in_stock": p.stock_count > 0,
                }
                for p in products
            ]
        }
    except Exception as e:
        logger.error(f"search_products error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_product_details(product_id: str) -> dict:
    """
    Get detailed info about a specific product.
    
    Args:
        product_id: Product UUID
        
    Returns:
        Full product details
    """
    try:
        db = get_db()
        product = await db.get_product_by_id(product_id)
        if not product:
            return {"success": False, "error": "Product not found"}
        
        return {
            "success": True,
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "currency": getattr(product, "currency", "RUB") or "RUB",
            "in_stock": product.stock_count > 0,
            "stock_count": product.stock_count,
            "status": product.status,
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
        Availability info with price
    """
    try:
        db = get_db()
        products = await db.search_products(product_name)
        
        if not products:
            return {
                "success": False,
                "found": False,
                "message": f"Product '{product_name}' not found"
            }
        
        p = products[0]  # Best match
        return {
            "success": True,
            "found": True,
            "product_id": p.id,
            "name": p.name,
            "price": p.price,
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
async def get_user_cart(user_telegram_id: int) -> dict:
    """
    Get user's shopping cart.
    ALWAYS call this before mentioning cart contents.
    
    Args:
        user_telegram_id: User's Telegram ID
        
    Returns:
        Cart with items and totals
    """
    try:
        from core.cart import get_cart_manager
        
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user_telegram_id)
        
        if not cart or not cart.items:
            return {"success": True, "empty": True, "items": [], "total": 0.0}
        
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
            "total": cart.total,
            "promo_code": cart.promo_code,
        }
    except Exception as e:
        logger.error(f"get_user_cart error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def add_to_cart(user_telegram_id: int, product_id: str, quantity: int = 1) -> dict:
    """
    Add product to user's cart.
    
    Args:
        user_telegram_id: User's Telegram ID
        product_id: Product UUID
        quantity: How many to add (default 1)
        
    Returns:
        Updated cart info
    """
    try:
        from core.cart import get_cart_manager
        
        db = get_db()
        product = await db.get_product_by_id(product_id)
        if not product:
            return {"success": False, "error": "Product not found"}
        
        # Get stock info
        stock_count = await db.get_available_stock_count(product_id)
        
        cart_manager = get_cart_manager()
        cart = await cart_manager.add_item(
            user_telegram_id=user_telegram_id,
            product_id=product_id,
            product_name=product.name,
            quantity=quantity,
            available_stock=stock_count,
            unit_price=product.price,
            discount_percent=0,
        )
        
        return {
            "success": True,
            "product_name": product.name,
            "quantity": quantity,
            "cart_total": cart.total,
            "message": f"Added {product.name} to cart"
        }
    except Exception as e:
        logger.error(f"add_to_cart error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def clear_cart(user_telegram_id: int) -> dict:
    """
    Clear user's shopping cart.
    
    Args:
        user_telegram_id: User's Telegram ID
        
    Returns:
        Confirmation
    """
    try:
        from core.cart import get_cart_manager
        
        cart_manager = get_cart_manager()
        await cart_manager.clear_cart(user_telegram_id)
        return {"success": True, "message": "Cart cleared"}
    except Exception as e:
        logger.error(f"clear_cart error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def apply_promo_code(code: str, user_telegram_id: int) -> dict:
    """
    Apply promo code to cart.
    
    Args:
        code: Promo code
        user_telegram_id: User's Telegram ID
        
    Returns:
        Discount info
    """
    try:
        db = get_db()
        promo = await db.validate_promo_code(code)
        
        if not promo:
            return {"success": False, "valid": False, "message": "Invalid or expired promo code"}
        
        # Apply to cart
        from core.cart import get_cart_manager
        cart_manager = get_cart_manager()
        await cart_manager.apply_promo(user_telegram_id, code, promo["discount_percent"])
        
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
async def get_user_orders(user_id: str, limit: int = 5) -> dict:
    """
    Get user's order history.
    Use when user asks about their orders.
    
    Args:
        user_id: User database ID
        limit: Max orders to return
        
    Returns:
        List of orders with status
    """
    try:
        db = get_db()
        orders = await db.get_user_orders(user_id, limit=limit)
        
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
async def get_order_credentials(user_id: str, order_id_prefix: str) -> dict:
    """
    Get credentials/login data for a delivered order.
    Use when user asks for login/password from their order.
    
    Args:
        user_id: User database ID
        order_id_prefix: First 8 characters of order ID (e.g. "c7e72095")
        
    Returns:
        Credentials for delivered items
    """
    try:
        db = get_db()
        
        # Find order by prefix
        orders = await db.get_user_orders(user_id, limit=20)
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
async def resend_order_credentials(user_id: str, order_id_prefix: str, telegram_id: int) -> dict:
    """
    Resend order credentials to user via Telegram.
    Use when user asks to resend/forward their login/password.
    
    Args:
        user_id: User database ID  
        order_id_prefix: First 8 characters of order ID
        telegram_id: User's Telegram ID to send to
        
    Returns:
        Confirmation
    """
    try:
        from core.services.notifications import NotificationService
        
        # First get credentials
        db = get_db()
        orders = await db.get_user_orders(user_id, limit=20)
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
            telegram_id=telegram_id,
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
async def get_user_profile(user_id: str) -> dict:
    """
    Get user's profile information.
    Use when user asks about their account, balance, or stats.
    
    Args:
        user_id: User database ID
        
    Returns:
        Profile with balance and stats
    """
    try:
        db = get_db()
        
        # Get user from DB
        result = await asyncio.to_thread(
            lambda: db.client.table("users").select("*").eq("id", user_id).single().execute()
        )
        
        if not result.data:
            return {"success": False, "error": "User not found"}
        
        user = result.data
        return {
            "success": True,
            "balance": user.get("balance", 0),
            "total_spent": user.get("total_spent", 0),
            "total_saved": user.get("total_saved", 0),
            "referral_level": user.get("referral_level", 1),
            "referral_earnings": user.get("referral_earnings", 0),
            "orders_count": user.get("orders_count", 0),
        }
    except Exception as e:
        logger.error(f"get_user_profile error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_referral_info(user_id: str, telegram_id: int) -> dict:
    """
    Get user's referral program info.
    Use when user asks about referrals, affiliate link, or earnings.
    
    Args:
        user_id: User database ID
        telegram_id: User's Telegram ID
        
    Returns:
        Referral link and stats
    """
    try:
        db = get_db()
        
        # Get user
        result = await asyncio.to_thread(
            lambda: db.client.table("users").select(
                "balance, referral_level, referral_earnings, total_spent"
            ).eq("id", user_id).single().execute()
        )
        
        if not result.data:
            return {"success": False, "error": "User not found"}
        
        user = result.data
        level = user.get("referral_level", 1)
        
        # Count referrals by level
        referral_counts = {"level_1": 0, "level_2": 0, "level_3": 0}
        
        # Level 1 - direct referrals
        l1 = await asyncio.to_thread(
            lambda: db.client.table("users").select("id", count="exact").eq("referrer_id", user_id).execute()
        )
        referral_counts["level_1"] = l1.count or 0
        
        # Level 2 - referrals of referrals
        if l1.data:
            l1_ids = [u["id"] for u in l1.data]
            if l1_ids:
                l2 = await asyncio.to_thread(
                    lambda: db.client.table("users").select("id", count="exact").in_("referrer_id", l1_ids).execute()
                )
                referral_counts["level_2"] = l2.count or 0
        
        # Referral percentages by level
        level_percents = {
            1: {"level_1": 5},
            2: {"level_1": 5, "level_2": 2},
            3: {"level_1": 5, "level_2": 2, "level_3": 1},
        }
        
        return {
            "success": True,
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{telegram_id}",
            "balance": user.get("balance", 0),
            "referral_level": level,
            "referral_earnings": user.get("referral_earnings", 0),
            "referral_counts": referral_counts,
            "total_referrals": sum(referral_counts.values()),
            "active_percentages": level_percents.get(level, level_percents[1]),
            "next_level_requirement": 5000 if level == 1 else (15000 if level == 2 else None),
            "total_spent": user.get("total_spent", 0),
        }
    except Exception as e:
        logger.error(f"get_referral_info error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# WISHLIST & WAITLIST TOOLS
# =============================================================================

@tool
async def add_to_wishlist(user_id: str, product_id: str) -> dict:
    """
    Add product to user's wishlist (saved for later).
    
    Args:
        user_id: User database ID
        product_id: Product UUID
        
    Returns:
        Confirmation
    """
    try:
        db = get_db()
        product = await db.get_product_by_id(product_id)
        if not product:
            return {"success": False, "error": "Product not found"}
        
        await db.add_to_wishlist(user_id, product_id)
        return {
            "success": True,
            "message": f"{product.name} added to wishlist"
        }
    except Exception as e:
        logger.error(f"add_to_wishlist error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_wishlist(user_id: str) -> dict:
    """
    Get user's wishlist.
    
    Args:
        user_id: User database ID
        
    Returns:
        List of saved products
    """
    try:
        db = get_db()
        products = await db.get_wishlist(user_id)
        
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
async def add_to_waitlist(user_id: str, product_name: str) -> dict:
    """
    Add user to waitlist for coming_soon product.
    User will be notified when product becomes available.
    
    Args:
        user_id: User database ID
        product_name: Product name
        
    Returns:
        Confirmation
    """
    try:
        db = get_db()
        await db.add_to_waitlist(user_id, product_name)
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
async def search_faq(question: str, language: str = "ru") -> dict:
    """
    Search FAQ for answer to common question.
    Use first before creating support ticket.
    
    Args:
        question: User's question
        language: Language code
        
    Returns:
        Matching FAQ entry if found
    """
    try:
        db = get_db()
        faq_entries = await db.get_faq(language)
        
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
async def create_support_ticket(user_id: str, message: str, order_id: Optional[str] = None) -> dict:
    """
    Create support ticket for user's issue.
    Use when user reports problem that can't be solved automatically.
    
    Args:
        user_id: User database ID
        message: Issue description
        order_id: Related order ID (optional)
        
    Returns:
        Ticket ID
    """
    try:
        db = get_db()
        result = await db.create_ticket(
            user_id=user_id,
            subject="Support Request",
            message=message,
            order_id=order_id
        )
        
        return {
            "success": True,
            "ticket_id": result.get("id", "")[:8] if result else None,
            "message": "Support ticket created. We'll respond soon."
        }
    except Exception as e:
        logger.error(f"create_support_ticket error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def request_refund(user_id: str, order_id: str, reason: str) -> dict:
    """
    Request refund for an order.
    
    Args:
        user_id: User database ID
        order_id: Order ID (full or prefix)
        reason: Reason for refund
        
    Returns:
        Ticket ID for refund request
    """
    try:
        db = get_db()
        
        # Find order
        orders = await db.get_user_orders(user_id, limit=20)
        order = next((o for o in orders if o.id.startswith(order_id)), None)
        
        if not order:
            return {"success": False, "error": f"Order {order_id} not found"}
        
        # Create refund ticket
        result = await db.create_ticket(
            user_id=user_id,
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
# BALANCE & PAYMENT TOOLS
# =============================================================================

@tool
async def check_user_balance(user_id: str) -> dict:
    """
    Check user's current balance.
    Use when user asks about their balance or before balance payment.
    
    Args:
        user_id: User database ID
        
    Returns:
        Current balance amount
    """
    try:
        db = get_db()
        result = await asyncio.to_thread(
            lambda: db.client.table("users").select("balance").eq("id", user_id).single().execute()
        )
        
        if not result.data:
            return {"success": False, "error": "User not found"}
        
        balance = result.data.get("balance", 0) or 0
        return {
            "success": True,
            "balance": float(balance),
            "formatted": f"{float(balance):.2f}₽"
        }
    except Exception as e:
        logger.error(f"check_user_balance error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def pay_cart_from_balance(user_telegram_id: int, user_id: str) -> dict:
    """
    Pay for cart items using internal balance.
    Use when user says "оплати с баланса", "спиши с баланса", "pay from balance".
    
    Args:
        user_telegram_id: User's Telegram ID
        user_id: User database ID
        
    Returns:
        Instructions or confirmation
    """
    try:
        from core.cart import get_cart_manager
        
        db = get_db()
        
        # Get cart first
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user_telegram_id)
        
        if not cart or not cart.items:
            return {"success": False, "error": "Корзина пуста. Сначала добавь товары."}
        
        # Check balance
        user_result = await asyncio.to_thread(
            lambda: db.client.table("users").select("balance").eq("id", user_id).single().execute()
        )
        balance = float(user_result.data.get("balance", 0) or 0) if user_result.data else 0
        
        if balance < cart.total:
            return {
                "success": False,
                "error": "Недостаточно средств на балансе",
                "balance": balance,
                "cart_total": cart.total,
                "shortage": cart.total - balance,
                "message": f"Баланс: {balance:.0f}₽, нужно: {cart.total:.0f}₽. Пополни баланс или оплати картой."
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
async def remove_from_wishlist(user_id: str, product_id: str) -> dict:
    """
    Remove product from user's wishlist.
    
    Args:
        user_id: User database ID
        product_id: Product UUID
        
    Returns:
        Confirmation
    """
    try:
        db = get_db()
        await db.remove_from_wishlist(user_id, product_id)
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
        # Cart
        get_user_cart,
        add_to_cart,
        clear_cart,
        apply_promo_code,
        # Orders
        get_user_orders,
        get_order_credentials,
        resend_order_credentials,
        # User & Referrals
        get_user_profile,
        get_referral_info,
        check_user_balance,
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
