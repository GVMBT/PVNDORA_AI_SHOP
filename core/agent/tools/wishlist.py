"""Wishlist & Waitlist Tools for Shop Agent.

Save products for later, join waitlists.
"""

from langchain_core.tools import tool

from core.logging import get_logger

from .base import get_db, get_user_context

logger = get_logger(__name__)


@tool
async def add_to_wishlist(product_id: str) -> dict:
    """Add product to user's wishlist (saved for later).
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
        return {"success": True, "message": f"{product.name} added to wishlist"}
    except Exception as e:
        logger.exception("add_to_wishlist error")
        return {"success": False, "error": str(e)}


@tool
async def get_wishlist() -> dict:
    """Get user's wishlist.
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
            ],
        }
    except Exception as e:
        logger.exception("get_wishlist error")
        return {"success": False, "error": str(e)}


@tool
async def remove_from_wishlist(product_id: str) -> dict:
    """Remove product from user's wishlist.
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
        logger.exception("remove_from_wishlist error")
        return {"success": False, "error": str(e)}


@tool
async def add_to_waitlist(product_name: str) -> dict:
    """Add user to waitlist for coming_soon product.
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
            "message": f"Added to waitlist for {product_name}. You'll be notified when available.",
        }
    except Exception as e:
        logger.exception("add_to_waitlist error")
        return {"success": False, "error": str(e)}
