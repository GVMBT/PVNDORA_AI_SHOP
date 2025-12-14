"""Product Repository - Product catalog operations."""
from typing import Optional, List, Dict, Any
from .base import BaseRepository
from core.services.models import Product


class ProductRepository(BaseRepository):
    """Product database operations."""
    
    async def get_all(self, status: str = "active") -> List[Product]:
        """Get all products with stock count."""
        result = self.client.table("products").select("*").eq("status", status).execute()
        
        products = []
        for p in result.data:
            stock = self.client.table("stock_items").select("id", count="exact").eq("product_id", p["id"]).eq("status", "available").execute()
            p["stock_count"] = stock.count or 0
            products.append(Product(**p))
        
        return products
    
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID with stock count."""
        result = self.client.table("products").select("*").eq("id", product_id).execute()
        
        if not result.data:
            return None
        
        p = result.data[0]
        stock = self.client.table("stock_items").select("id", count="exact").eq("product_id", product_id).eq("status", "available").execute()
        p["stock_count"] = stock.count or 0
        return Product(**p)
    
    async def search(self, query: str) -> List[Product]:
        """Search products by name or description."""
        result = self.client.table("products").select("*").or_(
            f"name.ilike.%{query}%,description.ilike.%{query}%"
        ).eq("status", "active").execute()
        
        products = []
        for p in result.data:
            stock = self.client.table("stock_items").select("id", count="exact").eq("product_id", p["id"]).eq("status", "available").execute()
            p["stock_count"] = stock.count or 0
            products.append(Product(**p))
        
        return products
    
    async def get_rating(self, product_id: str) -> Dict[str, Any]:
        """Get product rating and review count."""
        reviews = self.client.table("reviews").select("rating").eq("product_id", product_id).execute()
        
        if not reviews.data:
            return {"average": 0, "count": 0}
        
        ratings = [r["rating"] for r in reviews.data if r.get("rating")]
        return {
            "average": round(sum(ratings) / len(ratings), 1) if ratings else 0,
            "count": len(ratings)
        }
    
    async def create(self, data: Dict[str, Any]) -> Product:
        """Create new product."""
        result = self.client.table("products").insert(data).execute()
        return Product(**result.data[0])
    
    async def update(self, product_id: str, data: Dict[str, Any]) -> Optional[Product]:
        """Update product."""
        result = self.client.table("products").update(data).eq("id", product_id).execute()
        return Product(**result.data[0]) if result.data else None

