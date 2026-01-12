"""
Worker: Process Review Cashback
Called by QStash after review submission.

This worker:
1. Validates review exists and cashback not already given
2. Calculates 5% cashback from order amount
3. Credits user balance
4. Creates balance_transaction record
5. Sends Telegram notification
"""

import json
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# ASGI app
app = FastAPI()

QSTASH_CURRENT_SIGNING_KEY = os.environ.get("QSTASH_CURRENT_SIGNING_KEY", "")
QSTASH_NEXT_SIGNING_KEY = os.environ.get("QSTASH_NEXT_SIGNING_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")


def verify_qstash_signature(request: Request, body: bytes) -> bool:
    """Verify QStash request signature."""
    import hashlib
    import hmac

    signature = request.headers.get("Upstash-Signature", "")
    if not signature:
        return False

    for key in [QSTASH_CURRENT_SIGNING_KEY, QSTASH_NEXT_SIGNING_KEY]:
        if not key:
            continue
        expected = hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected):
            return True

    # In development, allow if no keys configured
    return bool(not QSTASH_CURRENT_SIGNING_KEY and not QSTASH_NEXT_SIGNING_KEY)


async def send_telegram_message(chat_id: int, text: str) -> bool:
    """Send a message via Telegram Bot API.

    Wrapper around consolidated telegram_messaging service.
    """
    from core.services.telegram_messaging import send_telegram_message as _send_msg

    return await _send_msg(chat_id=chat_id, text=text, parse_mode="HTML", bot_token=TELEGRAM_TOKEN)


@app.post("/api/workers/process-review-cashback")
async def process_review_cashback(request: Request):
    """
    Process 5% cashback for review.

    Expected payload:
    {
        "order_id": "uuid",
        "user_telegram_id": 123456,
        "order_amount": 60.0
    }
    """
    body = await request.body()

    # Verify signature
    if not verify_qstash_signature(request, body):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    order_id = payload.get("order_id")
    user_telegram_id = payload.get("user_telegram_id")
    order_amount = payload.get("order_amount")

    if not order_id:
        return JSONResponse({"error": "order_id required"}, status_code=400)

    from core.services.database import get_database_async
    from core.services.money import to_float

    db = await get_database_async()

    # Find review by order_id
    review_result = (
        await db.client.table("reviews")
        .select("id, cashback_given")
        .eq("order_id", order_id)
        .limit(1)
        .execute()
    )

    if not review_result.data:
        return JSONResponse({"error": "Review not found for order"}, status_code=404)

    review = review_result.data[0]

    if review.get("cashback_given"):
        return JSONResponse({"skipped": True, "reason": "Cashback already processed"})

    # Get user by telegram_id
    db_user = await db.get_user_by_telegram_id(user_telegram_id) if user_telegram_id else None

    # Fallback: get user from order
    if not db_user:
        order_result = (
            await db.client.table("orders")
            .select("user_id, amount, fiat_amount, fiat_currency")
            .eq("id", order_id)
            .single()
            .execute()
        )
        if not order_result.data:
            return JSONResponse({"error": "Order not found"}, status_code=404)
        user_result = (
            await db.client.table("users")
            .select("*")
            .eq("id", order_result.data["user_id"])
            .single()
            .execute()
        )
        if not user_result.data:
            return JSONResponse({"error": "User not found"}, status_code=404)
        from types import SimpleNamespace

        db_user = SimpleNamespace(**user_result.data)
        db_user.id = user_result.data["id"]
        db_user.telegram_id = user_result.data.get("telegram_id")
        db_user.balance = user_result.data.get("balance", 0)

    # CRITICAL: Calculate cashback in user's balance_currency, NOT in USD
    balance_currency = getattr(db_user, "balance_currency", "USD") or "USD"

    # Get order details (always fetch to get fiat_amount/fiat_currency)
    order_result = (
        await db.client.table("orders")
        .select("amount, fiat_amount, fiat_currency")
        .eq("id", order_id)
        .single()
        .execute()
    )
    if not order_result.data:
        return JSONResponse({"error": "Order not found"}, status_code=404)
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
    current_balance = to_float(db_user.balance or 0)
    new_balance = current_balance + cashback_amount

    await db.client.table("users").update({"balance": new_balance}).eq("id", db_user.id).execute()

    # 2. Create balance_transaction for history (amount in balance_currency!)
    await db.client.table("balance_transactions").insert(
        {
            "user_id": db_user.id,
            "type": "cashback",
            "amount": cashback_amount,  # In balance_currency
            "currency": balance_currency,  # User's balance currency
            "status": "completed",
            "description": "5% кэшбек за отзыв",
            "reference_id": order_id,
            "balance_before": current_balance,
            "balance_after": new_balance,
        }
    ).execute()

    # 3. Mark review as processed
    await db.client.table("reviews").update({"cashback_given": True}).eq(
        "id", review["id"]
    ).execute()

    # 4. Send Telegram notification using notification service (supports currency)
    if db_user.telegram_id:
        try:
            from core.routers.deps import get_notification_service

            notification_service = get_notification_service()
            await notification_service.send_cashback_notification(
                telegram_id=db_user.telegram_id,
                cashback_amount=cashback_amount,
                new_balance=new_balance,
                currency=balance_currency,
                reason="review",
            )
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to send cashback notification: {e}")

    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"Cashback processed: user={db_user.telegram_id}, amount={cashback_amount} {balance_currency}, order={order_id}"
    )

    return JSONResponse({"success": True, "cashback": cashback_amount, "new_balance": new_balance})
