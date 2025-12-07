"""
QStash Workers Router

Guaranteed delivery workers for critical operations.
All workers verify QStash request signature.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Request

from src.services.database import get_database
from core.routers.deps import verify_qstash, get_notification_service

router = APIRouter(prefix="/api/workers", tags=["workers"])


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
    
    # Complete purchase via RPC
    result = db.client.rpc("complete_purchase", {"p_order_id": order_id}).execute()
    
    if result.data and result.data[0].get("success"):
        content = result.data[0].get("content")
        instructions = result.data[0].get("instructions") or result.data[0].get("note") or ""
        
        # Get order details
        order = db.client.table("orders").select(
            "id, user_telegram_id, products(name)"
        ).eq("id", order_id).single().execute()
        
        # Persist delivery content for frontend (only on success)
        if content:
            try:
                db.client.table("orders").update({
                    "delivery_content": content,
                    "delivery_instructions": instructions
                }).eq("id", order_id).execute()
            except Exception as e:
                print(f"Failed to persist delivery content for order {order_id}: {e}")
        
        if order.data:
            await notification_service.send_delivery(
                telegram_id=order.data["user_telegram_id"],
                product_name=order.data.get("products", {}).get("name", "Product"),
                content=content
            )
        
        return {"success": True, "order_id": order_id}
    
    return {"error": "Failed to complete purchase", "order_id": order_id}


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
    amount = float(order.data["amount"])
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
    
    amount = float(order.data["amount"])
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
    cashback = float(order["amount"]) * 0.05
    
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

