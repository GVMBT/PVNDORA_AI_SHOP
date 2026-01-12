"""
Withdrawal Endpoints

Balance withdrawal operations.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from fastapi import APIRouter, Depends, HTTPException

from core.auth import verify_telegram_auth
from core.logging import get_logger
from core.services.database import get_database

from ..models import WithdrawalPreviewRequest, WithdrawalRequest

logger = get_logger(__name__)

withdrawals_router = APIRouter()


@withdrawals_router.post("/profile/withdraw/preview")
async def preview_withdrawal(request: WithdrawalPreviewRequest, user=Depends(verify_telegram_auth)):
    """
    Preview withdrawal calculation: shows fees and final USDT payout before creating request.
    """
    from core.db import get_redis
    from core.services.currency import MIN_USDT_AFTER_FEES, NETWORK_FEE_USDT, get_currency_service

    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    balance = float(db_user.balance) if db_user.balance else 0
    balance_currency = getattr(db_user, "balance_currency", None) or "USD"

    redis = get_redis()
    currency_service = get_currency_service(redis)

    amount = request.amount

    # Calculate minimum withdrawal amount (uses constants from currency service)
    min_withdrawal = await currency_service.calculate_min_withdrawal_amount(
        balance_currency=balance_currency
    )

    # Calculate maximum withdrawal amount (uses constants from currency service)
    max_withdrawal = await currency_service.calculate_max_withdrawal_amount(
        balance=balance, balance_currency=balance_currency
    )

    # Use requested amount, or full balance for preview
    amount_to_calc = amount if amount > 0 else balance

    # Calculate USDT payout for amount_to_calc
    withdrawal_calc = await currency_service.calculate_withdrawal_usdt(
        amount_in_balance_currency=amount_to_calc, balance_currency=balance_currency
    )

    # Check if user can withdraw
    can_withdraw_any = (
        max_withdrawal.get("can_withdraw", False) and max_withdrawal["max_amount"] > 0
    )
    if amount > 0:
        can_withdraw_requested = (
            amount <= balance and withdrawal_calc["amount_usdt"] >= MIN_USDT_AFTER_FEES
        )
    else:
        can_withdraw_requested = can_withdraw_any

    return {
        "amount_requested": amount_to_calc,
        "amount_requested_currency": balance_currency,
        "amount_usd": withdrawal_calc["amount_usd"],
        "amount_usdt_gross": withdrawal_calc["amount_usdt_gross"],
        "network_fee": NETWORK_FEE_USDT,
        "amount_usdt_net": withdrawal_calc["amount_usdt"],
        "exchange_rate": withdrawal_calc["exchange_rate"],
        "usdt_rate": withdrawal_calc["usdt_rate"],
        "can_withdraw": can_withdraw_any and can_withdraw_requested,
        "min_amount": min_withdrawal["min_amount"],
        "max_amount": max_withdrawal["max_amount"],
        "max_usdt_net": max_withdrawal["max_usdt_net"],
    }


@withdrawals_router.post("/profile/withdraw")
async def request_withdrawal(request: WithdrawalRequest, user=Depends(verify_telegram_auth)):
    """
    Request balance withdrawal to TRC20 USDT.

    Uses snapshot pricing: exchange rate is fixed at request creation time.
    Admin sees fixed USDT amount to pay, regardless of rate changes.
    """
    from core.db import get_redis
    from core.services.currency import MIN_USDT_AFTER_FEES, NETWORK_FEE_USDT, get_currency_service
    from core.services.currency_response import CurrencyFormatter

    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's balance and balance_currency
    balance = float(db_user.balance) if db_user.balance else 0
    balance_currency = getattr(db_user, "balance_currency", None) or "USD"

    # Get currency service for USDT calculation
    redis = get_redis()
    currency_service = get_currency_service(redis)

    # Get currency formatter for display
    formatter = await CurrencyFormatter.create(user.id, db, redis)

    # Calculate USDT payout with snapshot (uses constants from currency service)
    withdrawal_calc = await currency_service.calculate_withdrawal_usdt(
        amount_in_balance_currency=request.amount, balance_currency=balance_currency
    )

    amount_usd = withdrawal_calc["amount_usd"]
    amount_to_pay_usdt = withdrawal_calc["amount_usdt"]
    exchange_rate = withdrawal_calc["exchange_rate"]
    usdt_rate = withdrawal_calc["usdt_rate"]

    # Check balance first (balance is in user's balance_currency)
    if request.amount > balance:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: {formatter.format(balance)}, requested: {formatter.format(request.amount)}",
        )

    # Validate minimum withdrawal
    if amount_to_pay_usdt < MIN_USDT_AFTER_FEES:
        min_usdt_gross = MIN_USDT_AFTER_FEES + NETWORK_FEE_USDT
        min_usd = min_usdt_gross * usdt_rate
        min_in_user_currency = min_usd * exchange_rate if balance_currency != "USD" else min_usd
        raise HTTPException(
            status_code=400,
            detail=f"Минимальная сумма вывода: {formatter.format(min_in_user_currency)}. После комиссии сети ({NETWORK_FEE_USDT} USDT) вы получите минимум {MIN_USDT_AFTER_FEES} USDT (требование биржи: минимум 10 USD).",
        )

    if request.method not in ["crypto"]:
        raise HTTPException(
            status_code=400, detail="Invalid payment method. Only TRC20 USDT is supported."
        )

    # Extract wallet address from details
    wallet_address = request.details.strip() if request.details else None
    if not wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address is required")

    # Basic TRC20 address validation (starts with T, 34 characters)
    if not wallet_address.startswith("T") or len(wallet_address) != 34:
        raise HTTPException(status_code=400, detail="Invalid TRC20 wallet address format")

    # Create withdrawal request with SNAPSHOT pricing
    withdrawal_result = (
        await db.client.table("withdrawal_requests")
        .insert(
            {
                "user_id": db_user.id,
                "amount": round(amount_usd, 2),  # USD equivalent (for legacy/reporting)
                "payment_method": request.method,
                # NEW: Snapshot fields
                "amount_debited": round(request.amount, 2),  # What user sees (in their currency)
                "amount_to_pay": round(amount_to_pay_usdt, 2),  # FIXED USDT to pay
                "balance_currency": balance_currency,
                "exchange_rate": exchange_rate,  # 1 USD = X balance_currency
                "usdt_rate": usdt_rate,  # 1 USDT = X USD
                "network_fee": NETWORK_FEE_USDT,  # From centralized constant
                "wallet_address": wallet_address,
                # Legacy (for backwards compatibility)
                "payment_details": {
                    "details": wallet_address,
                    "original_amount": request.amount,
                    "original_currency": balance_currency,
                    "exchange_rate": exchange_rate,
                    "usdt_payout": amount_to_pay_usdt,
                },
            }
        )
        .execute()
    )

    request_id = withdrawal_result.data[0].get("id") if withdrawal_result.data else "unknown"

    # Send alert to admins (best-effort)
    try:
        from core.routers.deps import get_admin_alerts

        alert_service = get_admin_alerts()
        await alert_service.alert_withdrawal_request(
            user_telegram_id=user.id,
            username=db_user.username,
            amount=round(amount_to_pay_usdt, 2),  # Alert USDT amount!
            method=f"TRC20 USDT ({wallet_address[:8]}...)",
            request_id=request_id,
            user_balance=balance,
        )
    except Exception as e:
        logger.warning(f"Failed to send withdrawal alert: {e}")

    return {
        "success": True,
        "message": "Withdrawal request submitted",
        "details": {
            "amount_debited": request.amount,
            "amount_debited_currency": balance_currency,
            "amount_to_pay": amount_to_pay_usdt,
            "amount_to_pay_currency": "USDT",
            "network_fee": NETWORK_FEE_USDT,
            "exchange_rate": exchange_rate,
            "wallet_address": wallet_address,
        },
    }
