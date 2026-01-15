"""Profile Helpers.

Shared utility functions for profile endpoints.
"""

import contextlib
import os

import httpx

from core.logging import get_logger

logger = get_logger(__name__)

PHOTO_REFRESH_TTL = 6 * 60 * 60  # 6 hours


async def _fetch_telegram_photo_url(telegram_id: int) -> str | None:
    """Fetch user's Telegram profile photo via Bot API.
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
    """Refresh user photo if:
      - No photo_url stored, or
      - TTL expired (redis gate)
    Uses a 6h gate to avoid spamming Telegram API.
    """
    redis = None
    try:
        try:
            from core.db import get_redis

            redis = get_redis()
        except Exception:
            redis = None

        gate_key = f"user:photo:refresh:{telegram_id}"

        # Check gate (skip if recently refreshed)
        if redis:
            try:
                if await redis.get(gate_key):
                    return
            except Exception:
                pass

        # Fetch and update photo
        photo_url = await _fetch_telegram_photo_url(telegram_id)
        current_photo = getattr(db_user, "photo_url", None)

        if photo_url and photo_url != current_photo:
            try:
                await db.update_user_photo(telegram_id, photo_url)
                db_user.photo_url = photo_url
            except Exception as e:
                logger.warning(f"Failed to update user photo: {e}")

        # Set gate
        if redis:
            with contextlib.suppress(Exception):
                await redis.set(gate_key, "1", ex=PHOTO_REFRESH_TTL)
    except Exception as e:
        logger.warning(f"Photo refresh failed: {e}")


async def _get_anchor_thresholds_for_display(
    display_currency: str, settings: dict, threshold2: float, threshold3: float,
) -> dict:
    """Get thresholds for display (all in RUB now).

    NOTE: After RUB-only migration, thresholds are stored in RUB.
    display_currency parameter is kept for backward compatibility but ignored.
    """
    # All thresholds are now in RUB
    return {"level2": threshold2, "level3": threshold3}


async def _build_default_referral_program(
    threshold2: float,
    threshold3: float,
    comm1: float,
    comm2: float,
    comm3: float,
    display_currency: str = "RUB",
    settings: dict | None = None,
) -> dict:
    """Build default referral program data.

    NOTE: After RUB-only migration, all monetary values are in RUB.
    Field names with '_usd' suffix kept for backward compatibility.
    """
    # All thresholds are now in RUB
    thresholds_display = {"level2": threshold2, "level3": threshold3}

    return {
        "unlocked": False,
        "status": "locked",
        "is_partner": False,
        "partner_mode": "commission",
        "partner_discount_percent": 0,
        "effective_level": 0,
        "level1_unlocked": False,
        "level2_unlocked": False,
        "level3_unlocked": False,
        # NOTE: Field named '_usd' but values are in RUB after migration
        "turnover_usd": 0,
        "amount_to_level2_usd": threshold2,
        "amount_to_level3_usd": threshold3,
        "amount_to_next_level_usd": threshold2,
        "next_threshold_usd": threshold2,
        "next_threshold_display": threshold2,
        "thresholds_usd": thresholds_display,
        "thresholds_display": thresholds_display,
        "commissions_percent": {"level1": comm1, "level2": comm2, "level3": comm3},
        "level1_unlocked_at": None,
        "level2_unlocked_at": None,
        "level3_unlocked_at": None,
    }


def _calculate_effective_level(
    is_partner: bool,
    partner_override: int | None,
    unlocked: bool,
    turnover_usd: float,
    threshold2: float,
    threshold3: float,
) -> int:
    """Calculate effective referral level."""
    if is_partner and partner_override is not None:
        return partner_override
    if not unlocked:
        return 0
    if turnover_usd >= threshold3:
        return 3
    if turnover_usd >= threshold2:
        return 2
    # unlocked is True at this point (checked above)
    return 1


def _calculate_amounts_to_levels(
    effective_level: int, turnover_usd: float, threshold2: float, threshold3: float,
) -> tuple[float, float, float | None, float]:
    """Calculate amounts needed to reach next levels."""
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

    return amount_to_level2, amount_to_level3, next_threshold, amount_to_next


def _build_referral_stats(s: dict) -> dict:
    """Build referral stats from extended stats."""
    click_count = s.get("click_count", 0) or 0
    total_referrals = s.get("level1_count", 0) or 0
    conversion_rate = round((total_referrals / click_count * 100), 1) if click_count > 0 else 0

    return {
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


def _calculate_next_threshold_display(
    next_threshold: float | None, threshold2: float, threshold3: float, thresholds_display: dict,
) -> float | None:
    """Calculate next threshold in display currency."""
    if not next_threshold:
        return None
    if next_threshold == threshold2:
        return thresholds_display["level2"]
    if next_threshold == threshold3:
        return thresholds_display["level3"]
    return None


async def _build_referral_data(
    s: dict,
    threshold2: float,
    threshold3: float,
    comm1: float,
    comm2: float,
    comm3: float,
    display_currency: str = "RUB",
    settings: dict | None = None,
) -> tuple:
    """Build referral stats and program data from extended stats.

    NOTE: After RUB-only migration, all monetary values are in RUB.
    Field names with '_usd' suffix kept for backward compatibility.
    """
    referral_stats = _build_referral_stats(s)

    # Core program data from view
    unlocked = s.get("referral_program_unlocked", False)
    is_partner = s.get("is_partner", False)
    partner_override = s.get("partner_level_override")
    # NOTE: turnover_usd now contains RUB values after migration
    turnover = float(s.get("turnover_usd") or 0)

    # Calculate effective level (thresholds are in RUB)
    effective_level = _calculate_effective_level(
        is_partner, partner_override, unlocked, turnover, threshold2, threshold3,
    )

    status = "locked" if not unlocked else "active"
    level1_unlocked = effective_level >= 1
    level2_unlocked = effective_level >= 2
    level3_unlocked = effective_level >= 3

    # Calculate amounts to levels
    amount_to_level2, amount_to_level3, next_threshold, amount_to_next = (
        _calculate_amounts_to_levels(effective_level, turnover, threshold2, threshold3)
    )

    # All values are in RUB now
    thresholds_display = {"level2": threshold2, "level3": threshold3}

    referral_program = {
        "unlocked": unlocked,
        "status": status,
        "is_partner": is_partner,
        "effective_level": effective_level,
        "level1_unlocked": level1_unlocked,
        "level2_unlocked": level2_unlocked,
        "level3_unlocked": level3_unlocked,
        # NOTE: Field named '_usd' but values are in RUB
        "turnover_usd": turnover,
        "amount_to_level2_usd": amount_to_level2,
        "amount_to_level3_usd": amount_to_level3,
        "amount_to_next_level_usd": amount_to_next,
        "next_threshold_usd": next_threshold,
        "thresholds_usd": thresholds_display,
        "thresholds_display": thresholds_display,
        "next_threshold_display": next_threshold,
        "commissions_percent": {"level1": comm1, "level2": comm2, "level3": comm3},
        "level1_unlocked_at": s.get("level1_unlocked_at"),
        "level2_unlocked_at": s.get("level2_unlocked_at"),
        "level3_unlocked_at": s.get("level3_unlocked_at"),
    }

    return referral_stats, referral_program
