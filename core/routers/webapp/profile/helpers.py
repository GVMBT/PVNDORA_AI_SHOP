"""
Profile Helpers

Shared utility functions for profile endpoints.
"""
import os
from typing import Optional

import httpx

from core.logging import get_logger

logger = get_logger(__name__)

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


async def _build_default_referral_program(threshold2: float, threshold3: float, comm1: float, comm2: float, comm3: float,
                                         display_currency: str = "USD", settings: dict = None) -> dict:
    """Build default referral program data."""
    from core.db import get_redis
    from core.services.currency import get_currency_service
    
    # Get anchor thresholds for display
    thresholds_display = {"level2": threshold2, "level3": threshold3}
    
    if settings and display_currency != "USD":
        try:
            redis = get_redis()
            currency_service = get_currency_service(redis)
            thresholds_display["level2"] = float(await currency_service.get_anchor_threshold(settings, display_currency, 2))
            thresholds_display["level3"] = float(await currency_service.get_anchor_threshold(settings, display_currency, 3))
        except Exception as e:
            logger.warning(f"Failed to get anchor thresholds: {e}")
    
    # Next threshold for locked users (level 0) is level 2 threshold
    next_threshold_display = thresholds_display["level2"]
    
    return {
        "unlocked": False,
        "status": "locked",
        "is_partner": False,
        "partner_mode": "commission",  # Default partner mode
        "partner_discount_percent": 0,  # Default discount
        "effective_level": 0,
        "level1_unlocked": False,
        "level2_unlocked": False,
        "level3_unlocked": False,
        "turnover_usd": 0,
        "amount_to_level2_usd": threshold2,
        "amount_to_level3_usd": threshold3,
        "amount_to_next_level_usd": threshold2,
        "next_threshold_usd": threshold2,
        "next_threshold_display": next_threshold_display,
        "thresholds_usd": {"level2": threshold2, "level3": threshold3},
        "thresholds_display": thresholds_display,
        "commissions_percent": {"level1": comm1, "level2": comm2, "level3": comm3},
        "level1_unlocked_at": None,
        "level2_unlocked_at": None,
        "level3_unlocked_at": None,
    }


async def _build_referral_data(s: dict, threshold2: float, threshold3: float, comm1: float, comm2: float, comm3: float,
                               display_currency: str = "USD", settings: dict = None) -> tuple:
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
    
    # Get anchor thresholds for display (using anchor thresholds from settings, like anchor prices)
    # Priority: 1) anchor threshold in currency, 2) convert from USD
    thresholds_display = {"level2": threshold2, "level3": threshold3}
    
    if settings and display_currency != "USD":
        try:
            from core.db import get_redis
            from core.services.currency import get_currency_service
            redis = get_redis()
            currency_service = get_currency_service(redis)
            
            thresholds_display["level2"] = float(await currency_service.get_anchor_threshold(settings, display_currency, 2))
            thresholds_display["level3"] = float(await currency_service.get_anchor_threshold(settings, display_currency, 3))
        except Exception as e:
            logger.warning(f"Failed to get anchor thresholds for display: {e}")
            # Fallback: convert from USD using exchange rate
            try:
                exchange_rate = await currency_service.get_exchange_rate(display_currency)
                if exchange_rate > 0:
                    thresholds_display["level2"] = round(threshold2 * exchange_rate, 2)
                    thresholds_display["level3"] = round(threshold3 * exchange_rate, 2)
            except:
                pass
    
    referral_program["thresholds_display"] = thresholds_display
    
    # Also add next_threshold in display currency for progress calculation
    if referral_program.get("next_threshold_usd"):
        if next_threshold == threshold2:
            referral_program["next_threshold_display"] = thresholds_display["level2"]
        elif next_threshold == threshold3:
            referral_program["next_threshold_display"] = thresholds_display["level3"]
        else:
            referral_program["next_threshold_display"] = None
    else:
        referral_program["next_threshold_display"] = None
    
    return referral_stats, referral_program
