"""
QStash Workers Router - Main Router

Central router that aggregates all worker endpoints.
Contains shared utilities like _deliver_items_for_order.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter

from core.logging import get_logger, sanitize_id_for_logging
from core.services.money import to_float

from .broadcast import broadcast_router

# Import sub-routers and include their endpoints
from .delivery import delivery_router
from .payments import payments_router
from .referral import referral_router

logger = get_logger(__name__)

router = APIRouter(prefix="/api/workers", tags=["workers"])

# Include sub-routers
router.include_router(delivery_router)
router.include_router(referral_router)
router.include_router(payments_router)
router.include_router(broadcast_router)


# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


async def _validate_order_for_delivery(db, order_id: str) -> tuple[dict | None, str | None]:
    """
    Validate order status for delivery.

    Returns:
        (order_data, error_response) - error_response is None if valid
    """
    try:
        order_data = (
            await db.client.table("orders")
            .select(
                "status, payment_method, source_channel, user_id, original_price, amount, saved_calculated, user_telegram_id, delivered_at"
            )
            .eq("id", order_id)
            .single()
            .execute()
        )

        if not order_data.data:
            logger.warning("deliver-goods: Order %s not found", sanitize_id_for_logging(order_id))
            return None, "not_found"

        order_status = order_data.data.get("status", "").lower()
        source_channel = order_data.data.get("source_channel", "")

        # SKIP discount orders - they have separate delayed delivery
        if source_channel == "discount":
            logger.info(
                "deliver-goods: Order %s is from discount channel - skipping",
                sanitize_id_for_logging(order_id),
            )
            return None, "discount_channel"

        # If order is still pending, payment is NOT confirmed
        if order_status == "pending":
            logger.warning(
                "deliver-goods: Order %s is still PENDING - payment not confirmed",
                sanitize_id_for_logging(order_id),
            )
            return None, "payment_not_confirmed"

        # Valid statuses for delivery
        valid_statuses = ("paid", "prepaid", "partial", "delivered")
        if order_status not in valid_statuses:
            logger.warning(
                "deliver-goods: Order %s has invalid status '%s' for delivery",
                sanitize_id_for_logging(order_id),
                order_status,
            )
            return None, f"invalid_status:{order_status}"

        return order_data.data, None

    except Exception as e:
        logger.error(
            "deliver-goods: Failed to check order status for %s: %s",
            sanitize_id_for_logging(order_id),
            type(e).__name__,
            exc_info=True,
        )
        # Return empty dict to continue with delivery attempt
        return {}, None


async def _allocate_stock_item(db, product_id: str, now: datetime) -> tuple[str | None, str | None]:
    """
    Find and atomically reserve a stock item for a product.

    Returns:
        (stock_id, stock_content) or (None, None) if no stock available
    """
    try:
        stock_res = (
            await db.client.table("stock_items")
            .select("id,content")
            .eq("product_id", product_id)
            .eq("status", "available")
            .limit(1)
            .execute()
        )
        stock_item = stock_res.data[0] if stock_res.data else None
    except Exception as e:
        logger.exception(f"deliver-goods: stock query failed for product {product_id}: {e}")
        return None, None

    if not stock_item:
        return None, None

    stock_id = stock_item["id"]
    stock_content = stock_item.get("content", "")

    # Atomic update to reserve stock
    try:
        update_result = (
            await db.client.table("stock_items")
            .update({
                "status": "sold",
                "reserved_at": now.isoformat(),
                "sold_at": now.isoformat(),
            })
            .eq("id", stock_id)
            .eq("status", "available")
            .execute()
        )

        if update_result.data:
            return stock_id, stock_content

        logger.warning(f"deliver-goods: stock {stock_id} was already reserved")
        return None, None

    except Exception as e:
        logger.exception(f"deliver-goods: failed to mark stock sold {stock_id}: {e}")
        return None, None


async def _update_order_item_as_delivered(
    db,
    item_id: str,
    stock_id: str,
    stock_content: str,
    instructions: str,
    duration_days: int | None,
    now: datetime,
) -> bool:
    """Update order_item as delivered with stock content."""
    expires_at_str = None
    if duration_days and duration_days > 0:
        expires_at = now + timedelta(days=duration_days)
        expires_at_str = expires_at.isoformat()

    try:
        ts = now.isoformat()
        update_data = {
            "status": "delivered",
            "stock_item_id": stock_id,
            "delivery_content": stock_content,
            "delivery_instructions": instructions,
            "delivered_at": ts,
            "updated_at": ts,
        }
        if expires_at_str:
            update_data["expires_at"] = expires_at_str

        await db.client.table("order_items").update(update_data).eq("id", item_id).execute()
        return True

    except Exception as e:
        logger.exception(f"deliver-goods: failed to update order_item {item_id}: {e}")
        # Rollback: mark stock item as available again
        try:
            await (
                db.client.table("stock_items")
                .update({"status": "available", "reserved_at": None, "sold_at": None})
                .eq("id", stock_id)
                .execute()
            )
        except Exception:
            logger.exception("deliver-goods: failed to rollback stock item")
        return False


async def _process_single_item_delivery(
    db, item: dict, products_map: dict, now: datetime, only_instant: bool
) -> tuple[str | None, bool]:
    """
    Process delivery for a single order item.

    Returns:
        (delivery_line, is_waiting) - delivery_line is None if not delivered
    """
    status = str(item.get("status") or "").lower()
    if status in {"delivered", "cancelled", "refunded"}:
        return None, False  # Already processed

    fulfillment_type = str(item.get("fulfillment_type") or "instant")

    # Skip preorder items in only_instant mode
    if only_instant and fulfillment_type == "preorder":
        logger.debug(f"deliver-goods: skipping preorder item {item.get('id')} (only_instant=True)")
        return None, True  # Waiting

    product_id = item.get("product_id")
    prod = products_map.get(product_id, {})
    prod_name = prod.get("name", "Product")
    item_id = item.get("id")

    # Try to allocate stock
    stock_id, stock_content = await _allocate_stock_item(db, product_id, now)

    if stock_id and stock_content is not None:
        instructions = item.get("delivery_instructions") or prod.get("instructions") or ""
        duration_days = prod.get("duration_days")

        success = await _update_order_item_as_delivered(
            db, item_id, stock_id, stock_content, instructions, duration_days, now
        )

        if success:
            logger.info(
                f"deliver-goods: allocated stock item {stock_id} for product {product_id}, order_item {item_id}"
            )
            return f"{prod_name}:\n{stock_content}", False

        return None, True  # Failed, waiting

    # No stock available - update timestamp only
    logger.debug(f"deliver-goods: NO stock available for product {product_id}")
    try:
        await (
            db.client.table("order_items")
            .update({"updated_at": now.isoformat()})
            .eq("id", item_id)
            .execute()
        )
    except Exception as e:
        logger.error(f"deliver-goods: failed to update timestamp for item {item_id}: {e}")
    return None, True  # Waiting


async def _update_user_total_saved(db, order_data: dict, order_id: str) -> None:
    """Update user's total_saved (discount savings) if not already calculated."""
    if not order_data:
        return

    saved_calculated = order_data.get("saved_calculated", False)
    if saved_calculated:
        return

    user_id = order_data.get("user_id")
    original_price = to_float(order_data.get("original_price") or 0)
    final_amount = to_float(order_data.get("amount") or 0)
    saved_amount = max(0, original_price - final_amount)

    if saved_amount <= 0 or not user_id:
        return

    try:
        user_check = (
            await db.client.table("users")
            .select("total_saved")
            .eq("id", user_id)
            .single()
            .execute()
        )
        current_saved = to_float(user_check.data.get("total_saved") or 0) if user_check.data else 0
        new_saved = current_saved + saved_amount

        await db.client.table("users").update({"total_saved": new_saved}).eq("id", user_id).execute()
        await db.client.table("orders").update({"saved_calculated": True}).eq("id", order_id).execute()

        logger.info(
            f"deliver-goods: Updated total_saved for user {user_id}: {current_saved:.2f} -> {new_saved:.2f}"
        )
    except Exception as e:
        logger.error(f"deliver-goods: Failed to update total_saved for order {order_id}: {e}")


async def _fetch_delivered_items_content(db, order_id: str) -> list[str]:
    """Fetch content from already delivered items for notification."""
    try:
        delivered_items_result = (
            await db.client.table("order_items")
            .select("delivery_content, products(name)")
            .eq("order_id", order_id)
            .eq("status", "delivered")
            .execute()
        )

        lines = []
        for item in delivered_items_result.data or []:
            product_name = (
                item.get("products", {}).get("name")
                if isinstance(item.get("products"), dict)
                else "Product"
            )
            delivery_content = item.get("delivery_content", "")
            if delivery_content:
                lines.append(f"{product_name}:\n{delivery_content}")
        return lines
    except Exception as e:
        logger.error(f"deliver-goods: Failed to fetch delivered items content: {e}")
        return []


async def _send_delivery_notification(
    notification_service, order_data: dict, order_id: str, delivered_lines: list[str],
    waiting_count: int, new_status: str | None, db
) -> None:
    """Send delivery notification to user."""
    telegram_id = order_data.get("user_telegram_id")
    order_status = new_status or order_data.get("status", "").lower()
    delivered_at = order_data.get("delivered_at")

    should_notify = False
    content_block = None

    if delivered_lines:
        # NEW items were delivered - send notification
        should_notify = True
        content_block = "\n\n".join(delivered_lines)
    elif order_status == "delivered" and not delivered_at:
        # Order delivered but notification never sent
        logger.info(f"deliver-goods: Order {order_id} delivered but notification never sent")
        fetched_lines = await _fetch_delivered_items_content(db, order_id)
        if fetched_lines:
            should_notify = True
            content_block = "\n\n".join(fetched_lines)

    if not (should_notify and telegram_id and content_block):
        return

    # Add info about waiting items
    if waiting_count > 0:
        waiting_notice = (
            f"\n\n⏳ <b>Ожидает доставки:</b> {waiting_count} товар(ов)\n"
            "Мы уведомим вас, когда они будут готовы к доставке."
        )
        content_block += waiting_notice

    try:
        await notification_service.send_delivery(
            telegram_id=telegram_id,
            product_name=f"Заказ #{order_id[:8]}",
            content=content_block,
            order_id=order_id,
        )
        logger.info(f"deliver-goods: Sent delivery notification for order {order_id}")
    except Exception as e:
        logger.exception(
            "deliver-goods: failed to notify for order %s: %s",
            sanitize_id_for_logging(order_id),
            type(e).__name__,
        )


# =============================================================================
# Main Delivery Function
# =============================================================================


def _get_validation_error_response(error_note: str | None) -> dict | None:
    """Convert validation error to response dict."""
    if error_note == "not_found":
        return {"delivered": 0, "waiting": 0, "note": "not_found", "error": "Order not found"}
    if error_note == "discount_channel":
        return {"delivered": 0, "waiting": 0, "note": "discount_channel", "skipped": True}
    if error_note == "payment_not_confirmed":
        return {"delivered": 0, "waiting": 0, "note": "payment_not_confirmed", "error": "Order payment not confirmed yet"}
    if error_note and error_note.startswith("invalid_status:"):
        status = error_note.split(":")[1]
        return {"delivered": 0, "waiting": 0, "note": "invalid_status", "error": f"Order status '{status}' is not valid for delivery"}
    return None


async def _load_products_map(db, product_ids: list[str], order_id: str) -> dict:
    """Load products info for delivery."""
    if not product_ids:
        return {}

    try:
        prod_res = (
            await db.client.table("products")
            .select("id,name,instructions,duration_days")
            .in_("id", product_ids)
            .execute()
        )
        return {p["id"]: p for p in (prod_res.data or [])}
    except Exception as e:
        logger.error(f"deliver-goods: failed to load products for order {order_id}: {e}")
        return {}


async def _process_items_for_delivery(
    db, items: list, products_map: dict, now: datetime, only_instant: bool
) -> tuple[list[str], int, int, int]:
    """Process all items for delivery. Returns (delivered_lines, delivered_count, waiting_count, total_already_delivered)."""
    delivered_lines = []
    delivered_count = 0
    waiting_count = 0
    total_delivered = 0

    for it in items:
        status = str(it.get("status") or "").lower()
        if status in {"delivered", "cancelled", "refunded"}:
            total_delivered += 1
            continue

        delivery_line, is_waiting = await _process_single_item_delivery(
            db, it, products_map, now, only_instant
        )

        if delivery_line:
            delivered_lines.append(delivery_line)
            delivered_count += 1
        elif is_waiting:
            waiting_count += 1

    return delivered_lines, delivered_count, waiting_count, total_delivered


async def _update_order_delivery_status(
    db, order_id: str, total_delivered: int, waiting_count: int, order_status: str, now: datetime
) -> str | None:
    """Update order delivery status. Returns new status or None."""
    try:
        from core.orders.status_service import OrderStatusService

        status_service = OrderStatusService(db)
        new_status = await status_service.update_delivery_status(
            order_id=order_id,
            delivered_count=total_delivered,
            waiting_count=waiting_count,
            current_status=order_status,
        )
        if new_status == "delivered":
            await db.client.table("orders").update({"delivered_at": now.isoformat()}).eq("id", order_id).execute()
        return new_status
    except Exception as e:
        logger.exception(
            "deliver-goods: failed to update order status %s: %s",
            sanitize_id_for_logging(order_id),
            type(e).__name__,
        )
        return None


async def _deliver_items_for_order(
    db, notification_service, order_id: str, only_instant: bool = False
):
    """
    Deliver order_items for given order_id.
    - only_instant=True: выдаём только instant позиции (для первичной выдачи после оплаты)
    - otherwise: пытаемся выдать все открытые позиции, если есть сток

    CRITICAL: This function should ONLY be called AFTER payment is confirmed via webhook.
    Orders with status 'pending' should NOT be processed - payment is not confirmed yet.
    """
    logger.debug("deliver-goods: starting for order %s, only_instant=%s", sanitize_id_for_logging(order_id), only_instant)

    # Validate order
    order_data, error_note = await _validate_order_for_delivery(db, order_id)

    error_response = _get_validation_error_response(error_note)
    if error_response:
        return error_response

    order_status = (order_data or {}).get("status", "").lower()
    now = datetime.now(UTC)

    # Get order items
    items = await db.get_order_items_by_order(order_id)
    logger.debug("deliver-goods: found %d items for order %s", len(items) if items else 0, sanitize_id_for_logging(order_id))

    if not items:
        return {"delivered": 0, "waiting": 0, "note": "no_items"}

    # Load products info
    product_ids = list({it.get("product_id") for it in items if it.get("product_id")})
    products_map = await _load_products_map(db, product_ids, order_id)

    # Process each item
    delivered_lines, delivered_count, waiting_count, total_delivered = await _process_items_for_delivery(
        db, items, products_map, now, only_instant
    )

    # Update order status
    total_delivered_final = total_delivered + delivered_count
    logger.debug(f"deliver-goods: order {order_id} status calc: total_delivered={total_delivered_final}")

    new_status = await _update_order_delivery_status(
        db, order_id, total_delivered_final, waiting_count, order_status, now
    )

    # Update user's total_saved
    await _update_user_total_saved(db, order_data or {}, order_id)

    # Send notification
    if order_data:
        await _send_delivery_notification(
            notification_service, order_data, order_id, delivered_lines,
            waiting_count, new_status, db
        )

    return {"delivered": delivered_count, "waiting": waiting_count}
