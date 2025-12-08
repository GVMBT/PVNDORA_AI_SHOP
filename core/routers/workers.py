"""
QStash Workers Router

Guaranteed delivery workers for critical operations.
All workers verify QStash request signature.
"""
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Request

from src.services.database import get_database
from src.services.money import to_decimal, to_float
from core.routers.deps import verify_qstash, get_notification_service

router = APIRouter(prefix="/api/workers", tags=["workers"])


async def _deliver_items_for_order(db, notification_service, order_id: str, only_instant: bool = False):
    """
    Deliver order_items for given order_id.
    - only_instant=True: выдаём только instant позиции (для первичной выдачи после оплаты)
    - otherwise: пытаемся выдать все открытые позиции, если есть сток
    """
    print(f"deliver-goods: starting for order {order_id}, only_instant={only_instant}")
    now = datetime.now(timezone.utc)
    items = await db.get_order_items_by_order(order_id)
    print(f"deliver-goods: found {len(items) if items else 0} items for order {order_id}")
    if not items:
        return {"delivered": 0, "waiting": 0, "note": "no_items"}
    
    # Load products info
    product_ids = list({it.get("product_id") for it in items if it.get("product_id")})
    products_map = {}
    try:
        if product_ids:
            prod_res = await asyncio.to_thread(
                lambda: db.client.table("products").select("id,name,instructions").in_("id", product_ids).execute()
            )
            products_map = {p["id"]: p for p in (prod_res.data or [])}
    except Exception as e:
        print(f"deliver-goods: failed to load products for order {order_id}: {e}")
    
    delivered_lines = []
    delivered_count = 0
    waiting_count = 0
    
    for it in items:
        status = str(it.get("status") or "").lower()
        if status in {"delivered", "fulfilled", "completed", "ready", "refund_pending", "replacement_pending", "failed"}:
            continue
        if only_instant and str(it.get("fulfillment_type") or "instant") != "instant":
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
            print(f"deliver-goods: stock query failed for order {order_id}, product {product_id}: {e}")
            stock = None
        
        if stock:
            # Reserve/sell stock
            stock_id = stock["id"]
            stock_content = stock.get("content", "")
            print(f"deliver-goods: allocating stock {stock_id} for product {product_id}")
            try:
                await asyncio.to_thread(
                    lambda sid=stock_id, ts=now.isoformat(): db.client.table("stock_items").update({
                        "status": "sold",
                        "is_sold": True,
                        "reserved_at": ts,
                        "sold_at": ts
                    }).eq("id", sid).execute()
                )
            except Exception as e:
                print(f"deliver-goods: failed to mark stock sold {stock_id}: {e}")
                continue
            
            # Update item as delivered
            item_id = it.get("id")
            instructions = it.get("delivery_instructions") or prod.get("instructions") or ""
            try:
                await asyncio.to_thread(
                    lambda iid=item_id, sid=stock_id, content=stock_content, instr=instructions, ts=now.isoformat(): 
                        db.client.table("order_items").update({
                            "status": "delivered",
                            "stock_item_id": sid,
                            "delivery_content": content,
                            "delivery_instructions": instr,
                            "delivered_at": ts,
                            "updated_at": ts
                        }).eq("id", iid).execute()
                )
                delivered_count += 1
                delivered_lines.append(f"{prod_name}:\n{stock_content}")
            except Exception as e:
                print(f"deliver-goods: failed to update order_item {item_id}: {e}")
        else:
            # No stock yet - mark as prepaid/fulfilling
            print(f"deliver-goods: NO stock available for product {product_id}, marking as waiting")
            waiting_count += 1
            item_id = it.get("id")
            new_status = "prepaid" if status == "pending" else status
            try:
                await asyncio.to_thread(
                    lambda iid=item_id, st=new_status, ts=now.isoformat(): 
                        db.client.table("order_items").update({
                            "status": st,
                            "updated_at": ts
                        }).eq("id", iid).execute()
                )
            except Exception as e:
                print(f"deliver-goods: failed to mark waiting for item {item_id}: {e}")
    
    # Update order status summary
    try:
        order_status = None
        if delivered_count and waiting_count == 0:
            order_status = "delivered"
        elif delivered_count and waiting_count > 0:
            order_status = "partial"
        elif delivered_count == 0 and waiting_count > 0:
            order_status = "prepaid"
        
        if order_status:
            update_payload = {"status": order_status, "updated_at": now.isoformat()}
            if order_status == "delivered":
                update_payload["delivered_at"] = now.isoformat()
            await asyncio.to_thread(
                lambda: db.client.table("orders").update(update_payload).eq("id", order_id).execute()
            )
    except Exception as e:
        print(f"deliver-goods: failed to update order status {order_id}: {e}")
    
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
        print(f"deliver-goods: failed to notify for order {order_id}: {e}")
    
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
    bonus_result = db.client.rpc("process_referral_bonus", {
        "p_buyer_id": user_id,
        "p_order_id": order_id,
        "p_order_amount": amount
    }).execute()
    
    return {
        "success": True,
        "turnover": turnover_data,
        "first_unlock": not was_unlocked,
        "level_up": level_up,
        "new_level": new_level,
        "bonuses": bonus_result.data if bonus_result.data else {}
    }


@router.post("/deliver-batch")
async def worker_deliver_batch(request: Request):
    """
    QStash Worker: Try to deliver all waiting items (pending/prepaid/fulfilling), any fulfillment_type.
    Useful for автоаллоцирования при пополнении стока.
    """
    data = await verify_qstash(request)
    
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
        print(f"LOW STOCK ALERT: Product {product_id} has only {len(stock.data)} items")
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

