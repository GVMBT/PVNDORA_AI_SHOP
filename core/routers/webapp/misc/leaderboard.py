"""
Leaderboard endpoints.

Savings leaderboard with period filtering and pagination.
"""

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth import verify_telegram_auth
from core.db import get_redis
from core.services.currency_response import CurrencyFormatter
from core.services.database import get_database
from core.services.money import to_float

from .constants import DEFAULT_LEADERBOARD_LIMIT, LEADERBOARD_PERIOD_DAYS, MAX_LEADERBOARD_SIZE

leaderboard_router = APIRouter(tags=["webapp-misc-leaderboard"])

# Constants (avoid string duplication)
SELECT_USER_FIELDS = "telegram_id,username,first_name,total_saved,photo_url"


async def _get_period_leaderboard_data(
    db: Any, date_filter: str, leaderboard_size: int
) -> list[dict[str, Any]]:
    """Get leaderboard data for period-based queries (week/month)."""
    orders_result = (
        await db.client.table("orders")
        .select("user_id,amount,original_price,users(telegram_id,username,first_name,photo_url)")
        .eq("status", "delivered")
        .gte("created_at", date_filter)
        .execute()
    )

    user_savings = {}
    for order in orders_result.data or []:
        uid = order.get("user_id")
        if not uid:
            continue

        orig = to_float(order.get("original_price") or order.get("amount") or 0)
        paid = to_float(order.get("amount") or 0)
        saved = max(0, orig - paid)

        if uid not in user_savings:
            user_data = order.get("users", {})
            user_savings[uid] = {
                "user_id": uid,
                "telegram_id": user_data.get("telegram_id"),
                "username": user_data.get("username"),
                "first_name": user_data.get("first_name"),
                "photo_url": user_data.get("photo_url"),
                "total_saved": 0,
            }
        user_savings[uid]["total_saved"] += saved

    return sorted(user_savings.values(), key=lambda x: x["total_saved"], reverse=True)[
        :leaderboard_size
    ]


async def _get_users_with_savings_count(db: Any) -> int:
    """Get count of users with savings."""
    users_with_savings_count = (
        await db.client.table("users").select("id", count="exact").gt("total_saved", 0).execute()
    )
    return users_with_savings_count.count or 0


async def _get_users_with_savings(
    db: Any, offset: int, leaderboard_size: int
) -> list[dict[str, Any]]:
    """Get users with savings for leaderboard."""
    result = (
        await db.client.table("users")
        .select(SELECT_USER_FIELDS)
        .gt("total_saved", 0)
        .order("total_saved", desc=True)
        .range(offset, offset + leaderboard_size - 1)
        .execute()
    )
    return result.data or []


async def _get_users_with_zero_savings(db: Any, offset: int, limit: int) -> list[dict[str, Any]]:
    """Get users with zero savings for leaderboard."""
    fill_result = (
        await db.client.table("users")
        .select(SELECT_USER_FIELDS)
        .eq("total_saved", 0)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return fill_result.data or []


async def _get_alltime_leaderboard_data(
    db: Any, offset: int, leaderboard_size: int
) -> list[dict[str, Any]]:
    """Get leaderboard data for all-time queries with pagination."""
    savings_count = await _get_users_with_savings_count(db)

    if offset < savings_count:
        result_data = await _get_users_with_savings(db, offset, leaderboard_size)

        if len(result_data) < leaderboard_size:
            remaining = leaderboard_size - len(result_data)
            fill_data = await _get_users_with_zero_savings(db, 0, remaining)
            result_data.extend(fill_data)
    else:
        zero_offset = offset - savings_count
        result_data = await _get_users_with_zero_savings(db, zero_offset, leaderboard_size)

    return result_data


def _get_user_ids_for_period_query(
    result_data: list[dict[str, Any]],
) -> tuple[list[int], dict[int, int]]:
    """Extract user IDs and telegram mapping for period-based queries."""
    user_ids_for_count: list[int] = []
    telegram_id_to_user_id: dict[int, int] = {}

    for entry in result_data:
        uid = entry.get("user_id")
        tg_id = entry.get("telegram_id")
        if uid:
            user_ids_for_count.append(uid)
        if uid and tg_id:
            telegram_id_to_user_id[tg_id] = uid

    return user_ids_for_count, telegram_id_to_user_id


async def _get_user_ids_for_alltime_query(
    db: Any, result_data: list[dict[str, Any]]
) -> tuple[list[int], dict[int, int]]:
    """Extract user IDs and telegram mapping for all-time queries."""
    telegram_ids = [entry.get("telegram_id") for entry in result_data if entry.get("telegram_id")]

    if not telegram_ids:
        return [], {}

    users_result = (
        await db.client.table("users")
        .select("id, telegram_id")
        .in_("telegram_id", telegram_ids)
        .execute()
    )

    user_ids_for_count: list[int] = []
    telegram_id_to_user_id: dict[int, int] = {}

    for user_data in users_result.data or []:
        uid = user_data.get("id")
        tg_id = user_data.get("telegram_id")
        if uid and tg_id:
            user_ids_for_count.append(uid)
            telegram_id_to_user_id[tg_id] = uid

    return user_ids_for_count, telegram_id_to_user_id


async def _fetch_modules_count_map(db: Any, user_ids: list[int]) -> dict[int, int]:
    """Fetch modules count (delivered orders) for given user IDs."""
    if not user_ids:
        return {}

    orders_result = (
        await db.client.table("orders")
        .select("user_id")
        .in_("user_id", user_ids)
        .eq("status", "delivered")
        .execute()
    )

    order_counts = Counter(order.get("user_id") for order in (orders_result.data or []))
    return dict(order_counts)


async def _get_modules_count_map(
    db: Any, result_data: list[dict[str, Any]], date_filter: str | None
) -> tuple[dict[int, int], dict[int, int]]:
    """Get modules count (delivered orders) for users and telegram_id to user_id mapping."""
    if date_filter:
        user_ids_for_count, telegram_id_to_user_id = _get_user_ids_for_period_query(result_data)
    else:
        user_ids_for_count, telegram_id_to_user_id = await _get_user_ids_for_alltime_query(
            db, result_data
        )

    modules_count_map = await _fetch_modules_count_map(db, user_ids_for_count)

    return modules_count_map, telegram_id_to_user_id


async def _calculate_user_rank(db: Any, db_user: Any, total_users: int) -> tuple[int | None, float]:
    """Calculate user rank when user is not in current page."""
    if not db_user:
        return None, 0.0

    user_saved = (
        float(db_user.total_saved)
        if hasattr(db_user, "total_saved") and db_user.total_saved
        else 0.0
    )

    if user_saved > 0:
        rank_result = (
            await db.client.table("users")
            .select("id", count="exact")
            .gt("total_saved", user_saved)
            .execute()
        )
        user_rank = (rank_result.count or 0) + 1
    else:
        user_created = db_user.created_at
        if user_created:
            earlier_count = (
                await db.client.table("users")
                .select("id", count="exact")
                .eq("total_saved", 0)
                .lt("created_at", user_created.isoformat())
                .execute()
            )
            users_with_savings = (
                await db.client.table("users")
                .select("id", count="exact")
                .gt("total_saved", 0)
                .execute()
            )
            user_rank = (users_with_savings.count or 0) + (earlier_count.count or 0) + 1
        else:
            user_rank = total_users

    return user_rank, user_saved


def _format_display_name(entry: dict[str, Any]) -> str:
    """Format user display name with masking."""
    tg_id = entry.get("telegram_id")
    display_name = (
        entry.get("username")
        or entry.get("first_name")
        or (f"User{str(tg_id)[-4:]}" if tg_id else "User")
    )
    if len(display_name) > 3:
        display_name = display_name[:3] + "***"
    return display_name


async def _get_improved_today_count(db: Any, now: datetime) -> int:
    """Get count of users who improved today (delivered orders)."""
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    improved_result = (
        await db.client.table("orders")
        .select("user_id", count="exact")
        .eq("status", "delivered")
        .gte("created_at", today_start.isoformat())
        .execute()
    )
    return improved_result.count or 0


async def _get_total_users_count(db: Any) -> int:
    """Get total users count."""
    total_count = await db.client.table("users").select("id", count="exact").execute()
    return total_count.count or 0


def _build_empty_response(
    formatter: CurrencyFormatter, user_saved: float, total_users: int, offset: int, limit: int
) -> dict[str, Any]:
    """Build empty leaderboard response when offset exceeds total users."""
    return {
        "leaderboard": [],
        "user_rank": None,
        "user_saved": formatter.convert(user_saved),
        "user_saved_usd": user_saved,
        "total_users": total_users,
        "improved_today": 0,
        "has_more": False,
        "offset": offset,
        "limit": limit,
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }


def _build_leaderboard_response(
    formatter: CurrencyFormatter,
    leaderboard: list[dict[str, Any]],
    user_rank: int | None,
    user_saved: float,
    total_users: int,
    improved_today: int,
    has_more: bool,
    offset: int,
    limit: int,
) -> dict[str, Any]:
    """Build final leaderboard response."""
    return {
        "leaderboard": leaderboard,
        "user_rank": user_rank,
        "user_saved": formatter.convert(user_saved),
        "user_saved_usd": user_saved,
        "total_users": total_users,
        "improved_today": improved_today,
        "has_more": has_more,
        "offset": offset,
        "limit": limit,
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }


def _build_leaderboard_entry(
    entry: dict[str, Any],
    formatter: CurrencyFormatter,
    user_id: int,
    rank: int,
    modules_count_map: dict[int, int],
    telegram_id_to_user_id: dict[int, int],
) -> dict[str, Any]:
    """Build a single leaderboard entry."""
    tg_id = entry.get("telegram_id")
    display_name = _format_display_name(entry)
    is_current = tg_id == user_id if tg_id else False

    user_id_for_count = entry.get("user_id") or (
        telegram_id_to_user_id.get(tg_id) if tg_id else None
    )
    modules_count = modules_count_map.get(user_id_for_count, 0) if user_id_for_count else 0

    return {
        "rank": rank,
        "name": display_name,
        "total_saved": formatter.convert(float(entry.get("total_saved", 0))),
        "total_saved_usd": float(entry.get("total_saved", 0)),
        "is_current_user": is_current,
        "telegram_id": tg_id,
        "photo_url": entry.get("photo_url"),
        "modules_count": modules_count,
    }


def _build_leaderboard_entries(
    result_data: list[dict[str, Any]],
    formatter: CurrencyFormatter,
    user_id: int,
    offset: int,
    total_users: int,
    modules_count_map: dict[int, int],
    telegram_id_to_user_id: dict[int, int],
) -> tuple[list[dict[str, Any]], int | None, float, bool]:
    """Build leaderboard entries from result data."""
    leaderboard = []
    user_rank: int | None = None
    user_saved = 0.0
    user_found_in_list = False

    for i, entry in enumerate(result_data):
        actual_rank = min(i + 1 + offset, total_users)
        entry_data = _build_leaderboard_entry(
            entry, formatter, user_id, actual_rank, modules_count_map, telegram_id_to_user_id
        )

        if entry_data["is_current_user"]:
            user_found_in_list = True
            user_rank = actual_rank
            user_saved = float(entry.get("total_saved", 0))

        leaderboard.append(entry_data)

    return leaderboard, user_rank, user_saved, user_found_in_list


@leaderboard_router.get("/leaderboard")
async def get_webapp_leaderboard(
    period: str = "all",
    limit: int = DEFAULT_LEADERBOARD_LIMIT,
    offset: int = 0,
    user=Depends(verify_telegram_auth),
):
    """Get savings leaderboard. Supports period: all, month, week and pagination."""
    from core.logging import get_logger

    logger = get_logger(__name__)

    try:
        db = get_database()
        redis = get_redis()
        leaderboard_size = min(limit, MAX_LEADERBOARD_SIZE)
        now = datetime.now(UTC)

        formatter = await CurrencyFormatter.create(user.id, db, redis)

        date_filter = None
        if period in LEADERBOARD_PERIOD_DAYS:
            date_filter = (now - timedelta(days=LEADERBOARD_PERIOD_DAYS[period])).isoformat()

        if date_filter:
            result_data = await _get_period_leaderboard_data(db, date_filter, leaderboard_size)
        else:
            result_data = await _get_alltime_leaderboard_data(db, offset, leaderboard_size)

        total_users = await _get_total_users_count(db)

        if offset >= total_users:
            db_user = await db.get_user_by_telegram_id(user.id)
            user_saved = (
                float(db_user.total_saved)
                if db_user and hasattr(db_user, "total_saved") and db_user.total_saved
                else 0.0
            )
            return _build_empty_response(formatter, user_saved, total_users, offset, leaderboard_size)

        improved_today = await _get_improved_today_count(db, now)
        db_user = await db.get_user_by_telegram_id(user.id)

        modules_count_map, telegram_id_to_user_id = await _get_modules_count_map(
            db, result_data, date_filter
        )

        leaderboard, user_rank, user_saved, user_found_in_list = _build_leaderboard_entries(
            result_data,
            formatter,
            user.id,
            offset,
            total_users,
            modules_count_map,
            telegram_id_to_user_id,
        )

        if not user_found_in_list:
            user_rank, user_saved = await _calculate_user_rank(db, db_user, total_users)

        has_more = (offset + len(leaderboard) < total_users) and (len(leaderboard) == leaderboard_size)

        return _build_leaderboard_response(
            formatter,
            leaderboard,
            user_rank,
            user_saved,
            total_users,
            improved_today,
            has_more,
            offset,
            leaderboard_size,
        )
    except Exception as e:
        logger.error(f"Failed to fetch leaderboard: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch leaderboard")
