"""
Catalog Domain Service

Handles product search, discovery, and availability checking.
Combines RAG (semantic search) with traditional database queries.
"""

from dataclasses import dataclass
from typing import Any

from core.logging import get_logger
from core.services.models import Product

logger = get_logger(__name__)


@dataclass
class ProductAvailability:
    """Product availability check result."""

    found: bool
    product_id: str | None = None
    name: str | None = None
    price: float = 0.0
    in_stock: bool = False
    stock_count: int = 0
    status: str = "active"
    is_discontinued: bool = False
    can_fulfill_on_demand: bool = False
    fulfillment_time_hours: int | None = None
    requires_prepayment: bool = False


@dataclass
class ProductDetails:
    """Full product details."""

    found: bool
    id: str | None = None
    name: str | None = None
    description: str | None = None
    price: float = 0.0
    type: str | None = None
    in_stock: bool = False
    stock_count: int = 0
    warranty_hours: int = 24
    instructions: str | None = None
    rating: float = 0.0
    reviews_count: int = 0


@dataclass
class SearchResult:
    """Product search result."""

    id: str
    name: str
    price: float
    in_stock: bool
    stock_count: int
    similarity_score: float = 0.0


@dataclass
class PurchaseIntent:
    """Purchase intent result."""

    success: bool
    product_id: str | None = None
    product_name: str | None = None
    price: float = 0.0
    order_type: str | None = None  # 'instant' or 'prepaid'
    fulfillment_time_hours: int | None = None
    fulfillment_days: int | None = None
    action: str | None = None
    message: str | None = None
    reason: str | None = None


class CatalogService:
    """
    Catalog domain service.

    Provides clean interface for:
    - Product search (RAG + text fallback)
    - Availability checking
    - Purchase intent creation
    - Waitlist management
    """

    def __init__(self, db):
        self.db = db
        self._rag_search = None

    def _get_rag_search(self):
        """Lazy load RAG search to avoid import errors."""
        if self._rag_search is None:
            try:
                from core.rag import VECS_AVAILABLE, ProductSearch

                if VECS_AVAILABLE:
                    self._rag_search = ProductSearch()
                    if not self._rag_search.is_available:
                        self._rag_search = False  # Mark as unavailable
            except (ImportError, Exception) as e:
                logger.warning(f"RAG search unavailable: {e}")
                self._rag_search = False
        return self._rag_search if self._rag_search else None

    async def check_availability(self, product_name: str) -> ProductAvailability:
        """
        Check if a product is available.

        Args:
            product_name: Full or partial product name

        Returns:
            ProductAvailability with stock info
        """
        products = await self.db.search_products(product_name)
        if not products:
            return ProductAvailability(found=False)

        product = products[0]
        details = await self.db.get_product_by_id(product.id)

        fulfillment_hours = getattr(details, "fulfillment_time_hours", 48) if details else 48
        requires_prepayment = getattr(details, "requires_prepayment", False) if details else False
        status = getattr(details, "status", "active") if details else "active"

        is_discontinued = status == "discontinued"
        can_fulfill = status == "active" and not is_discontinued

        return ProductAvailability(
            found=True,
            product_id=product.id,
            name=product.name,
            price=product.price,
            in_stock=product.stock_count > 0,
            stock_count=product.stock_count,
            status=status,
            is_discontinued=is_discontinued,
            can_fulfill_on_demand=can_fulfill,
            fulfillment_time_hours=fulfillment_hours if can_fulfill else None,
            requires_prepayment=requires_prepayment,
        )

    async def get_details(self, product_id: str) -> ProductDetails:
        """
        Get full product details.

        Args:
            product_id: Product UUID

        Returns:
            ProductDetails with all info
        """
        product = await self.db.get_product_by_id(product_id)
        if not product:
            return ProductDetails(found=False)

        rating = await self.db.get_product_rating(product.id)

        return ProductDetails(
            found=True,
            id=product.id,
            name=product.name,
            description=product.description,
            price=product.price,
            type=product.type,
            in_stock=product.stock_count > 0,
            stock_count=product.stock_count,
            warranty_hours=product.warranty_hours,
            instructions=product.instructions,
            rating=rating.get("average", 0.0),
            reviews_count=rating.get("count", 0),
        )

    async def search(self, query: str, category: str = "all", limit: int = 5) -> list[SearchResult]:
        """
        Search products using RAG (semantic) or text fallback.

        Args:
            query: Search query
            category: Category filter
            limit: Max results

        Returns:
            List of SearchResult
        """
        results = []

        # Try RAG search first
        rag_search = self._get_rag_search()
        if rag_search:
            try:
                filters = {"status": {"$eq": "active"}}
                if category != "all":
                    category_map = {
                        "chatgpt": "shared",
                        "claude": "shared",
                        "midjourney": "shared",
                        "image": "shared",
                        "code": "key",
                        "writing": "shared",
                    }
                    if category in category_map:
                        filters["type"] = {"$eq": category_map[category]}

                rag_results = await rag_search.search(query, limit=limit, filters=filters)

                for result in rag_results:
                    product = await self.db.get_product_by_id(result["product_id"])
                    if product:
                        results.append(
                            SearchResult(
                                id=product.id,
                                name=product.name,
                                price=product.price,
                                in_stock=product.stock_count > 0,
                                stock_count=product.stock_count,
                                similarity_score=result.get("score", 0.0),
                            )
                        )
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")

        # Fallback or supplement with text search
        if len(results) < 3:
            text_products = await self.db.search_products(query)
            existing_ids = {r.id for r in results}

            for p in text_products:
                if p.id not in existing_ids and len(results) < limit:
                    results.append(
                        SearchResult(
                            id=p.id,
                            name=p.name,
                            price=p.price,
                            in_stock=p.stock_count > 0,
                            stock_count=p.stock_count,
                            similarity_score=0.0,
                        )
                    )

        return results[:limit]

    async def get_catalog(self, status: str = "active") -> list[Product]:
        """
        Get full product catalog.

        Args:
            status: Filter by status

        Returns:
            List of Product
        """
        return await self.db.get_products(status=status)

    async def compare(self, product_names: list[str]) -> list[dict[str, Any]]:
        """
        Compare multiple products.

        Args:
            product_names: List of product names to compare

        Returns:
            List of product comparisons
        """
        results = []
        for name in product_names:
            products = await self.db.search_products(name)
            if products:
                p = products[0]
                rating = await self.db.get_product_rating(p.id)
                results.append(
                    {
                        "name": p.name,
                        "price": p.price,
                        "type": p.type,
                        "description": p.description,
                        "in_stock": p.stock_count > 0,
                        "rating": rating.get("average", 0.0),
                    }
                )
        return results

    async def create_purchase_intent(self, product_id: str) -> PurchaseIntent:
        """
        Create purchase intent - validates product and determines order type.

        Args:
            product_id: Product UUID

        Returns:
            PurchaseIntent with order details or rejection reason
        """
        product = await self.db.get_product_by_id(product_id)
        if not product:
            return PurchaseIntent(success=False, reason="Product not found")

        status = getattr(product, "status", "active")

        # Discontinued - not available
        if status == "discontinued":
            return PurchaseIntent(
                success=False, reason="Product is discontinued and no longer available."
            )

        # Coming soon - only waitlist
        if status == "coming_soon":
            return PurchaseIntent(
                success=False, reason="Product is coming soon. Please use waitlist to be notified."
            )

        # Active or out_of_stock - can order
        if product.stock_count > 0:
            return PurchaseIntent(
                success=True,
                product_id=product.id,
                product_name=product.name,
                price=product.price,
                order_type="instant",
                action="show_payment_button",
            )
        fulfillment_hours = getattr(product, "fulfillment_time_hours", 48)
        fulfillment_days = fulfillment_hours // 24
        return PurchaseIntent(
            success=True,
            product_id=product.id,
            product_name=product.name,
            price=product.price,
            order_type="prepaid",
            fulfillment_time_hours=fulfillment_hours,
            fulfillment_days=fulfillment_days,
            action="show_payment_button",
            message=f"Will be made in {fulfillment_days}-{fulfillment_days + 1} days. 100% prepayment.",
        )

    async def add_to_waitlist(self, user_id: str, product_name: str) -> dict[str, Any]:
        """
        Add user to waitlist for coming_soon products.

        Args:
            user_id: User database ID
            product_name: Product name

        Returns:
            Success/failure result
        """
        if not product_name.strip():
            return {"success": False, "reason": "Product name is required"}

        products = await self.db.search_products(product_name)
        if not products:
            return {"success": False, "reason": "Product not found"}

        product = products[0]
        details = await self.db.get_product_by_id(product.id)
        if not details:
            return {"success": False, "reason": "Product not found"}

        status = getattr(details, "status", "active")

        if status == "discontinued":
            return {
                "success": False,
                "reason": "Product is discontinued. Waitlist is not available.",
            }

        if status == "coming_soon":
            try:
                await self.db.add_to_waitlist(user_id, product_name)
                return {
                    "success": True,
                    "product_name": product_name,
                    "message": f"Added to waitlist for {product_name}.",
                }
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    return {
                        "success": True,
                        "product_name": product_name,
                        "message": f"You are already on the waitlist for {product_name}.",
                    }
                raise

        # Active or out_of_stock - can order directly
        return {
            "success": False,
            "reason": "Product is available for order. You can purchase it directly.",
        }
