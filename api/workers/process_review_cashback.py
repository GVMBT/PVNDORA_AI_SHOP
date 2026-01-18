"""Worker: Process Review Cashback
Called by QStash after review submission.

This worker:
1. Validates review exists and cashback not already given
2. Calculates 5% cashback from order amount
3. Credits user balance
4. Creates balance_transaction record
5. Sends Telegram notification
"""

import json
import logging
import os
from typing import Any, cast

# Type alias for dict type hints
DictStrAny = dict[str, Any]

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from core.services.models import User

logger = logging.getLogger(__name__)

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

    return bool(not QSTASH_CURRENT_SIGNING_KEY and not QSTASH_NEXT_SIGNING_KEY)


async def _get_review(db: Any, order_id: str) -> dict[str, Any] | None:
    """Get review by order_id. Returns None if not found or already processed."""
    result = (
        await db.client.table("reviews")
        .select("id, cashback_given")
        .eq("order_id", order_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    review_raw = result.data[0]
    if not isinstance(review_raw, dict):
        return None
    return cast(DictStrAny, review_raw)


async def _get_user_from_order(db: Any, order_id: str) -> User | None:
    """Get user from order. Returns None if not found."""
    order_result = (
        await db.client.table("orders").select("user_id").eq("id", order_id).single().execute()
    )
    if not order_result.data or not isinstance(order_result.data, dict):
        return None
    user_id = cast(DictStrAny, order_result.data).get("user_id")
    if not user_id:
        return None
    user_result = await db.client.table("users").select("*").eq("id", user_id).single().execute()
    if not user_result.data or not isinstance(user_result.data, dict):
        return None
    return User(**cast(DictStrAny, user_result.data))


async def _get_order_amounts(db: Any, order_id: str) -> dict[str, Any] | None:
    """Get order amount data."""
    result = (
        await db.client.table("orders")
        .select("amount, fiat_amount, fiat_currency")
        .eq("id", order_id)
        .single()
        .execute()
    )
    if not result.data or not isinstance(result.data, dict):
        return None
    return cast(dict[str, Any], result.data)


def _calculate_cashback(
    order_data: dict[str, Any],
    balance_currency: str,
    fallback_amount: float | None,
) -> float:
    """Calculate 5% cashback in user's balance currency."""
    from core.db import get_redis
    from core.services.currency import get_currency_service
    from core.services.money import to_float

    redis = get_redis()
    currency_service = get_currency_service(redis)

    if order_data.get("fiat_amount") and order_data.get("fiat_currency") == balance_currency:
        cashback_base = to_float(order_data["fiat_amount"])
    else:
        cashback_base_usd = to_float(order_data.get("amount", fallback_amount or 0))
        if balance_currency == "USD":
            cashback_base = cashback_base_usd
        else:
            rate = currency_service.get_exchange_rate(balance_currency)
            cashback_base = cashback_base_usd * rate

    cashback = cashback_base * 0.05
    if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
        return round(cashback)
    return round(cashback, 2)


async def _credit_user_balance(
    db: Any,
    user: User,
    cashback_amount: float,
    balance_currency: str,
    order_id: str,
) -> float:
    """Credit user balance and create transaction. Returns new balance."""
    from core.services.money import to_float

    current_balance = to_float(user.balance or 0)
    new_balance = current_balance + cashback_amount

    await db.client.table("users").update({"balance": new_balance}).eq("id", user.id).execute()
    await (
        db.client.table("balance_transactions")
        .insert(
            {
                "user_id": user.id,
                "type": "cashback",
                "amount": cashback_amount,
                "currency": balance_currency,
                "status": "completed",
                "description": "5% кэшбек за отзыв",
                "reference_id": order_id,
                "balance_before": current_balance,
                "balance_after": new_balance,
            },
        )
        .execute()
    )

    # Emit realtime event for profile update (cashback received)
    try:
        from core.realtime import emit_profile_update

        await emit_profile_update(str(user.id), {"balance_updated": True, "cashback_received": True})
    except Exception as e:
        logger.warning(f"Failed to emit profile.updated event: {e}", exc_info=True)

    return new_balance


async def _send_cashback_notification(
    telegram_id: int,
    cashback_amount: float,
    new_balance: float,
    balance_currency: str,
) -> None:
    """Send cashback notification to user."""
    try:
        from core.routers.deps import get_notification_service

        notification_service = get_notification_service()
        await notification_service.send_cashback_notification(
            telegram_id=telegram_id,
            cashback_amount=cashback_amount,
            new_balance=new_balance,
            currency=balance_currency,
            reason="review",
        )
    except Exception as e:
        logger.warning(f"Failed to send cashback notification: {e}")


@app.post("/api/workers/process-review-cashback")
async def process_review_cashback(request: Request) -> JSONResponse:
    """Process 5% cashback for review."""
    body = await request.body()
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

    db = await get_database_async()

    # 1. Get and validate review
    review = await _get_review(db, order_id)
    if not review:
        return JSONResponse({"error": "Review not found for order"}, status_code=404)
    if review.get("cashback_given"):
        return JSONResponse({"skipped": True, "reason": "Cashback already processed"})

    # 2. Get user
    db_user = await db.get_user_by_telegram_id(user_telegram_id) if user_telegram_id else None
    if not db_user:
        db_user = await _get_user_from_order(db, order_id)
    if not db_user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    # 3. Get order amounts
    order_data = await _get_order_amounts(db, order_id)
    if not order_data:
        return JSONResponse({"error": "Order not found"}, status_code=404)

    # 4. Calculate cashback
    balance_currency = getattr(db_user, "balance_currency", "USD") or "USD"
    cashback_amount = _calculate_cashback(order_data, balance_currency, order_amount)

    # 5. Credit balance
    new_balance = await _credit_user_balance(
        db,
        db_user,
        cashback_amount,
        balance_currency,
        order_id,
    )

    # 6. Mark review as processed
    await (
        db.client.table("reviews").update({"cashback_given": True}).eq("id", review["id"]).execute()
    )

    # 7. Send notification
    if db_user.telegram_id:
        await _send_cashback_notification(
            db_user.telegram_id,
            cashback_amount,
            new_balance,
            balance_currency,
        )

    logger.info(
        f"Cashback processed: user={db_user.telegram_id}, amount={cashback_amount} {balance_currency}",
    )
    return JSONResponse({"success": True, "cashback": cashback_amount, "new_balance": new_balance})
