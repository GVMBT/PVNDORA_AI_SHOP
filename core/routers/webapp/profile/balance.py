"""
Balance Endpoints

Balance top-up and related operations.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
from fastapi import APIRouter, HTTPException, Depends

from core.logging import get_logger
from core.services.database import get_database
from core.auth import verify_telegram_auth
from ..models import TopUpRequest

logger = get_logger(__name__)

balance_router = APIRouter()


@balance_router.post("/profile/topup")
async def create_topup(
    request: TopUpRequest,
    user=Depends(verify_telegram_auth)
):
    """
    Create a balance top-up payment via CrystalPay.
    
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
    formatter = await CurrencyFormatter.create(
        user.id, db, redis, preferred_currency=currency
    )
    
    # Minimum: 5 USD equivalent
    MIN_USD = 5.0
    min_in_user_currency = formatter.convert(MIN_USD)
    
    if request.amount < min_in_user_currency:
        raise HTTPException(
            status_code=400, 
            detail=f"Minimum top-up is {format_price_simple(min_in_user_currency, currency)}"
        )
    
    # Use original currency and amount - CrystalPay supports multiple currencies
    payment_amount = request.amount
    payment_currency = currency
    
    # Get user's balance_currency (currency of their actual balance)
    balance_currency = getattr(db_user, 'balance_currency', 'USD') or 'USD'
    current_balance = float(db_user.balance) if db_user.balance else 0
    
    # Convert payment amount to user's balance_currency if needed
    from core.services.currency import get_currency_service
    from core.services.money import round_money
    from decimal import Decimal
    currency_service = get_currency_service(redis)
    
    if currency == balance_currency:
        # Same currency, use directly
        amount_to_credit = request.amount
    elif currency in ["USD", "RUB"] and balance_currency in ["USD", "RUB"]:
        # Direct conversion using convert_balance (RUB ↔ USD only)
        amount_decimal = await currency_service.convert_balance(currency, balance_currency, request.amount)
        amount_to_credit = float(amount_decimal)
    else:
        # Convert: payment_currency → USD → balance_currency
        # First convert to USD (base currency) if payment_currency is not USD
        if currency == "USD":
            amount_usd = request.amount
        else:
            # For non-USD/RUB currencies, use get_exchange_rate to convert to USD
            payment_rate = await currency_service.get_exchange_rate(currency)
            amount_usd = request.amount / payment_rate if payment_rate > 0 else request.amount
        
        # Then convert from USD to balance_currency (only RUB or USD supported)
        if balance_currency == "USD":
            amount_to_credit = amount_usd
        elif balance_currency == "RUB":
            # Use convert_balance for RUB (uses proper rounding)
            amount_decimal = await currency_service.convert_balance("USD", "RUB", amount_usd)
            amount_to_credit = float(amount_decimal)
        else:
            # Fallback for other currencies (shouldn't happen per plan: only RUB/USD)
            balance_rate = await currency_service.get_exchange_rate(balance_currency)
            amount_to_credit = amount_usd * balance_rate
            # Round for non-RUB/USD currencies
            amount_to_credit = float(round_money(Decimal(amount_to_credit), to_int=(balance_currency == "RUB")))
    
    # Create pending transaction record in user's balance_currency
    try:
        tx_result = await db.client.table("balance_transactions").insert({
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
                "exchange_rate": formatter.exchange_rate if currency != balance_currency else 1.0,
            }
        }).execute()
        topup_id = tx_result.data[0]["id"] if tx_result.data else None
    except Exception as e:
        logger.error(f"Failed to create topup transaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to create top-up request")
    
    if not topup_id:
        raise HTTPException(status_code=500, detail="Failed to create top-up request")
    
    # Create CrystalPay invoice with type="topup"
    try:
        from core.services.payments import PaymentService
        payment_service = PaymentService()
        
        # Check if request is from Telegram Mini App
        is_telegram_miniapp = True  # Default to True since this is via telegram auth
        
        # Pass user's currency directly to CrystalPay
        result = await payment_service.create_crystalpay_payment_topup(
            topup_id=topup_id,
            user_id=str(db_user.id),
            amount=payment_amount,
            currency=payment_currency,
            is_telegram_miniapp=is_telegram_miniapp,
        )
        
        if not result or not result.get("payment_url"):
            # Rollback transaction
            await db.client.table("balance_transactions").update({
                "status": "failed"
            }).eq("id", topup_id).execute()
            raise HTTPException(status_code=500, detail="Failed to create payment")
        
        # Update transaction with payment_id
        await db.client.table("balance_transactions").update({
            "reference_type": "payment",
            "reference_id": result.get("invoice_id"),
            "metadata": {
                "original_currency": currency,
                "original_amount": request.amount,
                "invoice_id": result.get("invoice_id"),
            }
        }).eq("id", topup_id).execute()
        
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
        logger.error(f"Failed to create CrystalPay payment: {e}")
        # Rollback transaction
        await db.client.table("balance_transactions").update({
            "status": "failed"
        }).eq("id", topup_id).execute()
        raise HTTPException(status_code=500, detail=f"Payment creation failed: {str(e)}")


@balance_router.get("/profile/topup/{topup_id}/status")
async def get_topup_status(topup_id: str):
    """
    Get top-up transaction status for polling.
    
    Note: This endpoint is public because:
    1. topup_id (UUID) is effectively a secret - only the user who created it knows it
    2. Returns minimal info (status only, no sensitive data)
    3. Required for payment redirect flow where auth may not be preserved
    """
    db = get_database()
    
    try:
        tx_result = await db.client.table("balance_transactions").select(
            "id, status, amount, currency, balance_after"
        ).eq("id", topup_id).single().execute()
        
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
        
        return {
            "topup_id": topup_id,
            "status": status_map.get(status, "pending"),
            "amount": tx.get("amount"),
            "currency": tx.get("currency"),
            "balance_after": tx.get("balance_after"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Topup status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch status")
