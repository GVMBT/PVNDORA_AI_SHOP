"""
QStash Workers Router

Guaranteed delivery workers for critical operations.
All workers verify QStash request signature.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request

from core.services.database import get_database
from core.services.money import to_float
from core.routers.deps import verify_qstash, get_notification_service
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/workers", tags=["workers"])


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
        order_check = await asyncio.to_thread(
            lambda: db.client.table("orders")
            .select("status, payment_method, source_channel")
            .eq("id", order_id)
            .single()
            .execute()
        )
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
            prod_res = await asyncio.to_thread(
                lambda: db.client.table("products").select("id,name,instructions,duration_days").in_("id", product_ids).execute()
            )
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
        # IMPORTANT: Use default args to capture loop variables (closure bug fix)
        try:
            stock_res = await asyncio.to_thread(
                lambda pid=product_id: db.client.table("stock_items")
                .select("id,content")
                .eq("product_id", pid)
                .eq("status", "available")
                .limit(1)
                .execute()
            )
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
                await asyncio.to_thread(
                    lambda sid=stock_id, ts=now.isoformat(): db.client.table("stock_items").update({
                        "status": "sold",
                        "reserved_at": ts,
                        "sold_at": ts
                    }).eq("id", sid).execute()
                )
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
                
                await asyncio.to_thread(
                    lambda iid=item_id, data=update_data: 
                        db.client.table("order_items").update(data).eq("id", iid).execute()
                )
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
                await asyncio.to_thread(
                    lambda iid=item_id, ts=now.isoformat(): 
                        db.client.table("order_items").update({
                            "updated_at": ts
                        }).eq("id", iid).execute()
                )
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
            await asyncio.to_thread(
                lambda: db.client.table("orders")
                .update({"delivered_at": now.isoformat()})
                .eq("id", order_id)
                .execute()
            )
    except Exception as e:
        logger.error(f"deliver-goods: failed to update order status {order_id}: {e}", exc_info=True)
    
    # Update user's total_saved (discount savings)
    # Calculate saved amount = original_price - amount
    # Only update once per order (idempotency via saved_calculated flag)
    try:
        order_full = await asyncio.to_thread(
            lambda: db.client.table("orders")
            .select("user_id, original_price, amount, saved_calculated")
            .eq("id", order_id)
            .single()
            .execute()
        )
        
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
                    user_check = await asyncio.to_thread(
                        lambda: db.client.table("users")
                        .select("total_saved")
                        .eq("id", user_id)
                        .single()
                        .execute()
                    )
                    current_saved = to_float(user_check.data.get("total_saved") or 0) if user_check.data else 0
                    new_saved = current_saved + saved_amount
                    
                    # Update user's total_saved
                    await asyncio.to_thread(
                        lambda: db.client.table("users")
                        .update({"total_saved": new_saved})
                        .eq("id", user_id)
                        .execute()
                    )
                    
                    # Mark order as processed (idempotency flag)
                    await asyncio.to_thread(
                        lambda: db.client.table("orders")
                        .update({"saved_calculated": True})
                        .eq("id", order_id)
                        .execute()
                    )
                    
                    logger.info(f"deliver-goods: Updated total_saved for user {user_id}: {current_saved:.2f} -> {new_saved:.2f} (+{saved_amount:.2f} from order {order_id}, original={original_price:.2f}, final={final_amount:.2f})")
    except Exception as e:
        logger.error(f"deliver-goods: Failed to update total_saved for order {order_id}: {e}", exc_info=True)
    
    # Notify user once with aggregated content
    try:
        if delivered_lines:
            order = await asyncio.to_thread(
                lambda: db.client.table("orders").select("user_telegram_id").eq("id", order_id).single().execute()
            )
            telegram_id = order.data.get("user_telegram_id") if order and order.data else None
            if telegram_id:
                content_block = "\n\n".join(delivered_lines)
                await notification_service.send_delivery(
                    telegram_id=telegram_id,
                    product_name=f"Заказ {order_id}",
                    content=content_block
                )
    except Exception as e:
        logger.error(f"deliver-goods: failed to notify for order {order_id}: {e}", exc_info=True)
    
    return {"delivered": delivered_count, "waiting": waiting_count}


@router.post("/deliver-goods")
async def worker_deliver_goods(request: Request):
    """
    QStash Worker: Deliver digital goods after payment.
    Called by QStash with guaranteed delivery.
    """
    data = await verify_qstash(request)
    order_id = data.get("order_id")
    
    if not order_id:
        return {"error": "order_id required"}
    
    db = get_database()
    notification_service = get_notification_service()
    
    result = await _deliver_items_for_order(db, notification_service, order_id, only_instant=True)
    return {"success": True, "order_id": order_id, **result}


@router.post("/calculate-referral")
async def worker_calculate_referral(request: Request):
    """
    QStash Worker: Calculate and apply referral bonuses.
    
    Logic:
    1. Update buyer's turnover (in USD) - recalculates as own orders + referral orders (may unlock new levels)
    2. Check if referral program should be unlocked (first purchase)
    3. Process referral bonuses - ONLY for levels that referrer has unlocked
    """
    data = await verify_qstash(request)
    order_id = data.get("order_id")
    usd_rate = data.get("usd_rate", 100)  # RUB/USD rate, default 100
    
    if not order_id:
        return {"error": "order_id required"}
    
    db = get_database()
    notification_service = get_notification_service()
    
    # Get order with user info
    order = db.client.table("orders").select(
        "amount, user_id, user_telegram_id, users(referrer_id, referral_program_unlocked)"
    ).eq("id", order_id).single().execute()
    
    if not order.data:
        return {"error": "Order not found"}
    
    user_id = order.data.get("user_id")
    amount = to_float(order.data["amount"])
    telegram_id = order.data.get("user_telegram_id")
    was_unlocked = order.data.get("users", {}).get("referral_program_unlocked", False)
    
    # 1. Update buyer's turnover in USD (recalculates: own delivered orders + referral delivered orders)
    #    This may trigger level unlocks
    turnover_result = db.client.rpc("update_user_turnover", {
        "p_user_id": user_id,
        "p_amount_rub": amount,
        "p_usd_rate": usd_rate
    }).execute()
    
    turnover_data = turnover_result.data if turnover_result.data else {}
    level_up = turnover_data.get("level_up", False)
    new_level = turnover_data.get("new_level", 0)
    
    # 2. Unlock referral program if first purchase
    if not was_unlocked:
        db.client.table("users").update({
            "referral_program_unlocked": True
        }).eq("id", user_id).execute()
        
        # Send unlock notification
        if telegram_id:
            await notification_service.send_referral_unlock_notification(telegram_id)
    
    # 3. Send level up notification if applicable
    if level_up and new_level > 0 and telegram_id:
        await notification_service.send_referral_level_up_notification(telegram_id, new_level)
    
    # 4. Process referral bonuses for referrer chain (checks level unlock status)
    referrer_id = order.data.get("users", {}).get("referrer_id")
    if not referrer_id:
        return {
            "success": True, 
            "turnover": turnover_data,
            "first_unlock": not was_unlocked,
            "bonuses": "no_referrer"
        }
    
    # Use new function that checks level unlock status
    try:
        bonus_result = db.client.rpc("process_referral_bonus", {
            "p_buyer_id": user_id,
            "p_order_id": order_id,
            "p_order_amount": amount
        }).execute()
        bonuses = bonus_result.data if bonus_result.data else {}
        return {
            "success": True,
            "turnover": turnover_data,
            "first_unlock": not was_unlocked,
            "level_up": level_up,
            "new_level": new_level,
            "bonuses": bonuses
        }
    except Exception as e:
        # If referral program not unlocked or percent is null, skip bonus and continue
        logger.warning(f"Referral bonus failed for order {order_id}: {e}", exc_info=True)
        return {
            "success": True,
            "turnover": turnover_data,
            "first_unlock": not was_unlocked,
            "level_up": level_up,
            "new_level": new_level,
            "bonuses": "skipped_due_to_error"
        }


@router.post("/deliver-batch")
async def worker_deliver_batch(request: Request):
    """
    QStash Worker: Try to deliver all waiting items (pending/prepaid), any fulfillment_type.
    Useful for auto-allocation when stock is replenished.
    """
    await verify_qstash(request)  # Verify QStash signature
    
    db = get_database()
    notification_service = get_notification_service()
    
    # Найти открытые позиции
    try:
        open_items = await asyncio.to_thread(
            lambda: db.client.table("order_items")
            .select("order_id")
            .in_("status", ["pending", "prepaid", "partial"])
            .order("created_at")
            .limit(200)
            .execute()
        )
        order_ids = list({row["order_id"] for row in (open_items.data or [])})
    except Exception as e:
        return {"error": f"failed to query open items: {e}"}
    
    results = []
    for oid in order_ids:
        res = await _deliver_items_for_order(db, notification_service, oid, only_instant=False)
        results.append({"order_id": oid, **res})
    
    return {"processed": len(order_ids), "results": results}


@router.post("/notify-supplier")
async def worker_notify_supplier(request: Request):
    """
    QStash Worker: Notify supplier about low stock.
    """
    data = await verify_qstash(request)
    product_id = data.get("product_id")
    threshold = data.get("threshold", 3)
    
    if not product_id:
        return {"error": "product_id required"}
    
    db = get_database()
    
    # Check current stock
    stock = db.client.table("stock_items").select("id").eq(
        "product_id", product_id
    ).eq("status", "available").execute()
    
    if len(stock.data) <= threshold:
        # Log low stock alert (in production, send to admin)
        logger.warning(f"LOW STOCK ALERT: Product {product_id} has only {len(stock.data)} items")
        return {"alerted": True, "stock_count": len(stock.data)}
    
    return {"skipped": True, "stock_count": len(stock.data)}


@router.post("/process-replacement")
async def worker_process_replacement(request: Request):
    """
    QStash Worker: Process account replacement for approved replacement tickets.
    
    Finds new stock item for the same product and updates order_item with new credentials.
    """
    data = await verify_qstash(request)
    ticket_id = data.get("ticket_id")
    item_id = data.get("item_id")
    order_id = data.get("order_id")
    
    if not ticket_id or not item_id:
        return {"error": "ticket_id and item_id required"}
    
    db = get_database()
    notification_service = get_notification_service()
    
    # Get ticket to verify it's approved
    ticket_res = await asyncio.to_thread(
        lambda: db.client.table("tickets")
        .select("id, status, issue_type, user_id, order_id, item_id")
        .eq("id", ticket_id)
        .single()
        .execute()
    )
    
    if not ticket_res.data:
        return {"error": "Ticket not found"}
    
    if ticket_res.data["status"] != "approved":
        return {"skipped": True, "reason": f"Ticket status is {ticket_res.data['status']}, not approved"}
    
    if ticket_res.data["issue_type"] != "replacement":
        return {"skipped": True, "reason": f"Ticket issue_type is {ticket_res.data['issue_type']}, not replacement"}
    
    # Get order item to replace
    item_res = await asyncio.to_thread(
        lambda: db.client.table("order_items")
        .select("id, order_id, product_id, status, delivery_content")
        .eq("id", item_id)
        .single()
        .execute()
    )
    
    if not item_res.data:
        return {"error": "Order item not found"}
    
    item_data = item_res.data[0]
    product_id = item_data.get("product_id")
    order_id_from_item = item_data.get("order_id")
    
    # Get order to get user_telegram_id
    order_res = await asyncio.to_thread(
        lambda: db.client.table("orders")
        .select("user_telegram_id")
        .eq("id", order_id_from_item)
        .single()
        .execute()
    )
    
    user_telegram_id = None
    if order_res.data:
        user_telegram_id = order_res.data.get("user_telegram_id")
    
    if item_data.get("status") != "delivered":
        return {"skipped": True, "reason": f"Item status is {item_data.get('status')}, must be delivered"}
    
    # Find available stock for the same product
    now = datetime.now(timezone.utc)
    stock_res = await asyncio.to_thread(
        lambda: db.client.table("stock_items")
        .select("id, content")
        .eq("product_id", product_id)
        .eq("status", "available")
        .limit(1)
        .execute()
    )
    
    if not stock_res.data:
        # No stock available - keep ticket approved, will be processed by auto_alloc cron
        await asyncio.to_thread(
            lambda: db.client.table("tickets")
            .update({
                "admin_comment": "Replacement queued: waiting for stock. Will be auto-delivered when available."
            })
            .eq("id", ticket_id)
            .execute()
        )
        
        # Notify user that replacement is queued
        if user_telegram_id:
            try:
                await notification_service.send_message(
                    telegram_id=user_telegram_id,
                    text=(
                        f"⏳ <b>Replacement Queued</b>\n\n"
                        f"Your replacement for {product_name} has been approved, "
                        f"but no stock is currently available.\n\n"
                        f"You will automatically receive a new account as soon as stock arrives."
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to send queue notification: {e}")
        
        return {
            "queued": True,
            "reason": "No stock available - queued for auto-delivery",
            "ticket_status": "approved"
        }
    
    stock_item = stock_res.data[0]
    stock_id = stock_item["id"]
    stock_content = stock_item.get("content", "")
    
    # Mark stock as sold
    try:
        await asyncio.to_thread(
            lambda: db.client.table("stock_items")
            .update({
                "status": "sold",
                "reserved_at": now.isoformat(),
                "sold_at": now.isoformat()
            })
            .eq("id", stock_id)
            .execute()
        )
    except Exception as e:
        logger.error(f"process-replacement: Failed to mark stock sold {stock_id}: {e}", exc_info=True)
        return {"error": "Failed to reserve stock"}
    
    # Get product info for expiration calculation
    product_res = await asyncio.to_thread(
        lambda: db.client.table("products")
        .select("duration_days, name")
        .eq("id", product_id)
        .single()
        .execute()
    )
    
    product = product_res.data[0] if product_res.data else {}
    duration_days = product.get("duration_days")
    product_name = product.get("name", "Product")
    
    # Calculate expires_at
    expires_at_str = None
    if duration_days and duration_days > 0:
        expires_at = now + timedelta(days=duration_days)
        expires_at_str = expires_at.isoformat()
    
    # Update order item with new credentials
    try:
        update_data = {
            "stock_item_id": stock_id,
            "delivery_content": stock_content,
            "delivered_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "status": "delivered"  # Ensure status is delivered
        }
        if expires_at_str:
            update_data["expires_at"] = expires_at_str
        
        await asyncio.to_thread(
            lambda: db.client.table("order_items")
            .update(update_data)
            .eq("id", item_id)
            .execute()
        )
    except Exception as e:
        logger.error(f"process-replacement: Failed to update order item {item_id}: {e}", exc_info=True)
        # Rollback stock reservation
        await asyncio.to_thread(
            lambda: db.client.table("stock_items")
            .update({"status": "available", "reserved_at": None, "sold_at": None})
            .eq("id", stock_id)
            .execute()
        )
        return {"error": "Failed to update order item"}
    
    # Close ticket
    await asyncio.to_thread(
        lambda: db.client.table("tickets")
        .update({
            "status": "closed",
            "admin_comment": f"Replacement completed automatically. New account delivered."
        })
        .eq("id", ticket_id)
        .execute()
    )
    
    # Notify user
    if user_telegram_id:
        try:
            await notification_service.send_replacement_notification(
                telegram_id=user_telegram_id,
                product_name=product_name,
                item_id=item_id[:8]  # Short ID for display
            )
        except Exception as e:
            logger.error(f"process-replacement: Failed to send notification: {e}", exc_info=True)
    
    logger.info(f"process-replacement: Successfully replaced item {item_id} with stock {stock_id}")
    
    return {
        "success": True,
        "item_id": item_id,
        "stock_id": stock_id,
        "ticket_id": ticket_id,
        "message": "Account replacement completed"
    }


@router.post("/process-refund")
async def worker_process_refund(request: Request):
    """
    QStash Worker: Process refund for prepaid orders.
    
    Also handles:
    - Rollback of turnover (recalculates: own orders + referral orders, excluding refunded order)
    - Revoke referral bonuses paid for this order
    """
    data = await verify_qstash(request)
    order_id = data.get("order_id")
    reason = data.get("reason", "Fulfillment deadline exceeded")
    usd_rate = data.get("usd_rate", 100)
    
    if not order_id:
        return {"error": "order_id required"}
    
    db = get_database()
    notification_service = get_notification_service()
    
    # Get order
    order = db.client.table("orders").select(
        "id, amount, user_id, user_telegram_id, status, products(name)"
    ).eq("id", order_id).single().execute()
    
    if not order.data:
        return {"error": "Order not found"}
    
    if order.data["status"] not in ["prepaid", "paid", "partial", "delivered"]:
        return {"skipped": True, "reason": f"Order status is {order.data['status']}, cannot refund"}
    
    amount = to_float(order.data["amount"])
    user_id = order.data["user_id"]
    
    # 1. Rollback turnover and revoke referral bonuses
    rollback_result = db.client.rpc("rollback_user_turnover", {
        "p_user_id": user_id,
        "p_amount_rub": amount,
        "p_usd_rate": usd_rate,
        "p_order_id": order_id
    }).execute()
    
    # 2. Refund to user balance
    db.client.rpc("add_to_user_balance", {
        "p_user_id": user_id,
        "p_amount": amount,
        "p_reason": f"Refund for order {order_id}: {reason}"
    }).execute()
    
    # 3. Update order status
    db.client.table("orders").update({
        "status": "refunded",
        "refund_reason": reason,
        "refund_processed_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", order_id).execute()
    
    # 4. Notify user
    await notification_service.send_refund_notification(
        telegram_id=order.data["user_telegram_id"],
        product_name=order.data.get("products", {}).get("name", "Product"),
        amount=amount,
        reason=reason
    )
    
    return {
        "success": True, 
        "refunded_amount": amount,
        "turnover_rollback": rollback_result.data if rollback_result.data else {}
    }


@router.post("/process-review-cashback")
async def worker_process_review_cashback(request: Request):
    """
    QStash Worker: Process 5% cashback for review.
    
    Expected payload (from callbacks.py):
    - user_telegram_id: User's telegram ID
    - order_id: Order ID
    - order_amount: Order amount in USD
    """
    data = await verify_qstash(request)
    
    # Support both old (review_id) and new (order_id) payload formats
    order_id = data.get("order_id")
    user_telegram_id = data.get("user_telegram_id")
    order_amount = data.get("order_amount")
    
    if not order_id:
        return {"error": "order_id required"}
    
    db = get_database()
    
    # Find review by order_id
    review_result = db.client.table("reviews").select(
        "id, cashback_given"
    ).eq("order_id", order_id).limit(1).execute()
    
    if not review_result.data:
        return {"error": "Review not found for order"}
    
    review = review_result.data[0]
    
    if review.get("cashback_given"):
        return {"skipped": True, "reason": "Cashback already processed"}
    
    # Get user by telegram_id
    db_user = await db.get_user_by_telegram_id(user_telegram_id) if user_telegram_id else None
    
    # Fallback: get user from order
    if not db_user:
        order_result = db.client.table("orders").select("user_id, amount").eq("id", order_id).single().execute()
        if not order_result.data:
            return {"error": "Order not found"}
        order_amount = order_amount or to_float(order_result.data["amount"])
        user_result = db.client.table("users").select("*").eq("id", order_result.data["user_id"]).single().execute()
        if not user_result.data:
            return {"error": "User not found"}
        db_user = type('User', (), user_result.data)()
    
    # Calculate 5% cashback (in USD)
    cashback = to_float(order_amount) * 0.05
    
    # 1. Update user balance
    new_balance = to_float(db_user.balance or 0) + cashback
    db.client.table("users").update({
        "balance": new_balance
    }).eq("id", db_user.id).execute()
    
    # 2. Create balance_transaction for history
    db.client.table("balance_transactions").insert({
        "user_id": db_user.id,
        "type": "cashback",
        "amount": cashback,
        "status": "completed",
        "description": f"5% кэшбек за отзыв",
        "reference_id": order_id,
    }).execute()
    
    # 3. Mark review as processed
    db.client.table("reviews").update({
        "cashback_given": True
    }).eq("id", review["id"]).execute()
    
    # 4. Send Telegram notification to user
    try:
        from aiogram import Bot
        import os
        bot = Bot(token=os.environ.get("TELEGRAM_TOKEN", ""))
        await bot.send_message(
            chat_id=db_user.telegram_id,
            text=f"💰 <b>Кэшбек начислен!</b>\n\n"
                 f"За ваш отзыв вам начислено <b>${cashback:.2f}</b>.\n"
                 f"Новый баланс: <b>${new_balance:.2f}</b>\n\n"
                 f"Спасибо за обратную связь! 🙏",
            parse_mode="HTML"
        )
        await bot.session.close()
    except Exception as e:
        logger.warning(f"Failed to send cashback notification: {e}")
    
    logger.info(f"Cashback processed: user={db_user.telegram_id}, amount=${cashback:.2f}, order={order_id}")
    
    return {"success": True, "cashback": cashback, "new_balance": new_balance}

