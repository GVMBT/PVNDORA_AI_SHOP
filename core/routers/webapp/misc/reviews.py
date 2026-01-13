"""
Review endpoints.

Product reviews with cashback rewards.
"""

from fastapi import APIRouter, Depends, HTTPException

from core.auth import verify_telegram_auth
from core.db import get_redis
from core.logging import get_logger
from core.services.currency import INTEGER_CURRENCIES, get_currency_service
from core.services.database import get_database
from core.services.money import to_float

from ..models import WebAppReviewRequest
from .constants import REVIEW_CASHBACK_PERCENT

logger = get_logger(__name__)
reviews_router = APIRouter(tags=["webapp-misc-reviews"])


# ==================== REVIEW HELPER FUNCTIONS ====================


async def _determine_review_product_id(
    request: WebAppReviewRequest, order_items: list
) -> str | None:
    """Determine which product is being reviewed from request and order items."""
    if request.product_id:
        return request.product_id
    if request.order_item_id:
        for item in order_items:
            if item.get("id") == request.order_item_id:
                product_id = item.get("product_id")
                if product_id:
                    return product_id
                break
    # Fallback: first item in order (legacy behavior for single-item orders)
    if order_items and order_items[0].get("product_id"):
        return order_items[0].get("product_id")
    return None


def _is_duplicate_key_error(exception: Exception) -> bool:
    """Check if exception is a duplicate key constraint violation."""
    error_str = str(exception)

    # Check error code/status if available
    if hasattr(exception, "code") and (
        exception.code == 409 or str(exception.code) == "23505" or "23505" in str(exception.code)
    ):
        return True
    if hasattr(exception, "status_code") and exception.status_code == 409:
        return True

    # Check error message for conflict indicators
    duplicate_keywords = [
        "23505",
        "duplicate key",
        "unique constraint",
        "already exists",
        "conflict",
    ]
    return any(keyword in error_str.lower() for keyword in duplicate_keywords)


async def _calculate_review_cashback(
    target_item: dict, order, balance_currency: str, currency_service
) -> float:
    """Calculate 5% cashback amount in user's balance currency.
    
    Uses order's fiat_amount and exchange_rate_snapshot for accurate calculation
    based on the currency rate at the time of purchase, not current rate.
    """
    # Get item price in USD
    item_price_usd = to_float(target_item.get("price", 0))
    if item_price_usd <= 0:
        raise HTTPException(status_code=400, detail="Invalid item price")

    # Determine cashback base amount (item price in user's balance currency)
    order_amount_usd = to_float(order.amount) if hasattr(order, "amount") and order.amount else 0
    
    # Priority 1: Use order's fiat_amount if available and currency matches
    # This ensures we use the exact amount user paid, not current exchange rate
    if (
        hasattr(order, "fiat_amount")
        and order.fiat_amount
        and hasattr(order, "fiat_currency")
        and order.fiat_currency == balance_currency
        and order_amount_usd > 0
    ):
        # Calculate proportional item price in fiat currency
        # This preserves the exact exchange rate from when order was created
        item_price_fiat = item_price_usd / order_amount_usd * to_float(order.fiat_amount)
        cashback_base = item_price_fiat
    # Priority 2: Use exchange_rate_snapshot from order if available (for orders without fiat_amount)
    elif (
        hasattr(order, "exchange_rate_snapshot")
        and order.exchange_rate_snapshot
        and balance_currency != "USD"
    ):
        # Use the exchange rate from when the order was created
        rate = to_float(order.exchange_rate_snapshot)
        cashback_base = item_price_usd * rate
    # Fallback: convert item price from USD to user's currency using current rate
    elif balance_currency == "USD":
        cashback_base = item_price_usd
    else:
        # Last resort: use current exchange rate (not ideal, but better than error)
        rate = await currency_service.get_exchange_rate(balance_currency)
        cashback_base = item_price_usd * rate

    # Calculate cashback percentage
    cashback_amount = cashback_base * REVIEW_CASHBACK_PERCENT

    # Round for integer currencies
    if balance_currency in INTEGER_CURRENCIES:
        cashback_amount = round(cashback_amount)
    else:
        cashback_amount = round(cashback_amount, 2)

    return cashback_amount


async def _update_order_expenses_cashback(
    db, order_id: str, cashback_amount: float, balance_currency: str, currency_service
) -> None:
    """Update order_expenses with review cashback amount (in USD for accounting)."""
    try:
        # Convert cashback to USD for accounting
        if balance_currency == "USD":
            cashback_usd = cashback_amount
        else:
            rate = await currency_service.get_exchange_rate(balance_currency)
            cashback_usd = cashback_amount / rate if rate > 0 else cashback_amount

        # Check if order_expenses exists
        current_expenses = (
            await db.client.table("order_expenses")
            .select("review_cashback_amount")
            .eq("order_id", order_id)
            .execute()
        )

        current_cashback_usd = 0.0
        if current_expenses.data and len(current_expenses.data) > 0:
            current_cashback_usd = to_float(
                current_expenses.data[0].get("review_cashback_amount", 0)
            )

        # Sum: existing + new cashback
        total_cashback_usd = current_cashback_usd + cashback_usd

        if current_expenses.data and len(current_expenses.data) > 0:
            # Update existing order_expenses
            await db.client.table("order_expenses").update(
                {"review_cashback_amount": total_cashback_usd}
            ).eq("order_id", order_id).execute()
            logger.info(
                f"Updated order_expenses for {order_id}: review_cashback_amount={total_cashback_usd:.2f} USD (added {cashback_usd:.2f} USD)"
            )
        else:
            # order_expenses doesn't exist - create it via calculate_order_expenses first
            logger.warning(
                f"order_expenses not found for {order_id}, calling calculate_order_expenses first"
            )
            await db.client.rpc("calculate_order_expenses", {"p_order_id": order_id}).execute()

            # Now update review_cashback_amount
            await db.client.table("order_expenses").update(
                {"review_cashback_amount": total_cashback_usd}
            ).eq("order_id", order_id).execute()
            logger.info(
                f"Created and updated order_expenses for {order_id}: review_cashback_amount={total_cashback_usd:.2f} USD"
            )
    except Exception as e:
        logger.error(f"Failed to update order_expenses for {order_id}: {e}", exc_info=True)


@reviews_router.post("/reviews")
async def submit_webapp_review(request: WebAppReviewRequest, user=Depends(verify_telegram_auth)):
    """Submit a product review. Awards 5% cashback per review."""
    db = get_database()

    if not 1 <= request.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Order does not belong to user")
    if order.status not in ["delivered", "partial"]:
        raise HTTPException(status_code=400, detail="Can only review completed orders")

    # Get order items to determine product_id
    order_items = await db.get_order_items_by_order(request.order_id)
    if not order_items:
        raise HTTPException(status_code=400, detail="Order has no products")

    # Determine which product is being reviewed
    product_id = await _determine_review_product_id(request, order_items)
    if not product_id:
        raise HTTPException(status_code=400, detail="Product not found in order")

    # Check if THIS specific product in THIS order already has a review
    existing = (
        await db.client.table("reviews")
        .select("id")
        .eq("order_id", request.order_id)
        .eq("product_id", product_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=400, detail="Вы уже оставили отзыв на этот товар")

    # Insert with race condition handling
    try:
        result = (
            await db.client.table("reviews")
            .insert(
                {
                    "user_id": db_user.id,
                    "order_id": request.order_id,
                    "product_id": product_id,
                    "rating": request.rating,
                    "text": request.text,
                    "cashback_given": False,
                }
            )
            .execute()
        )
    except Exception as e:
        if _is_duplicate_key_error(e):
            logger.info(f"Review already exists for order {request.order_id}, product {product_id}")
            raise HTTPException(status_code=400, detail="Вы уже оставили отзыв на этот товар")

        error_str = str(e)
        error_type = type(e).__name__
        logger.exception(f"Error creating review: {error_type}: {error_str}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании отзыва: {error_str}")

    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=500, detail="Ошибка при создании отзыва")

    review_id = result.data[0]["id"]

    # Find the specific order_item for this product to get its price
    target_item = None
    for item in order_items:
        if item.get("product_id") == product_id:
            target_item = item
            break

    if not target_item:
        raise HTTPException(status_code=400, detail="Product not found in order items")

    # Calculate cashback in user's balance_currency
    balance_currency = getattr(db_user, "balance_currency", "USD") or "USD"
    redis = get_redis()
    currency_service = get_currency_service(redis)

    cashback_amount = await _calculate_review_cashback(
        target_item, order, balance_currency, currency_service
    )

    # Update user balance atomically using RPC
    current_balance = to_float(db_user.balance) if db_user.balance else 0.0
    new_balance = current_balance + cashback_amount

    await db.client.rpc(
        "add_to_user_balance",
        {
            "p_user_id": str(db_user.id),
            "p_amount": cashback_amount,
            "p_reason": f"5% кэшбек за отзыв (заказ {request.order_id})",
        },
    ).execute()

    # Mark review as processed
    await db.client.table("reviews").update({"cashback_given": True}).eq("id", review_id).execute()

    # Update order_expenses for accounting (cashback in USD for financial reports)
    await _update_order_expenses_cashback(
        db, request.order_id, cashback_amount, balance_currency, currency_service
    )

    # Send notification (best-effort)
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
        logger.info(
            f"Cashback notification sent to user {db_user.telegram_id}: {cashback_amount} {balance_currency}"
        )
    except Exception as e:
        logger.error(
            f"Failed to send cashback notification to user {db_user.telegram_id}: {e}",
            exc_info=True,
        )

    return {
        "success": True,
        "review_id": review_id,
        "cashback_amount": round(cashback_amount, 2),
        "new_balance": round(new_balance, 2),
        "message": "Кэшбек начислен!",
    }
