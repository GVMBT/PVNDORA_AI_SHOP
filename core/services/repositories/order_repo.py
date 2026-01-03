"""Order Repository - Order operations."""
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from .base import BaseRepository
from core.services.models import Order


class OrderRepository(BaseRepository):
    """Order database operations."""
    
    async def create(
        self,
        user_id: str,
        amount: float,
        original_price: Optional[float] = None,
        discount_percent: int = 0,
        payment_method: str = "card",
        payment_gateway: str = "crystalpay",
        user_telegram_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        payment_url: Optional[str] = None,
        source_channel: str = "premium"
    ) -> Order:
        """Create new order with payment expiration.
        
        Note: product_id removed - products are stored in order_items table.
        
        Args:
            source_channel: Order origin - 'premium' (PVNDORA), 'discount' (discount bot), 'migrated' (converted user)
        """
        data = {
            "user_id": user_id,
            "amount": amount,
            "original_price": original_price or amount,
            "discount_percent": discount_percent,
            "status": "pending",
            "payment_method": payment_method,
            "payment_gateway": payment_gateway,
            "source_channel": source_channel
        }
        if user_telegram_id:
            data["user_telegram_id"] = user_telegram_id
        if expires_at:
            data["expires_at"] = expires_at.isoformat()
        if payment_url:
            data["payment_url"] = payment_url
        
        # Debug: ensure product_id is not in data
        if "product_id" in data:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"ERROR: product_id found in order data: {data}")
            raise ValueError("product_id should not be in order data - it was removed from orders table")
        
        # Remove any deprecated fields that might accidentally be in data
        deprecated_fields = ["product_id", "stock_item_id", "delivery_content", "delivery_instructions"]
        for field in deprecated_fields:
            if field in data:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Removed deprecated field '{field}' from order data before insert")
                data.pop(field, None)
        
        result = self.client.table("orders").insert(data).execute()
        return Order(**result.data[0])
    
    async def get_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        result = self.client.table("orders").select("*").eq("id", order_id).execute()
        return Order(**result.data[0]) if result.data else None
    
    async def update_status(
        self,
        order_id: str,
        status: str,
        expires_at: Optional[datetime] = None
    ) -> None:
        """Update order status.
        
        Note: stock_item_id removed - stock items are linked via order_items table.
        """
        data = {"status": status}
        
        if expires_at:
            data["expires_at"] = expires_at.isoformat()
        if status == "delivered":
            data["delivered_at"] = datetime.now(timezone.utc).isoformat()
        
        self.client.table("orders").update(data).eq("id", order_id).execute()
    
    async def get_by_user(self, user_id: str, limit: int = 10, offset: int = 0) -> List[Order]:
        """Get user's orders with pagination."""
        query = self.client.table("orders").select("*").eq(
            "user_id", user_id
        ).order("created_at", desc=True).limit(limit)
        
        if offset > 0:
            query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        return [Order(**o) for o in result.data]
    
    async def get_expiring(self, days_before: int = 3) -> List[Order]:
        """Get orders expiring in N days."""
        now = datetime.now(timezone.utc)
        target = now + timedelta(days=days_before)
        
        result = self.client.table("orders").select("*").eq("status", "delivered").lt(
            "expires_at", target.isoformat()
        ).gt("expires_at", now.isoformat()).execute()
        
        return [Order(**o) for o in result.data]
    
    async def get_pending_expired(self) -> List[Order]:
        """Get pending orders that have expired (expires_at < now)."""
        now = datetime.now(timezone.utc).isoformat()
        # Get orders where expires_at is set and has passed
        result = self.client.table("orders").select("*").eq("status", "pending").not_.is_("expires_at", "null").lt(
            "expires_at", now
        ).execute()
        return [Order(**o) for o in result.data]
    
    async def get_pending_stale(self, minutes: int = 60) -> List[Order]:
        """Get pending orders older than N minutes (fallback for orders without expires_at)."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        result = self.client.table("orders").select("*").eq("status", "pending").is_("expires_at", "null").lt(
            "created_at", cutoff
        ).execute()
        return [Order(**o) for o in result.data]
    
    async def count_by_status(self, status: str) -> int:
        """Count orders by status."""
        result = self.client.table("orders").select("id", count="exact").eq("status", status).execute()
        return result.count or 0

