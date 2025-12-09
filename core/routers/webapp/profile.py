"""
WebApp Profile Router

User profile and referral program endpoints.
"""
import asyncio
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends

from src.services.database import get_database
from core.auth import verify_telegram_auth
from .models import WithdrawalRequest

router = APIRouter(tags=["webapp-profile"])


@router.get("/profile")
async def get_webapp_profile(user=Depends(verify_telegram_auth)):
    """Get user profile with referral stats, balance, and history."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Load dynamic settings from DB
    try:
        settings_result = await asyncio.to_thread(
            lambda: db.client.table("referral_settings").select("*").limit(1).execute()
        )
        settings = settings_result.data[0] if settings_result.data and len(settings_result.data) > 0 else {}
    except Exception as e:
        print(f"ERROR: Failed to load referral_settings: {e}")
        settings = {}
    
    # Level thresholds in USD (from settings)
    THRESHOLD_LEVEL2 = float(settings.get("level2_threshold_usd", 250) or 250)
    THRESHOLD_LEVEL3 = float(settings.get("level3_threshold_usd", 1000) or 1000)
    
    # Commissions
    COMMISSION_LEVEL1 = float(settings.get("level1_commission_percent", 20) or 20)
    COMMISSION_LEVEL2 = float(settings.get("level2_commission_percent", 10) or 10)
    COMMISSION_LEVEL3 = float(settings.get("level3_commission_percent", 5) or 5)
    
    # Get extended referral stats from view
    try:
        extended_stats_result = await asyncio.to_thread(
            lambda: db.client.table("referral_stats_extended").select("*").eq("user_id", db_user.id).execute()
        )
    except Exception as e:
        print(f"ERROR: Failed to query referral_stats_extended: {e}")
        import traceback
        print(f"ERROR: Traceback: {traceback.format_exc()}")
        extended_stats_result = type('obj', (object,), {'data': []})()
    
    # Initialize with default values
    referral_stats = {
        "level1_count": 0, "level2_count": 0, "level3_count": 0,
        "level1_earnings": 0, "level2_earnings": 0, "level3_earnings": 0,
        "active_referrals": 0
    }
    referral_program = _build_default_referral_program(THRESHOLD_LEVEL2, THRESHOLD_LEVEL3, COMMISSION_LEVEL1, COMMISSION_LEVEL2, COMMISSION_LEVEL3)
    
    if extended_stats_result.data and len(extended_stats_result.data) > 0:
        s = extended_stats_result.data[0]
        referral_stats, referral_program = _build_referral_data(
            s, THRESHOLD_LEVEL2, THRESHOLD_LEVEL3, COMMISSION_LEVEL1, COMMISSION_LEVEL2, COMMISSION_LEVEL3
        )
    
    try:
        bonus_result = await asyncio.to_thread(
            lambda: db.client.table("referral_bonuses").select("*").eq("user_id", db_user.id).eq("eligible", True).order("created_at", desc=True).limit(10).execute()
        )
    except Exception as e:
        print(f"ERROR: Failed to query referral_bonuses: {e}")
        bonus_result = type('obj', (object,), {'data': []})()
    
    try:
        withdrawal_result = await asyncio.to_thread(
            lambda: db.client.table("withdrawal_requests").select("*").eq("user_id", db_user.id).order("created_at", desc=True).limit(10).execute()
        )
    except Exception as e:
        print(f"ERROR: Failed to query withdrawal_requests: {e}")
        withdrawal_result = type('obj', (object,), {'data': []})()
    
    # Get currency service and determine user currency
    currency = "USD"
    try:
        from core.db import get_redis
        from src.services.currency import get_currency_service
        redis = get_redis()  # get_redis() is synchronous, no await needed
        currency_service = get_currency_service(redis)
        currency = currency_service.get_user_currency(db_user.language_code if db_user and db_user.language_code else user.language_code)
    except Exception as e:
        print(f"Warning: Currency service unavailable: {e}, using USD")
    
    return {
        "profile": {
            "balance": float(db_user.balance) if db_user.balance else 0,
            "total_referral_earnings": float(db_user.total_referral_earnings) if hasattr(db_user, 'total_referral_earnings') and db_user.total_referral_earnings else 0,
            "total_saved": float(db_user.total_saved) if db_user.total_saved else 0,
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{user.id}",
            "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
            "is_admin": db_user.is_admin or False,
            "is_partner": referral_program.get("is_partner", False),
            "currency": currency
        },
        "referral_program": referral_program,
        "referral_stats": referral_stats,
        "bonus_history": bonus_result.data or [],
        "withdrawals": withdrawal_result.data or [],
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
                .select("id, telegram_id, username, first_name, created_at, referral_program_unlocked")
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
                .select("id, telegram_id, username, first_name, created_at, referral_program_unlocked, referrer_id")
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
                .select("id, telegram_id, username, first_name, created_at, referral_program_unlocked, referrer_id")
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
            })
        
        return {
            "referrals": enriched_referrals,
            "total": len(enriched_referrals),
            "level": level,
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        print(f"ERROR: Failed to get referral network: {e}")
        import traceback
        print(f"ERROR: Traceback: {traceback.format_exc()}")
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
    referral_stats = {
        "level1_count": s.get("level1_count", 0),
        "level2_count": s.get("level2_count", 0),
        "level3_count": s.get("level3_count", 0),
        "level1_earnings": float(s.get("level1_earnings") or 0),
        "level2_earnings": float(s.get("level2_earnings") or 0),
        "level3_earnings": float(s.get("level3_earnings") or 0),
        "active_referrals": s.get("active_referrals_count", 0),
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
