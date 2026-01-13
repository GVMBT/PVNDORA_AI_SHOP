"""
Order Status Management Service

Centralized service for managing order status transitions.
Ensures status changes only happen after payment confirmation.

All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from datetime import UTC, datetime
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


def _sanitize_id_for_logging(id_value: str) -> str:
    """Sanitize ID for safe logging (truncate to first 8 chars to avoid logging user-controlled data)."""
    return id_value[:8] if id_value else "N/A"


class OrderStatusService:
    """Centralized service for order status management."""

    def __init__(self, db):
        self.db = db

    async def get_order_status(self, order_id: str) -> str | None:
        """Get current order status."""
        try:
            result = (
                await self.db.client.table("orders")
                .select("status")
                .eq("id", order_id)
                .single()
                .execute()
            )
            if result.data:
                return result.data.get("status")
        except Exception:
            logger.exception("Failed to get order status")
        return None

    async def can_transition_to(self, order_id: str, target_status: str) -> tuple[bool, str | None]:
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
            return (
                False,
                f"Cannot transition from '{current_status}' to '{target_status}'. Allowed: {allowed}",
            )

        return True, None

    async def update_status(
        self,
        order_id: str,
        new_status: str,
        reason: str | None = None,
        check_transition: bool = True,
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
        order_id_safe = _sanitize_id_for_logging(order_id)
        logger.debug(
            f"[StatusService] update_status called: order_id={order_id_safe}, new_status={new_status}, check_transition={check_transition}"
        )

        if check_transition:
            can_transition, reason_msg = await self.can_transition_to(order_id, new_status)
            if not can_transition:
                logger.warning("Cannot update order status: transition not allowed")
                return False

        try:
            update_data = {
                "status": new_status,
                "updated_at": datetime.now(UTC).isoformat(),
            }

            order_id_safe = _sanitize_id_for_logging(order_id)
            logger.debug("[StatusService] Updating order %s status", order_id_safe)

            result = (
                await self.db.client.table("orders")
                .update(update_data)
                .eq("id", order_id)
                .execute()
            )

            # Log the result to verify update happened
            rows_affected = len(result.data) if result.data else 0
            logger.debug("[StatusService] Update result: rows_affected=%d", rows_affected)

            if rows_affected == 0:
                logger.warning("[StatusService] NO ROWS UPDATED! Order might not exist.")
                return False

            logger.info("Updated order status successfully")
            return True
        except Exception:
            logger.exception("Failed to update order status")
            import traceback

            logger.exception("[StatusService] Traceback: %s", traceback.format_exc())
            return False

    async def mark_payment_confirmed(
        self, order_id: str, payment_id: str | None = None, check_stock: bool = True
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
        order_id_safe = _sanitize_id_for_logging(order_id)
        logger.debug(
            "[mark_payment_confirmed] Called for order_id=%s, check_stock=%s",
            order_id_safe,
            check_stock,
        )

        # Get order info
        try:
            order_id_safe = _sanitize_id_for_logging(order_id)
            logger.debug("[mark_payment_confirmed] Fetching order %s from DB...", order_id_safe)
            # OPTIMIZATION #6: Include user_telegram_id to avoid duplicate query later
            order_result = (
                await self.db.client.table("orders")
                .select(
                    "status, order_type, payment_method, user_id, user_telegram_id, amount, fiat_amount, fiat_currency"
                )
                .eq("id", order_id)
                .single()
                .execute()
            )
            # Don't log full order data (security: user-controlled data)
            logger.debug("[mark_payment_confirmed] Order fetched successfully")

            if not order_result.data:
                order_id_safe = _sanitize_id_for_logging(order_id)
                raise ValueError(f"Order {order_id_safe} not found")

            current_status = order_result.data.get("status", "").lower()
            order_type = order_result.data.get("order_type", "instant")
            payment_method = order_result.data.get("payment_method", "")
            user_id = order_result.data.get("user_id")
            user_telegram_id = order_result.data.get(
                "user_telegram_id"
            )  # OPTIMIZATION #6: Extract from first query
            order_amount = order_result.data.get("amount", 0)
            fiat_amount = order_result.data.get("fiat_amount")
            fiat_currency = order_result.data.get("fiat_currency")

            logger.debug(
                "[mark_payment_confirmed] Order status: current_status=%s, order_type=%s, payment_method=%s",
                current_status,
                order_type,
                payment_method,
            )

            # IDEMPOTENCY: If already paid/prepaid/delivered, return current status
            if current_status in ("paid", "prepaid", "delivered", "partial"):
                logger.debug(
                    "Order already in status '%s' (idempotency check), skipping", current_status
                )
                return current_status

            # Determine final status based on stock availability
            final_status = await self._determine_final_status(order_id, check_stock)

            # Update payment_id if provided
            if payment_id:
                try:
                    logger.debug("[mark_payment_confirmed] Updating payment_id")
                    await (
                        self.db.client.table("orders")
                        .update({"payment_id": payment_id})
                        .eq("id", order_id)
                        .execute()
                    )
                except Exception:
                    logger.warning("Failed to update payment_id", exc_info=True)

            logger.debug(
                "[mark_payment_confirmed] About to call update_status with final_status=%s",
                final_status,
            )
            update_result = await self.update_status(
                order_id, final_status, "Payment confirmed via webhook", check_transition=False
            )
            logger.debug("[mark_payment_confirmed] update_status returned: %s", update_result)

            # OPTIMIZATION #6: Parallelize independent queries (order_items and user balance)
            import asyncio

            async def fetch_order_items():
                """Fetch order_items for notification and fulfillment deadline."""
                try:
                    result = (
                        await self.db.client.table("order_items")
                        .select("fulfillment_type")
                        .eq("order_id", order_id)
                        .execute()
                    )
                    return result.data or []
                except Exception:
                    logger.warning("Failed to fetch order_items", exc_info=True)
                    return []

            async def fetch_user_balance_and_check_tx():
                """Fetch user balance and check if transaction exists (only if needed)."""
                if (
                    payment_method
                    and payment_method.lower() != "balance"
                    and user_id
                    and order_amount
                ):
                    try:
                        # Check if transaction already exists (idempotency)
                        existing_tx = (
                            await self.db.client.table("balance_transactions")
                            .select("id")
                            .eq("user_id", user_id)
                            .eq("type", "purchase")
                            .eq("description", f"Purchase: Order {order_id}")
                            .limit(1)
                            .execute()
                        )

                        if not existing_tx.data:
                            # Get user's current balance for logging
                            user_result = (
                                await self.db.client.table("users")
                                .select("balance")
                                .eq("id", user_id)
                                .single()
                                .execute()
                            )
                            balance = (
                                float(user_result.data.get("balance", 0)) if user_result.data else 0
                            )
                            return balance, False  # (balance, tx_exists)
                        return None, True  # Transaction exists
                    except Exception:
                        logger.warning("Failed to fetch user balance", exc_info=True)
                        return None, False
                return None, False  # Not needed

            # Execute queries in parallel (outside if/else to use results in both branches)
            items_result, (user_balance, tx_exists) = await asyncio.gather(
                fetch_order_items(), fetch_user_balance_and_check_tx(), return_exceptions=True
            )

            # Handle exceptions
            if isinstance(items_result, Exception):
                items_result = []
            if isinstance(user_balance, Exception) or isinstance(tx_exists, Exception):
                user_balance = None
                tx_exists = False

            if not update_result:
                logger.error("[mark_payment_confirmed] FAILED to update order status")
            else:
                # Send admin alert for paid orders (best-effort)
                try:
                    await self._send_order_alert(order_id, order_amount, user_id)
                except Exception:
                    logger.warning("Failed to send admin alert", exc_info=True)

                # Send payment confirmation to user (best-effort)
                await self._send_payment_notification(
                    user_telegram_id,
                    order_id,
                    order_amount,
                    fiat_amount,
                    fiat_currency,
                    final_status,
                    items_result,
                )

            # Create balance_transaction record for purchase (for system_log visibility)
            # Only for external payments (not balance) - balance payments already create records via add_to_user_balance
            if payment_method and payment_method.lower() != "balance" and user_id and order_amount:
                try:
                    # OPTIMIZATION #6: Use user_balance from parallel query (already fetched above)
                    if user_balance is not None and not tx_exists:
                        current_balance = user_balance

                        # Use fiat_amount and fiat_currency if available (real payment amount), otherwise fallback to USD amount
                        if fiat_amount is not None and fiat_currency:
                            transaction_amount = float(fiat_amount)
                            transaction_currency = fiat_currency
                        else:
                            # Fallback: use USD amount (legacy orders)
                            transaction_amount = float(order_amount)
                            transaction_currency = "USD"

                        # Create purchase transaction record
                        await (
                            self.db.client.table("balance_transactions")
                            .insert(
                                {
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
                                        "payment_id": payment_id,
                                    },
                                }
                            )
                            .execute()
                        )
                        logger.debug(
                            "[mark_payment_confirmed] Created balance_transaction for purchase: %s %s",
                            transaction_amount,
                            transaction_currency,
                        )
                    elif tx_exists:
                        logger.debug(
                            "[mark_payment_confirmed] balance_transaction already exists, skipping"
                        )
                except Exception:
                    logger.warning("Failed to create balance_transaction", exc_info=True)
                    # Non-critical - don't fail the payment confirmation

            # Set fulfillment deadline for orders with preorder items
            await self._set_fulfillment_deadline(order_id, items_result, final_status)

            # CRITICAL: Create order_expenses for accounting (best-effort, non-blocking)
            if update_result:
                try:
                    logger.debug("[mark_payment_confirmed] Creating order_expenses")
                    await self.db.client.rpc(
                        "calculate_order_expenses", {"p_order_id": order_id}
                    ).execute()
                    logger.debug("[mark_payment_confirmed] Successfully created order_expenses")
                except Exception:
                    logger.warning("Failed to create order_expenses", exc_info=True)
                    # Non-critical - don't fail payment confirmation

            return final_status

        except Exception:
            logger.exception("Failed to mark payment confirmed")
            import traceback

            logger.exception("[mark_payment_confirmed] Traceback: %s", traceback.format_exc())
            raise

    async def _calculate_display_amount(
        self, fiat_amount: float | None, amount: float, currency: str
    ) -> float:
        """Calculate display amount for alert (reduces cognitive complexity)."""
        if fiat_amount is not None:
            return float(fiat_amount)

        display_amount = float(amount)
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

        return display_amount

    async def _get_product_display(self, order_id: str) -> tuple[str, int]:
        """Get product display string and total quantity (reduces cognitive complexity)."""
        items_result = (
            await self.db.client.table("order_items")
            .select("quantity, products(name)")
            .eq("order_id", order_id)
            .limit(3)
            .execute()
        )

        product_names = []
        total_qty = 0
        for item in items_result.data or []:
            prod = item.get("products", {}) or {}
            name = prod.get("name", "Unknown")
            qty = item.get("quantity", 1)
            product_names.append(name)
            total_qty += qty

        if not product_names:
            return "Unknown", total_qty

        product_display = ", ".join(product_names[:2])
        if len(product_names) > 2:
            product_display += f" +{len(product_names) - 2}"

        return product_display, total_qty

    async def _send_order_alert(self, order_id: str, amount: float, user_id: str) -> None:
        """Send admin alert for new paid order (best-effort)."""
        try:
            from core.services.admin_alerts import get_admin_alert_service

            order_details = (
                await self.db.client.table("orders")
                .select("fiat_amount, fiat_currency, users(telegram_id, username)")
                .eq("id", order_id)
                .single()
                .execute()
            )

            user_data = order_details.data.get("users", {}) or {} if order_details.data else {}
            telegram_id = user_data.get("telegram_id", 0)
            username = user_data.get("username")

            fiat_amount = order_details.data.get("fiat_amount") if order_details.data else None
            currency = (
                order_details.data.get("fiat_currency", "RUB") if order_details.data else "RUB"
            )

            display_amount = await self._calculate_display_amount(fiat_amount, amount, currency)
            product_display, total_qty = await self._get_product_display(order_id)

            alert_service = get_admin_alert_service()
            await alert_service.alert_new_order(
                order_id=order_id,
                amount=display_amount,
                currency=currency,
                user_telegram_id=telegram_id,
                username=username,
                product_name=product_display,
                quantity=total_qty,
            )
        except Exception:
            logger.warning("Failed to send order alert", exc_info=True)

    # Helper: Determine final status based on stock (reduces cognitive complexity)
    async def _determine_final_status(self, order_id: str, check_stock: bool) -> str:
        """Determine final status (paid/prepaid) based on stock availability."""
        if not check_stock:
            return "prepaid"

        logger.debug("[mark_payment_confirmed] Checking stock availability...")
        has_stock = await self._check_stock_availability(order_id)
        final_status = "paid" if has_stock else "prepaid"
        logger.debug(
            "[mark_payment_confirmed] has_stock=%s, final_status=%s", has_stock, final_status
        )
        return final_status

    # Helper: Send payment confirmation notification (reduces cognitive complexity)
    async def _send_payment_notification(
        self,
        user_telegram_id: int | None,
        order_id: str,
        order_amount: float,
        fiat_amount: float | None,
        fiat_currency: str | None,
        final_status: str,
        items_result: list[dict[str, Any]],
    ) -> None:
        """Send payment confirmation notification to user."""
        if not user_telegram_id:
            return

        try:
            display_amount = float(fiat_amount) if fiat_amount else float(order_amount)
            display_currency = fiat_currency if fiat_amount else "USD"

            preorder_count = sum(
                1 for item in items_result if item.get("fulfillment_type") == "preorder"
            )
            has_instant = any(item.get("fulfillment_type") != "preorder" for item in items_result)

            from core.routers.deps import get_notification_service

            notification_service = get_notification_service()
            await notification_service.send_payment_confirmed(
                telegram_id=user_telegram_id,
                order_id=order_id,
                amount=display_amount,
                currency=display_currency,
                status=final_status,
                has_instant_items=has_instant,
                preorder_count=preorder_count,
            )
        except Exception:
            logger.warning("Failed to send payment confirmation to user", exc_info=True)

    # Helper: Create balance transaction for external payments (reduces cognitive complexity)
    async def _create_purchase_transaction(
        self,
        user_id: str,
        order_id: str,
        order_amount: float,
        fiat_amount: float | None,
        fiat_currency: str | None,
        payment_method: str,
        payment_id: str | None,
        user_balance: float | None,
        tx_exists: bool,
    ) -> None:
        """Create balance_transaction record for external payment purchases."""
        if not user_balance or tx_exists:
            if tx_exists:
                logger.debug(
                    "[mark_payment_confirmed] balance_transaction already exists, skipping"
                )
            return

        try:
            transaction_amount = (
                float(fiat_amount) if fiat_amount is not None else float(order_amount)
            )
            transaction_currency = fiat_currency if fiat_amount else "USD"

            await (
                self.db.client.table("balance_transactions")
                .insert(
                    {
                        "user_id": user_id,
                        "type": "purchase",
                        "amount": transaction_amount,
                        "currency": transaction_currency,
                        "balance_before": user_balance,
                        "balance_after": user_balance,  # Balance doesn't change for external payments
                        "status": "completed",
                        "description": f"Purchase: Order {order_id}",
                        "metadata": {
                            "order_id": order_id,
                            "payment_method": payment_method,
                            "payment_id": payment_id,
                        },
                    }
                )
                .execute()
            )
            logger.debug(
                "[mark_payment_confirmed] Created balance_transaction for purchase: %s %s",
                transaction_amount,
                transaction_currency,
            )
        except Exception:
            logger.warning("Failed to create balance_transaction", exc_info=True)

    # Helper: Set fulfillment deadline for preorder items (reduces cognitive complexity)
    async def _set_fulfillment_deadline(
        self, order_id: str, items_result: list[dict[str, Any]], final_status: str
    ) -> None:
        """Set fulfillment deadline for orders with preorder items."""
        has_preorder_items = any(
            item.get("fulfillment_type") == "preorder" for item in items_result
        )

        if not has_preorder_items:
            logger.debug(
                "[mark_payment_confirmed] Order has no preorder items, skipping fulfillment_deadline"
            )
            return

        try:
            logger.debug(
                "[mark_payment_confirmed] Setting fulfillment deadline for preorder items (final_status=%s)",
                final_status,
            )
            await self.db.client.rpc(
                "set_fulfillment_deadline_for_prepaid_order",
                {"p_order_id": order_id, "p_hours_from_now": 24},
            ).execute()
        except Exception:
            logger.warning("Failed to set fulfillment deadline", exc_info=True)

    async def _check_stock_availability(self, order_id: str) -> bool:
        """Check if order has available stock for instant delivery.

        IMPORTANT: Checks REAL stock availability, not just fulfillment_type.
        Even if item was created as 'instant', stock might be gone by payment time.
        """
        try:
            # Get order items
            items_result = (
                await self.db.client.table("order_items")
                .select("product_id, fulfillment_type")
                .eq("order_id", order_id)
                .execute()
            )

            if not items_result.data:
                return False

            # Check REAL stock availability for each product
            # Don't trust fulfillment_type - check actual stock_items table
            product_ids = list(
                {item.get("product_id") for item in items_result.data if item.get("product_id")}
            )

            for product_id in product_ids:
                # Check if product has ANY available stock right now
                stock_check = (
                    await self.db.client.table("stock_items")
                    .select("id")
                    .eq("product_id", product_id)
                    .eq("status", "available")
                    .limit(1)
                    .execute()
                )
                if stock_check.data:
                    # At least one product has stock
                    return True

            # No stock available for any product
            return False
        except Exception:
            logger.exception("Failed to check stock availability")
            return False

    async def update_delivery_status(
        self,
        order_id: str,
        delivered_count: int,
        waiting_count: int,
        current_status: str | None = None,
    ) -> str | None:
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
            logger.warning("Order is still pending - cannot update delivery status")
            return None

        new_status = None
        if delivered_count > 0 and waiting_count == 0:
            new_status = "delivered"
        elif delivered_count > 0 and waiting_count > 0:
            new_status = "partial"
        # Don't set to 'prepaid' here - should already be set by payment confirmation

        if new_status and new_status != current_status.lower():
            await self.update_status(
                order_id,
                new_status,
                f"Delivery: {delivered_count} delivered, {waiting_count} waiting",
                check_transition=False,
            )
            return new_status

        return None
