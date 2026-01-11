"""
QStash Workers Router - Main Router

Central router that aggregates all worker endpoints.
Contains shared utilities like _deliver_items_for_order.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

from core.services.money import to_float
from core.logging import get_logger

# Import sub-routers and include their endpoints
from .delivery import delivery_router
from .referral import referral_router
from .payments import payments_router
from .broadcast import broadcast_router

logger = get_logger(__name__)

router = APIRouter(prefix="/api/workers", tags=["workers"])

# Include sub-routers
router.include_router(delivery_router)
router.include_router(referral_router)
router.include_router(payments_router)
router.include_router(broadcast_router)


async def _deliver_items_for_order(db, notification_service, order_id: str, only_instant: bool = False):
    """
    Deliver order_items for given order_id.
    - only_instant=True: выдаём только instant позиции (для первичной выдачи после оплаты)
    - otherwise: пытаемся выдать все открытые позиции, если есть сток
    
    CRITICAL: This function should ONLY be called AFTER payment is confirmed via webhook.
    Orders with status 'pending' should NOT be processed - payment is not confirmed yet.
    """
    logger.info(f"deliver-goods: starting for order {order_id}, only_instant={only_instant}")
    
    # OPTIMIZATION: Load all order data in one query (combines requests #1, #6, #8)
    # Fields needed:
    # - status, payment_method, source_channel (for validation)
    # - user_id, original_price, amount, saved_calculated (for total_saved calculation)
    # - user_telegram_id, delivered_at (for notification)
    try:
        order_data = await db.client.table("orders").select(
            "status, payment_method, source_channel, user_id, original_price, amount, saved_calculated, user_telegram_id, delivered_at"
        ).eq("id", order_id).single().execute()
        
        if not order_data.data:
            logger.warning(f"deliver-goods: Order {order_id} not found")
            return {"delivered": 0, "waiting": 0, "note": "not_found", "error": "Order not found"}
        
        order_status = order_data.data.get("status", "").lower()
        source_channel = order_data.data.get("source_channel", "")
        
        # SKIP discount orders - they have separate delayed delivery via QStash worker
        if source_channel == "discount":
            logger.info(f"deliver-goods: Order {order_id} is from discount channel - skipping (uses separate delivery)")
            return {"delivered": 0, "waiting": 0, "note": "discount_channel", "skipped": True}
        
        # If order is still pending, payment is NOT confirmed - DO NOT process
        if order_status == "pending":
            logger.warning(f"deliver-goods: Order {order_id} is still PENDING - payment not confirmed. Skipping delivery.")
            return {"delivered": 0, "waiting": 0, "note": "payment_not_confirmed", "error": "Order payment not confirmed yet"}
        
        # Valid statuses for delivery:
        # - 'paid': Payment confirmed + stock available (balance or external)
        # - 'prepaid': Payment confirmed + stock unavailable (balance or external)
        # - 'partial': Some items delivered
        # - 'delivered': All items delivered
        if order_status not in ("paid", "prepaid", "partial", "delivered"):
            logger.warning(f"deliver-goods: Order {order_id} has invalid status '{order_status}' for delivery. Skipping.")
            return {"delivered": 0, "waiting": 0, "note": "invalid_status", "error": f"Order status '{order_status}' is not valid for delivery"}
    except Exception as e:
        logger.error(f"deliver-goods: Failed to check order status for {order_id}: {e}", exc_info=True)
        # Continue with delivery attempt, but log the error
    
    now = datetime.now(timezone.utc)
    items = await db.get_order_items_by_order(order_id)
    logger.info(f"deliver-goods: found {len(items) if items else 0} items for order {order_id}")
    if not items:
        return {"delivered": 0, "waiting": 0, "note": "no_items"}
    
    # Load products info (including duration_days for license expiration)
    product_ids = list({it.get("product_id") for it in items if it.get("product_id")})
    products_map = {}
    try:
        if product_ids:
            prod_res = await db.client.table("products").select(
                "id,name,instructions,duration_days"
            ).in_("id", product_ids).execute()
            products_map = {p["id"]: p for p in (prod_res.data or [])}
    except Exception as e:
        logger.error(f"deliver-goods: failed to load products for order {order_id}: {e}", exc_info=True)
    
    delivered_lines = []
    delivered_count = 0
    waiting_count = 0
    
    # Track total items for proper status calculation
    total_delivered = 0  # Already delivered (before this run)
    
    for it in items:
        status = str(it.get("status") or "").lower()
        if status in {"delivered", "cancelled", "refunded"}:
            # Already delivered items - track separately
            total_delivered += 1
            continue
        
        # Determine fulfillment_type for this item
        fulfillment_type = str(it.get("fulfillment_type") or "instant")
        
        # For only_instant mode (called immediately after payment):
        # - Skip preorder items - they will be delivered later by auto_alloc when stock arrives
        # - This is the FIRST delivery attempt, we only deliver what's immediately available
        if only_instant and fulfillment_type == "preorder":
            waiting_count += 1
            logger.debug(f"deliver-goods: skipping preorder item {it.get('id')} (only_instant=True, will be delivered by auto_alloc)")
            continue
        
        # For auto_alloc (only_instant=False):
        # - Try to deliver ALL items (instant AND preorder) if stock is available
        # - This runs every 10 minutes to check if new stock arrived for preorder items
        
        product_id = it.get("product_id")
        prod = products_map.get(product_id, {})
        prod_name = prod.get("name", "Product")
        item_quantity = it.get("quantity", 1)  # Get quantity from order_item
        
        # Try to allocate stock - need quantity stock items
        try:
            stock_res = await db.client.table("stock_items").select(
                "id,content"
            ).eq("product_id", product_id).eq("status", "available").limit(item_quantity).execute()
            stock_items = stock_res.data or []
        except Exception as e:
            logger.error(f"deliver-goods: stock query failed for order {order_id}, product {product_id}: {e}", exc_info=True)
            stock_items = []
        
        # Check if we have enough stock items
        if len(stock_items) >= item_quantity:
            # Allocate all required stock items
            stock_ids = []
            stock_contents = []
            allocated_count = 0
            
            for stock in stock_items[:item_quantity]:
                stock_id = stock["id"]
                stock_content = stock.get("content", "")
                
                # CRITICAL: Double-check stock is actually available before reserving
                # This prevents race conditions where stock was reserved between query and update
                try:
                    # Use atomic update to reserve stock (only update if status is still available)
                    update_result = await db.client.table("stock_items").update({
                        "status": "sold",
                        "reserved_at": now.isoformat(),
                        "sold_at": now.isoformat()
                    }).eq("id", stock_id).eq("status", "available").execute()
                    
                    # Check if update was successful (updated at least one row)
                    if update_result.data:
                        stock_ids.append(stock_id)
                        stock_contents.append(stock_content)
                        allocated_count += 1
                    else:
                        logger.warning(f"deliver-goods: stock {stock_id} was already reserved, skipping")
                except Exception as e:
                    logger.error(f"deliver-goods: failed to mark stock sold {stock_id}: {e}", exc_info=True)
            
            # Only proceed if we successfully allocated all required stock items
            if allocated_count == item_quantity:
                # Update item as delivered with all credentials
                item_id = it.get("id")
                instructions = it.get("delivery_instructions") or prod.get("instructions") or ""
                
                # Combine all stock contents into one delivery_content
                # Each credential on a new line
                combined_content = "\n".join(stock_contents)
                
                # Calculate expires_at from product.duration_days
                duration_days = prod.get("duration_days")
                expires_at_str = None
                if duration_days and duration_days > 0:
                    expires_at = now + timedelta(days=duration_days)
                    expires_at_str = expires_at.isoformat()
                
                try:
                    ts = now.isoformat()
                    update_data = {
                        "status": "delivered",
                        "stock_item_id": stock_ids[0] if stock_ids else None,  # Store first stock_item_id for reference
                        "delivery_content": combined_content,  # All credentials combined
                        "delivery_instructions": instructions,
                        "delivered_at": ts,
                        "updated_at": ts
                    }
                    if expires_at_str:
                        update_data["expires_at"] = expires_at_str
                    
                    await db.client.table("order_items").update(update_data).eq("id", item_id).execute()
                    delivered_count += 1
                    
                    # For notification: show product name with quantity if > 1
                    display_name = f"{prod_name}" + (f" (x{item_quantity})" if item_quantity > 1 else "")
                    delivered_lines.append(f"{display_name}:\n{combined_content}")
                    
                    logger.info(f"deliver-goods: allocated {allocated_count} stock items for product {product_id}, order_item {item_id}, quantity={item_quantity}")
                except Exception as e:
                    logger.error(f"deliver-goods: failed to update order_item {item_id}: {e}", exc_info=True)
                    # Rollback: mark stock items as available again
                    if stock_ids:
                        try:
                            await db.client.table("stock_items").update({
                                "status": "available",
                                "reserved_at": None,
                                "sold_at": None
                            }).in_("id", stock_ids).execute()
                        except Exception as rollback_err:
                            logger.error(f"deliver-goods: failed to rollback stock items: {rollback_err}")
            else:
                # Not enough stock items allocated - rollback and mark as waiting
                logger.warning(f"deliver-goods: only allocated {allocated_count}/{item_quantity} stock items for product {product_id}, order_item {it.get('id')}")
                # Rollback allocated stock items
                if stock_ids:
                    try:
                        await db.client.table("stock_items").update({
                            "status": "available",
                            "reserved_at": None,
                            "sold_at": None
                        }).in_("id", stock_ids).execute()
                    except Exception as rollback_err:
                        logger.error(f"deliver-goods: failed to rollback stock items: {rollback_err}")
                waiting_count += 1
        else:
            # No stock yet - keep current status (don't change to prepaid here)
            # Status should already be 'prepaid' if payment was confirmed and stock unavailable
            # If status is 'pending', it means payment is not confirmed - don't change it
            logger.debug(f"deliver-goods: NO stock available for product {product_id}, keeping current status")
            waiting_count += 1
            item_id = it.get("id")
            # Don't change status - keep it as is (should be 'prepaid' if payment confirmed, 'pending' if not)
            # Only update timestamp to track that we checked
            try:
                await db.client.table("order_items").update({
                    "updated_at": now.isoformat()
                }).eq("id", item_id).execute()
            except Exception as e:
                logger.error(f"deliver-goods: failed to update timestamp for item {item_id}: {e}", exc_info=True)
    
    # Update order status summary using centralized service
    # IMPORTANT: Include previously delivered items + newly delivered items
    total_delivered_final = total_delivered + delivered_count
    logger.debug(f"deliver-goods: order {order_id} status calc: total_delivered={total_delivered_final} (prev={total_delivered} + new={delivered_count}), waiting={waiting_count}")
    
    # Initialize new_status to None (will be set if status changes)
    new_status = None
    try:
        from core.orders.status_service import OrderStatusService
        status_service = OrderStatusService(db)
        # OPTIMIZATION: Pass current status to avoid GET request in update_delivery_status
        # We already have order_status from the initial query
        new_status = await status_service.update_delivery_status(
            order_id=order_id,
            delivered_count=total_delivered_final,  # Use TOTAL delivered (not just new)
            waiting_count=waiting_count,
            current_status=order_status  # Pass status to avoid GET request
        )
        if new_status == "delivered":
            # Update delivered_at timestamp
            await db.client.table("orders").update({
                "delivered_at": now.isoformat()
            }).eq("id", order_id).execute()
    except Exception as e:
        logger.error(f"deliver-goods: failed to update order status {order_id}: {e}", exc_info=True)
    
    # Update user's total_saved (discount savings)
    # Calculate saved amount = original_price - amount
    # Only update once per order (idempotency via saved_calculated flag)
    # OPTIMIZATION: Use order_data from initial query instead of new GET request
    try:
        if order_data.data:
            # Idempotency: only update once per order
            saved_calculated = order_data.data.get("saved_calculated", False)
            if not saved_calculated:
                user_id = order_data.data.get("user_id")
                original_price = to_float(order_data.data.get("original_price") or 0)
                final_amount = to_float(order_data.data.get("amount") or 0)
                
                # Calculate saved amount (difference between original and final price)
                saved_amount = max(0, original_price - final_amount)
                
                if saved_amount > 0 and user_id:
                    # Get current total_saved
                    user_check = await db.client.table("users").select(
                        "total_saved"
                    ).eq("id", user_id).single().execute()
                    current_saved = to_float(user_check.data.get("total_saved") or 0) if user_check.data else 0
                    new_saved = current_saved + saved_amount
                    
                    # Update user's total_saved
                    await db.client.table("users").update({
                        "total_saved": new_saved
                    }).eq("id", user_id).execute()
                    
                    # Mark order as processed (idempotency flag)
                    await db.client.table("orders").update({
                        "saved_calculated": True
                    }).eq("id", order_id).execute()
                    
                    logger.info(f"deliver-goods: Updated total_saved for user {user_id}: {current_saved:.2f} -> {new_saved:.2f} (+{saved_amount:.2f} from order {order_id}, original={original_price:.2f}, final={final_amount:.2f})")
    except Exception as e:
        logger.error(f"deliver-goods: Failed to update total_saved for order {order_id}: {e}", exc_info=True)
    
    # Notify user once with aggregated content
    # Send notification if:
    # 1. There are NEW delivered items (delivered_lines), OR
    # 2. Order is delivered but notification was never sent (delivered_at is NULL)
    # OPTIMIZATION: Use order_data from initial query instead of new GET request
    try:
        if not order_data.data:
            return {"delivered": delivered_count, "waiting": waiting_count}
        
        telegram_id = order_data.data.get("user_telegram_id")
        # Get current status (may have changed after update_delivery_status)
        # Use new_status if it was set, otherwise use order_status from initial query
        current_order_status = new_status if new_status else order_status
        delivered_at = order_data.data.get("delivered_at")
        
        should_notify = False
        content_block = None
        
        if delivered_lines:
            # NEW items were delivered in this run - send notification
            should_notify = True
            content_block = "\n\n".join(delivered_lines)
        elif current_order_status == "delivered" and not delivered_at:
            # Order is delivered but delivered_at is NULL - notification was never sent
            # Fetch content from already delivered items
            logger.info(f"deliver-goods: Order {order_id} is delivered but notification was never sent, fetching content from delivered items")
            delivered_items_result = await db.client.table("order_items").select(
                "delivery_content, products(name)"
            ).eq("order_id", order_id).eq("status", "delivered").execute()
            
            if delivered_items_result.data:
                delivered_content_lines = []
                for item in delivered_items_result.data:
                    product_name_item = item.get("products", {}).get("name") if isinstance(item.get("products"), dict) else "Product"
                    delivery_content = item.get("delivery_content", "")
                    if delivery_content:
                        delivered_content_lines.append(f"{product_name_item}:\n{delivery_content}")
                
                if delivered_content_lines:
                    should_notify = True
                    content_block = "\n\n".join(delivered_content_lines)
        
        if should_notify and telegram_id and content_block:
            # Add info about waiting items if partial delivery
            if waiting_count > 0:
                waiting_notice = (
                    f"\n\n⏳ <b>Ожидает доставки:</b> {waiting_count} товар(ов)\n"
                    "Мы уведомим вас, когда они будут готовы к доставке."
                )
                content_block += waiting_notice
            
            await notification_service.send_delivery(
                telegram_id=telegram_id,
                product_name=f"Заказ #{order_id[:8]}",
                content=content_block,
                order_id=order_id
            )
            logger.info(f"deliver-goods: Sent delivery notification for order {order_id} to user {telegram_id} (new_items={delivered_count}, was_missing={not delivered_lines})")
    except Exception as e:
        logger.error(f"deliver-goods: failed to notify for order {order_id}: {e}", exc_info=True)
    
    return {"delivered": delivered_count, "waiting": waiting_count}
