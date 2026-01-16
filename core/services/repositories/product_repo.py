"""Product Repository - Product catalog operations.

Uses products_with_stock_summary VIEW to eliminate N+1 queries.
All methods properly use async/await with supabase-py v2.
"""

from typing import Any

from core.services.models import Product

from .base import BaseRepository


class ProductRepository(BaseRepository):
    """Product database operations."""

    # View name for aggregated product data (eliminates N+1)
    VIEW_NAME = "products_with_stock_summary"

    async def get_all(self, status: str = "active") -> list[Product]:
        """Get all products with stock count using VIEW (no N+1).

        Uses products_with_stock_summary VIEW which joins products
        with aggregated stock_items counts in a single query.
        """
        result = await self.client.table(self.VIEW_NAME).select("*").eq("status", status).execute()

        return [Product(**p) for p in result.data]

    async def get_by_id(self, product_id: str) -> Product | None:
        """Get product by ID with stock count using VIEW (no N+1)."""
        result = await self.client.table(self.VIEW_NAME).select("*").eq("id", product_id).execute()

        if not result.data:
            return None

        return Product(**result.data[0])

    async def search(self, query: str) -> list[Product]:
        """Search products by name or description using VIEW (no N+1)."""
        result = (
            await self.client.table(self.VIEW_NAME)
            .select("*")
            .or_(f"name.ilike.%{query}%,description.ilike.%{query}%")
            .eq("status", "active")
            .execute()
        )

        return [Product(**p) for p in result.data]

    async def get_rating(self, product_id: str) -> dict[str, Any]:
        """Get product rating and review count."""
        result = (
            await self.client.table("reviews")
            .select("rating")
            .eq("product_id", product_id)
            .execute()
        )

        if not result.data:
            return {"average": 0, "count": 0}

        ratings = [r["rating"] for r in result.data if r.get("rating")]
        return {
            "average": round(sum(ratings) / len(ratings), 1) if ratings else 0,
            "count": len(ratings),
        }

    async def create(self, data: dict[str, Any]) -> Product:
        """Create new product."""
        result = await self.client.table("products").insert(data).execute()
        # Fetch from VIEW to get stock_count = 0
        if not result.data:
            raise ValueError("Failed to create product: no data returned")
        product_id = (
            result.data[0].get("id") if isinstance(result.data[0], dict) else result.data[0]["id"]
        )
        product = await self.get_by_id(product_id)
        if product is None:
            raise ValueError(f"Failed to fetch created product: {product_id}")
        return product

    async def update(self, product_id: str, data: dict[str, Any]) -> Product | None:
        """Update product."""
        result = await self.client.table("products").update(data).eq("id", product_id).execute()
        if not result.data:
            return None
        # Fetch from VIEW to get current stock_count
        return await self.get_by_id(product_id)
