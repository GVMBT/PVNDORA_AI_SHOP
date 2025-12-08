"""Order domain service wrapping OrderRepository and related operations."""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from src.services.models import Order, StockItem, Product
from src.services.repositories import OrderRepository


class OrdersDomain:
    """Order domain operations."""

    def __init__(self, repo: OrderRepository, client):
        self.repo = repo
        self.client = client

    # Basic order operations
    async def create(
        self,
        user_id: str,
        product_id: str,
        amount: float,
        original_price: Optional[float] = None,
        discount_percent: int = 0,
        payment_method: str = "card",
        payment_gateway: str = "rukassa",
        user_telegram_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        payment_url: Optional[str] = None,
    ) -> Order:
        return await self.repo.create(
            user_id=user_id,
            product_id=product_id,
            amount=amount,
            original_price=original_price,
            discount_percent=discount_percent,
            payment_method=payment_method,
            payment_gateway=payment_gateway,
            user_telegram_id=user_telegram_id,
            expires_at=expires_at,
            payment_url=payment_url,
        )

    async def get_by_id(self, order_id: str) -> Optional[Order]:
        return await self.repo.get_by_id(order_id)

    async def update_status(
        self,
        order_id: str,
        status: str,
        stock_item_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> None:
        await self.repo.update_status(order_id, status, stock_item_id, expires_at)

    async def get_by_user(self, user_id: str, limit: int = 10, offset: int = 0) -> List[Order]:
        return await self.repo.get_by_user(user_id, limit, offset)

    async def get_expiring(self, days_before: int = 3) -> List[Order]:
        return await self.repo.get_expiring(days_before)

    async def get_pending_expired(self) -> List[Order]:
        return await self.repo.get_pending_expired()

    async def get_pending_stale(self, minutes: int = 60) -> List[Order]:
        return await self.repo.get_pending_stale(minutes)

    async def count_by_status(self, status: str) -> int:
        return await self.repo.count_by_status(status)

    # RPC-based creation with availability
    async def create_with_availability_check(
        self,
        product_id: str,
        user_telegram_id: int,
    ) -> Dict[str, Any]:
        """Call RPC create_order_with_availability_check."""
        def _call_rpc():
            result = self.client.rpc(
                "create_order_with_availability_check",
                {
                    "p_product_id": product_id,
                    "p_user_telegram_id": user_telegram_id,
                },
            ).execute()
            if not result.data:
                raise ValueError("Failed to create order")
            return result.data[0]

        return await asyncio.to_thread(_call_rpc)

    # Order items operations (using raw client)
    async def create_order_items(self, items: List[dict]) -> List[dict]:
        if not items:
            return []
        result = await asyncio.to_thread(
            lambda: self.client.table("order_items").insert(items).execute()
        )
        return result.data or []

    async def get_order_items_by_order(self, order_id: str) -> List[dict]:
        result = await asyncio.to_thread(
            lambda: self.client.table("order_items").select("*").eq("order_id", order_id).execute()
        )
        return result.data or []

    async def get_order_items_by_orders(self, order_ids: List[str]) -> List[dict]:
        if not order_ids:
            return []
        result = await asyncio.to_thread(
            lambda: self.client.table("order_items").select("*").in_("order_id", order_ids).execute()
        )
        return result.data or []

