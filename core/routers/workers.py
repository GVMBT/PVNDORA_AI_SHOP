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
    
    # CRITICAL CHECK: Verify order status - must be paid/prepaid, NOT pending
    try:
        order_check = await asyncio.to_thread(
            lambda: db.client.table("orders")
            .select("status, payment_method")
            .eq("id", order_id)
            .single()
            .execute()
        )
        if order_check.data:
            order_status = order_check.data.get("status", "").lower()
            
            # If order is still pending, payment is NOT confirmed - DO NOT process
            if order_status == "pending":
                logger.warning(f"deliver-goods: Order {order_id} is still PENDING - payment not confirmed. Skipping delivery.")
                return {"delivered": 0, "waiting": 0, "note": "payment_not_confirmed", "error": "Order payment not confirmed yet"}
            
            # For balance payments, status should be 'paid' (set during order creation)
            # For external payments, status should be 'prepaid' or 'paid' (set by webhook)
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
        if status in {"delivered", "fulfilled", "completed", "ready", "refund_pending", "replacement_pending", "failed"}:
            # Already delivered items - track separately
            total_delivered += 1
            continue
        
        # For only_instant mode, count preorder items as waiting but don't try to deliver
        if only_instant and str(it.get("fulfillment_type") or "instant") != "instant":
            waiting_count += 1
            logger.debug(f"deliver-goods: skipping preorder item {it.get('id')} (only_instant=True), counting as waiting")
            continue
        
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
            # Reserve/sell stock
            stock_id = stock["id"]
            stock_content = stock.get("content", "")
            logger.info(f"deliver-goods: allocating stock {stock_id} for product {product_id}")
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
    1. Update buyer's turnover (in USD) - this may unlock new levels
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
    
    # 1. Update buyer's turnover in USD (this may trigger level unlocks)
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
    QStash Worker: Try to deliver all waiting items (pending/prepaid/fulfilling), any fulfillment_type.
    Useful for автоаллоцирования при пополнении стока.
    """
    await verify_qstash(request)  # Verify QStash signature
    
    db = get_database()
    notification_service = get_notification_service()
    
    # Найти открытые позиции
    try:
        open_items = await asyncio.to_thread(
            lambda: db.client.table("order_items")
            .select("order_id")
            .in_("status", ["pending", "prepaid", "fulfilling"])
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


@router.post("/process-refund")
async def worker_process_refund(request: Request):
    """
    QStash Worker: Process refund for prepaid orders.
    
    Also handles:
    - Rollback of turnover (user loses referral progress)
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
    
    if order.data["status"] not in ["prepaid", "completed", "delivered"]:
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
    """
    data = await verify_qstash(request)
    review_id = data.get("review_id")
    
    if not review_id:
        return {"error": "review_id required"}
    
    db = get_database()
    
    # Get review with order info
    review = db.client.table("reviews").select(
        "id, order_id, cashback_processed, orders(amount, user_id)"
    ).eq("id", review_id).single().execute()
    
    if not review.data:
        return {"error": "Review not found"}
    
    if review.data.get("cashback_processed"):
        return {"skipped": True, "reason": "Cashback already processed"}
    
    order = review.data.get("orders", {})
    if not order:
        return {"error": "Order not found"}
    
    # Calculate 5% cashback
    cashback = to_float(order["amount"]) * 0.05
    
    # Add to user balance
    db.client.rpc("add_to_user_balance", {
        "p_user_id": order["user_id"],
        "p_amount": cashback,
        "p_reason": "Review cashback for order"
    }).execute()
    
    # Mark as processed
    db.client.table("reviews").update({
        "cashback_processed": True
    }).eq("id", review_id).execute()
    
    return {"success": True, "cashback": cashback}

