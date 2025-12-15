"""
Order Status Management Service

Centralized service for managing order status transitions.
Ensures status changes only happen after payment confirmation.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)


class OrderStatusService:
    """Centralized service for order status management."""
    
    def __init__(self, db):
        self.db = db
    
    async def get_order_status(self, order_id: str) -> Optional[str]:
        """Get current order status."""
        try:
            result = await asyncio.to_thread(
                lambda: self.db.client.table("orders")
                .select("status")
                .eq("id", order_id)
                .single()
                .execute()
            )
            if result.data:
                return result.data.get("status")
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
        return None
    
    async def can_transition_to(self, order_id: str, target_status: str) -> tuple[bool, Optional[str]]:
        """
        Check if order can transition to target status.
        
        Returns:
            (can_transition, reason_if_not)
        """
        current_status = await self.get_order_status(order_id)
        if not current_status:
            return False, "Order not found"
        
        current_status = current_status.lower()
        target_status = target_status.lower()
        
        # Status transition rules
        transitions = {
            "pending": ["paid", "prepaid", "cancelled", "expired"],
            "paid": ["delivered", "partial", "prepaid", "refunded"],
            "prepaid": ["fulfilling", "ready", "delivered", "refunded", "failed"],
            "fulfilling": ["ready", "delivered", "failed", "refunded"],
            "ready": ["delivered"],
            "partial": ["delivered"],
            "delivered": [],  # Final state
            "cancelled": [],  # Final state
            "expired": ["cancelled", "refunded"],
            "refunded": [],  # Final state
            "failed": ["refunded"],
        }
        
        allowed = transitions.get(current_status, [])
        if target_status not in allowed:
            return False, f"Cannot transition from '{current_status}' to '{target_status}'. Allowed: {allowed}"
        
        return True, None
    
    async def update_status(
        self, 
        order_id: str, 
        new_status: str, 
        reason: Optional[str] = None,
        check_transition: bool = True
    ) -> bool:
        """
        Update order status with validation.
        
        Args:
            order_id: Order ID
            new_status: Target status
            reason: Optional reason for status change
            check_transition: Whether to validate transition rules
            
        Returns:
            True if updated, False otherwise
        """
        logger.info(f"[StatusService] update_status called: order_id={order_id}, new_status={new_status}, check_transition={check_transition}")
        
        if check_transition:
            can_transition, reason_msg = await self.can_transition_to(order_id, new_status)
            if not can_transition:
                logger.warning(f"Cannot update order {order_id} status: {reason_msg}")
                return False
        
        try:
            update_data = {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"[StatusService] Updating order {order_id} with data: {update_data}")
            
            result = await asyncio.to_thread(
                lambda: self.db.client.table("orders")
                .update(update_data)
                .eq("id", order_id)
                .execute()
            )
            
            # Log the result to verify update happened
            rows_affected = len(result.data) if result.data else 0
            logger.info(f"[StatusService] Update result for {order_id}: rows_affected={rows_affected}, data={result.data}")
            
            if rows_affected == 0:
                logger.warning(f"[StatusService] NO ROWS UPDATED for order {order_id}! Order might not exist.")
                return False
            
            logger.info(f"Updated order {order_id} status to '{new_status}'")
            return True
        except Exception as e:
            logger.error(f"Failed to update order {order_id} status: {e}")
            import traceback
            logger.error(f"[StatusService] Traceback: {traceback.format_exc()}")
            return False
    
    async def mark_payment_confirmed(
        self, 
        order_id: str, 
        payment_id: Optional[str] = None,
        check_stock: bool = True
    ) -> str:
        """
        Mark order as payment confirmed.
        
        IDEMPOTENT: If order is already paid/prepaid, returns current status without changes.
        
        Determines correct status based on:
        - Stock availability (if check_stock=True)
        - Order type (instant vs prepaid)
        
        Returns:
            Final status set ('paid' or 'prepaid')
        """
        logger.info(f"[mark_payment_confirmed] Called for order_id={order_id}, payment_id={payment_id}, check_stock={check_stock}")
        
        # Get order info
        try:
            logger.info(f"[mark_payment_confirmed] Fetching order {order_id} from DB...")
            order_result = await asyncio.to_thread(
                lambda: self.db.client.table("orders")
                .select("status, order_type, payment_method")
                .eq("id", order_id)
                .single()
                .execute()
            )
            logger.info(f"[mark_payment_confirmed] Order fetch result: {order_result.data}")
            
            if not order_result.data:
                raise ValueError(f"Order {order_id} not found")
            
            current_status = order_result.data.get("status", "").lower()
            order_type = order_result.data.get("order_type", "instant")
            payment_method = order_result.data.get("payment_method", "")
            
            logger.info(f"[mark_payment_confirmed] Order {order_id}: current_status={current_status}, order_type={order_type}, payment_method={payment_method}")
            
            # IDEMPOTENCY: If already paid/prepaid/delivered, return current status
            if current_status in ("paid", "prepaid", "delivered", "partial"):
                logger.info(f"Order {order_id} already in status '{current_status}' (idempotency check), skipping")
                return current_status
            
            # Check stock availability for ALL payment methods (including balance)
            # Balance payment doesn't mean stock is available!
            if check_stock:
                logger.info("[mark_payment_confirmed] Checking stock availability...")
                has_stock = await self._check_stock_availability(order_id)
                final_status = "paid" if has_stock else "prepaid"
                logger.info(f"[mark_payment_confirmed] has_stock={has_stock}, final_status={final_status}, payment_method={payment_method}")
            else:
                # If not checking stock, default to 'prepaid' for safety
                final_status = "prepaid"
            
            # Update payment_id if provided
            if payment_id:
                try:
                    logger.info(f"[mark_payment_confirmed] Updating payment_id to {payment_id}")
                    await asyncio.to_thread(
                        lambda: self.db.client.table("orders")
                        .update({"payment_id": payment_id})
                        .eq("id", order_id)
                        .execute()
                    )
                except Exception as e:
                    logger.warning(f"Failed to update payment_id for {order_id}: {e}")
            
            logger.info(f"[mark_payment_confirmed] About to call update_status with final_status={final_status}")
            update_result = await self.update_status(order_id, final_status, "Payment confirmed via webhook", check_transition=False)
            logger.info(f"[mark_payment_confirmed] update_status returned: {update_result}")
            
            if not update_result:
                logger.error(f"[mark_payment_confirmed] FAILED to update order {order_id} status to {final_status}!")
            
            # Set fulfillment deadline for prepaid orders
            if final_status == "prepaid":
                try:
                    logger.info(f"[mark_payment_confirmed] Setting fulfillment deadline for prepaid order {order_id}")
                    await asyncio.to_thread(
                        lambda: self.db.client.rpc("set_fulfillment_deadline_for_prepaid_order", {
                            "p_order_id": order_id,
                            "p_hours_from_now": 48
                        }).execute()
                    )
                except Exception as e:
                    logger.warning(f"Failed to set fulfillment deadline for {order_id}: {e}")
            
            return final_status
            
        except Exception as e:
            logger.error(f"Failed to mark payment confirmed for {order_id}: {e}")
            import traceback
            logger.error(f"[mark_payment_confirmed] Traceback: {traceback.format_exc()}")
            raise
    
    async def _check_stock_availability(self, order_id: str) -> bool:
        """Check if order has available stock for instant delivery.
        
        IMPORTANT: Checks REAL stock availability, not just fulfillment_type.
        Even if item was created as 'instant', stock might be gone by payment time.
        """
        try:
            # Get order items
            items_result = await asyncio.to_thread(
                lambda: self.db.client.table("order_items")
                .select("product_id, fulfillment_type")
                .eq("order_id", order_id)
                .execute()
            )
            
            if not items_result.data:
                return False
            
            # Check REAL stock availability for each product
            # Don't trust fulfillment_type - check actual stock_items table
            product_ids = list({item.get("product_id") for item in items_result.data if item.get("product_id")})
            
            for product_id in product_ids:
                # Check if product has ANY available stock right now
                stock_check = await asyncio.to_thread(
                    lambda pid=product_id: self.db.client.table("stock_items")
                    .select("id")
                    .eq("product_id", pid)
                    .eq("status", "available")
                    .eq("is_sold", False)
                    .limit(1)
                    .execute()
                )
                if stock_check.data:
                    # At least one product has stock
                    return True
            
            # No stock available for any product
            return False
        except Exception as e:
            logger.error(f"Failed to check stock availability for {order_id}: {e}")
            return False
    
    async def update_delivery_status(
        self, 
        order_id: str,
        delivered_count: int,
        waiting_count: int
    ) -> Optional[str]:
        """
        Update order status based on delivery results.
        
        Args:
            order_id: Order ID
            delivered_count: Number of items delivered
            waiting_count: Number of items waiting for stock
            
        Returns:
            New status or None if no change
        """
        current_status = await self.get_order_status(order_id)
        if not current_status:
            return None
        
        # Only update if payment is confirmed
        if current_status.lower() == "pending":
            logger.warning(f"Order {order_id} is still pending - cannot update delivery status")
            return None
        
        new_status = None
        if delivered_count > 0 and waiting_count == 0:
            new_status = "delivered"
        elif delivered_count > 0 and waiting_count > 0:
            new_status = "partial"
        # Don't set to 'prepaid' here - should already be set by payment confirmation
        
        if new_status and new_status != current_status.lower():
            await self.update_status(order_id, new_status, f"Delivery: {delivered_count} delivered, {waiting_count} waiting")
            return new_status
        
        return None
