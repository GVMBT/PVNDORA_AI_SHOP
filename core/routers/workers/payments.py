"""Payment Workers.

QStash workers for payment-related operations (refund, cashback).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Request

from core.logging import get_logger
from core.routers.deps import get_notification_service, verify_qstash
from core.services.database import get_database
from core.services.money import to_float

logger = get_logger(__name__)

# Constants
ERROR_ORDER_NOT_FOUND = "Order not found"


# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


async def _calculate_cashback_base(
    order_data: dict,
    order_amount: float,
    balance_currency: str,
) -> float:
    """Calculate cashback base amount in user's balance currency."""
    fiat_amount = order_data.get("fiat_amount")
    fiat_currency = order_data.get("fiat_currency")

    if fiat_amount is not None and fiat_currency == balance_currency:
        return float(fiat_amount)

    if balance_currency == "USD":
        return float(order_amount)

    from core.db import get_redis
    from core.services.currency import get_currency_service

    redis = get_redis()
    currency_service = get_currency_service(redis)
    rate = await currency_service.get_exchange_rate(balance_currency)

    return float(order_amount) * rate


def _get_currency_service():
    """Get currency service instance."""
    from core.db import get_redis
    from core.services.currency import get_currency_service

    redis = get_redis()
    return get_currency_service(redis)


def _round_for_currency(amount: float, currency: str) -> float:
    """Round amount appropriately for the currency."""
    integer_currencies = ["RUB", "UAH", "TRY", "INR"]
    if currency in integer_currencies:
        return round(amount)
    return round(amount, 2)


async def _get_refund_amount(order_data: dict, amount_usd: float, balance_currency: str) -> float:
    """Calculate refund amount in user's balance currency."""
    # Use fiat_amount if available and matches balance currency
    if order_data.get("fiat_amount") and order_data.get("fiat_currency") == balance_currency:
        return to_float(order_data["fiat_amount"])

    if balance_currency == "USD":
        return amount_usd

    # Convert USD to balance currency
    currency_service = _get_currency_service()
    rate = await currency_service.get_exchange_rate(balance_currency)
    return round(amount_usd * rate)


async def _update_order_expenses(db, order_id: str, cashback_usd: float) -> None:
    """Update order_expenses with review cashback amount."""
    current_expenses = (
        await db.client.table("order_expenses")
        .select("review_cashback_amount")
        .eq("order_id", order_id)
        .execute()
    )

    current_cashback_usd = 0.0
    if current_expenses.data:
        current_cashback_usd = float(current_expenses.data[0].get("review_cashback_amount", 0) or 0)

    total_cashback_usd = current_cashback_usd + cashback_usd

    if current_expenses.data:
        await (
            db.client.table("order_expenses")
            .update({"review_cashback_amount": total_cashback_usd})
            .eq("order_id", order_id)
            .execute()
        )
        logger.info(
            f"Updated order_expenses for {order_id}: review_cashback_amount={total_cashback_usd:.2f} USD",
        )
    else:
        # Create order_expenses first
        logger.warning(
            f"order_expenses not found for {order_id}, calling calculate_order_expenses first",
        )
        await db.client.rpc("calculate_order_expenses", {"p_order_id": order_id}).execute()
        await (
            db.client.table("order_expenses")
            .update({"review_cashback_amount": total_cashback_usd})
            .eq("order_id", order_id)
            .execute()
        )
        logger.info(
            f"Created and updated order_expenses for {order_id}: review_cashback_amount={total_cashback_usd:.2f} USD",
        )


async def _convert_to_usd(amount: float, currency: str) -> float:
    """Convert amount to USD."""
    if currency == "USD":
        return float(amount)
    currency_service = _get_currency_service()
    rate = await currency_service.get_exchange_rate(currency)
    return float(amount / rate) if rate > 0 else float(amount)


async def _get_user_from_order(db, order_id: str):
    """Get user from order for cashback processing."""
    order_result = (
        await db.client.table("orders")
        .select("user_id, amount, fiat_amount, fiat_currency")
        .eq("id", order_id)
        .single()
        .execute()
    )
    if not order_result.data:
        return None, None

    user_result = (
        await db.client.table("users")
        .select("*")
        .eq("id", order_result.data["user_id"])
        .single()
        .execute()
    )
    if not user_result.data:
        return None, order_result.data

    return type("User", (), user_result.data)(), order_result.data


async def _get_user_and_order_for_cashback(db, order_id: str, user_telegram_id: int | None):
    """Get user and order data for cashback processing."""
    if user_telegram_id:
        db_user = await db.get_user_by_telegram_id(user_telegram_id)
        if db_user:
            order_result = (
                await db.client.table("orders")
                .select("amount, fiat_amount, fiat_currency")
                .eq("id", order_id)
                .single()
                .execute()
            )
            order_data = order_result.data if order_result.data else {}
            return db_user, order_data

    return await _get_user_from_order(db, order_id)


async def _process_cashback_update(
    db,
    db_user,
    order_id: str,
    cashback_amount: float,
    balance_currency: str,
) -> float:
    """Update user balance and create transaction for cashback."""
    new_balance = to_float(db_user.balance or 0) + cashback_amount
    await db.client.table("users").update({"balance": new_balance}).eq("id", db_user.id).execute()

    await (
        db.client.table("balance_transactions")
        .insert(
            {
                "user_id": db_user.id,
                "type": "cashback",
                "amount": cashback_amount,
                "currency": balance_currency,
                "status": "completed",
                "description": "5% кэшбек за отзыв",
                "reference_id": order_id,
            },
        )
        .execute()
    )

    return new_balance


async def _send_cashback_notification_safe(
    db_user,
    cashback_amount: float,
    new_balance: float,
    balance_currency: str,
) -> None:
    """Send cashback notification (safe, logs errors)."""
    try:
        notification_service = get_notification_service()
        await notification_service.send_cashback_notification(
            telegram_id=db_user.telegram_id,
            cashback_amount=cashback_amount,
            new_balance=new_balance,
            currency=balance_currency,
            reason="review",
        )
    except Exception as e:
        logger.warning(f"Failed to send cashback notification: {e}")


# =============================================================================
# Worker Endpoints
# =============================================================================


payments_router = APIRouter()


@payments_router.post("/process-refund")
async def worker_process_refund(request: Request):
    """QStash Worker: Process refund for prepaid orders."""
    data = await verify_qstash(request)
    order_id = data.get("order_id")
    reason = data.get("reason", "Fulfillment deadline exceeded")
    usd_rate = data.get("usd_rate", 100)

    if not order_id:
        return {"error": "order_id required"}

    db = get_database()
    notification_service = get_notification_service()

    # Get order with fiat amount
    order = (
        await db.client.table("orders")
        .select(
            "id, amount, fiat_amount, fiat_currency, user_id, user_telegram_id, status, products(name)",
        )
        .eq("id", order_id)
        .single()
        .execute()
    )

    if not order.data or not isinstance(order.data, dict):
        return {"error": ERROR_ORDER_NOT_FOUND}

    order_data = order.data
    if order_data.get("status") not in ["prepaid", "paid", "partial", "delivered"]:
        status = order_data.get("status", "unknown")
        return {"skipped": True, "reason": f"Order status is {status}, cannot refund"}

    user_id = order_data.get("user_id")
    if not user_id:
        return {"error": "Order missing user_id"}
    amount_val = order_data.get("amount", 0)
    amount_usd = to_float(
        str(amount_val) if not isinstance(amount_val, (int, float)) else amount_val
    )

    # Get user's balance_currency
    user_result = (
        await db.client.table("users")
        .select("balance_currency")
        .eq("id", user_id)
        .single()
        .execute()
    )
    balance_currency_val = (
        user_result.data.get("balance_currency", "RUB")
        if isinstance(user_result.data, dict) and user_result.data
        else "RUB"
    )
    balance_currency = str(balance_currency_val) if balance_currency_val else "RUB"

    # Calculate refund amount
    refund_amount = await _get_refund_amount(order_data, amount_usd, balance_currency)

    # 1. Rollback turnover and revoke referral bonuses
    rollback_result = await db.client.rpc(
        "rollback_user_turnover",
        {
            "p_user_id": user_id,
            "p_amount_rub": amount_usd * usd_rate,
            "p_usd_rate": usd_rate,
            "p_order_id": order_id,
        },
    ).execute()

    # 2. Refund to user balance
    await db.client.rpc(
        "add_to_user_balance",
        {
            "p_user_id": user_id,
            "p_amount": refund_amount,
            "p_reason": f"Возврат средств: {reason}",
            "p_reference_type": "order",
            "p_reference_id": str(order_id),
            "p_metadata": {
                "order_id": str(order_id),
                "refund_reason": reason,
                "refund_type": "manual",
            },
        },
    ).execute()

    # 3. Update order status
    await (
        db.client.table("orders")
        .update(
            {
                "status": "refunded",
                "refund_reason": reason,
                "refund_processed_at": datetime.now(UTC).isoformat(),
            },
        )
        .eq("id", order_id)
        .execute()
    )

    # 4. Notify user
    telegram_id_val = order_data.get("user_telegram_id")
    telegram_id = (
        int(telegram_id_val) if telegram_id_val and isinstance(telegram_id_val, (int, str)) else 0
    )
    products_data = order_data.get("products")
    if isinstance(products_data, dict):
        product_name = str(products_data.get("name", "Product"))
    else:
        product_name = "Product"

    await notification_service.send_refund_notification(
        telegram_id=telegram_id,
        product_name=product_name,
        amount=refund_amount,
        currency=balance_currency,
        reason=reason,
    )

    return {
        "success": True,
        "refunded_amount": refund_amount,
        "refund_currency": balance_currency,
        "turnover_rollback": rollback_result.data if rollback_result.data else {},
    }


@payments_router.post("/process-review-cashback")
async def worker_process_review_cashback(request: Request):
    """QStash Worker: Process 5% cashback for review."""
    data = await verify_qstash(request)

    order_id = data.get("order_id")
    user_telegram_id = data.get("user_telegram_id")
    order_amount = data.get("order_amount")

    if not order_id:
        return {"error": "order_id required"}

    db = get_database()

    # Find review by order_id
    review_result = (
        await db.client.table("reviews")
        .select("id, cashback_given")
        .eq("order_id", order_id)
        .limit(1)
        .execute()
    )

    if not review_result.data:
        return {"error": "Review not found for order"}

    review = review_result.data[0]

    if review.get("cashback_given"):
        return {"skipped": True, "reason": "Cashback already processed"}

    # Additional check: verify no existing cashback transaction for this order
    existing_tx = (
        await db.client.table("balance_transactions")
        .select("id")
        .eq("reference_id", order_id)
        .eq("type", "cashback")
        .limit(1)
        .execute()
    )
    if existing_tx.data:
        logger.warning(
            f"Cashback transaction already exists for order {order_id}, marking review as processed",
        )
        await (
            db.client.table("reviews")
            .update({"cashback_given": True})
            .eq("id", review["id"])
            .execute()
        )
        return {"skipped": True, "reason": "Cashback transaction already exists"}

    # Get user and order data
    db_user, order_data = await _get_user_and_order_for_cashback(db, order_id, user_telegram_id)
    if not db_user:
        return {"error": "User not found"}
    if not order_data:
        return {"error": ERROR_ORDER_NOT_FOUND}

    # Calculate cashback in user's balance_currency
    balance_currency = getattr(db_user, "balance_currency", "RUB") or "RUB"
    cashback_base = await _calculate_cashback_base(order_data, order_amount, balance_currency)
    cashback_amount = _round_for_currency(cashback_base * 0.05, balance_currency)

    # Update user balance and create transaction
    new_balance = await _process_cashback_update(
        db,
        db_user,
        order_id,
        cashback_amount,
        balance_currency,
    )

    # Mark review as processed
    await (
        db.client.table("reviews").update({"cashback_given": True}).eq("id", review["id"]).execute()
    )

    # Update order_expenses
    try:
        cashback_usd = await _convert_to_usd(cashback_amount, balance_currency)
        await _update_order_expenses(db, order_id, cashback_usd)
    except Exception as e:
        logger.error(f"Failed to update order_expenses for {order_id}: {e}", exc_info=True)

    # Send notification
    await _send_cashback_notification_safe(db_user, cashback_amount, new_balance, balance_currency)

    logger.info(
        f"Cashback processed: user={db_user.telegram_id}, amount={cashback_amount} {balance_currency}",
    )

    return {"success": True, "cashback": cashback_amount, "new_balance": new_balance}
