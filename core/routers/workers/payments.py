"""
Payment Workers

QStash workers for payment-related operations (refund, cashback).
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Request

from core.services.database import get_database
from core.services.money import to_float
from core.routers.deps import verify_qstash, get_notification_service
from core.logging import get_logger

logger = get_logger(__name__)

payments_router = APIRouter()


@payments_router.post("/process-refund")
async def worker_process_refund(request: Request):
    """
    QStash Worker: Process refund for prepaid orders.
    
    Also handles:
    - Rollback of turnover (recalculates: own orders + referral orders, excluding refunded order)
    - Revoke referral bonuses paid for this order
    
    IMPORTANT: Refund is credited in user's balance_currency, using fiat_amount if available.
    """
    data = await verify_qstash(request)
    order_id = data.get("order_id")
    reason = data.get("reason", "Fulfillment deadline exceeded")
    usd_rate = data.get("usd_rate", 100)
    
    if not order_id:
        return {"error": "order_id required"}
    
    db = get_database()
    notification_service = get_notification_service()
    
    # Get order with fiat amount
    order = await db.client.table("orders").select(
        "id, amount, fiat_amount, fiat_currency, user_id, user_telegram_id, status, products(name)"
    ).eq("id", order_id).single().execute()
    
    if not order.data:
        return {"error": "Order not found"}
    
    if order.data["status"] not in ["prepaid", "paid", "partial", "delivered"]:
        return {"skipped": True, "reason": f"Order status is {order.data['status']}, cannot refund"}
    
    user_id = order.data["user_id"]
    amount_usd = to_float(order.data["amount"])
    
    # Get user's balance_currency
    user_result = await db.client.table("users").select("balance_currency").eq("id", user_id).single().execute()
    balance_currency = user_result.data.get("balance_currency", "USD") if user_result.data else "USD"
    
    # Determine refund amount in user's balance currency
    # Priority: fiat_amount (what user actually paid) > convert from USD
    if order.data.get("fiat_amount") and order.data.get("fiat_currency") == balance_currency:
        # User paid in their balance currency - use exact fiat amount
        refund_amount = to_float(order.data["fiat_amount"])
    else:
        # Convert USD to user's balance currency
        if balance_currency == "USD":
            refund_amount = amount_usd
        else:
            # Use provided usd_rate or current rate
            from core.db import get_redis
            from core.services.currency import get_currency_service
            redis = get_redis()
            currency_service = get_currency_service(redis)
            rate = await currency_service.get_exchange_rate(balance_currency)
            refund_amount = round(amount_usd * rate)  # Round for integer currencies
    
    # 1. Rollback turnover and revoke referral bonuses (always in RUB for consistency)
    rollback_result = await db.client.rpc("rollback_user_turnover", {
        "p_user_id": user_id,
        "p_amount_rub": amount_usd * usd_rate,  # Convert to RUB for turnover
        "p_usd_rate": usd_rate,
        "p_order_id": order_id
    }).execute()
    
    # 2. Refund to user balance (in user's balance_currency)
    await db.client.rpc("add_to_user_balance", {
        "p_user_id": user_id,
        "p_amount": refund_amount,
        "p_reason": f"Refund for order {order_id}: {reason}"
    }).execute()
    
    # 3. Update order status
    await db.client.table("orders").update({
        "status": "refunded",
        "refund_reason": reason,
        "refund_processed_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", order_id).execute()
    
    # 4. Notify user with correct currency
    await notification_service.send_refund_notification(
        telegram_id=order.data["user_telegram_id"],
        product_name=order.data.get("products", {}).get("name", "Product"),
        amount=refund_amount,
        currency=balance_currency,
        reason=reason
    )
    
    return {
        "success": True, 
        "refunded_amount": refund_amount,
        "refund_currency": balance_currency,
        "turnover_rollback": rollback_result.data if rollback_result.data else {}
    }


@payments_router.post("/process-review-cashback")
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
    review_result = await db.client.table("reviews").select(
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
        order_result = await db.client.table("orders").select("user_id, amount, fiat_amount, fiat_currency").eq("id", order_id).single().execute()
        if not order_result.data:
            return {"error": "Order not found"}
        user_result = await db.client.table("users").select("*").eq("id", order_result.data["user_id"]).single().execute()
        if not user_result.data:
            return {"error": "User not found"}
        db_user = type('User', (), user_result.data)()
    
    # CRITICAL: Calculate cashback in user's balance_currency, NOT in USD
    balance_currency = getattr(db_user, 'balance_currency', 'USD') or 'USD'
    
    # Get order details
    order_result = await db.client.table("orders").select("amount, fiat_amount, fiat_currency").eq("id", order_id).single().execute()
    if not order_result.data:
        return {"error": "Order not found"}
    order_data = order_result.data
    
    # Determine cashback base amount - use fiat_amount if available
    from core.db import get_redis
    from core.services.currency import get_currency_service
    redis = get_redis()
    currency_service = get_currency_service(redis)
    
    if order_data.get("fiat_amount") and order_data.get("fiat_currency") == balance_currency:
        # Use fiat_amount (what user actually paid in their currency)
        cashback_base = to_float(order_data["fiat_amount"])
    else:
        # Fallback: convert from USD amount
        cashback_base_usd = to_float(order_data.get("amount", order_amount or 0))
        if balance_currency == "USD":
            cashback_base = cashback_base_usd
        else:
            rate = await currency_service.get_exchange_rate(balance_currency)
            cashback_base = cashback_base_usd * rate
    
    # Calculate 5% cashback in user's balance_currency
    cashback_amount = cashback_base * 0.05
    
    # Round for integer currencies
    if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
        cashback_amount = round(cashback_amount)
    else:
        cashback_amount = round(cashback_amount, 2)
    
    # 1. Update user balance
    new_balance = to_float(db_user.balance or 0) + cashback_amount
    await db.client.table("users").update({
        "balance": new_balance
    }).eq("id", db_user.id).execute()
    
    # 2. Create balance_transaction for history (amount in balance_currency!)
    await db.client.table("balance_transactions").insert({
        "user_id": db_user.id,
        "type": "cashback",
        "amount": cashback_amount,  # In balance_currency
        "currency": balance_currency,  # User's balance currency
        "status": "completed",
        "description": "5% кэшбек за отзыв",
        "reference_id": order_id,
    }).execute()
    
    # 3. Mark review as processed
    await db.client.table("reviews").update({
        "cashback_given": True
    }).eq("id", review["id"]).execute()
    
    # 4. Update order_expenses for accounting (cashback in USD for financial reports)
    try:
        # Convert cashback to USD for accounting
        if balance_currency == "USD":
            cashback_usd = cashback_amount
        else:
            rate = await currency_service.get_exchange_rate(balance_currency)
            cashback_usd = cashback_amount / rate if rate > 0 else cashback_amount
        
        # Update order_expenses table
        await db.client.table("order_expenses").update({
            "review_cashback_amount": cashback_usd
        }).eq("order_id", order_id).execute()
        logger.info(f"Updated order_expenses for {order_id}: review_cashback_amount={cashback_usd:.2f} USD")
    except Exception as e:
        logger.warning(f"Failed to update order_expenses for {order_id}: {e}")
    
    # 5. Send Telegram notification using notification service (supports currency)
    try:
        from core.routers.deps import get_notification_service
        notification_service = get_notification_service()
        await notification_service.send_cashback_notification(
            telegram_id=db_user.telegram_id,
            cashback_amount=cashback_amount,
            new_balance=new_balance,
            currency=balance_currency,
            reason="review"
        )
    except Exception as e:
        logger.warning(f"Failed to send cashback notification: {e}")
    
    logger.info(f"Cashback processed: user={db_user.telegram_id}, amount={cashback_amount} {balance_currency}, order={order_id}")
    
    return {"success": True, "cashback": cashback, "new_balance": new_balance}
