"""Wishlist Domain Service.

Handles user wishlist operations.
Currently used only for stock notifications (waitlist_notify_in_stock).
All methods use async/await with supabase-py v2 (no asyncio.to_thread).

TODO: Add UI for wishlist management in the frontend.
User should be able to:
- View wishlist items
- Add/remove items from wishlist
- Receive notifications when items come back in stock
"""

from dataclasses import dataclass
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WishlistItem:
    """Wishlist item."""

    id: str
    product_id: str
    product_name: str
    price: float
    in_stock: bool


class WishlistService:
    """Wishlist domain service.

    Provides clean interface for wishlist operations.
    """

    def __init__(self, db) -> None:
        self.db = db

    async def get_items(self, user_id: str) -> list[WishlistItem]:
        """Get user's wishlist items.

        Args:
            user_id: User database ID

        Returns:
            List of WishlistItem

        """
        try:
            result = (
                await self.db.client.table("wishlist")
                .select("id,product_id,products(name,price,stock_count:stock_items(count))")
                .eq("user_id", user_id)
                .execute()
            )

            items = []
            for item in result.data or []:
                products_data = item.get("products", {})
                stock_data = products_data.get("stock_count") or [{}]
                stock_count = stock_data[0].get("count", 0) if stock_data else 0

                items.append(
                    WishlistItem(
                        id=item.get("id", ""),
                        product_id=item.get("product_id", ""),
                        product_name=products_data.get("name", "Unknown"),
                        price=products_data.get("price", 0),
                        in_stock=stock_count > 0,
                    ),
                )

            return items
        except Exception as e:
            logger.error("Failed to get wishlist: %s", type(e).__name__, exc_info=True)
            return []

    async def add_item(self, user_id: str, product_id: str) -> dict[str, Any]:
        """Add product to wishlist.

        Args:
            user_id: User database ID
            product_id: Product UUID

        Returns:
            Success/failure result

        """
        # Get product info
        product = await self.db.get_product_by_id(product_id)
        if not product:
            return {"success": False, "reason": "Product not found"}

        # Check if already exists
        existing = (
            await self.db.client.table("wishlist")
            .select("id")
            .eq("user_id", user_id)
            .eq("product_id", product_id)
            .execute()
        )

        if existing.data:
            return {"success": False, "reason": "Already in wishlist"}

        try:
            result = (
                await self.db.client.table("wishlist")
                .insert({"user_id": user_id, "product_id": product_id, "reminded": False})
                .execute()
            )

            if result.data:
                return {
                    "success": True,
                    "product_name": product.name,
                    "message": "Added to wishlist",
                }
            return {"success": False, "reason": "Failed to add to wishlist"}
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                return {"success": False, "reason": "Already in wishlist"}
            logger.error("Failed to add to wishlist: %s", type(e).__name__, exc_info=True)
            return {"success": False, "reason": "Database error"}

    async def remove_item(self, user_id: str, product_id: str) -> dict[str, Any]:
        """Remove product from wishlist.

        Args:
            user_id: User database ID
            product_id: Product UUID

        Returns:
            Success/failure result

        """
        try:
            await (
                self.db.client.table("wishlist")
                .delete()
                .eq("user_id", user_id)
                .eq("product_id", product_id)
                .execute()
            )

            return {"success": True, "message": "Removed from wishlist"}
        except Exception as e:
            logger.error("Failed to remove from wishlist: %s", type(e).__name__, exc_info=True)
            return {"success": False, "reason": "Failed to remove"}

    async def is_in_wishlist(self, user_id: str, product_id: str) -> bool:
        """Check if product is in user's wishlist.

        Args:
            user_id: User database ID
            product_id: Product UUID

        Returns:
            True if in wishlist

        """
        try:
            result = (
                await self.db.client.table("wishlist")
                .select("id")
                .eq("user_id", user_id)
                .eq("product_id", product_id)
                .execute()
            )
            return bool(result.data)
        except Exception:
            return False
