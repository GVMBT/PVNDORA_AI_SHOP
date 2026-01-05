"""
Order Tools for Shop Agent.

Order history, credentials retrieval, resending.
"""
from langchain_core.tools import tool

from core.logging import get_logger
from .base import get_db, get_user_context

logger = get_logger(__name__)


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
        
        order_ids = [o.id for o in orders]
        all_items = await db.get_order_items_by_orders(order_ids)
        
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
        
        orders = await db.get_user_orders(ctx.user_id, limit=20)
        order = next((o for o in orders if o.id.startswith(order_id_prefix)), None)
        
        if not order:
            return {
                "success": False,
                "error": f"Order {order_id_prefix} not found. Check order ID."
            }
        
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
