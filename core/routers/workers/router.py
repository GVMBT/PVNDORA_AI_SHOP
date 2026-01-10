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
    
    # CRITICAL CHECK: Verify order status and source channel
    try:
        order_check = await db.client.table("orders").select(
            "status, payment_method, source_channel"
        ).eq("id", order_id).single().execute()
        if order_check.data:
            order_status = order_check.data.get("status", "").lower()
            source_channel = order_check.data.get("source_channel", "")
            
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
        
        # Try to allocate stock
        try:
            stock_res = await db.client.table("stock_items").select(
                "id,content"
            ).eq("product_id", product_id).eq("status", "available").limit(1).execute()
            stock = stock_res.data[0] if stock_res.data else None
        except Exception as e:
            logger.error(f"deliver-goods: stock query failed for order {order_id}, product {product_id}: {e}", exc_info=True)
            stock = None
        
        if stock:
            # CRITICAL: Double-check stock is actually available before reserving
            # This prevents race conditions where stock was reserved between query and update
            stock_id = stock["id"]
            stock_content = stock.get("content", "")
            logger.info(f"deliver-goods: allocating stock {stock_id} for product {product_id}, fulfillment_type={fulfillment_type}")
            try:
                await db.client.table("stock_items").update({
                    "status": "sold",
                    "reserved_at": now.isoformat(),
                    "sold_at": now.isoformat()
                }).eq("id", stock_id).execute()
            except Exception as e:
                logger.error(f"deliver-goods: failed to mark stock sold {stock_id}: {e}", exc_info=True)
                continue
            
            # Update item as delivered
            item_id = it.get("id")
            instructions = it.get("delivery_instructions") or prod.get("instructions") or ""
            
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
                    "stock_item_id": stock_id,
                    "delivery_content": stock_content,
                    "delivery_instructions": instructions,
                    "delivered_at": ts,
                    "updated_at": ts
                }
                if expires_at_str:
                    update_data["expires_at"] = expires_at_str
                
                await db.client.table("order_items").update(update_data).eq("id", item_id).execute()
                delivered_count += 1
                delivered_lines.append(f"{prod_name}:\n{stock_content}")
            except Exception as e:
                logger.error(f"deliver-goods: failed to update order_item {item_id}: {e}", exc_info=True)
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
    
    try:
        from core.orders.status_service import OrderStatusService
        status_service = OrderStatusService(db)
        new_status = await status_service.update_delivery_status(
            order_id=order_id,
            delivered_count=total_delivered_final,  # Use TOTAL delivered (not just new)
            waiting_count=waiting_count
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
    try:
        order_full = await db.client.table("orders").select(
            "user_id, original_price, amount, saved_calculated"
        ).eq("id", order_id).single().execute()
        
        if order_full.data:
            # Idempotency: only update once per order
            saved_calculated = order_full.data.get("saved_calculated", False)
            if not saved_calculated:
                user_id = order_full.data.get("user_id")
                original_price = to_float(order_full.data.get("original_price") or 0)
                final_amount = to_float(order_full.data.get("amount") or 0)
                
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
    try:
        if delivered_lines:
            order = await db.client.table("orders").select(
                "user_telegram_id"
            ).eq("id", order_id).single().execute()
            telegram_id = order.data.get("user_telegram_id") if order and order.data else None
            if telegram_id:
                content_block = "\n\n".join(delivered_lines)
                await notification_service.send_delivery(
                    telegram_id=telegram_id,
                    product_name=f"Заказ #{order_id[:8]}",
                    content=content_block,
                    order_id=order_id
                )
    except Exception as e:
        logger.error(f"deliver-goods: failed to notify for order {order_id}: {e}", exc_info=True)
    
    return {"delivered": delivered_count, "waiting": waiting_count}
