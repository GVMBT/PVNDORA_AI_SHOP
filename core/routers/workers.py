"""
QStash Workers Router

Guaranteed delivery workers for critical operations.
All workers verify QStash request signature.
"""

from datetime import datetime
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
        
        # Get order details
        order = db.client.table("orders").select(
            "user_telegram_id, products(name)"
        ).eq("id", order_id).single().execute()
        
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
    Also handles referral program unlock notification.
    """
    data = await verify_qstash(request)
    order_id = data.get("order_id")
    
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
    
    # 1. Unlock referral program and check level up
    unlock_result = db.client.rpc("unlock_referral_program", {
        "p_user_id": user_id,
        "p_order_amount": amount
    }).execute()
    
    if unlock_result.data:
        result_data = unlock_result.data
        
        # Send notification if first unlock
        if result_data.get("first_unlock"):
            telegram_id = order.data.get("user_telegram_id")
            if telegram_id:
                await notification_service.send_referral_unlock_notification(telegram_id)
        
        # Send notification if level up
        if result_data.get("level_up"):
            telegram_id = order.data.get("user_telegram_id")
            new_level = result_data.get("new_level", 1)
            if telegram_id:
                await notification_service.send_referral_level_up_notification(telegram_id, new_level)
    
    # 2. Calculate referral bonuses for referrer chain
    referrer_id = order.data.get("users", {}).get("referrer_id")
    if not referrer_id:
        return {"success": True, "unlock_result": unlock_result.data, "bonuses": "no_referrer"}
    
    bonuses_paid = []
    current_referrer = referrer_id
    
    for level in range(1, 4):  # Levels 1, 2, 3
        if not current_referrer:
            break
        
        # Get referrer's level and calculate percent
        referrer = db.client.table("users").select(
            "id, referrer_id, referral_level, telegram_id"
        ).eq("id", current_referrer).single().execute()
        
        if not referrer.data:
            break
        
        referrer_level = referrer.data.get("referral_level", 1)
        
        # Get percents based on referrer's level
        percents = db.client.rpc("get_referral_percents", {
            "p_user_level": referrer_level
        }).execute()
        
        if percents.data:
            percent_key = f"level{level}_percent"
            percent = percents.data[0].get(percent_key, 0) if percents.data else 0
            
            if percent > 0:
                bonus = amount * percent / 100
                
                # Record bonus
                db.client.table("referral_bonuses").insert({
                    "user_id": current_referrer,
                    "from_user_id": user_id,
                    "order_id": order_id,
                    "level": level,
                    "percent": percent,
                    "amount": bonus
                }).execute()
                
                # Add to balance
                db.client.table("users").update({
                    "balance": db.client.table("users").select("balance").eq("id", current_referrer).single().execute().data.get("balance", 0) + bonus,
                    "total_referral_earnings": db.client.table("users").select("total_referral_earnings").eq("id", current_referrer).single().execute().data.get("total_referral_earnings", 0) + bonus
                }).eq("id", current_referrer).execute()
                
                bonuses_paid.append({
                    "level": level,
                    "referrer_id": current_referrer,
                    "percent": percent,
                    "bonus": bonus
                })
        
        # Move to next level referrer
        current_referrer = referrer.data.get("referrer_id")
    
    return {"success": True, "bonuses_paid": bonuses_paid}


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
    """
    data = await verify_qstash(request)
    order_id = data.get("order_id")
    reason = data.get("reason", "Fulfillment deadline exceeded")
    
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
    
    if order.data["status"] != "prepaid":
        return {"skipped": True, "reason": f"Order status is {order.data['status']}"}
    
    # Refund to balance
    db.client.rpc("add_to_user_balance", {
        "p_user_id": order.data["user_id"],
        "p_amount": float(order.data["amount"]),
        "p_reason": f"Refund for order {order_id}: {reason}"
    }).execute()
    
    # Update order
    db.client.table("orders").update({
        "status": "refunded",
        "refund_reason": reason,
        "refund_processed_at": datetime.utcnow().isoformat()
    }).eq("id", order_id).execute()
    
    # Notify user
    await notification_service.send_refund_notification(
        telegram_id=order.data["user_telegram_id"],
        product_name=order.data.get("products", {}).get("name", "Product"),
        amount=order.data["amount"],
        reason=reason
    )
    
    return {"success": True, "refunded_amount": order.data["amount"]}


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

