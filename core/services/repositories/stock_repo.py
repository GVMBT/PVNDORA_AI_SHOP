"""Stock Repository - Stock item operations.

All methods use async/await with supabase-py v2.
"""
from datetime import datetime, timezone
from typing import Optional, List
from .base import BaseRepository
from core.services.models import StockItem, Product


class StockRepository(BaseRepository):
    """Stock item database operations."""
    
    async def get_available(self, product_id: str) -> Optional[StockItem]:
        """Get first available stock item (oldest first)."""
        result = await self.client.table("stock_items").select("*").eq(
            "product_id", product_id
        ).eq("status", "available").order("created_at").limit(1).execute()
        
        return StockItem(**result.data[0]) if result.data else None
    
    async def get_available_count(self, product_id: str) -> int:
        """Get count of available stock items."""
        result = await self.client.table("stock_items").select(
            "id", count="exact"
        ).eq("product_id", product_id).eq("status", "available").execute()
        
        return result.count or 0
    
    async def reserve(self, stock_item_id: str) -> bool:
        """Mark stock item as sold (atomic)."""
        result = await self.client.table("stock_items").update({
            "status": "sold"
        }).eq("id", stock_item_id).eq("status", "available").execute()
        
        return len(result.data) > 0
    
    async def calculate_discount(self, stock_item: StockItem, product: Product) -> int:
        """Calculate age-based discount (max 20%)."""
        if not stock_item.created_at:
            return 0
        
        now = datetime.now(timezone.utc)
        created_at = stock_item.created_at
        
        # Ensure timezone-aware
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        elif created_at.tzinfo != timezone.utc:
            created_at = created_at.astimezone(timezone.utc)
        
        days_in_stock = (now - created_at).days
        
        if days_in_stock < 14:
            return 0
        
        if stock_item.expires_at:
            expires_at = stock_item.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            elif expires_at.tzinfo != timezone.utc:
                expires_at = expires_at.astimezone(timezone.utc)
            total_days = (expires_at - created_at).days
        else:
            total_days = product.warranty_hours // 24 * 365
        
        if total_days <= 0:
            return 0
        
        return min(20, int((days_in_stock / total_days) * 0.5 * 100))
    
    async def create(self, product_id: str, content: str, expires_at: datetime = None, supplier_id: str = None) -> StockItem:
        """Create new stock item."""
        data = {"product_id": product_id, "content": content}
        if expires_at:
            data["expires_at"] = expires_at.isoformat()
        if supplier_id:
            data["supplier_id"] = supplier_id
        
        result = await self.client.table("stock_items").insert(data).execute()
        return StockItem(**result.data[0])
    
    async def get_for_product(self, product_id: str, include_sold: bool = False) -> List[StockItem]:
        """Get all stock items for product."""
        query = self.client.table("stock_items").select("*").eq(
            "product_id", product_id
        )
        if not include_sold:
            query = query.eq("status", "available")
        result = await query.order("created_at", desc=True).execute()
        return [StockItem(**s) for s in result.data]
