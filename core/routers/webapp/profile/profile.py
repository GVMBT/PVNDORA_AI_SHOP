"""
Profile Endpoints

User profile, preferences, and referral network endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
from fastapi import APIRouter, HTTPException, Depends
import asyncio

from core.logging import get_logger
from core.services.database import get_database
from core.auth import verify_telegram_auth
from ..models import UpdatePreferencesRequest, ConvertBalanceRequest

from .helpers import (
    _maybe_refresh_photo,
    _build_default_referral_program,
    _build_referral_data,
)

logger = get_logger(__name__)

profile_router = APIRouter()

# Cache for referral_settings (TTL 10 minutes)
_referral_settings_cache = None
_referral_settings_cache_ttl = 10 * 60  # 10 minutes
_referral_settings_cache_time = None


async def _get_referral_settings_cached(db):
    """
    Get referral_settings with Redis cache (TTL 10 minutes).
    Falls back to DB query if Redis unavailable.
    """
    global _referral_settings_cache, _referral_settings_cache_time
    
    from core.db import get_redis
    from datetime import datetime, timezone
    
    redis = None
    try:
        redis = get_redis()
    except (ValueError, ImportError):
        pass
    
    cache_key = "referral_settings:cache"
    
    # Try Redis cache first
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception:
            pass
    
    # Fallback to in-memory cache (within same request cycle)
    current_time = datetime.now(timezone.utc).timestamp()
    if _referral_settings_cache and _referral_settings_cache_time:
        if current_time - _referral_settings_cache_time < _referral_settings_cache_ttl:
            return _referral_settings_cache
    
    # Fetch from DB
    try:
        result = await db.client.table("referral_settings").select("*").limit(1).execute()
        settings = result.data[0] if result.data else {}
    except Exception as e:
        logger.warning(f"Failed to load referral_settings: {e}")
        settings = {}
    
    # Update caches
    if redis:
        try:
            import json
            await redis.set(cache_key, json.dumps(settings), ex=_referral_settings_cache_ttl)
        except Exception:
            pass
    
    _referral_settings_cache = settings
    _referral_settings_cache_time = current_time
    
    return settings


@profile_router.get("/profile")
async def get_webapp_profile(user=Depends(verify_telegram_auth)):
    """Get user profile with referral stats, balance, and history."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Refresh photo (with 6h gate) to catch avatar updates or missing photos
    await _maybe_refresh_photo(db, db_user, user.id)
    
    # OPTIMIZATION #8: Use cached referral_settings (Redis cache with 10min TTL)
    async def fetch_settings():
        return await _get_referral_settings_cached(db)
    
    async def fetch_extended_stats():
        try:
            return await db.client.table("referral_stats_extended").select("*").eq(
                "user_id", db_user.id
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to query referral_stats_extended: {e}")
            return type('obj', (object,), {'data': []})()
    
    async def fetch_bonuses():
        try:
            return await db.client.table("referral_bonuses").select("*").eq(
                "user_id", db_user.id
            ).eq("eligible", True).order("created_at", desc=True).limit(10).execute()
        except Exception as e:
            logger.warning(f"Failed to query referral_bonuses: {e}")
            return type('obj', (object,), {'data': []})()
    
    async def fetch_withdrawals():
        try:
            return await db.client.table("withdrawal_requests").select("*").eq(
                "user_id", db_user.id
            ).order("created_at", desc=True).limit(10).execute()
        except Exception as e:
            logger.warning(f"Failed to query withdrawal_requests: {e}")
            return type('obj', (object,), {'data': []})()
    
    async def fetch_balance_transactions():
        try:
            return await db.client.table("balance_transactions").select("*").eq(
                "user_id", db_user.id
            ).eq("status", "completed").order("created_at", desc=True).limit(50).execute()
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
    
    # Commissions (fallback values match DB defaults)
    COMMISSION_LEVEL1 = float(settings.get("level1_commission_percent", 10) or 10)
    COMMISSION_LEVEL2 = float(settings.get("level2_commission_percent", 7) or 7)
    COMMISSION_LEVEL3 = float(settings.get("level3_commission_percent", 3) or 3)
    
    # Initialize with default values
    referral_stats = {
        "level1_count": 0, "level2_count": 0, "level3_count": 0,
        "level1_earnings": 0, "level2_earnings": 0, "level3_earnings": 0,
        "active_referrals": 0,
        "click_count": 0,
        "conversion_rate": 0,
    }
    
    # OPTIMIZATION #5: Pass db_user directly to CurrencyFormatter to avoid duplicate DB query
    from core.db import get_redis
    from core.services.currency_response import CurrencyFormatter
    redis = get_redis()
    formatter = await CurrencyFormatter.create(
        db_user=db_user,  # Pass db_user directly (already fetched above)
        redis=redis
    )
    
    referral_program = await _build_default_referral_program(
        THRESHOLD_LEVEL2, THRESHOLD_LEVEL3, COMMISSION_LEVEL1, COMMISSION_LEVEL2, COMMISSION_LEVEL3,
        formatter.currency, settings
    )
    
    if extended_stats_result.data and len(extended_stats_result.data) > 0:
        s = extended_stats_result.data[0]
        referral_stats, referral_program = await _build_referral_data(
            s, THRESHOLD_LEVEL2, THRESHOLD_LEVEL3, COMMISSION_LEVEL1, COMMISSION_LEVEL2, COMMISSION_LEVEL3,
            formatter.currency, settings
        )
    
    # Add partner mode settings (from user record)
    referral_program["partner_mode"] = getattr(db_user, 'partner_mode', 'commission') or 'commission'
    referral_program["partner_discount_percent"] = getattr(db_user, 'partner_discount_percent', 0) or 0
    
    # Get user's balance in their local currency
    balance_in_local = float(db_user.balance) if db_user.balance else 0
    balance_currency = getattr(db_user, 'balance_currency', 'USD') or 'USD'
    
    # Convert balance to USD for calculations (if needed)
    from core.services.currency import get_currency_service
    currency_service = get_currency_service(redis)
    
    if balance_currency == 'USD':
        balance_usd = balance_in_local
    elif balance_currency == 'RUB':
        # Use convert_balance for RUB → USD (uses proper rounding)
        balance_usd_decimal = await currency_service.convert_balance("RUB", "USD", balance_in_local)
        balance_usd = float(balance_usd_decimal)
    else:
        # Fallback: shouldn't happen per plan (only RUB/USD supported for balance)
        # But handle gracefully if balance_currency is somehow set to another currency
        rate = await currency_service.get_exchange_rate(balance_currency)
        balance_usd = balance_in_local / rate if rate > 0 else balance_in_local
    
    # Other USD amounts (referral earnings and saved are tracked in USD)
    total_referral_earnings_usd = float(db_user.total_referral_earnings) if hasattr(db_user, 'total_referral_earnings') and db_user.total_referral_earnings else 0
    total_saved_usd = float(db_user.total_saved) if db_user.total_saved else 0
    
    return {
        "profile": {
            # USD values (for calculations)
            "balance_usd": round(balance_usd, 2),
            "total_referral_earnings_usd": total_referral_earnings_usd,
            "total_saved_usd": total_saved_usd,
            # Display values in user's balance currency (NOT converted!)
            "balance": balance_in_local,
            "total_referral_earnings": formatter.convert(total_referral_earnings_usd),
            "total_saved": formatter.convert(total_saved_usd),
            # Formatted strings (ready for display)
            "balance_formatted": currency_service.format_price(balance_in_local, balance_currency),
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{user.id}",
            "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
            "is_admin": db_user.is_admin or False,
            "is_partner": referral_program.get("is_partner", False),
            # User identity info
            "first_name": db_user.first_name,
            "username": db_user.username,
            "telegram_id": db_user.telegram_id,
            "photo_url": getattr(db_user, 'photo_url', None),
            # Balance currency (user's wallet currency)
            "balance_currency": balance_currency,
        },
        "referral_program": referral_program,
        "referral_stats": referral_stats,
        "bonus_history": bonus_result.data or [],
        "withdrawals": withdrawal_result.data or [],
        "balance_transactions": balance_transactions_result.data or [],
        # Currency info (for frontend display)
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }


@profile_router.put("/profile/preferences")
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


@profile_router.post("/profile/convert-balance")
async def convert_balance(request: ConvertBalanceRequest, user=Depends(verify_telegram_auth)):
    """
    Convert user balance to a different currency.
    
    WARNING: This is a one-way conversion. The balance will be physically
    converted using the current exchange rate. Use with caution.
    
    Example: 10 USD → 900 RUB (at rate 90)
    """
    from core.db import get_redis
    from core.services.currency import get_currency_service
    
    req = request
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_balance = float(db_user.balance) if db_user.balance else 0
    current_currency = getattr(db_user, 'balance_currency', 'USD') or 'USD'
    target_currency = req.target_currency.upper()
    
    # Validate target currency (only RUB and USD are supported for balance)
    valid_currencies = ["USD", "RUB"]
    if target_currency not in valid_currencies:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid target currency. Valid options: {', '.join(valid_currencies)}"
        )
    
    # No conversion needed if same currency
    if current_currency == target_currency:
        return {
            "success": True,
            "message": "Balance is already in target currency",
            "balance": current_balance,
            "currency": current_currency
        }
    
    # Prevent conversion with zero balance
    if current_balance <= 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot convert zero balance"
        )
    
    # Get currency service and convert balance
    redis = get_redis()
    currency_service = get_currency_service(redis)
    
    # Use centralized convert_balance method (handles RUB ↔ USD)
    new_balance_decimal = await currency_service.convert_balance(
        from_currency=current_currency,
        to_currency=target_currency,
        amount=current_balance
    )
    new_balance = float(new_balance_decimal)
    
    # Get exchange rate for logging/transaction record
    # Use convert_balance's internal rate calculation for consistency
    if current_currency == "USD" and target_currency == "RUB":
        # Calculate rate from conversion result (more accurate than separate API call)
        rate = float(new_balance_decimal) / current_balance if current_balance > 0 else await currency_service.get_exchange_rate("RUB")
    elif current_currency == "RUB" and target_currency == "USD":
        # Inverse rate: RUB amount / USD result = rate
        rate = current_balance / float(new_balance_decimal) if new_balance > 0 else await currency_service.get_exchange_rate("RUB")
    else:
        # Shouldn't happen (only RUB/USD supported per plan)
        # Use get_exchange_rate for fallback only
        rate = await currency_service.get_exchange_rate("RUB")
    
    # Update balance and currency in database
    await db.client.table("users").update({
        "balance": new_balance,
        "balance_currency": target_currency
    }).eq("telegram_id", user.id).execute()
    
    # Log the conversion (amount = 0 because balance doesn't change, only currency)
    # This is a system transaction that doesn't affect balance amount
    await db.client.table("balance_transactions").insert({
        "user_id": db_user.id,
        "type": "conversion",
        "amount": 0,  # Balance doesn't change, only currency changes
        "currency": target_currency,
        "balance_before": current_balance,
        "balance_after": new_balance,
        "status": "completed",
        "description": f"Конвертация {current_balance:.2f} {current_currency} → {new_balance:.2f} {target_currency}",
        "metadata": {
            "from_currency": current_currency,
            "to_currency": target_currency,
            "exchange_rate": rate if current_currency == "USD" else (1/rate if target_currency == "USD" else 1.0)
        }
    }).execute()
    
    logger.info(f"User {user.id} converted balance: {current_balance:.2f} {current_currency} → {new_balance:.2f} {target_currency}")
    
    return {
        "success": True,
        "message": f"Balance converted to {target_currency}",
        "previous_balance": current_balance,
        "previous_currency": current_currency,
        "new_balance": new_balance,
        "new_currency": target_currency,
        "exchange_rate": rate if current_currency == "USD" else 1/rate
    }


@profile_router.get("/referral/network")
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
            referrals_result = await db.client.table("users").select(
                "id, telegram_id, username, first_name, created_at, referral_program_unlocked, photo_url"
            ).eq("referrer_id", user_id).order("created_at", desc=True).range(
                offset, offset + limit - 1
            ).execute()
        elif level == 2:
            # Level 2: referrals of my referrals
            direct_refs = await db.client.table("users").select("id").eq(
                "referrer_id", user_id
            ).execute()
            direct_ref_ids = [r["id"] for r in (direct_refs.data or [])]
            
            if not direct_ref_ids:
                return {"referrals": [], "total": 0, "level": level}
            
            referrals_result = await db.client.table("users").select(
                "id, telegram_id, username, first_name, created_at, referral_program_unlocked, referrer_id, photo_url"
            ).in_("referrer_id", direct_ref_ids).order("created_at", desc=True).range(
                offset, offset + limit - 1
            ).execute()
        else:  # level == 3
            # Level 3: referrals of level 2
            l1_refs = await db.client.table("users").select("id").eq(
                "referrer_id", user_id
            ).execute()
            l1_ids = [r["id"] for r in (l1_refs.data or [])]
            
            if not l1_ids:
                return {"referrals": [], "total": 0, "level": level}
            
            l2_refs = await db.client.table("users").select("id").in_(
                "referrer_id", l1_ids
            ).execute()
            l2_ids = [r["id"] for r in (l2_refs.data or [])]
            
            if not l2_ids:
                return {"referrals": [], "total": 0, "level": level}
            
            referrals_result = await db.client.table("users").select(
                "id, telegram_id, username, first_name, created_at, referral_program_unlocked, referrer_id, photo_url"
            ).in_("referrer_id", l2_ids).order("created_at", desc=True).range(
                offset, offset + limit - 1
            ).execute()
        
        referrals_data = referrals_result.data or []
        
        # Deduplicate and drop self to avoid cycles
        seen_ids = set()
        referral_ids = []
        for ref in referrals_data:
            ref_id = ref.get("id")
            if not ref_id or ref_id == user_id:
                continue
            if ref_id in seen_ids:
                continue
            seen_ids.add(ref_id)
            referral_ids.append(ref_id)
        
        if not referral_ids:
            return {
                "referrals": [],
                "total": 0,
                "level": level,
                "offset": offset,
                "limit": limit
            }
        
        # OPTIMIZATION: Batch fetch orders count for all referrals (eliminate N+1)
        orders_count_map = {}
        try:
            # Use aggregation to count orders per user_id in a single query
            orders_result = await db.client.table("orders").select(
                "user_id"
            ).in_("user_id", referral_ids).in_("status", ["delivered"]).execute()
            
            # Count orders per user_id
            for order in (orders_result.data or []):
                order_user_id = order.get("user_id")
                if order_user_id:
                    orders_count_map[order_user_id] = orders_count_map.get(order_user_id, 0) + 1
        except Exception as e:
            logger.warning(f"Failed to batch fetch orders count: {e}")
        
        # OPTIMIZATION: Batch fetch earnings for all referrals (eliminate N+1)
        earnings_map = {}
        try:
            earnings_result = await db.client.table("referral_bonuses").select(
                "from_user_id, amount"
            ).eq("referrer_id", db_user.id).in_("from_user_id", referral_ids).eq(
                "eligible", True
            ).execute()
            
            # Sum earnings per from_user_id
            for bonus in (earnings_result.data or []):
                from_user_id = bonus.get("from_user_id")
                amount = float(bonus.get("amount", 0))
                if from_user_id:
                    earnings_map[from_user_id] = earnings_map.get(from_user_id, 0) + amount
        except Exception as e:
            logger.warning(f"Failed to batch fetch earnings: {e}")
        
        # Build enriched referrals list
        enriched_referrals = []
        for ref in referrals_data:
            ref_id = ref.get("id")
            if not ref_id or ref_id == user_id:
                continue
            if ref_id not in referral_ids:
                continue
            
            order_count = orders_count_map.get(ref_id, 0)
            earnings = earnings_map.get(ref_id, 0)
            
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
