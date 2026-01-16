"""Balance Endpoints.

Balance top-up and related operations.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from fastapi import APIRouter, Depends, HTTPException

from core.auth import verify_telegram_auth
from core.logging import get_logger
from core.routers.webapp.models import TopUpRequest
from core.services.database import get_database

logger = get_logger(__name__)

balance_router = APIRouter()

# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


async def _calculate_amount_to_credit(
    currency: str,
    balance_currency: str,
    amount: float,
    currency_service,
) -> float:
    """Calculate amount to credit in balance currency (reduces cognitive complexity)."""
    if currency == balance_currency:
        return amount

    if currency in ["USD", "RUB"] and balance_currency in ["USD", "RUB"]:
        amount_decimal = await currency_service.convert_balance(currency, balance_currency, amount)
        return float(amount_decimal)

    # Convert: payment_currency → USD → balance_currency
    if currency == "USD":
        amount_usd = amount
    else:
        payment_rate = await currency_service.get_exchange_rate(currency)
        amount_usd = amount / payment_rate if payment_rate > 0 else amount

    if balance_currency == "USD":
        return amount_usd

    if balance_currency == "RUB":
        amount_decimal = await currency_service.convert_balance("USD", "RUB", amount_usd)
        return float(amount_decimal)

    logger.warning("Unexpected balance_currency: %s (expected USD or RUB)", balance_currency)
    balance_rate = await currency_service.get_exchange_rate(balance_currency)
    return amount_usd * balance_rate


@balance_router.post("/profile/topup")
async def create_topup(request: TopUpRequest, user=Depends(verify_telegram_auth)):
    """Create a balance top-up payment via CrystalPay.

    Minimum: 5 USD equivalent.
    Returns payment URL for redirect.
    """
    from core.db import get_redis
    from core.services.currency_response import CurrencyFormatter, format_price_simple

    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    currency = request.currency.upper()
    redis = get_redis()

    # Get formatter to calculate minimum in user's currency
    formatter = CurrencyFormatter.create(user.id, db, redis, preferred_currency=currency)

    # Minimum top-up amounts by currency (fixed amounts, not converted)
    MIN_AMOUNTS = {
        "USD": 5.0,
        "RUB": 500.0,
        "EUR": 5.0,
        "UAH": 200.0,
        "TRY": 150.0,
        "INR": 400.0,
        "AED": 20.0,
    }

    # Use fixed minimum for currency if available, otherwise convert from USD
    if currency in MIN_AMOUNTS:
        min_in_user_currency = MIN_AMOUNTS[currency]
    else:
        MIN_USD = 5.0
        min_in_user_currency = formatter.convert(MIN_USD)

    if request.amount < min_in_user_currency:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum top-up is {format_price_simple(min_in_user_currency, currency)}",
        )

    # Use original currency and amount - CrystalPay supports multiple currencies
    payment_amount = request.amount
    payment_currency = currency

    # Get user's balance_currency (currency of their actual balance)
    balance_currency = getattr(db_user, "balance_currency", "RUB") or "RUB"
    current_balance = float(db_user.balance) if db_user.balance else 0

    # Convert payment amount to user's balance_currency if needed
    from decimal import Decimal

    from core.services.currency import get_currency_service
    from core.services.money import round_money

    currency_service = get_currency_service(redis)

    # Calculate amount to credit in balance currency
    amount_to_credit = await _calculate_amount_to_credit(
        currency,
        balance_currency,
        request.amount,
        currency_service,
    )

    # Round for non-RUB/USD currencies
    amount_to_credit = float(
        round_money(
            Decimal(amount_to_credit),
            to_int=(balance_currency in ["RUB", "UAH", "TRY", "INR"]),
        ),
    )

    # Create pending transaction record in user's balance_currency
    try:
        tx_result = (
            await db.client.table("balance_transactions")
            .insert(
                {
                    "user_id": db_user.id,
                    "type": "topup",
                    "amount": amount_to_credit,  # Store in balance_currency!
                    "currency": balance_currency,  # User's actual balance currency
                    "balance_before": current_balance,
                    "balance_after": current_balance,  # Will be updated on completion by webhook
                    "status": "pending",
                    "description": f"Пополнение баланса {request.amount} {currency}",
                    "metadata": {
                        "payment_currency": currency,
                        "payment_amount": request.amount,
                        "balance_currency": balance_currency,
                        "credit_amount": amount_to_credit,
                        "exchange_rate": (
                            formatter.exchange_rate if currency != balance_currency else 1.0
                        ),
                    },
                },
            )
            .execute()
        )
        topup_id = str(tx_result.data[0]["id"]) if tx_result.data and isinstance(tx_result.data, list) and len(tx_result.data) > 0 and isinstance(tx_result.data[0], dict) else None
    except Exception:
        logger.exception("Failed to create topup transaction")
        raise HTTPException(status_code=500, detail="Failed to create top-up request")

    if not topup_id:
        raise HTTPException(status_code=500, detail="Failed to create top-up request")

    # Create CrystalPay invoice with type="topup"
    try:
        from core.services.payments import PaymentService

        payment_service = PaymentService()

        # Pass user's currency directly to CrystalPay
        if not topup_id or not isinstance(topup_id, str):
            raise HTTPException(status_code=500, detail="Invalid topup_id")
        result = await payment_service.create_crystalpay_payment_topup(
            topup_id=topup_id,
            user_id=str(db_user.id),
            amount=payment_amount,
            currency=payment_currency,
        )

        if not result or not result.get("payment_url"):
            # Rollback transaction
            await (
                db.client.table("balance_transactions")
                .update({"status": "failed"})
                .eq("id", topup_id)
                .execute()
            )
            raise HTTPException(status_code=500, detail="Failed to create payment")

        # Update transaction with payment_id
        await (
            db.client.table("balance_transactions")
            .update(
                {
                    "reference_type": "payment",
                    "reference_id": result.get("invoice_id"),
                    "metadata": {
                        "original_currency": currency,
                        "original_amount": request.amount,
                        "invoice_id": result.get("invoice_id"),
                    },
                },
            )
            .eq("id", topup_id)
            .execute()
        )

        return {
            "success": True,
            "topup_id": topup_id,
            "payment_url": result["payment_url"],
            "amount": request.amount,
            "currency": currency,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create CrystalPay payment")
        # Rollback transaction
        await (
            db.client.table("balance_transactions")
            .update({"status": "failed"})
            .eq("id", topup_id)
            .execute()
        )
        raise HTTPException(status_code=500, detail=f"Payment creation failed: {e!s}")


@balance_router.get("/profile/topup/{topup_id}/status")
async def get_topup_status(topup_id: str):
    """Get top-up transaction status for polling.

    Note: This endpoint is public because:
    1. topup_id (UUID) is effectively a secret - only the user who created it knows it
    2. Returns minimal info (status only, no sensitive data)
    3. Required for payment redirect flow where auth may not be preserved
    """
    db = get_database()

    try:
        tx_result = (
            await db.client.table("balance_transactions")
            .select("id, status, amount, currency, balance_after")
            .eq("id", topup_id)
            .single()
            .execute()
        )

        if not tx_result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        tx = tx_result.data

        # Map internal status to frontend status
        status = tx.get("status", "pending")
        status_map = {
            "pending": "pending",
            "paid": "paid",
            "completed": "delivered",  # Webhook sets "completed" → frontend expects "delivered"
            "cancelled": "cancelled",
            "failed": "failed",
        }

        status_str = str(status) if status else "pending"
        tx_amount = tx.get("amount") if isinstance(tx.get("amount"), (int, float)) else None
        tx_currency = tx.get("currency") if isinstance(tx.get("currency"), str) else None
        tx_balance_after = tx.get("balance_after") if isinstance(tx.get("balance_after"), (int, float)) else None
        return {
            "topup_id": topup_id,
            "status": status_map.get(status_str, "pending"),
            "amount": tx_amount,
            "currency": tx_currency,
            "balance_after": tx_balance_after,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Topup status error")
        raise HTTPException(status_code=500, detail="Failed to fetch status")
