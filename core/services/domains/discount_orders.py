"""Discount order service for delayed delivery via QStash.

Implements artificial delay (1-4 hours) for discount bot orders.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx

from pydantic import BaseModel

from core.logging import get_logger

logger = get_logger(__name__)


# ============================================
# Models
# ============================================

class DelayedDeliveryTask(BaseModel):
    """Task for delayed delivery."""
    order_id: str
    order_item_id: str
    telegram_id: int
    stock_item_id: str
    scheduled_at: datetime
    delay_minutes: int


# ============================================
# Service
# ============================================

class DiscountOrderService:
    """Discount order operations with delayed delivery.
    
    Orders from discount bot are queued for 1-4 hour delay via QStash.
    This differentiates from PVNDORA's instant delivery.
    """
    
    # Delay range in minutes (1-4 hours)
    MIN_DELAY_MINUTES = 60
    MAX_DELAY_MINUTES = 240
    
    def __init__(self, db_client):
        self.client = db_client
        self.qstash_token = os.environ.get("QSTASH_TOKEN", "")
        self.qstash_url = os.environ.get("QSTASH_URL", "https://qstash.upstash.io")
        
        # Get base URL for worker endpoints (same logic as core/queue.py)
        webapp_url = os.environ.get("WEBAPP_URL", "")
        base_url = os.environ.get("BASE_URL", "")
        
        if webapp_url:
            self.base_url = webapp_url.rstrip("/") if webapp_url.startswith("http") else f"https://{webapp_url}"
        elif base_url:
            self.base_url = base_url.rstrip("/") if base_url.startswith("http") else f"https://{base_url}"
        else:
            # Fallback to TELEGRAM_WEBHOOK_URL and extract base
            telegram_webhook = os.environ.get("TELEGRAM_WEBHOOK_URL", "https://pvndora.app")
            self.base_url = telegram_webhook.rsplit("/api", 1)[0].rsplit("/webhook", 1)[0].rstrip("/")
    
    def _calculate_delay(self) -> int:
        """Calculate random delay between MIN and MAX minutes."""
        return random.randint(self.MIN_DELAY_MINUTES, self.MAX_DELAY_MINUTES)
    
    async def schedule_delayed_delivery(
        self,
        order_id: str,
        order_item_id: str,
        telegram_id: int,
        stock_item_id: str
    ) -> Optional[DelayedDeliveryTask]:
        """Schedule delayed delivery via QStash.
        
        Args:
            order_id: The order UUID
            order_item_id: The order item UUID
            telegram_id: User's Telegram ID for notification
            stock_item_id: Stock item to deliver
            
        Returns:
            DelayedDeliveryTask if scheduled successfully, None on error
        """
        try:
            delay_minutes = self._calculate_delay()
            scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
            
            # Construct worker endpoint
            worker_url = f"{self.base_url}/api/workers/deliver-discount-order"
            
            # QStash publish with delay
            publish_url = f"{self.qstash_url}/v2/publish/{worker_url}"
            
            headers = {
                "Authorization": f"Bearer {self.qstash_token}",
                "Content-Type": "application/json",
                "Upstash-Delay": f"{delay_minutes}m"
            }
            
            payload = {
                "order_id": order_id,
                "order_item_id": order_item_id,
                "telegram_id": telegram_id,
                "stock_item_id": stock_item_id,
                "scheduled_at": scheduled_at.isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    publish_url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code not in (200, 201, 202):
                    logger.error(f"QStash publish failed: {response.status_code} - {response.text}")
                    return None
            
            logger.info(
                f"Scheduled delivery for order {order_id} in {delay_minutes} minutes "
                f"(at {scheduled_at.isoformat()})"
            )
            
            # Update order with scheduled delivery time
            await self.client.table("orders").update({
                "scheduled_delivery_at": scheduled_at.isoformat()
            }).eq("id", order_id).execute()
            
            return DelayedDeliveryTask(
                order_id=order_id,
                order_item_id=order_item_id,
                telegram_id=telegram_id,
                stock_item_id=stock_item_id,
                scheduled_at=scheduled_at,
                delay_minutes=delay_minutes
            )
            
        except Exception as e:
            logger.error(f"Failed to schedule delayed delivery: {e}")
            return None
    
    async def get_estimated_delivery_time(self, order_id: str) -> Optional[datetime]:
        """Get scheduled delivery time for an order."""
        try:
            result = await self.client.table("orders").select(
                "scheduled_delivery_at"
            ).eq("id", order_id).single().execute()
            
            if result.data and result.data.get("scheduled_delivery_at"):
                return datetime.fromisoformat(
                    result.data["scheduled_delivery_at"].replace("Z", "+00:00")
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get delivery time: {e}")
            return None
    
    async def mark_discount_user(self, telegram_id: int) -> bool:
        """Mark user as originating from discount tier."""
        try:
            await self.client.table("users").update({
                "discount_tier_source": True
            }).eq("telegram_id", telegram_id).execute()
            
            logger.info(f"Marked user {telegram_id} as discount_tier_source")
            return True
        except Exception as e:
            logger.error(f"Failed to mark discount user: {e}")
            return False
    
    async def accept_terms(self, telegram_id: int) -> bool:
        """Record user's acceptance of terms in discount bot."""
        try:
            await self.client.table("users").update({
                "terms_accepted": True,
                "terms_accepted_at": datetime.now(timezone.utc).isoformat()
            }).eq("telegram_id", telegram_id).execute()
            
            logger.info(f"User {telegram_id} accepted terms")
            return True
        except Exception as e:
            logger.error(f"Failed to record terms acceptance: {e}")
            return False
    
    async def check_terms_accepted(self, telegram_id: int) -> bool:
        """Check if user has accepted terms."""
        try:
            result = await self.client.table("users").select(
                "terms_accepted"
            ).eq("telegram_id", telegram_id).single().execute()
            
            return result.data.get("terms_accepted", False) if result.data else False
        except Exception as e:
            logger.error(f"Failed to check terms: {e}")
            return False
