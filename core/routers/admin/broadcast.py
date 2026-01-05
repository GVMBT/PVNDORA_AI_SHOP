"""
Admin Broadcast Router

Allows admin to send messages to all users via Telegram bots.
"""
import os
import asyncio
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import httpx

from core.services.database import get_database
from core.auth import verify_admin
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/broadcast", tags=["admin-broadcast"])

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")


class BroadcastRequest(BaseModel):
    """Request model for broadcast message."""
    message: str = Field(..., min_length=1, max_length=4096)
    target_bot: str = Field(default="main", description="Target bot: 'main', 'discount', or 'all'")
    filter_language: Optional[str] = Field(None, description="Filter users by language_code (ru, en, etc)")
    filter_has_orders: Optional[bool] = Field(None, description="Filter users who have made orders")
    preview_only: bool = Field(default=False, description="If true, only return count of target users")
    parse_mode: str = Field(default="HTML", description="Telegram parse mode: HTML or Markdown")


class BroadcastResult(BaseModel):
    """Result of broadcast operation."""
    target_count: int
    sent_count: int
    failed_count: int
    failed_user_ids: List[int]
    preview_only: bool


async def send_telegram_message(
    bot_token: str, 
    chat_id: int, 
    text: str, 
    parse_mode: str = "HTML"
) -> bool:
    """Send a single message via Telegram Bot API."""
    if not bot_token:
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Telegram API error for {chat_id}: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")
        return False


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
    
    # Build query for target users
    query = db.client.table("users").select("telegram_id, language_code")
    
    # Apply language filter
    if request.filter_language:
        query = query.eq("language_code", request.filter_language)
    
    # Apply orders filter
    if request.filter_has_orders is True:
        # Get users who have at least one order
        orders_result = await asyncio.to_thread(
            lambda: db.client.table("orders")
            .select("user_telegram_id")
            .execute()
        )
        user_telegram_ids_with_orders = set(
            o["user_telegram_id"] for o in (orders_result.data or []) if o.get("user_telegram_id")
        )
        
        # Fetch all users and filter in Python
        all_users_result = await asyncio.to_thread(lambda: query.execute())
        target_users = [
            u for u in (all_users_result.data or [])
            if u.get("telegram_id") in user_telegram_ids_with_orders
        ]
    else:
        result = await asyncio.to_thread(lambda: query.execute())
        target_users = result.data or []
    
    target_count = len(target_users)
    
    # Preview mode - just return count
    if request.preview_only:
        return BroadcastResult(
            target_count=target_count,
            sent_count=0,
            failed_count=0,
            failed_user_ids=[],
            preview_only=True
        )
    
    # Determine which bot tokens to use
    bot_tokens = []
    if request.target_bot in ("main", "all") and TELEGRAM_TOKEN:
        bot_tokens.append(("main", TELEGRAM_TOKEN))
    if request.target_bot in ("discount", "all") and DISCOUNT_BOT_TOKEN:
        bot_tokens.append(("discount", DISCOUNT_BOT_TOKEN))
    
    if not bot_tokens:
        raise HTTPException(
            status_code=400, 
            detail=f"No bot token configured for target: {request.target_bot}"
        )
    
    sent_count = 0
    failed_count = 0
    failed_user_ids = []
    
    # Send messages with rate limiting (30 messages per second max)
    for user in target_users:
        telegram_id = user.get("telegram_id")
        if not telegram_id:
            continue
        
        # Try each bot token
        message_sent = False
        for bot_name, bot_token in bot_tokens:
            success = await send_telegram_message(
                bot_token, telegram_id, request.message, request.parse_mode
            )
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
    
    logger.info(
        f"Broadcast completed: sent={sent_count}, failed={failed_count}, "
        f"target_bot={request.target_bot}, admin={admin_user.username if admin_user else 'unknown'}"
    )
    
    return BroadcastResult(
        target_count=target_count,
        sent_count=sent_count,
        failed_count=failed_count,
        failed_user_ids=failed_user_ids[:100],  # Limit to first 100 failed
        preview_only=False
    )


@router.get("/stats")
async def get_broadcast_stats(admin_user=Depends(verify_admin)):
    """Get statistics for broadcast targeting."""
    db = get_database()
    
    # Total users
    total_result = await asyncio.to_thread(
        lambda: db.client.table("users").select("id", count="exact").execute()
    )
    total_users = total_result.count or 0
    
    # Users by language
    lang_result = await asyncio.to_thread(
        lambda: db.client.table("users").select("language_code").execute()
    )
    language_counts = {}
    for u in (lang_result.data or []):
        lang = u.get("language_code") or "unknown"
        language_counts[lang] = language_counts.get(lang, 0) + 1
    
    # Users with orders
    orders_result = await asyncio.to_thread(
        lambda: db.client.table("orders")
        .select("user_telegram_id")
        .execute()
    )
    unique_buyers = len(set(
        o["user_telegram_id"] for o in (orders_result.data or []) if o.get("user_telegram_id")
    ))
    
    # Bot availability
    bots_available = {
        "main": bool(TELEGRAM_TOKEN),
        "discount": bool(DISCOUNT_BOT_TOKEN)
    }
    
    return {
        "total_users": total_users,
        "users_with_orders": unique_buyers,
        "language_breakdown": language_counts,
        "bots_available": bots_available
    }
