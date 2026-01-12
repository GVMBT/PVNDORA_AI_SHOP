"""
Leaderboard endpoints.

Savings leaderboard with period filtering and pagination.
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from core.services.database import get_database
from core.services.money import to_float
from core.services.currency_response import CurrencyFormatter
from core.db import get_redis
from core.auth import verify_telegram_auth
from .constants import MAX_LEADERBOARD_SIZE, DEFAULT_LEADERBOARD_LIMIT, LEADERBOARD_PERIOD_DAYS

leaderboard_router = APIRouter(tags=["webapp-misc-leaderboard"])


@leaderboard_router.get("/leaderboard")
async def get_webapp_leaderboard(period: str = "all", limit: int = DEFAULT_LEADERBOARD_LIMIT, offset: int = 0, user=Depends(verify_telegram_auth)):
    """Get savings leaderboard. Supports period: all, month, week and pagination."""
    db = get_database()
    redis = get_redis()
    LEADERBOARD_SIZE = min(limit, MAX_LEADERBOARD_SIZE)
    now = datetime.now(timezone.utc)
    
    # Get user's currency formatter for converting amounts
    formatter = await CurrencyFormatter.create(user.id, db, redis)
    
    date_filter = None
    if period in LEADERBOARD_PERIOD_DAYS:
        date_filter = (now - timedelta(days=LEADERBOARD_PERIOD_DAYS[period])).isoformat()
    
    if date_filter:
        orders_result = await db.client.table("orders").select(
            "user_id,amount,original_price,users(telegram_id,username,first_name,photo_url)"
        ).eq("status", "delivered").gte("created_at", date_filter).execute()
        
        user_savings = {}
        user_ids_from_orders = set()  # Collect user_ids for modules count
        for order in (orders_result.data or []):
            uid = order.get("user_id")
            if not uid:
                continue
            user_ids_from_orders.add(uid)  # Track user_id for modules count
            orig = to_float(order.get("original_price") or order.get("amount") or 0)
            paid = to_float(order.get("amount") or 0)
            saved = max(0, orig - paid)
            
            if uid not in user_savings:
                user_data = order.get("users", {})
                user_savings[uid] = {
                    "user_id": uid,  # Store user_id for modules count lookup
                    "telegram_id": user_data.get("telegram_id"),
                    "username": user_data.get("username"),
                    "first_name": user_data.get("first_name"),
                    "photo_url": user_data.get("photo_url"),
                    "total_saved": 0
                }
            user_savings[uid]["total_saved"] += saved
        
        result_data = sorted(user_savings.values(), key=lambda x: x["total_saved"], reverse=True)[:LEADERBOARD_SIZE]
        
        # Pre-fetch modules count for period-based queries (we already have user_ids)
        # Note: modules_count_map will be populated below in the unified logic
    else:
        # Get users with savings (sorted by total_saved desc)
        # Use range() for proper pagination
        users_with_savings_count = await db.client.table("users").select(
            "id", count="exact"
        ).gt("total_saved", 0).execute()
        savings_count = users_with_savings_count.count or 0
        
        if offset < savings_count:
            # Still within users who have savings
            result = await db.client.table("users").select(
                "telegram_id,username,first_name,total_saved,photo_url"
            ).gt("total_saved", 0).order("total_saved", desc=True).range(
                offset, offset + LEADERBOARD_SIZE - 1
            ).execute()
            result_data = result.data or []
            
            # If we need more to fill the page, get users with 0 savings
            if len(result_data) < LEADERBOARD_SIZE:
                remaining = LEADERBOARD_SIZE - len(result_data)
                fill_result = await db.client.table("users").select(
                    "telegram_id,username,first_name,total_saved,photo_url"
                ).eq("total_saved", 0).order("created_at", desc=True).range(0, remaining - 1).execute()
                result_data.extend(fill_result.data or [])
        else:
            # We're past all users with savings, now showing users with 0 savings
            zero_offset = offset - savings_count
            fill_result = await db.client.table("users").select(
                "telegram_id,username,first_name,total_saved,photo_url"
            ).eq("total_saved", 0).order("created_at", desc=True).range(
                zero_offset, zero_offset + LEADERBOARD_SIZE - 1
            ).execute()
            result_data = fill_result.data or []
    
    total_count = await db.client.table("users").select(
        "id", count="exact"
    ).execute()
    total_users = total_count.count or 0
    
    # CRITICAL: If offset exceeds total users, return empty result
    if offset >= total_users:
        db_user = await db.get_user_by_telegram_id(user.id)
        user_saved = float(db_user.total_saved) if db_user and hasattr(db_user, 'total_saved') and db_user.total_saved else 0
        return {
            "leaderboard": [], 
            "user_rank": None, 
            "user_saved": formatter.convert(user_saved),
            "user_saved_usd": user_saved,
            "total_users": total_users, 
            "improved_today": 0,
            "has_more": False,
            "offset": offset,
            "limit": LEADERBOARD_SIZE,
            "currency": formatter.currency,
            "exchange_rate": formatter.exchange_rate,
        }
    
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    improved_result = await db.client.table("orders").select(
        "user_id", count="exact"
    ).eq("status", "delivered").gte("created_at", today_start.isoformat()).execute()
    improved_today = improved_result.count or 0
    
    db_user = await db.get_user_by_telegram_id(user.id)
    user_rank, user_saved = None, 0
    user_found_in_list = False
    
    # Collect user IDs to batch fetch delivered orders count
    # For period-based queries, user_ids are already in result_data
    # For all-time queries, we need to get them from telegram_ids
    telegram_id_to_user_id = {}
    modules_count_map = {}
    
    # Build user_id mapping and collect user_ids for modules count
    user_ids_for_count = []
    if date_filter:
        # For period-based queries, user_ids are already in result_data
        for entry in result_data:
            uid = entry.get("user_id")
            tg_id = entry.get("telegram_id")
            if uid:
                user_ids_for_count.append(uid)
            if uid and tg_id:
                telegram_id_to_user_id[tg_id] = uid
    else:
        # For all-time queries, get user_ids from telegram_ids
        telegram_ids = [entry.get("telegram_id") for entry in result_data if entry.get("telegram_id")]
        if telegram_ids:
            # Batch fetch user_ids for all telegram_ids
            users_result = await db.client.table("users").select("id, telegram_id").in_(
                "telegram_id", telegram_ids
            ).execute()
            
            for user_data in (users_result.data or []):
                uid = user_data.get("id")
                tg_id = user_data.get("telegram_id")
                if uid and tg_id:
                    user_ids_for_count.append(uid)
                    telegram_id_to_user_id[tg_id] = uid
    
    # OPTIMIZED: Batch fetch delivered orders count for all users in ONE query
    if user_ids_for_count:
        # Get all delivered orders for these users in a single query
        orders_result = await db.client.table("orders").select(
            "user_id"
        ).in_("user_id", user_ids_for_count).eq("status", "delivered").execute()
        
        # Count orders per user client-side (much faster than N queries)
        from collections import Counter
        order_counts = Counter(order.get("user_id") for order in (orders_result.data or []))
        modules_count_map = dict(order_counts)
    
    leaderboard = []
    for i, entry in enumerate(result_data):
        # Cap rank at total_users to avoid inflated ranks
        actual_rank = min(i + 1 + offset, total_users)
        
        tg_id = entry.get("telegram_id")
        display_name = entry.get("username") or entry.get("first_name") or (f"User{str(tg_id)[-4:]}" if tg_id else "User")
        if len(display_name) > 3:
            display_name = display_name[:3] + "***"
        
        is_current = tg_id == user.id if tg_id else False
        if is_current:
            user_found_in_list = True
            user_rank = actual_rank
            user_saved = float(entry.get("total_saved", 0))
        
        # Get modules count (delivered orders) for this user
        # For period-based queries, user_id is already in entry
        # For all-time queries, get it from telegram_id mapping
        user_id = entry.get("user_id") or (telegram_id_to_user_id.get(tg_id) if tg_id else None)
        modules_count = modules_count_map.get(user_id, 0) if user_id else 0
        
        leaderboard.append({
            "rank": actual_rank,
            "name": display_name, 
            "total_saved": formatter.convert(float(entry.get("total_saved", 0))),
            "total_saved_usd": float(entry.get("total_saved", 0)),
            "is_current_user": is_current,
            "telegram_id": tg_id,  # For avatar lookup
            "photo_url": entry.get("photo_url"),  # User profile photo from Telegram
            "modules_count": modules_count, # Count of delivered orders
        })
    
    # If user not in current page, calculate their actual rank
    if not user_found_in_list and db_user:
        user_saved = float(db_user.total_saved) if hasattr(db_user, 'total_saved') and db_user.total_saved else 0
        if user_saved > 0:
            rank_result = await db.client.table("users").select(
                "id", count="exact"
            ).gt("total_saved", user_saved).execute()
            user_rank = (rank_result.count or 0) + 1
        else:
            # For users with no savings, find their position by created_at
            # This matches the fill_result ordering
            user_created = db_user.created_at
            if user_created:
                earlier_count = await db.client.table("users").select(
                    "id", count="exact"
                ).eq("total_saved", 0).lt("created_at", user_created.isoformat()).execute()
                users_with_savings = await db.client.table("users").select(
                    "id", count="exact"
                ).gt("total_saved", 0).execute()
                user_rank = (users_with_savings.count or 0) + (earlier_count.count or 0) + 1
            else:
                user_rank = total_users
    
    # Calculate has_more based on actual data availability
    # has_more is True only if there are more users beyond current offset + returned count
    next_offset = offset + len(leaderboard)
    has_more = next_offset < total_users and len(leaderboard) == LEADERBOARD_SIZE
    
    return {
        "leaderboard": leaderboard, 
        "user_rank": user_rank, 
        "user_saved": formatter.convert(user_saved),
        "user_saved_usd": user_saved,
        "total_users": total_users, 
        "improved_today": improved_today,
        "has_more": has_more,
        "offset": offset,
        "limit": LEADERBOARD_SIZE,
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }
