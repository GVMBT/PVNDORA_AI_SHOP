"""
LangChain Tools for Shop Agent

Async tools that delegate to Service Layer.
Each tool:
- Has clear docstring (used by LLM to understand when to use)
- Uses type hints (for schema generation)
- Is async-native (no run_until_complete hacks)
"""
from typing import List, Optional

from langchain_core.tools import tool

from core.services.domains import (
    CatalogService,
    WishlistService,
    ReferralService,
    SupportService,
)
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
async def check_product_availability(product_name: str) -> dict:
    """
    Check if a product is available in stock.
    Use when user asks about product availability or stock.
    
    Args:
        product_name: Name or partial name of the product
        
    Returns:
        Product availability info including stock count and price
    """
    service = CatalogService(get_db())
    result = await service.check_availability(product_name)
    return {
        "found": result.found,
        "product_id": result.product_id,
        "name": result.name,
        "price": result.price,
        "in_stock": result.in_stock,
        "stock_count": result.stock_count,
        "status": result.status,
    }


@tool
async def get_product_details(product_id: str) -> dict:
    """
    Get detailed information about a specific product.
    Use when user wants to know more about a product.
    
    Args:
        product_id: UUID of the product
        
    Returns:
        Full product details including description, price, rating
    """
    service = CatalogService(get_db())
    result = await service.get_details(product_id)
    return {
        "found": result.found,
        "id": result.id,
        "name": result.name,
        "description": result.description,
        "price": result.price,
        "type": result.type,
        "in_stock": result.in_stock,
        "rating": result.rating,
        "reviews_count": result.reviews_count,
    }


@tool
async def search_products(query: str, category: str = "all") -> dict:
    """
    Search for products by name or description.
    Use when user is looking for products or asking what's available.
    
    Args:
        query: Search query (what user is looking for)
        category: Optional category filter (all, chatgpt, claude, midjourney, etc.)
        
    Returns:
        List of matching products with prices and availability
    """
    service = CatalogService(get_db())
    results = await service.search(query, category, limit=5)
    return {
        "count": len(results),
        "products": [
            {
                "id": r.id,
                "name": r.name,
                "price": r.price,
                "in_stock": r.in_stock,
            }
            for r in results
        ]
    }


@tool
async def get_catalog() -> dict:
    """
    Get full product catalog.
    Use when user wants to see all available products.
    
    Returns:
        List of all active products
    """
    service = CatalogService(get_db())
    products = await service.get_catalog(status="active")
    return {
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


@tool
async def create_purchase_intent(product_id: str) -> dict:
    """
    Create purchase intent for a product.
    Use when user wants to buy a product.
    
    Args:
        product_id: UUID of the product to purchase
        
    Returns:
        Purchase details including order type (instant/prepaid) and price
    """
    service = CatalogService(get_db())
    result = await service.create_purchase_intent(product_id)
    return {
        "success": result.success,
        "product_id": result.product_id,
        "product_name": result.product_name,
        "price": result.price,
        "order_type": result.order_type,
        "action": result.action,
        "message": result.message,
        "reason": result.reason,
    }


# =============================================================================
# WISHLIST TOOLS
# =============================================================================

@tool
async def add_to_wishlist(user_id: str, product_id: str) -> dict:
    """
    Add a product to user's wishlist.
    Use when user wants to save a product for later.
    
    Args:
        user_id: User database ID
        product_id: Product UUID
        
    Returns:
        Success status and message
    """
    service = WishlistService(get_db())
    return await service.add_item(user_id, product_id)


@tool
async def get_wishlist(user_id: str) -> dict:
    """
    Get user's wishlist.
    Use when user wants to see saved products.
    
    Args:
        user_id: User database ID
        
    Returns:
        List of wishlist items
    """
    service = WishlistService(get_db())
    items = await service.get_items(user_id)
    return {
        "count": len(items),
        "items": [
            {
                "id": item.product_id,
                "name": item.product_name,
                "price": item.price,
                "in_stock": item.in_stock,
            }
            for item in items
        ]
    }


# =============================================================================
# USER TOOLS
# =============================================================================

@tool
async def get_referral_info(user_id: str) -> dict:
    """
    Get user's referral information and statistics.
    Use when user asks about referral program or their referral link.
    
    Args:
        user_id: User database ID
        
    Returns:
        Referral link and statistics by level
    """
    service = ReferralService(get_db())
    result = await service.get_info(user_id)
    
    if not result.success:
        return {"success": False, "error": result.error}
    
    return {
        "success": True,
        "referral_link": result.referral_link,
        "total_referrals": result.total_referrals,
        "balance": result.balance,
        "levels": {
            f"level_{k}": {"count": v.count, "percent": v.percent}
            for k, v in (result.levels or {}).items()
        }
    }


# =============================================================================
# SUPPORT TOOLS
# =============================================================================

@tool
async def create_support_ticket(
    user_id: str, 
    message: str, 
    order_id: Optional[str] = None
) -> dict:
    """
    Create a support ticket.
    Use when user reports a problem or needs help.
    
    Args:
        user_id: User database ID
        message: Description of the issue
        order_id: Related order ID (optional)
        
    Returns:
        Ticket creation result
    """
    service = SupportService(get_db())
    return await service.create_ticket(user_id, message, order_id)


@tool
async def search_faq(question: str, language: str = "en") -> dict:
    """
    Search FAQ for an answer.
    Use when user asks a common question.
    
    Args:
        question: User's question
        language: Language code
        
    Returns:
        FAQ entry if found
    """
    service = SupportService(get_db())
    entry = await service.search_faq(question, language)
    
    if entry:
        return {
            "found": True,
            "question": entry.question,
            "answer": entry.answer,
        }
    return {"found": False}


@tool
async def request_refund(user_id: str, order_id: str, reason: str = "") -> dict:
    """
    Request a refund for an order.
    Use when user wants to return/refund an order.
    
    Args:
        user_id: User database ID
        order_id: Order ID
        reason: Reason for refund
        
    Returns:
        Refund request result
    """
    service = SupportService(get_db())
    return await service.request_refund(user_id, order_id, reason)


# =============================================================================
# CART TOOLS
# =============================================================================

@tool
async def get_user_cart(user_telegram_id: int) -> dict:
    """
    Get user's shopping cart.
    Use when user wants to see what's in their cart.
    
    Args:
        user_telegram_id: User's Telegram ID
        
    Returns:
        Cart contents and totals
    """
    from core.cart import get_cart_manager
    
    cart_manager = get_cart_manager()
    cart = await cart_manager.get_cart(user_telegram_id)
    
    if not cart:
        return {"success": True, "empty": True, "items": [], "total": 0.0}
    
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
                "total_price": item.total_price,
            }
            for item in cart.items
        ],
        "instant_total": cart.instant_total,
        "prepaid_total": cart.prepaid_total,
        "total": cart.total,
        "promo_code": cart.promo_code,
    }


@tool
async def add_to_cart(
    user_telegram_id: int,
    product_id: str,
    quantity: int = 1
) -> dict:
    """
    Add a product to user's cart.
    Use when user wants to add something to cart.
    
    Args:
        user_telegram_id: User's Telegram ID
        product_id: Product UUID
        quantity: How many to add
        
    Returns:
        Updated cart info
    """
    import asyncio
    from core.cart import get_cart_manager
    
    db = get_db()
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
    
    cart_manager = get_cart_manager()
    cart = await cart_manager.add_item(
        user_telegram_id=user_telegram_id,
        product_id=product_id,
        product_name=product.name,
        quantity=quantity,
        available_stock=available_stock,
        unit_price=product.price,
        discount_percent=discount_percent,
    )
    
    return {
        "success": True,
        "product_name": product.name,
        "quantity": quantity,
        "cart_total": cart.total,
    }


@tool
async def update_cart(
    user_telegram_id: int,
    operation: str,
    product_id: Optional[str] = None,
    quantity: Optional[int] = None
) -> dict:
    """
    Update shopping cart: change quantity, remove item, or clear cart.
    
    Args:
        user_telegram_id: User's Telegram ID
        operation: One of: 'update_quantity', 'remove_item', 'clear'
        product_id: Product UUID (required for update/remove)
        quantity: New quantity (required for update_quantity, 0 = remove)
        
    Returns:
        Updated cart status
    """
    import asyncio
    from core.cart import get_cart_manager
    
    cart_manager = get_cart_manager()
    db = get_db()
    
    if operation == "clear":
        await cart_manager.clear_cart(user_telegram_id)
        return {"success": True, "message": "Cart cleared", "cart_total": 0.0}
    
    if operation == "remove_item":
        if not product_id:
            return {"success": False, "reason": "product_id required"}
        cart = await cart_manager.remove_item(user_telegram_id, product_id)
        return {"success": True, "message": "Item removed", "cart_total": cart.total if cart else 0.0}
    
    if operation == "update_quantity":
        if not product_id or quantity is None:
            return {"success": False, "reason": "product_id and quantity required"}
        
        if quantity == 0:
            cart = await cart_manager.remove_item(user_telegram_id, product_id)
        else:
            stock_result = await asyncio.to_thread(
                lambda: db.client.table("available_stock_with_discounts").select(
                    "*"
                ).eq("product_id", product_id).limit(1).execute()
            )
            available_stock = len(stock_result.data) if stock_result.data else 0
            cart = await cart_manager.update_item_quantity(
                user_telegram_id, product_id, quantity, available_stock
            )
        return {"success": True, "message": "Cart updated", "cart_total": cart.total if cart else 0.0}
    
    return {"success": False, "reason": f"Unknown operation: {operation}"}


# =============================================================================
# ORDER TOOLS
# =============================================================================

@tool
async def get_user_orders(user_id: str, limit: int = 5) -> dict:
    """
    Get user's recent orders.
    Use when user asks about their orders or order history.
    
    Args:
        user_id: User database ID
        limit: Maximum number of orders to return
        
    Returns:
        List of recent orders with status
    """
    db = get_db()
    orders = await db.get_user_orders(user_id, limit=limit)
    
    return {
        "count": len(orders),
        "orders": [
            {
                "id": o.id[:8],
                "product_id": o.product_id,
                "amount": o.amount,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ]
    }


@tool
async def apply_promo_code(code: str) -> dict:
    """
    Check and apply a promo code for discount.
    Use when user provides a promo or discount code.
    
    Args:
        code: The promo code to validate
        
    Returns:
        Validation result with discount percentage
    """
    db = get_db()
    code = code.strip().upper()
    promo = await db.validate_promo_code(code)
    
    if promo:
        return {
            "valid": True,
            "code": code,
            "discount_percent": promo["discount_percent"],
            "message": f"Promo code applied! {promo['discount_percent']}% discount"
        }
    return {"valid": False, "message": "Invalid or expired promo code"}


# =============================================================================
# ADDITIONAL CATALOG TOOLS
# =============================================================================

@tool
async def compare_products(product_names: List[str]) -> dict:
    """
    Compare two or more products side by side.
    Use when user wants to compare different products.
    
    Args:
        product_names: List of product names to compare (e.g. ["ChatGPT", "Claude"])
        
    Returns:
        Comparison data for all products
    """
    service = CatalogService(get_db())
    results = await service.compare(product_names)
    return {"products": results}


@tool
async def add_to_waitlist(user_id: str, product_name: str) -> dict:
    """
    Add user to waitlist for a coming_soon product.
    Use when user wants to be notified when product becomes available.
    
    Args:
        user_id: User database ID
        product_name: Name of the product to wait for
        
    Returns:
        Waitlist status
    """
    service = CatalogService(get_db())
    return await service.add_to_waitlist(user_id=user_id, product_name=product_name)


# =============================================================================
# ALL TOOLS
# =============================================================================

def get_all_tools():
    """Get all available tools for the agent."""
    return [
        # Catalog
        check_product_availability,
        get_product_details,
        search_products,
        get_catalog,
        compare_products,
        create_purchase_intent,
        add_to_waitlist,
        # Wishlist
        add_to_wishlist,
        get_wishlist,
        # User
        get_referral_info,
        get_user_orders,
        apply_promo_code,
        # Support
        create_support_ticket,
        search_faq,
        request_refund,
        # Cart
        get_user_cart,
        add_to_cart,
        update_cart,
    ]
