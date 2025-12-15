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
    Use when user asks about a specific product or before purchase.
    
    Args:
        product_id: Product UUID
        
    Returns:
        Full product details including description, pricing, availability
    """
    try:
        db = get_db()
        product = await db.get_product_by_id(product_id)
        if not product:
            return {"success": False, "error": "Product not found"}
        
        # Determine availability message
        if product.stock_count > 0:
            availability = f"В наличии ({product.stock_count} шт), мгновенная доставка"
        else:
            hours = getattr(product, 'fulfillment_time_hours', 48) or 48
            availability = f"Предзаказ, доставка {hours}ч"
        
        # Get price formatted
        price = float(product.price or 0)
        currency = getattr(product, "currency", "RUB") or "RUB"
        symbol = "₽" if currency.upper() == "RUB" else currency
        
        return {
            "success": True,
            "id": product.id,
            "name": product.name,
            "description": product.description or "Нет описания",
            "price": price,
            "price_formatted": f"{price:.0f}{symbol}",
            "currency": currency,
            "in_stock": product.stock_count > 0,
            "stock_count": product.stock_count,
            "availability": availability,
            "status": product.status,
            "category": getattr(product, "category", None),
            "fulfillment_hours": getattr(product, "fulfillment_time_hours", 48),
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
    Get user's full profile information.
    Use when user asks about their account, balance, stats, or career level.
    
    Args:
        user_id: User database ID
        
    Returns:
        Complete profile with balance, career level, stats
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
        balance = float(user.get("balance", 0) or 0)
        turnover = float(user.get("turnover_usd", 0) or 0)
        total_saved = float(user.get("total_saved", 0) or 0)
        referral_earnings = float(user.get("total_referral_earnings", 0) or 0)
        
        # Determine career level
        if turnover >= 1000:
            career_level = "ARCHITECT"
            career_id = 3
            next_level = None
            progress = 100
        elif turnover >= 250:
            career_level = "OPERATOR"
            career_id = 2
            next_level = "ARCHITECT"
            progress = int((turnover - 250) / 750 * 100)
        else:
            career_level = "PROXY"
            career_id = 1
            next_level = "OPERATOR"
            progress = int(turnover / 250 * 100)
        
        # Get referral percentages by level
        referral_percents = {
            1: {"line1": 5},
            2: {"line1": 5, "line2": 2},
            3: {"line1": 5, "line2": 2, "line3": 1},
        }
        
        # Count orders
        orders_result = await asyncio.to_thread(
            lambda: db.client.table("orders").select("id", count="exact").eq("user_id", user_id).execute()
        )
        orders_count = orders_result.count or 0
        
        return {
            "success": True,
            "balance": balance,
            "balance_formatted": f"{balance:.0f}₽",
            "career_level": career_level,
            "career_level_id": career_id,
            "turnover_usd": turnover,
            "next_level": next_level,
            "progress_to_next": progress,
            "total_saved": total_saved,
            "total_saved_formatted": f"{total_saved:.0f}₽",
            "referral_earnings": referral_earnings,
            "referral_earnings_formatted": f"{referral_earnings:.0f}₽",
            "orders_count": orders_count,
            "referral_percents": referral_percents.get(career_id, referral_percents[1]),
            "partner_mode": user.get("partner_mode", "commission"),
        }
    except Exception as e:
        logger.error(f"get_user_profile error: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_referral_info(user_id: str, telegram_id: int) -> dict:
    """
    Get user's referral program info.
    Use when user asks about referrals, affiliate link, earnings, or network.
    
    Args:
        user_id: User database ID
        telegram_id: User's Telegram ID
        
    Returns:
        Complete referral info with link, earnings, network stats
    """
    try:
        db = get_db()
        
        # Get user with all referral fields
        result = await asyncio.to_thread(
            lambda: db.client.table("users").select(
                "balance, turnover_usd, total_referral_earnings, partner_mode, partner_discount_percent"
            ).eq("id", user_id).single().execute()
        )
        
        if not result.data:
            return {"success": False, "error": "User not found"}
        
        user = result.data
        turnover = float(user.get("turnover_usd", 0) or 0)
        earnings = float(user.get("total_referral_earnings", 0) or 0)
        
        # Determine career level
        if turnover >= 1000:
            career_level = "ARCHITECT"
            career_id = 3
            next_level = None
            turnover_to_next = 0
        elif turnover >= 250:
            career_level = "OPERATOR"
            career_id = 2
            next_level = "ARCHITECT"
            turnover_to_next = 1000 - turnover
        else:
            career_level = "PROXY"
            career_id = 1
            next_level = "OPERATOR"
            turnover_to_next = 250 - turnover
        
        # Count referrals by line
        network = {"line1": 0, "line2": 0, "line3": 0}
        
        # Line 1 - direct referrals
        l1 = await asyncio.to_thread(
            lambda: db.client.table("users").select("id", count="exact").eq("referrer_id", user_id).execute()
        )
        network["line1"] = l1.count or 0
        
        # Line 2 - referrals of referrals
        l1_ids = [u["id"] for u in (l1.data or [])]
        if l1_ids:
            l2 = await asyncio.to_thread(
                lambda ids=l1_ids: db.client.table("users").select("id", count="exact").in_("referrer_id", ids).execute()
            )
            network["line2"] = l2.count or 0
            
            # Line 3
            l2_ids = [u["id"] for u in (l2.data or [])]
            if l2_ids and career_id >= 3:
                l3 = await asyncio.to_thread(
                    lambda ids=l2_ids: db.client.table("users").select("id", count="exact").in_("referrer_id", ids).execute()
                )
                network["line3"] = l3.count or 0
        
        # Commission percentages by career level
        commission_percents = {
            1: {"line1": 5},
            2: {"line1": 5, "line2": 2},
            3: {"line1": 5, "line2": 2, "line3": 1},
        }
        
        partner_mode = user.get("partner_mode", "commission")
        
        return {
            "success": True,
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{telegram_id}",
            "career_level": career_level,
            "career_level_id": career_id,
            "turnover_usd": turnover,
            "next_level": next_level,
            "turnover_to_next": turnover_to_next,
            "total_earnings": earnings,
            "total_earnings_formatted": f"{earnings:.0f}₽",
            "network": network,
            "total_referrals": sum(network.values()),
            "commission_percents": commission_percents.get(career_id, commission_percents[1]),
            "partner_mode": partner_mode,
            "discount_percent": user.get("partner_discount_percent", 0) if partner_mode == "discount" else 0,
            "balance": float(user.get("balance", 0) or 0),
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
async def create_support_ticket(user_id: str, issue_type: str, message: str, order_id_prefix: Optional[str] = None) -> dict:
    """
    Create support ticket for user's issue.
    Automatically checks warranty and approves if within warranty period.
    
    Args:
        user_id: User database ID
        issue_type: Type of issue (replacement, refund, technical_issue, other)
        message: Issue description
        order_id_prefix: First 8 chars of related order ID (optional)
        
    Returns:
        Ticket info with status
    """
    try:
        from datetime import datetime, timezone
        
        db = get_db()
        
        order_id = None
        warranty_status = "unknown"
        auto_approved = False
        
        # If order specified, check warranty
        if order_id_prefix:
            orders = await db.get_user_orders(user_id, limit=20)
            order = next((o for o in orders if o.id.startswith(order_id_prefix)), None)
            
            if order:
                order_id = order.id
                
                # Get order items to check product warranty
                items = await db.get_order_items_by_order(order.id)
                
                if items and order.created_at:
                    # Check if within warranty
                    order_date = order.created_at
                    now = datetime.now(timezone.utc)
                    days_since = (now - order_date).days
                    
                    # Default warranty: 14 days for annual, 1 day for trial
                    # Check product type
                    product_name = items[0].get("product_name", "").lower()
                    if "trial" in product_name or "7 дней" in product_name:
                        warranty_days = 1
                    else:
                        warranty_days = 14
                    
                    if days_since <= warranty_days:
                        warranty_status = "in_warranty"
                        if issue_type == "replacement":
                            auto_approved = True
                    else:
                        warranty_status = "out_of_warranty"
        
        # Create ticket
        result = await db.create_ticket(
            user_id=user_id,
            subject=f"{issue_type.title()}: {order_id_prefix or 'General'}",
            message=message,
            order_id=order_id
        )
        
        ticket_id = result.get("id", "")[:8] if result else None
        
        # If auto-approved, update status
        status = "approved" if auto_approved else "open"
        if auto_approved and result:
            await db.update_ticket_status(result.get("id"), "approved")
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": status,
            "warranty_status": warranty_status,
            "auto_approved": auto_approved,
            "message": (
                f"Запрос на замену одобрен автоматически (в гарантии). Ticket: {ticket_id}"
                if auto_approved else
                f"Тикет создан: {ticket_id}. Мы ответим в ближайшее время."
            )
        }
    except Exception as e:
        logger.error(f"create_support_ticket error: {e}", exc_info=True)
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
