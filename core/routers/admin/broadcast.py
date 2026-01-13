"""
Admin Broadcast Router

Allows admin to send messages to all users via Telegram bots.
All methods use async/await with supabase-py v2.
"""

import asyncio
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import verify_admin
from core.logging import get_logger
from core.services.database import get_database
from core.services.telegram_messaging import send_telegram_message as _send_telegram_message

logger = get_logger(__name__)

router = APIRouter(prefix="/broadcast", tags=["admin-broadcast"])

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")


class BroadcastRequest(BaseModel):
    """Request model for broadcast message."""

    message: str = Field(..., min_length=1, max_length=4096)
    target_bot: str = Field(default="main", description="Target bot: 'main', 'discount', or 'all'")
    filter_language: str | None = Field(
        None, description="Filter users by language_code (ru, en, etc)"
    )
    filter_has_orders: bool | None = Field(None, description="Filter users who have made orders")
    preview_only: bool = Field(
        default=False, description="If true, only return count of target users"
    )
    parse_mode: str = Field(default="HTML", description="Telegram parse mode: HTML or Markdown")


class BroadcastResult(BaseModel):
    """Result of broadcast operation."""

    target_count: int
    sent_count: int
    failed_count: int
    failed_user_ids: list[int]
    preview_only: bool


async def send_telegram_message(
    bot_token: str, chat_id: int, text: str, parse_mode: str = "HTML"
) -> bool:
    """Send a single message via Telegram Bot API.

    Wrapper around consolidated telegram_messaging service for backward compatibility.
    """
    return await _send_telegram_message(
        chat_id=chat_id, text=text, parse_mode=parse_mode, bot_token=bot_token
    )


async def _get_target_users(db, request: BroadcastRequest) -> list[dict]:
    """
    Get list of target users based on broadcast filters.

    Args:
        db: Database instance
        request: Broadcast request with filters

    Returns:
        List of user dicts with telegram_id
    """
    query = db.client.table("users").select("telegram_id, language_code")

    # Filter out banned and blocked users
    query = query.eq("is_banned", False).is_("bot_blocked_at", "null")

    # Apply language filter
    if request.filter_language:
        query = query.eq("language_code", request.filter_language)

    # Apply orders filter
    if request.filter_has_orders is True:
        # Get users with delivered orders
        orders_result = (
            await db.client.table("orders").select("user_id").eq("status", "delivered").execute()
        )
        user_ids_with_orders = list({o["user_id"] for o in (orders_result.data or [])})
        if user_ids_with_orders:
            query = query.in_("id", user_ids_with_orders)
        else:
            return []  # No users with orders
    elif request.filter_has_orders is False:
        # Get users without delivered orders
        orders_result = (
            await db.client.table("orders").select("user_id").eq("status", "delivered").execute()
        )
        user_ids_with_orders = list({o["user_id"] for o in (orders_result.data or [])})
        if user_ids_with_orders:
            query = query.not_.in_("id", user_ids_with_orders)

    # Apply bot-specific filter for discount bot
    if request.target_bot == "discount":
        query = query.eq("discount_tier_source", True)

    result = await query.execute()
    return result.data or []


# Helper: Get bot tokens for target (reduces cognitive complexity)
def _get_bot_tokens(target_bot: str) -> list[tuple[str, str]]:
    """Get list of (bot_name, token) tuples for target bot."""
    bot_tokens = []
    if target_bot in ("main", "all") and TELEGRAM_TOKEN:
        bot_tokens.append(("main", TELEGRAM_TOKEN))
    if target_bot in ("discount", "all") and DISCOUNT_BOT_TOKEN:
        bot_tokens.append(("discount", DISCOUNT_BOT_TOKEN))
    return bot_tokens


# Helper: Send messages to users with rate limiting (reduces cognitive complexity)
async def _send_broadcast_messages(
    target_users: list[dict],
    bot_tokens: list[tuple[str, str]],
    message: str,
    parse_mode: str | None,
) -> tuple[int, int, list[int]]:
    """Send messages to users, return (sent_count, failed_count, failed_user_ids)."""
    sent_count = 0
    failed_count = 0
    failed_user_ids = []

    for user in target_users:
        telegram_id = user.get("telegram_id")
        if not telegram_id:
            continue

        # Try each bot token
        message_sent = False
        for bot_name, bot_token in bot_tokens:
            success = await send_telegram_message(bot_token, telegram_id, message, parse_mode)
            if success:
                message_sent = True
                break  # Don't send via multiple bots

        if message_sent:
            sent_count += 1
        else:
            failed_count += 1
            failed_user_ids.append(telegram_id)

        # Rate limiting: ~20 messages per second
        if (sent_count + failed_count) % 20 == 0:
            await asyncio.sleep(1)

    return sent_count, failed_count, failed_user_ids


@router.post("", response_model=BroadcastResult)
async def send_broadcast(request: BroadcastRequest, admin_user=Depends(verify_admin)):
    """
    Send broadcast message to users.

    Parameters:
    - message: Text to send (supports HTML)
    - target_bot: 'main', 'discount', or 'all'
    - filter_language: Optional language filter (ru, en, etc)
    - filter_has_orders: Optional filter for users with orders
    - preview_only: If true, only return count without sending
    """
    db = get_database()

    target_users = await _get_target_users(db, request)
    target_count = len(target_users)

    # Preview mode - just return count
    if request.preview_only:
        return BroadcastResult(
            target_count=target_count,
            sent_count=0,
            failed_count=0,
            failed_user_ids=[],
            preview_only=True,
        )

    # Determine which bot tokens to use
    bot_tokens = _get_bot_tokens(request.target_bot)
    if not bot_tokens:
        raise HTTPException(
            status_code=400, detail=f"No bot token configured for target: {request.target_bot}"
        )

    # Send messages with rate limiting
    sent_count, failed_count, failed_user_ids = await _send_broadcast_messages(
        target_users, bot_tokens, request.message, request.parse_mode
    )

    logger.info(
        f"Broadcast completed: sent={sent_count}, failed={failed_count}, "
        f"target_bot={request.target_bot}, admin={admin_user.username if admin_user else 'unknown'}"
    )

    return BroadcastResult(
        target_count=target_count,
        sent_count=sent_count,
        failed_count=failed_count,
        failed_user_ids=failed_user_ids[:100],  # Limit to first 100 failed
        preview_only=False,
    )


@router.get("/stats")
async def get_broadcast_stats(admin_user=Depends(verify_admin)):
    """Get statistics for broadcast targeting."""
    db = get_database()

    # Total users
    total_result = await db.client.table("users").select("id", count="exact").execute()
    total_users = total_result.count or 0

    # Users by language
    lang_result = await db.client.table("users").select("language_code").execute()
    language_counts = {}
    for u in lang_result.data or []:
        lang = u.get("language_code") or "unknown"
        language_counts[lang] = language_counts.get(lang, 0) + 1

    # Users with orders
    orders_result = await db.client.table("orders").select("user_telegram_id").execute()
    unique_buyers = len(
        set(o["user_telegram_id"] for o in (orders_result.data or []) if o.get("user_telegram_id"))
    )

    # Bot availability
    bots_available = {"main": bool(TELEGRAM_TOKEN), "discount": bool(DISCOUNT_BOT_TOKEN)}

    return {
        "total_users": total_users,
        "users_with_orders": unique_buyers,
        "language_breakdown": language_counts,
        "bots_available": bots_available,
    }
