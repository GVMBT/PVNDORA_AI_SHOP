"""Profile Endpoints.

User profile, preferences, and referral network endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import asyncio
import contextlib
from datetime import UTC
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth import verify_telegram_auth
from core.auth.dependencies import get_db_user
from core.logging import get_logger
from core.routers.webapp.models import ConvertBalanceRequest, UpdatePreferencesRequest
from core.services.database import get_database
from core.services.models import User

if TYPE_CHECKING:
    from core.services.database import Database
    from core.utils.validators import TelegramUser

from .helpers import (
    _build_default_referral_program,
    _build_referral_data,
    _maybe_refresh_photo,
)

logger = get_logger(__name__)

profile_router = APIRouter()

# Type alias for clarity
DictStrAny = dict[str, Any]


# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


def calculate_exchange_rate(_rate: float, _from_currency: str, _to_currency: str) -> float:
    """Format exchange rate for display.

    DEPRECATED: After RUB-only migration, always returns 1.0.
    Kept for backward compatibility.
    """
    # All RUB now
    return 1.0


def _calculate_conversion_rate(
    _current_currency: str,
    _target_currency: str,
    _current_balance: float,
    _new_balance_decimal: float,
    _currency_service: Any,
) -> float:
    """Calculate exchange rate for conversion metadata.

    DEPRECATED: After RUB-only migration, always returns 1.0.
    Kept for backward compatibility.
    """
    return 1.0


def _convert_balance_to_usd(balance_in_local: float, _balance_currency: str, _redis) -> float:
    """Get balance value.

    DEPRECATED: After RUB-only migration, returns balance as-is (in RUB).
    The function name mentions USD for backward compatibility.
    """
    # All balances are now in RUB
    return balance_in_local


# Cache for referral_settings (TTL 10 minutes)
_referral_settings_cache: DictStrAny | None = None
_referral_settings_cache_ttl = 10 * 60
_referral_settings_cache_time: float | None = None


async def _get_referral_settings_cached(db: Any) -> DictStrAny:
    """Get referral_settings with Redis cache (TTL 10 minutes)."""
    global _referral_settings_cache, _referral_settings_cache_time

    from datetime import datetime

    from core.db import get_redis

    redis = None
    with contextlib.suppress(ValueError, ImportError):
        redis = get_redis()

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

    # Fallback to in-memory cache
    current_time = datetime.now(UTC).timestamp()
    if (
        _referral_settings_cache
        and _referral_settings_cache_time
        and current_time - _referral_settings_cache_time < _referral_settings_cache_ttl
    ):
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


async def _fetch_profile_data(
    db: "Database", db_user: User
) -> tuple[dict[str, Any], Any, Any, Any, Any]:
    """Fetch all profile-related data using optimized VIEW.

    OPTIMIZATION: Uses user_profile_data VIEW to get all data in 1 query
    instead of 4 separate queries. Reduces DB round-trips from 5 to 2.
    """

    async def fetch_settings():
        return await _get_referral_settings_cached(db)

    async def fetch_profile_view():
        """Fetch all profile data from optimized VIEW in one query."""
        try:
            return (
                await db.client.table("user_profile_data")
                .select("*")
                .eq("user_id", db_user.id)
                .single()
                .execute()
            )
        except Exception as e:
            logger.warning(f"Failed to query user_profile_data VIEW: {e}")
            # Fallback to empty structure
            return type(
                "obj",
                (object,),
                {
                    "data": {
                        "level1_count": 0,
                        "level2_count": 0,
                        "level3_count": 0,
                        "effective_level": 0,
                        "recent_bonuses": None,
                        "recent_withdrawals": None,
                        "recent_transactions": None,
                    },
                },
            )()

    settings, profile_view = await asyncio.gather(
        fetch_settings(),
        fetch_profile_view(),
    )

    # Transform VIEW data to match old format for backward compatibility
    profile_data = profile_view.data if profile_view.data else {}

    # Create mock result objects matching old structure
    extended_stats_result = type(
        "obj",
        (object,),
        {
            "data": [
                {
                    "level1_count": profile_data.get("level1_count", 0),
                    "level2_count": profile_data.get("level2_count", 0),
                    "level3_count": profile_data.get("level3_count", 0),
                    "effective_level": profile_data.get("effective_level", 0),
                }
            ]
            if profile_data.get("level1_count", 0) > 0
            else [],
        },
    )()

    bonuses_result = type(
        "obj",
        (object,),
        {
            "data": profile_data.get("recent_bonuses") or [],
        },
    )()

    withdrawals_result = type(
        "obj",
        (object,),
        {
            "data": profile_data.get("recent_withdrawals") or [],
        },
    )()

    transactions_result = type(
        "obj",
        (object,),
        {
            "data": profile_data.get("recent_transactions") or [],
        },
    )()

    return (
        settings,
        extended_stats_result,
        bonuses_result,
        withdrawals_result,
        transactions_result,
    )


def _build_profile_response(
    db_user: Any,
    formatter: Any,
    referral_program: DictStrAny,
    referral_stats: DictStrAny,
    bonus_result: Any,
    withdrawal_result: Any,
    balance_transactions_result: Any,
    balance_in_local: float,
    balance_currency: str,
    balance_usd: float,
) -> DictStrAny:
    """Build the profile response dict."""
    total_referral_earnings_usd = (
        float(db_user.total_referral_earnings)
        if hasattr(db_user, "total_referral_earnings") and db_user.total_referral_earnings
        else 0
    )
    total_saved_usd = float(db_user.total_saved) if db_user.total_saved else 0

    return {
        "profile": {
            "balance_usd": round(balance_usd, 2),
            "total_referral_earnings_usd": total_referral_earnings_usd,
            "total_saved_usd": total_saved_usd,
            "balance": balance_in_local,
            "total_referral_earnings": formatter.convert(total_referral_earnings_usd),
            "total_saved": formatter.convert(total_saved_usd),
            "balance_formatted": formatter.format_balance(balance_in_local, balance_currency),
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{db_user.telegram_id}",
            "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
            "is_admin": db_user.is_admin or False,
            "is_partner": referral_program.get("is_partner", False),
            "first_name": db_user.first_name,
            "username": db_user.username,
            "telegram_id": db_user.telegram_id,
            "photo_url": getattr(db_user, "photo_url", None),
            "balance_currency": balance_currency,
        },
        "referral_program": referral_program,
        "referral_stats": referral_stats,
        "bonus_history": bonus_result.data or [],
        "withdrawals": withdrawal_result.data or [],
        "balance_transactions": balance_transactions_result.data or [],
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }


async def _fetch_level_referrals(
    db: Any, user_id: str, level: int, offset: int, limit: int
) -> tuple[list[dict[str, Any]], None]:
    """Fetch referrals for a specific level. Returns (referrals_data, direct_ref_ids_for_level2)."""
    if level == 1:
        result = (
            await db.client.table("users")
            .select(
                "id, telegram_id, username, first_name, created_at, referral_program_unlocked, photo_url",
            )
            .eq("referrer_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or [], None

    if level == 2:
        direct_refs = (
            await db.client.table("users").select("id").eq("referrer_id", user_id).execute()
        )
        direct_ref_ids = [r["id"] for r in (direct_refs.data or [])]

        if not direct_ref_ids:
            return [], None

        result = (
            await db.client.table("users")
            .select(
                "id, telegram_id, username, first_name, created_at, referral_program_unlocked, referrer_id, photo_url",
            )
            .in_("referrer_id", direct_ref_ids)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or [], None

    # level == 3
    l1_refs = await db.client.table("users").select("id").eq("referrer_id", user_id).execute()
    l1_ids = [r["id"] for r in (l1_refs.data or [])]

    if not l1_ids:
        return [], None

    l2_refs = await db.client.table("users").select("id").in_("referrer_id", l1_ids).execute()
    l2_ids = [r["id"] for r in (l2_refs.data or [])]

    if not l2_ids:
        return [], None

    result = (
        await db.client.table("users")
        .select(
            "id, telegram_id, username, first_name, created_at, referral_program_unlocked, referrer_id, photo_url",
        )
        .in_("referrer_id", l2_ids)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data or [], None


async def _batch_fetch_referral_data(
    db: "Database", referral_ids: list[str], referrer_id: str
) -> tuple[dict[str, int], dict[str, float]]:
    """Batch fetch orders count and earnings for referrals."""
    orders_count_map: dict[str, int] = {}
    earnings_map: dict[str, float] = {}

    # Batch fetch orders count
    try:
        orders_result = (
            await db.client.table("orders")
            .select("user_id")
            .in_("user_id", referral_ids)
            .in_("status", ["delivered"])
            .execute()
        )
        for order in orders_result.data or []:
            if isinstance(order, dict):
                order_user_id = order.get("user_id")
                if order_user_id and isinstance(order_user_id, str):
                    orders_count_map[order_user_id] = orders_count_map.get(order_user_id, 0) + 1
    except Exception as e:
        logger.warning(f"Failed to batch fetch orders count: {e}")

    # Batch fetch earnings
    try:
        earnings_result = (
            await db.client.table("referral_bonuses")
            .select("from_user_id, amount")
            .eq("referrer_id", referrer_id)
            .in_("from_user_id", referral_ids)
            .eq("eligible", True)
            .execute()
        )
        for bonus in earnings_result.data or []:
            if isinstance(bonus, dict):
                from_user_id = bonus.get("from_user_id")
                amount_raw = bonus.get("amount", 0)
                amount = float(amount_raw) if amount_raw is not None else 0.0
                if from_user_id and isinstance(from_user_id, str):
                    earnings_map[from_user_id] = earnings_map.get(from_user_id, 0) + amount
    except Exception as e:
        logger.warning(f"Failed to batch fetch earnings: {e}")

    return orders_count_map, earnings_map


def _build_enriched_referrals(
    referrals_data: list[dict[str, Any]],
    user_id: str,
    referral_ids: list[str],
    orders_count_map: dict[str, int],
    earnings_map: dict[str, float],
) -> list[dict[str, Any]]:
    """Build enriched referrals list with order counts and earnings."""
    enriched = []
    for ref in referrals_data:
        ref_id = ref.get("id")
        if not ref_id or ref_id == user_id or ref_id not in referral_ids:
            continue

        enriched.append(
            {
                "id": ref_id,
                "telegram_id": ref.get("telegram_id"),
                "username": ref.get("username"),
                "first_name": ref.get("first_name"),
                "created_at": ref.get("created_at"),
                "is_active": ref.get("referral_program_unlocked", False),
                "order_count": orders_count_map.get(ref_id, 0),
                "earnings_generated": round(earnings_map.get(ref_id, 0), 2),
                "photo_url": ref.get("photo_url"),
            },
        )
    return enriched


# =============================================================================
# Profile Endpoints
# =============================================================================


@profile_router.get("/profile")
async def get_webapp_profile(db_user: Annotated[User, Depends(get_db_user)]) -> dict[str, Any]:
    """Get user profile with referral stats, balance, and history."""
    db = get_database()

    await _maybe_refresh_photo(db, db_user, db_user.telegram_id)

    # Fetch all data in parallel
    (
        settings,
        extended_stats_result,
        bonus_result,
        withdrawal_result,
        balance_transactions_result,
    ) = await _fetch_profile_data(db, db_user)

    # Extract thresholds and commissions (defaults in RUB after migration)
    # Ensure settings is a dict
    if not isinstance(settings, dict):
        settings = {}
    THRESHOLD_LEVEL2 = float(settings.get("level2_threshold_usd", 20000) or 20000)
    THRESHOLD_LEVEL3 = float(settings.get("level3_threshold_usd", 80000) or 80000)
    COMMISSION_LEVEL1 = float(settings.get("level1_commission_percent", 10) or 10)
    COMMISSION_LEVEL2 = float(settings.get("level2_commission_percent", 7) or 7)
    COMMISSION_LEVEL3 = float(settings.get("level3_commission_percent", 3) or 3)

    # Setup formatter
    from core.db import get_redis
    from core.services.currency_response import CurrencyFormatter

    redis = get_redis()
    formatter = CurrencyFormatter.create(db_user=db_user, redis=redis)

    # Build referral data
    referral_stats = {
        "level1_count": 0,
        "level2_count": 0,
        "level3_count": 0,
        "level1_earnings": 0,
        "level2_earnings": 0,
        "level3_earnings": 0,
        "active_referrals": 0,
        "click_count": 0,
        "conversion_rate": 0,
    }

    referral_program = _build_default_referral_program(
        THRESHOLD_LEVEL2,
        THRESHOLD_LEVEL3,
        COMMISSION_LEVEL1,
        COMMISSION_LEVEL2,
        COMMISSION_LEVEL3,
        formatter.currency,
        settings,
    )

    if extended_stats_result.data:
        s = extended_stats_result.data[0]
        # Ensure s is a dict
        if isinstance(s, dict):
            referral_stats, referral_program = _build_referral_data(
                s,
                THRESHOLD_LEVEL2,
                THRESHOLD_LEVEL3,
                COMMISSION_LEVEL1,
                COMMISSION_LEVEL2,
                COMMISSION_LEVEL3,
                formatter.currency,
                settings,
            )
        else:
            # Fallback if data is not dict
            referral_stats = {
                "level1_count": 0,
                "level2_count": 0,
                "level3_count": 0,
                "level1_earnings": 0,
                "level2_earnings": 0,
                "level3_earnings": 0,
                "active_referrals": 0,
                "click_count": 0,
                "conversion_rate": 0,
            }

    # Add partner mode settings
    referral_program["partner_mode"] = (
        getattr(db_user, "partner_mode", "commission") or "commission"
    )
    referral_program["partner_discount_percent"] = (
        getattr(db_user, "partner_discount_percent", 0) or 0
    )

    # Get balance info (all RUB now)
    balance_in_local = float(db_user.balance) if db_user.balance else 0
    balance_currency = "RUB"  # Always RUB after migration
    balance_usd = balance_in_local  # Same value (RUB)

    return _build_profile_response(
        db_user,
        formatter,
        referral_program,
        referral_stats,
        bonus_result,
        withdrawal_result,
        balance_transactions_result,
        balance_in_local,
        balance_currency,
        balance_usd,
    )


@profile_router.put("/profile/preferences")
async def update_preferences(
    request: UpdatePreferencesRequest, user=Depends(verify_telegram_auth)
) -> dict[str, Any]:
    """Update user preferences (interface language only).

    NOTE: Currency preference is ignored after RUB-only migration.
    """
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    valid_languages = ["ru", "en", "de", "es", "fr", "tr", "ar", "hi", "uk", "be", "kk"]
    if request.interface_language and request.interface_language.lower() not in valid_languages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid language. Valid options: {', '.join(valid_languages)}",
        )

    # NOTE: preferred_currency is ignored (all RUB now)
    await db.update_user_preferences(
        user.id,
        preferred_currency="RUB",  # Always RUB
        interface_language=request.interface_language,
    )

    return {"success": True, "message": "Preferences updated"}


@profile_router.post("/profile/convert-balance")
async def convert_balance(
    request: ConvertBalanceRequest, user: "TelegramUser" = Depends(verify_telegram_auth)
) -> dict[str, Any]:
    """Convert user balance to a different currency.

    DEPRECATED: After RUB-only migration, this endpoint returns current balance.
    Currency conversion is no longer supported.
    """
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    current_balance = float(db_user.balance) if db_user.balance else 0

    # After RUB-only migration, conversion is not supported
    return {
        "success": True,
        "message": "Currency conversion is no longer supported. All amounts are in RUB.",
        "balance": current_balance,
        "currency": "RUB",
    }


@profile_router.get("/referral/network")
async def get_referral_network(
    db_user: Annotated[User, Depends(get_db_user)],
    level: int = 1,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Get user's referral network (tree of referrals)."""
    db = get_database()
    user_id = db_user.id

    if level not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Level must be 1, 2, or 3")

    try:
        referrals_data, _ = await _fetch_level_referrals(db, user_id, level, offset, limit)

        if not referrals_data:
            return {"referrals": [], "total": 0, "level": level, "offset": offset, "limit": limit}

        # Deduplicate
        seen_ids = set()
        referral_ids = []
        for ref in referrals_data:
            ref_id = ref.get("id")
            if ref_id and ref_id != user_id and ref_id not in seen_ids:
                seen_ids.add(ref_id)
                referral_ids.append(ref_id)

        if not referral_ids:
            return {"referrals": [], "total": 0, "level": level, "offset": offset, "limit": limit}

        orders_count_map, earnings_map = await _batch_fetch_referral_data(
            db,
            referral_ids,
            db_user.id,
        )

        enriched_referrals = _build_enriched_referrals(
            referrals_data,
            user_id,
            referral_ids,
            orders_count_map,
            earnings_map,
        )

        return {
            "referrals": enriched_referrals,
            "total": len(enriched_referrals),
            "level": level,
            "offset": offset,
            "limit": limit,
        }

    except Exception as e:
        logger.error(f"Failed to get referral network: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load referral network")
