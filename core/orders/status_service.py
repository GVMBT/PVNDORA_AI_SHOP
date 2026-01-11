"""
Order Status Management Service

Centralized service for managing order status transitions.
Ensures status changes only happen after payment confirmation.

All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
from datetime import datetime, timezone
from typing import Optional

from core.logging import get_logger

logger = get_logger(__name__)


class OrderStatusService:
    """Centralized service for order status management."""
    
    def __init__(self, db):
        self.db = db
    
    async def get_order_status(self, order_id: str) -> Optional[str]:
        """Get current order status."""
        try:
            result = await self.db.client.table("orders").select(
                "status"
            ).eq("id", order_id).single().execute()
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
        
        # Status transition rules (simplified)
        # See docs/ORDER_STATUSES.md for details
        transitions = {
            "pending": ["paid", "prepaid", "cancelled"],
            "paid": ["delivered", "partial", "cancelled", "refunded"],
            "prepaid": ["paid", "partial", "delivered", "cancelled", "refunded"],
            "partial": ["delivered", "cancelled", "refunded"],
            "delivered": [],  # Final state
            "cancelled": [],  # Final state
            "refunded": [],  # Final state
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
            
            result = await self.db.client.table("orders").update(
                update_data
            ).eq("id", order_id).execute()
            
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
            order_result = await self.db.client.table("orders").select(
                "status, order_type, payment_method, user_id, amount, fiat_amount, fiat_currency"
            ).eq("id", order_id).single().execute()
            logger.info(f"[mark_payment_confirmed] Order fetch result: {order_result.data}")
            
            if not order_result.data:
                raise ValueError(f"Order {order_id} not found")
            
            current_status = order_result.data.get("status", "").lower()
            order_type = order_result.data.get("order_type", "instant")
            payment_method = order_result.data.get("payment_method", "")
            user_id = order_result.data.get("user_id")
            order_amount = order_result.data.get("amount", 0)
            fiat_amount = order_result.data.get("fiat_amount")
            fiat_currency = order_result.data.get("fiat_currency")
            
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
                    await self.db.client.table("orders").update({
                        "payment_id": payment_id
                    }).eq("id", order_id).execute()
                except Exception as e:
                    logger.warning(f"Failed to update payment_id for {order_id}: {e}")
            
            logger.info(f"[mark_payment_confirmed] About to call update_status with final_status={final_status}")
            update_result = await self.update_status(order_id, final_status, "Payment confirmed via webhook", check_transition=False)
            logger.info(f"[mark_payment_confirmed] update_status returned: {update_result}")
            
            if not update_result:
                logger.error(f"[mark_payment_confirmed] FAILED to update order {order_id} status to {final_status}!")
            else:
                # Send admin alert for paid orders (best-effort)
                try:
                    await self._send_order_alert(order_id, order_amount, user_id)
                except Exception as e:
                    logger.warning(f"Failed to send admin alert for order {order_id}: {e}")
                
                # Send payment confirmation to user (best-effort)
                try:
                    # Get user telegram_id and order details
                    user_order_result = await self.db.client.table("orders").select(
                        "user_telegram_id, fiat_amount, fiat_currency, amount"
                    ).eq("id", order_id).single().execute()
                    
                    if user_order_result.data:
                        telegram_id = user_order_result.data.get("user_telegram_id")
                        fiat_amount = user_order_result.data.get("fiat_amount")
                        fiat_currency = user_order_result.data.get("fiat_currency") or "USD"
                        usd_amount = float(user_order_result.data.get("amount", 0))
                        
                        if telegram_id:
                            # Use fiat_amount if available
                            display_amount = float(fiat_amount) if fiat_amount else usd_amount
                            display_currency = fiat_currency if fiat_amount else "USD"
                            
                            # Count preorder items
                            items_result = await self.db.client.table("order_items").select(
                                "fulfillment_type"
                            ).eq("order_id", order_id).execute()
                            preorder_count = sum(1 for item in (items_result.data or []) if item.get("fulfillment_type") == "preorder")
                            has_instant = any(item.get("fulfillment_type") != "preorder" for item in (items_result.data or []))
                            
                            from core.routers.deps import get_notification_service
                            notification_service = get_notification_service()
                            await notification_service.send_payment_confirmed(
                                telegram_id=telegram_id,
                                order_id=order_id,
                                amount=display_amount,
                                currency=display_currency,
                                status=final_status,
                                has_instant_items=has_instant,
                                preorder_count=preorder_count
                            )
                except Exception as e:
                    logger.warning(f"Failed to send payment confirmation to user for order {order_id}: {e}")
            
            # Create balance_transaction record for purchase (for system_log visibility)
            # Only for external payments (not balance) - balance payments already create records via add_to_user_balance
            if payment_method and payment_method.lower() != "balance" and user_id and order_amount:
                try:
                    # Check if transaction already exists (idempotency)
                    existing_tx = await self.db.client.table("balance_transactions").select(
                        "id"
                    ).eq("user_id", user_id).eq("type", "purchase").eq(
                        "description", f"Purchase: Order {order_id}"
                    ).limit(1).execute()
                    
                    if not existing_tx.data:
                        # Get user's current balance for logging
                        user_result = await self.db.client.table("users").select(
                            "balance"
                        ).eq("id", user_id).single().execute()
                        current_balance = float(user_result.data.get("balance", 0)) if user_result.data else 0
                        
                        # Use fiat_amount and fiat_currency if available (real payment amount), otherwise fallback to USD amount
                        if fiat_amount is not None and fiat_currency:
                            transaction_amount = float(fiat_amount)
                            transaction_currency = fiat_currency
                        else:
                            # Fallback: use USD amount (legacy orders)
                            transaction_amount = float(order_amount)
                            transaction_currency = "USD"
                        
                        # Create purchase transaction record
                        await self.db.client.table("balance_transactions").insert({
                            "user_id": user_id,
                            "type": "purchase",
                            "amount": transaction_amount,
                            "currency": transaction_currency,
                            "balance_before": current_balance,
                            "balance_after": current_balance,  # Balance doesn't change for external payments
                            "status": "completed",
                            "description": f"Purchase: Order {order_id}",
                            "metadata": {
                                "order_id": order_id,
                                "payment_method": payment_method,
                                "payment_id": payment_id
                            }
                        }).execute()
                        logger.info(f"[mark_payment_confirmed] Created balance_transaction for purchase order {order_id}: {transaction_amount} {transaction_currency}")
                    else:
                        logger.info(f"[mark_payment_confirmed] balance_transaction already exists for order {order_id}, skipping")
                except Exception as e:
                    logger.warning(f"Failed to create balance_transaction for order {order_id}: {e}")
                    # Non-critical - don't fail the payment confirmation
            
            # Set fulfillment deadline for orders with preorder items
            # Check if order has any preorder items (regardless of final_status)
            try:
                items_result = await self.db.client.table("order_items").select(
                    "fulfillment_type"
                ).eq("order_id", order_id).execute()
                has_preorder_items = any(
                    item.get("fulfillment_type") == "preorder" 
                    for item in (items_result.data or [])
                )
                
                if has_preorder_items:
                    logger.info(f"[mark_payment_confirmed] Setting fulfillment deadline for order {order_id} with preorder items (final_status={final_status})")
                    await self.db.client.rpc("set_fulfillment_deadline_for_prepaid_order", {
                        "p_order_id": order_id,
                        "p_hours_from_now": 24
                    }).execute()
                else:
                    logger.info(f"[mark_payment_confirmed] Order {order_id} has no preorder items, skipping fulfillment_deadline")
            except Exception as e:
                logger.warning(f"Failed to set fulfillment deadline for {order_id}: {e}")
            
            # CRITICAL: Create order_expenses for accounting (best-effort, non-blocking)
            if update_result:
                try:
                    logger.info(f"[mark_payment_confirmed] Creating order_expenses for order {order_id}")
                    await self.db.client.rpc("calculate_order_expenses", {
                        "p_order_id": order_id
                    }).execute()
                    logger.info(f"[mark_payment_confirmed] Successfully created order_expenses for order {order_id}")
                except Exception as e:
                    logger.warning(f"Failed to create order_expenses for order {order_id}: {e}")
                    # Non-critical - don't fail payment confirmation
            
            return final_status
            
        except Exception as e:
            logger.error(f"Failed to mark payment confirmed for {order_id}: {e}")
            import traceback
            logger.error(f"[mark_payment_confirmed] Traceback: {traceback.format_exc()}")
            raise
    
    async def _send_order_alert(self, order_id: str, amount: float, user_id: str) -> None:
        """Send admin alert for new paid order (best-effort)."""
        try:
            from core.services.admin_alerts import get_admin_alert_service
            
            # Get order details for alert - include fiat_amount to show what user actually paid
            order_details = await self.db.client.table("orders").select(
                "fiat_amount, fiat_currency, users(telegram_id, username)"
            ).eq("id", order_id).single().execute()
            
            user_data = order_details.data.get("users", {}) or {} if order_details.data else {}
            telegram_id = user_data.get("telegram_id", 0)
            username = user_data.get("username")
            
            # Use fiat_amount if available (what user actually paid), otherwise fallback to USD amount
            fiat_amount = order_details.data.get("fiat_amount") if order_details.data else None
            currency = order_details.data.get("fiat_currency", "RUB") if order_details.data else "RUB"
            
            # Use fiat_amount if available, otherwise convert USD amount
            if fiat_amount is not None:
                display_amount = float(fiat_amount)
            else:
                # Fallback: convert USD to user's currency (best-effort)
                display_amount = float(amount)
                # If no fiat_currency, assume RUB
                if currency == "RUB" and amount < 10:
                    # Likely USD amount, convert roughly (best-effort)
                    from core.db import get_redis
                    from core.services.currency import get_currency_service
                    try:
                        redis = get_redis()
                        currency_service = get_currency_service(redis)
                        display_amount = await currency_service.convert_price(amount, currency)
                    except Exception:
                        pass  # Keep USD amount if conversion fails
            
            # Get product name from order items
            items_result = await self.db.client.table("order_items").select(
                "quantity, products(name)"
            ).eq("order_id", order_id).limit(3).execute()
            
            product_names = []
            total_qty = 0
            for item in (items_result.data or []):
                prod = item.get("products", {}) or {}
                name = prod.get("name", "Unknown")
                qty = item.get("quantity", 1)
                product_names.append(name)
                total_qty += qty
            
            product_display = ", ".join(product_names[:2])
            if len(product_names) > 2:
                product_display += f" +{len(product_names) - 2}"
            
            alert_service = get_admin_alert_service()
            await alert_service.alert_new_order(
                order_id=order_id,
                amount=display_amount,
                currency=currency,
                user_telegram_id=telegram_id,
                username=username,
                product_name=product_display or "Unknown",
                quantity=total_qty
            )
        except Exception as e:
            logger.warning(f"Failed to send order alert: {e}")
    
    async def _check_stock_availability(self, order_id: str) -> bool:
        """Check if order has available stock for instant delivery.
        
        IMPORTANT: Checks REAL stock availability, not just fulfillment_type.
        Even if item was created as 'instant', stock might be gone by payment time.
        """
        try:
            # Get order items
            items_result = await self.db.client.table("order_items").select(
                "product_id, fulfillment_type"
            ).eq("order_id", order_id).execute()
            
            if not items_result.data:
                return False
            
            # Check REAL stock availability for each product
            # Don't trust fulfillment_type - check actual stock_items table
            product_ids = list({item.get("product_id") for item in items_result.data if item.get("product_id")})
            
            for product_id in product_ids:
                # Check if product has ANY available stock right now
                stock_check = await self.db.client.table("stock_items").select(
                    "id"
                ).eq("product_id", product_id).eq("status", "available").limit(1).execute()
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
        waiting_count: int,
        current_status: Optional[str] = None
    ) -> Optional[str]:
        """
        Update order status based on delivery results.
        
        Args:
            order_id: Order ID
            delivered_count: Number of items delivered
            waiting_count: Number of items waiting for stock
            current_status: Optional current status (to avoid GET request)
            
        Returns:
            New status or None if no change
        """
        # OPTIMIZATION: Use provided current_status if available, otherwise fetch
        if current_status is None:
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
            await self.update_status(order_id, new_status, f"Delivery: {delivered_count} delivered, {waiting_count} waiting", check_transition=False)
            return new_status
        
        return None
