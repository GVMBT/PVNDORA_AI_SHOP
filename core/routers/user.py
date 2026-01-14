"""
User API Router

User-specific endpoints (referral, wishlist, reviews).
These are non-webapp endpoints with /api prefix.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import urllib.parse
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import verify_telegram_auth
from core.logging import get_logger
from core.routers.deps import get_bot, get_webapp_url
from core.services.database import get_database

logger = get_logger(__name__)

# Error message constants
ERR_USER_NOT_FOUND = "User not found"

router = APIRouter(prefix="/api", tags=["user"])


class SubmitReviewRequest(BaseModel):
    order_id: str
    rating: int
    text: str | None = None


# ==================== REFERRAL ====================


@router.get("/user/referral")
async def get_referral_info(user=Depends(verify_telegram_auth)):
    """Get referral link and stats"""
    bot_instance = get_bot()

    if not bot_instance:
        raise HTTPException(status_code=500, detail="Bot not configured")

    bot_info = await bot_instance.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"

    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    return {
        "link": referral_link,
        "percent": db_user.personal_ref_percent if db_user else 20,
        "balance": db_user.balance if db_user else 0,
    }


# Helper to calculate user rank (reduces cognitive complexity)
async def _calculate_user_rank(db, total_saved: int) -> int | None:
    """Calculate user's leaderboard rank."""
    if total_saved <= 0:
        return None
    rank_result = (
        await db.client.table("users")
        .select("id", count="exact")
        .gt("total_saved", total_saved)
        .execute()
    )
    return (rank_result.count or 0) + 1


# Helper to get avatar URL (reduces cognitive complexity)
def _get_avatar_url(user, display_name: str) -> str:
    """Get user avatar URL or generate initials avatar."""
    avatar_url = getattr(user, "photo_url", None)
    if avatar_url:
        return str(avatar_url)
    initials_seed = urllib.parse.quote(display_name)
    return f"https://api.dicebear.com/7.x/initials/png?seed={initials_seed}&backgroundColor=1f1f2e,4c1d95&fontWeight=700"


# Helper to get localized texts (reduces cognitive complexity)
def _get_localized_texts(language_code: str) -> tuple[str, str]:
    """Get localized caption and button texts."""
    if language_code == "ru":
        return "Экономлю на AI-подписках с PVNDORA", "🎁 Попробовать"
    return "Saving on AI subscriptions with PVNDORA", "🎁 Try it"


@router.post("/webapp/referral/share-link")
async def create_referral_share_link(user=Depends(verify_telegram_auth)):
    """
    Create a prepared inline message for sharing.
    Returns prepared_message_id to be used with Telegram.WebApp.shareMessage()
    """
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultPhoto

    bot_instance = get_bot()
    if not bot_instance:
        raise HTTPException(status_code=500, detail="Bot not configured")

    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail=ERR_USER_NOT_FOUND)

    total_saved = (
        int(float(db_user.total_saved))
        if hasattr(db_user, "total_saved") and db_user.total_saved
        else 0
    )
    display_name = db_user.first_name or db_user.username or "User"

    user_rank = await _calculate_user_rank(db, total_saved)

    bot_info = await bot_instance.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"

    webapp_url = get_webapp_url()
    timestamp = int(datetime.now(UTC).timestamp())
    avatar_url = _get_avatar_url(user, display_name)

    query_params = {
        "name": display_name,
        "saved": total_saved,
        "lang": db_user.language_code or "ru",
        "avatar": avatar_url,
        "t": timestamp,
        "handle": f"@{bot_info.username}",
    }
    if user_rank:
        query_params["rank"] = user_rank

    query_string = urllib.parse.urlencode(query_params, doseq=False)
    photo_url = f"{webapp_url}/og/referral?{query_string}"

    result_id = f"share_{user.id}_{timestamp}"
    caption_text, button_text = _get_localized_texts(db_user.language_code or "ru")

    photo = InlineQueryResultPhoto(
        id=result_id,
        photo_url=photo_url,
        thumbnail_url=photo_url,
        title="🎁 PVNDORA AI",
        description=caption_text,
        caption=caption_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=button_text, url=ref_link)]]
        ),
    )

    try:
        prepared_message = await bot_instance.save_prepared_inline_message(
            user_id=user.id,
            result=photo,
            allow_user_chats=True,
            allow_group_chats=True,
            allow_channel_chats=True,
        )
        return {"prepared_message_id": prepared_message.id}
    except Exception as e:
        error_msg = str(e)

        if "object has no attribute 'save_prepared_inline_message'" in error_msg:
            raise HTTPException(
                status_code=501, detail="Feature not supported by bot backend version"
            )

        # Check if it's a Telegram API error
        if "Bad Request" in error_msg or "400" in error_msg:
            raise HTTPException(status_code=400, detail=f"Telegram API error: {error_msg}")

        raise HTTPException(status_code=500, detail=f"Failed to save prepared message: {error_msg}")


# ==================== WISHLIST ====================


@router.get("/wishlist")
async def get_wishlist(user=Depends(verify_telegram_auth)):
    """Get user's wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user:
        raise HTTPException(status_code=404, detail=ERR_USER_NOT_FOUND)

    products = await db.get_wishlist(db_user.id)
    return [
        {"id": p.id, "name": p.name, "price": p.price, "stock_count": p.stock_count}
        for p in products
    ]


@router.post("/wishlist/{product_id}")
async def add_to_wishlist(product_id: str, user=Depends(verify_telegram_auth)):
    """Add product to wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user:
        raise HTTPException(status_code=404, detail=ERR_USER_NOT_FOUND)

    await db.add_to_wishlist(db_user.id, product_id)
    return {"success": True}


@router.delete("/wishlist/{product_id}")
async def remove_from_wishlist(product_id: str, user=Depends(verify_telegram_auth)):
    """Remove product from wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user:
        raise HTTPException(status_code=404, detail=ERR_USER_NOT_FOUND)

    await db.remove_from_wishlist(db_user.id, product_id)
    return {"success": True}


# ==================== REVIEWS ====================


@router.post("/reviews")
async def submit_review(request: SubmitReviewRequest, user=Depends(verify_telegram_auth)):
    """Submit product review with 5% cashback via QStash worker"""
    from core.services.money import to_float

    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail=ERR_USER_NOT_FOUND)

    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.status not in ["delivered", "partial"]:
        raise HTTPException(status_code=400, detail="Order not completed")

    existing = (
        await db.client.table("reviews").select("id").eq("order_id", request.order_id).execute()
    )
    if existing.data:
        raise HTTPException(status_code=400, detail="Review already submitted")

    # Get product_id from order_items (source of truth)
    order_items = await db.get_order_items_by_order(request.order_id)
    product_id = order_items[0].get("product_id") if order_items else None

    await db.create_review(
        user_id=db_user.id,
        order_id=request.order_id,
        product_id=product_id,
        rating=request.rating,
        text=request.text,
    )

    # Trigger QStash worker for cashback (creates balance_transaction + sends notification)
    cashback = to_float(order.amount) * 0.05
    try:
        from core.queue import WorkerEndpoints, publish_to_worker

        await publish_to_worker(
            endpoint=WorkerEndpoints.PROCESS_REVIEW_CASHBACK,
            body={
                "user_telegram_id": db_user.telegram_id,
                "order_id": request.order_id,
                "order_amount": to_float(order.amount),
            },
        )
    except Exception as e:
        # Fallback: direct cashback if QStash fails
        import logging

        logging.warning(f"QStash failed for review cashback: {e}")
        await db.update_user_balance(db_user.id, cashback)
        await (
            db.client.table("reviews")
            .update({"cashback_given": True})
            .eq("order_id", request.order_id)
            .execute()
        )
        await (
            db.client.table("balance_transactions")
            .insert(
                {
                    "user_id": db_user.id,
                    "type": "cashback",
                    "amount": cashback,
                    "status": "completed",
                    "description": "5% кэшбек за отзыв",
                    "reference_id": request.order_id,
                }
            )
            .execute()
        )

    return {
        "success": True,
        "cashback_pending": cashback,
        "message": "Кэшбек будет начислен в течение минуты",
    }
