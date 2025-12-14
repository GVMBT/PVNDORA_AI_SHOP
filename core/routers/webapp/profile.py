"""
WebApp Profile Router

User profile and referral program endpoints.
"""
import os
import asyncio
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends

from core.logging import get_logger
from core.services.database import get_database
from core.auth import verify_telegram_auth
from .models import WithdrawalRequest, UpdatePreferencesRequest, TopUpRequest

logger = get_logger(__name__)

router = APIRouter(tags=["webapp-profile"])

PHOTO_REFRESH_TTL = 6 * 60 * 60  # 6 hours


async def _fetch_telegram_photo_url(telegram_id: int) -> Optional[str]:
    """
    Fetch user's Telegram profile photo via Bot API.
    Returns direct file URL or None if not available.
    """
    bot_token = os.environ.get("TELEGRAM_TOKEN")
    if not bot_token:
        return None
    
    api_base = f"https://api.telegram.org/bot{bot_token}"
    file_base = f"https://api.telegram.org/file/bot{bot_token}"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{api_base}/getUserProfilePhotos",
                params={"user_id": telegram_id, "limit": 1},
            )
            data = resp.json()
            if not data.get("ok"):
                return None
            photos = data.get("result", {}).get("photos", [])
            if not photos:
                return None
            largest = photos[0][-1] if photos[0] else None
            if not largest or not largest.get("file_id"):
                return None
            file_id = largest["file_id"]
            
            file_resp = await client.get(f"{api_base}/getFile", params={"file_id": file_id})
            file_data = file_resp.json()
            if not file_data.get("ok"):
                return None
            file_path = file_data.get("result", {}).get("file_path")
            if not file_path:
                return None
            return f"{file_base}/{file_path}"
    except Exception:
        return None


async def _maybe_refresh_photo(db, db_user, telegram_id: int) -> None:
    """
    Refresh user photo if:
      - No photo_url stored, or
      - TTL expired (redis gate)
    Uses a 6h gate to avoid spamming Telegram API.
    """
    redis = None
    try:
        try:
            from core.db import get_redis  # local import to avoid cycles
            redis = get_redis()
        except Exception:
            redis = None
        
        gate_key = f"user:photo:refresh:{telegram_id}"
        if redis:
            try:
                if await redis.get(gate_key):
                    return
            except Exception:
                pass
        
        current_photo = getattr(db_user, "photo_url", None)
        if current_photo:
            # We still allow refresh (for updated TG photo) but behind gate
            pass
        
        photo_url = await _fetch_telegram_photo_url(telegram_id)
        if photo_url and photo_url != current_photo:
            try:
                await db.update_user_photo(telegram_id, photo_url)
                db_user.photo_url = photo_url
            except Exception as e:
                logger.warning(f"Failed to update user photo: {e}")
        
        if redis:
            try:
                await redis.set(gate_key, "1", ex=PHOTO_REFRESH_TTL)
            except Exception:
                pass
    except Exception as e:
        # Non-fatal
        logger.warning(f"Photo refresh failed: {e}")


@router.get("/profile")
async def get_webapp_profile(user=Depends(verify_telegram_auth)):
    """Get user profile with referral stats, balance, and history."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Refresh photo (with 6h gate) to catch avatar updates or missing photos
    await _maybe_refresh_photo(db, db_user, user.id)
    
    # Parallel database queries for better performance
    async def fetch_settings():
        try:
            result = await asyncio.to_thread(
                lambda: db.client.table("referral_settings").select("*").limit(1).execute()
            )
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning(f"Failed to load referral_settings: {e}")
            return {}
    
    async def fetch_extended_stats():
        try:
            return await asyncio.to_thread(
                lambda: db.client.table("referral_stats_extended").select("*").eq("user_id", db_user.id).execute()
            )
        except Exception as e:
            logger.warning(f"Failed to query referral_stats_extended: {e}")
            return type('obj', (object,), {'data': []})()
    
    async def fetch_bonuses():
        try:
            return await asyncio.to_thread(
                lambda: db.client.table("referral_bonuses").select("*").eq("user_id", db_user.id).eq("eligible", True).order("created_at", desc=True).limit(10).execute()
            )
        except Exception as e:
            logger.warning(f"Failed to query referral_bonuses: {e}")
            return type('obj', (object,), {'data': []})()
    
    async def fetch_withdrawals():
        try:
            return await asyncio.to_thread(
                lambda: db.client.table("withdrawal_requests").select("*").eq("user_id", db_user.id).order("created_at", desc=True).limit(10).execute()
            )
        except Exception as e:
            logger.warning(f"Failed to query withdrawal_requests: {e}")
            return type('obj', (object,), {'data': []})()
    
    async def fetch_balance_transactions():
        try:
            return await asyncio.to_thread(
                lambda: db.client.table("balance_transactions")
                .select("*")
                .eq("user_id", db_user.id)
                .eq("status", "completed")
                .order("created_at", desc=True)
                .limit(50)
                .execute()
            )
        except Exception as e:
            logger.warning(f"Failed to query balance_transactions: {e}")
            return type('obj', (object,), {'data': []})()
    
    # Execute all DB queries in parallel
    settings, extended_stats_result, bonus_result, withdrawal_result, balance_transactions_result = await asyncio.gather(
        fetch_settings(),
        fetch_extended_stats(),
        fetch_bonuses(),
        fetch_withdrawals(),
        fetch_balance_transactions()
    )
    
    # Level thresholds in USD (from settings)
    THRESHOLD_LEVEL2 = float(settings.get("level2_threshold_usd", 250) or 250)
    THRESHOLD_LEVEL3 = float(settings.get("level3_threshold_usd", 1000) or 1000)
    
    # Commissions
    COMMISSION_LEVEL1 = float(settings.get("level1_commission_percent", 20) or 20)
    COMMISSION_LEVEL2 = float(settings.get("level2_commission_percent", 10) or 10)
    COMMISSION_LEVEL3 = float(settings.get("level3_commission_percent", 5) or 5)
    
    # Initialize with default values
    referral_stats = {
        "level1_count": 0, "level2_count": 0, "level3_count": 0,
        "level1_earnings": 0, "level2_earnings": 0, "level3_earnings": 0,
        "active_referrals": 0,
        "click_count": 0,
        "conversion_rate": 0,
    }
    referral_program = _build_default_referral_program(THRESHOLD_LEVEL2, THRESHOLD_LEVEL3, COMMISSION_LEVEL1, COMMISSION_LEVEL2, COMMISSION_LEVEL3)
    
    if extended_stats_result.data and len(extended_stats_result.data) > 0:
        s = extended_stats_result.data[0]
        referral_stats, referral_program = _build_referral_data(
            s, THRESHOLD_LEVEL2, THRESHOLD_LEVEL3, COMMISSION_LEVEL1, COMMISSION_LEVEL2, COMMISSION_LEVEL3
        )
    
    # Get currency service and determine user currency
    currency = "USD"
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service
        redis = get_redis()
        currency_service = get_currency_service(redis)
        # Use preferred_currency if set, otherwise fallback to language_code
        user_lang = getattr(db_user, 'interface_language', None) or (db_user.language_code if db_user and db_user.language_code else user.language_code)
        preferred_curr = getattr(db_user, 'preferred_currency', None)
        currency = currency_service.get_user_currency(user_lang, preferred_curr)
    except Exception as e:
        logger.warning(f"Currency service unavailable: {e}, using USD")
    
    return {
        "profile": {
            "balance": float(db_user.balance) if db_user.balance else 0,
            "total_referral_earnings": float(db_user.total_referral_earnings) if hasattr(db_user, 'total_referral_earnings') and db_user.total_referral_earnings else 0,
            "total_saved": float(db_user.total_saved) if db_user.total_saved else 0,
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{user.id}",
            "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
            "is_admin": db_user.is_admin or False,
            "is_partner": referral_program.get("is_partner", False),
            "currency": currency,
            # User identity info (for web login where initData not available)
            "first_name": db_user.first_name,
            "username": db_user.username,
            "telegram_id": db_user.telegram_id,
            "photo_url": getattr(db_user, 'photo_url', None),
        },
        "referral_program": referral_program,
        "referral_stats": referral_stats,
        "bonus_history": bonus_result.data or [],
        "withdrawals": withdrawal_result.data or [],
        "balance_transactions": balance_transactions_result.data or [],
        "currency": currency
    }


@router.post("/profile/withdraw")
async def request_withdrawal(request: WithdrawalRequest, user=Depends(verify_telegram_auth)):
    """Request balance withdrawal."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    MIN_WITHDRAWAL = 500
    balance = float(db_user.balance) if db_user.balance else 0
    
    if request.amount < MIN_WITHDRAWAL:
        raise HTTPException(status_code=400, detail=f"Minimum withdrawal is {MIN_WITHDRAWAL}₽")
    if request.amount > balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    if request.method not in ['card', 'phone', 'crypto']:
        raise HTTPException(status_code=400, detail="Invalid payment method")
    
    await asyncio.to_thread(
        lambda: db.client.table("withdrawal_requests").insert({
            "user_id": db_user.id, "amount": request.amount,
            "payment_method": request.method, "payment_details": {"details": request.details}
        }).execute()
    )
    
    await asyncio.to_thread(
        lambda: db.client.table("users").update({"balance": balance - request.amount}).eq("id", db_user.id).execute()
    )
    
    return {"success": True, "message": "Withdrawal request submitted"}


@router.post("/profile/topup")
async def create_topup(
    request: TopUpRequest,
    user=Depends(verify_telegram_auth)
):
    """
    Create a balance top-up payment via CrystalPay.
    
    Minimum amounts:
    - RUB: 500₽
    - USD: 5$
    
    Returns payment URL for redirect.
    """
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate minimum amounts
    currency = request.currency.upper()
    MIN_AMOUNTS = {"RUB": 500, "USD": 5}
    
    if currency not in MIN_AMOUNTS:
        raise HTTPException(status_code=400, detail=f"Invalid currency. Supported: {', '.join(MIN_AMOUNTS.keys())}")
    
    min_amount = MIN_AMOUNTS[currency]
    if request.amount < min_amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Minimum top-up is {min_amount} {currency}"
        )
    
    # Convert USD to RUB for CrystalPay (which works in RUB)
    amount_rub = request.amount
    if currency == "USD":
        try:
            from core.db import get_redis
            from core.services.currency import get_currency_service
            redis = get_redis()
            currency_service = get_currency_service(redis)
            rate = currency_service.get_rate("USD", "RUB")
            amount_rub = request.amount * rate
        except Exception as e:
            logger.warning(f"Currency conversion failed: {e}, using fallback rate")
            amount_rub = request.amount * 100  # Fallback rate
    
    # Create pending transaction record
    current_balance = float(db_user.balance) if db_user.balance else 0
    
    try:
        tx_result = await asyncio.to_thread(
            lambda: db.client.table("balance_transactions").insert({
                "user_id": db_user.id,
                "type": "topup",
                "amount": request.amount,
                "currency": currency,
                "balance_before": current_balance,
                "balance_after": current_balance,  # Will be updated on completion
                "status": "pending",
                "description": f"Balance top-up: {request.amount} {currency}",
                "metadata": {
                    "original_currency": currency,
                    "original_amount": request.amount,
                    "rub_amount": amount_rub,
                }
            }).execute()
        )
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
        
        result = await payment_service.create_crystalpay_payment_topup(
            topup_id=topup_id,
            user_id=str(db_user.id),
            amount=amount_rub,
            currency="RUB",
            is_telegram_miniapp=is_telegram_miniapp,
        )
        
        if not result or not result.get("payment_url"):
            # Rollback transaction
            await asyncio.to_thread(
                lambda: db.client.table("balance_transactions")
                .update({"status": "failed"})
                .eq("id", topup_id)
                .execute()
            )
            raise HTTPException(status_code=500, detail="Failed to create payment")
        
        # Update transaction with payment_id
        await asyncio.to_thread(
            lambda: db.client.table("balance_transactions")
            .update({
                "reference_type": "payment",
                "reference_id": result.get("invoice_id"),
                "metadata": {
                    "original_currency": currency,
                    "original_amount": request.amount,
                    "rub_amount": amount_rub,
                    "invoice_id": result.get("invoice_id"),
                }
            })
            .eq("id", topup_id)
            .execute()
        )
        
        return {
            "success": True,
            "topup_id": topup_id,
            "payment_url": result["payment_url"],
            "amount": request.amount,
            "currency": currency,
            "amount_rub": amount_rub,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create CrystalPay payment: {e}")
        # Rollback transaction
        await asyncio.to_thread(
            lambda: db.client.table("balance_transactions")
            .update({"status": "failed"})
            .eq("id", topup_id)
            .execute()
        )
        raise HTTPException(status_code=500, detail=f"Payment creation failed: {str(e)}")


@router.get("/profile/topup/{topup_id}/status")
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
        tx_result = await asyncio.to_thread(
            lambda: db.client.table("balance_transactions")
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
            "completed": "delivered",  # Use "delivered" for consistency with orders
            "failed": "failed",
            "cancelled": "cancelled",
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


@router.put("/profile/preferences")
async def update_preferences(request: UpdatePreferencesRequest, user=Depends(verify_telegram_auth)):
    """Update user preferences (currency and interface language)."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate currency if provided
    valid_currencies = ["USD", "RUB", "EUR", "UAH", "TRY", "AED", "INR"]
    if request.preferred_currency and request.preferred_currency.upper() not in valid_currencies:
        raise HTTPException(status_code=400, detail=f"Invalid currency. Valid options: {', '.join(valid_currencies)}")
    
    # Validate language if provided
    valid_languages = ["ru", "en", "de", "es", "fr", "tr", "ar", "hi", "uk", "be", "kk"]
    if request.interface_language and request.interface_language.lower() not in valid_languages:
        raise HTTPException(status_code=400, detail=f"Invalid language. Valid options: {', '.join(valid_languages)}")
    
    await db.update_user_preferences(
        user.id,
        preferred_currency=request.preferred_currency,
        interface_language=request.interface_language
    )
    
    return {"success": True, "message": "Preferences updated"}


@router.get("/referral/network")
async def get_referral_network(user=Depends(verify_telegram_auth), level: int = 1, limit: int = 50, offset: int = 0):
    """
    Get user's referral network (tree of referrals).
    
    Args:
        level: 1, 2, or 3 - which level of referrals to fetch
        limit: max number of referrals to return
        offset: pagination offset
    
    Returns:
        List of referrals with their stats (purchases, earnings generated)
    """
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = db_user.id
    
    if level not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Level must be 1, 2, or 3")
    
    try:
        if level == 1:
            # Direct referrals
            referrals_result = await asyncio.to_thread(
                lambda: db.client.table("users")
                .select("id, telegram_id, username, first_name, created_at, referral_program_unlocked, photo_url")
                .eq("referrer_id", user_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
        elif level == 2:
            # Level 2: referrals of my referrals
            direct_refs = await asyncio.to_thread(
                lambda: db.client.table("users")
                .select("id")
                .eq("referrer_id", user_id)
                .execute()
            )
            direct_ref_ids = [r["id"] for r in (direct_refs.data or [])]
            
            if not direct_ref_ids:
                return {"referrals": [], "total": 0, "level": level}
            
            referrals_result = await asyncio.to_thread(
                lambda: db.client.table("users")
                .select("id, telegram_id, username, first_name, created_at, referral_program_unlocked, referrer_id, photo_url")
                .in_("referrer_id", direct_ref_ids)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
        else:  # level == 3
            # Level 3: referrals of level 2
            l1_refs = await asyncio.to_thread(
                lambda: db.client.table("users")
                .select("id")
                .eq("referrer_id", user_id)
                .execute()
            )
            l1_ids = [r["id"] for r in (l1_refs.data or [])]
            
            if not l1_ids:
                return {"referrals": [], "total": 0, "level": level}
            
            l2_refs = await asyncio.to_thread(
                lambda: db.client.table("users")
                .select("id")
                .in_("referrer_id", l1_ids)
                .execute()
            )
            l2_ids = [r["id"] for r in (l2_refs.data or [])]
            
            if not l2_ids:
                return {"referrals": [], "total": 0, "level": level}
            
            referrals_result = await asyncio.to_thread(
                lambda: db.client.table("users")
                .select("id, telegram_id, username, first_name, created_at, referral_program_unlocked, referrer_id, photo_url")
                .in_("referrer_id", l2_ids)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
        
        referrals_data = referrals_result.data or []
        
        # Deduplicate and drop self to avoid cycles; avoid any ref that is ancestor/child of self_id == db_user.id
        seen_ids = set()
        enriched_referrals = []
        for ref in referrals_data:
            ref_id = ref.get("id")
            if not ref_id or ref_id == user_id:
                continue
            if ref_id in seen_ids:
                continue
            seen_ids.add(ref_id)
            
            # Count orders
            orders_result = await asyncio.to_thread(
                lambda rid=ref_id: db.client.table("orders")
                .select("id", count="exact")
                .eq("user_id", rid)
                .in_("status", ["delivered", "completed", "ready"])
                .execute()
            )
            order_count = orders_result.count or 0
            
            # Get earnings generated (bonuses to the current user from this referral)
            earnings_result = await asyncio.to_thread(
                lambda rid=ref_id: db.client.table("referral_bonuses")
                .select("amount")
                .eq("referrer_id", db_user.id)
                .eq("from_user_id", rid)
                .eq("eligible", True)
                .execute()
            )
            earnings = sum(float(b.get("amount", 0)) for b in (earnings_result.data or []))
            
            enriched_referrals.append({
                "id": ref_id,
                "telegram_id": ref.get("telegram_id"),
                "username": ref.get("username"),
                "first_name": ref.get("first_name"),
                "created_at": ref.get("created_at"),
                "is_active": ref.get("referral_program_unlocked", False),
                "order_count": order_count,
                "earnings_generated": round(earnings, 2),
                "photo_url": ref.get("photo_url"),
            })
        
        return {
            "referrals": enriched_referrals,
            "total": len(enriched_referrals),
            "level": level,
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get referral network: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load referral network")


def _build_default_referral_program(threshold2: float, threshold3: float, comm1: float, comm2: float, comm3: float) -> dict:
    """Build default referral program data."""
    return {
        "unlocked": False,
        "status": "locked",
        "is_partner": False,
        "effective_level": 0,
        "level1_unlocked": False,
        "level2_unlocked": False,
        "level3_unlocked": False,
        "turnover_usd": 0,
        "amount_to_level2_usd": threshold2,
        "amount_to_level3_usd": threshold3,
        "amount_to_next_level_usd": threshold2,
        "next_threshold_usd": threshold2,
        "thresholds_usd": {"level2": threshold2, "level3": threshold3},
        "commissions_percent": {"level1": comm1, "level2": comm2, "level3": comm3},
        "level1_unlocked_at": None,
        "level2_unlocked_at": None,
        "level3_unlocked_at": None,
    }


def _build_referral_data(s: dict, threshold2: float, threshold3: float, comm1: float, comm2: float, comm3: float) -> tuple:
    """Build referral stats and program data from extended stats."""
    # Calculate conversion rate (referrals / clicks * 100)
    click_count = s.get("click_count", 0) or 0
    total_referrals = (s.get("level1_count", 0) or 0)
    conversion_rate = round((total_referrals / click_count * 100), 1) if click_count > 0 else 0
    
    referral_stats = {
        "level1_count": s.get("level1_count", 0),
        "level2_count": s.get("level2_count", 0),
        "level3_count": s.get("level3_count", 0),
        "level1_earnings": float(s.get("level1_earnings") or 0),
        "level2_earnings": float(s.get("level2_earnings") or 0),
        "level3_earnings": float(s.get("level3_earnings") or 0),
        "active_referrals": s.get("active_referrals_count", 0),
        "click_count": click_count,
        "conversion_rate": conversion_rate,
    }
    
    # Core program data from view
    unlocked = s.get("referral_program_unlocked", False)
    is_partner = s.get("is_partner", False)
    partner_override = s.get("partner_level_override")
    turnover_usd = float(s.get("turnover_usd") or 0)
    
    # Calculate effective level
    if is_partner and partner_override is not None:
        effective_level = partner_override
    elif not unlocked:
        effective_level = 0
    elif turnover_usd >= threshold3:
        effective_level = 3
    elif turnover_usd >= threshold2:
        effective_level = 2
    elif unlocked:
        effective_level = 1
    else:
        effective_level = 0
    
    status = "locked" if not unlocked else "active"
    
    level1_unlocked = effective_level >= 1
    level2_unlocked = effective_level >= 2
    level3_unlocked = effective_level >= 3
    
    amount_to_level2 = max(0, threshold2 - turnover_usd) if not level2_unlocked else 0
    amount_to_level3 = max(0, threshold3 - turnover_usd) if not level3_unlocked else 0
    
    if not level2_unlocked:
        next_threshold = threshold2
        amount_to_next = amount_to_level2
    elif not level3_unlocked:
        next_threshold = threshold3
        amount_to_next = amount_to_level3
    else:
        next_threshold = None
        amount_to_next = 0
    
    referral_program = {
        "unlocked": unlocked,
        "status": status,
        "is_partner": is_partner,
        "effective_level": effective_level,
        "level1_unlocked": level1_unlocked,
        "level2_unlocked": level2_unlocked,
        "level3_unlocked": level3_unlocked,
        "turnover_usd": turnover_usd,
        "amount_to_level2_usd": amount_to_level2,
        "amount_to_level3_usd": amount_to_level3,
        "amount_to_next_level_usd": amount_to_next,
        "next_threshold_usd": next_threshold,
        "thresholds_usd": {"level2": threshold2, "level3": threshold3},
        "commissions_percent": {"level1": comm1, "level2": comm2, "level3": comm3},
        "level1_unlocked_at": s.get("level1_unlocked_at"),
        "level2_unlocked_at": s.get("level2_unlocked_at"),
        "level3_unlocked_at": s.get("level3_unlocked_at"),
    }
    
    return referral_stats, referral_program
