"""Worker: Deliver Discount Order
Called by QStash after 1-4 hour delay.

This worker:
1. Validates the order is still paid
2. Delivers the stock item to user
3. Sends Telegram notification with offer for PVNDORA
"""

import asyncio
import os
from datetime import UTC, datetime
from typing import Any, cast

# Type alias for dict type hints
DictStrAny = dict[str, Any]

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger

logger = get_logger(__name__)

app = FastAPI()

QSTASH_CURRENT_SIGNING_KEY = os.environ.get("QSTASH_CURRENT_SIGNING_KEY", "")
QSTASH_NEXT_SIGNING_KEY = os.environ.get("QSTASH_NEXT_SIGNING_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", TELEGRAM_TOKEN)


def verify_qstash_signature(request: Request, body: bytes) -> bool:
    """Verify QStash request signature."""
    import hashlib
    import hmac

    signature = request.headers.get("Upstash-Signature", "")
    if not signature:
        return False

    for key in [QSTASH_CURRENT_SIGNING_KEY, QSTASH_NEXT_SIGNING_KEY]:
        if not key:
            continue
        expected = hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected):
            return True

    return bool(not QSTASH_CURRENT_SIGNING_KEY and not QSTASH_NEXT_SIGNING_KEY)


async def send_telegram_message(chat_id: int, text: str, token: str | None = None) -> bool:
    """Send a message via Telegram Bot API."""
    from core.services.telegram_messaging import send_telegram_message as _send_msg

    bot_token = token or DISCOUNT_BOT_TOKEN
    return await _send_msg(chat_id=chat_id, text=text, parse_mode="HTML", bot_token=bot_token)


async def _validate_order(db: Any, order_id: str) -> str | None:
    """Validate order exists and is paid. Returns status or None if not found."""
    order_result = (
        await db.client.table("orders").select("status").eq("id", order_id).single().execute()
    )
    if not order_result.data or not isinstance(order_result.data, dict):
        return None
    status = cast(DictStrAny, order_result.data).get("status")
    return str(status) if status is not None else None


async def _get_stock_item(db: Any, stock_item_id: str) -> tuple[str, str] | None:
    """Get stock item content and product name. Returns (content, product_name) or None."""
    stock_result = (
        await db.client.table("stock_items")
        .select("id, product_id, content, products(name)")
        .eq("id", stock_item_id)
        .single()
        .execute()
    )
    if not stock_result.data or not isinstance(stock_result.data, dict):
        return None
    stock_item = cast(dict[str, Any], stock_result.data)
    product_name = (
        stock_item.get("products", {}).get("name", "Product")
        if isinstance(stock_item.get("products"), dict)
        else "Product"
    )
    return stock_item.get("content", ""), product_name


async def _mark_order_delivered(
    db: Any,
    order_id: str,
    order_item_id: str,
    stock_item_id: str,
) -> None:
    """Mark stock as sold and order as delivered."""
    now_iso = datetime.now(UTC).isoformat()
    await (
        db.client.table("stock_items")
        .update({"status": "sold", "sold_at": now_iso})
        .eq("id", stock_item_id)
        .execute()
    )
    await (
        db.client.table("order_items")
        .update({"stock_item_id": stock_item_id, "delivered_at": now_iso})
        .eq("id", order_item_id)
        .execute()
    )
    await (
        db.client.table("orders")
        .update({"status": "delivered", "delivered_at": now_iso})
        .eq("id", order_id)
        .execute()
    )


async def _get_user_info(db: Any, telegram_id: int) -> tuple[str | None, str]:
    """Get user_id and language. Returns (user_id, lang)."""
    user_result = (
        await db.client.table("users")
        .select("id, language_code")
        .eq("telegram_id", telegram_id)
        .single()
        .execute()
    )
    if user_result.data and isinstance(user_result.data, dict):
        user_data = cast(dict[str, Any], user_result.data)
        return user_data.get("id"), user_data.get("language_code", "en")
    return None, "en"


def _format_delivery_message(lang: str, product_name: str, order_id: str, content: str) -> str:
    """Format delivery notification message."""
    truncated = content[:500] + ("...(truncated)" if len(content) > 500 else "")
    if lang == "ru":
        return (
            f"╔══════════════════════════════╗\n"
            f"     ✅ <b>ЗАКАЗ ДОСТАВЛЕН</b>\n"
            f"╚══════════════════════════════╝\n\n"
            f"📦 <b>Товар:</b> {product_name}\n"
            f"🔖 <b>Заказ:</b> <code>#{order_id[:8]}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔐 <b>ДАННЫЕ ДОСТУПА:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<code>{truncated}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>СОХРАНИТЕ ЭТИ ДАННЫЕ!</b>\n\n"
            f"💬 Проблема? → /orders → выберите заказ"
        )
    return (
        f"╔══════════════════════════════╗\n"
        f"      ✅ <b>ORDER DELIVERED</b>\n"
        f"╚══════════════════════════════╝\n\n"
        f"📦 <b>Product:</b> {product_name}\n"
        f"🔖 <b>Order:</b> <code>#{order_id[:8]}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔐 <b>ACCESS CREDENTIALS:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<code>{truncated}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>SAVE THIS DATA!</b>\n\n"
        f"💬 Problem? → /orders → select order"
    )


def _get_progress_text(lang: str, purchase_count: int) -> str:
    """Get personalized progress text based on purchase count."""
    if lang == "ru":
        if purchase_count == 1:
            return "🎯 <b>Это твоя первая покупка!</b>\n   В PVNDORA ты сразу получишь партнёрку\n"
        if purchase_count < 3:
            return f"🎯 <b>Уже {purchase_count} покупок!</b>\n   Ещё {3 - purchase_count} — и персональная скидка 50%\n"
        return "🎯 <b>Ты наш постоянный клиент!</b>\n   Смотри ниже — там подарок!\n"
    if purchase_count == 1:
        return "🎯 <b>This is your first purchase!</b>\n   In PVNDORA you instantly get affiliate\n"
    if purchase_count < 3:
        return f"🎯 <b>Already {purchase_count} purchases!</b>\n   {3 - purchase_count} more — and personal 50% discount\n"
    return "🎯 <b>You're a loyal customer!</b>\n   Check below — there's a gift!\n"


def _format_offer_message(lang: str, product_name: str, progress_text: str) -> str:
    """Format PVNDORA offer message."""
    if lang == "ru":
        return (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>ПОНРАВИЛСЯ {product_name.upper()}?</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{progress_text}\n"
            f"В <b>PVNDORA</b> такие товары:\n\n"
            f"⚡️ <b>Доставляются мгновенно</b>\n   Не ждёшь 1-4 часа в очереди\n\n"
            f"🛡 <b>С полной гарантией</b>\n   Проблема? Бесплатная замена\n\n"
            f"💰 <b>+ Партнёрка 10/7/3%</b>\n   Пригласи друга — получи 10% с его покупок\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👉 <b>@pvndora_ai_bot</b>"
        )
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>LIKED {product_name.upper()}?</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{progress_text}\n"
        f"In <b>PVNDORA</b> such products:\n\n"
        f"⚡️ <b>Delivered instantly</b>\n   No 1-4 hour queue wait\n\n"
        f"🛡 <b>With full warranty</b>\n   Problem? Free replacement\n\n"
        f"💰 <b>+ Affiliate 10/7/3%</b>\n   Invite a friend — get 10% of their purchases\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👉 <b>@pvndora_ai_bot</b>"
    )


async def _get_purchase_count(db: Any, telegram_id: int) -> int:
    """Get user's delivered discount order count."""
    result = (
        await db.client.table("orders")
        .select("id", count="exact")
        .eq("user_telegram_id", telegram_id)
        .eq("source_channel", "discount")
        .eq("status", "delivered")
        .execute()
    )
    return result.count if result.count else 1


async def _send_loyal_promo_if_eligible(
    user_id: str,
    telegram_id: int,
    lang: str,
    purchase_count: int,
) -> bool:
    """Send loyal customer promo code immediately after 3rd purchase."""
    from core.services.database import get_database_async
    from core.services.domains.promo import PromoCodeService, PromoTriggers

    db = await get_database_async()
    promo_service = PromoCodeService(db.client)

    try:
        existing = await promo_service.get_promo_by_trigger(
            user_id,
            PromoTriggers.LOYAL_3_PURCHASES,
        )
        if existing:
            return False

        promo_code = await promo_service.generate_personal_promo(
            user_id=user_id,
            telegram_id=telegram_id,
            trigger=PromoTriggers.LOYAL_3_PURCHASES,
            discount_percent=50,
            expiration_days=7,
        )
        if not promo_code:
            return False

        await asyncio.sleep(5)

        if lang == "ru":
            loyal_msg = (
                f"🎁 <b>ПЕРСОНАЛЬНЫЙ ПОДАРОК</b>\n\n"
                f"Ты сделал {purchase_count} покупок — это круто!\n"
                f"Держи промокод на <b>50% скидку</b>:\n\n"
                f"<code>{promo_code}</code>\n\n"
                f"⏰ Действует 7 дней\n👉 @pvndora_ai_bot"
            )
        else:
            loyal_msg = (
                f"🎁 <b>PERSONAL GIFT</b>\n\n"
                f"You made {purchase_count} purchases — that's awesome!\n"
                f"Here's a promo code for <b>50% discount</b>:\n\n"
                f"<code>{promo_code}</code>\n\n"
                f"⏰ Valid for 7 days\n👉 @pvndora_ai_bot"
            )

        await send_telegram_message(telegram_id, loyal_msg, token=TELEGRAM_TOKEN)
        return True

    except Exception:
        logger.exception("Failed to send loyal promo")
        return False


@app.post("/api/workers/deliver-discount-order")
async def deliver_discount_order(request: Request) -> JSONResponse:
    """Deliver a discount order after delay."""
    body = await request.body()
    if not verify_qstash_signature(request, body):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        import json

        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    order_id = payload.get("order_id")
    order_item_id = payload.get("order_item_id")
    telegram_id = payload.get("telegram_id")
    stock_item_id = payload.get("stock_item_id")

    if not all([order_id, order_item_id, telegram_id, stock_item_id]):
        return JSONResponse({"error": "Missing required fields"}, status_code=400)

    from core.services.database import get_database_async

    db = await get_database_async()

    # 1. Validate order
    order_status = await _validate_order(db, order_id)
    if not order_status:
        return JSONResponse({"error": "Order not found"}, status_code=404)
    if order_status != "paid":
        return JSONResponse({"error": f"Order status is {order_status}, not paid", "skipped": True})

    # 2. Get stock item
    stock_info = await _get_stock_item(db, stock_item_id)
    if not stock_info:
        return JSONResponse({"error": "Stock item not found"}, status_code=404)
    content, product_name = stock_info

    # 3. Mark as delivered
    await _mark_order_delivered(db, order_id, order_item_id, stock_item_id)

    # 4. Get user info
    user_id, lang = await _get_user_info(db, telegram_id)

    # 5. Send delivery notification
    delivery_msg = _format_delivery_message(lang, product_name, order_id, content)
    await send_telegram_message(telegram_id, delivery_msg)

    # 6. Get purchase count and send offer
    purchase_count = await _get_purchase_count(db, telegram_id)
    await asyncio.sleep(10)

    progress_text = _get_progress_text(lang, purchase_count)
    offer_msg = _format_offer_message(lang, product_name, progress_text)
    await send_telegram_message(telegram_id, offer_msg)

    # 7. Send loyal promo if eligible
    if purchase_count >= 3 and user_id:
        await _send_loyal_promo_if_eligible(user_id, telegram_id, lang, purchase_count)

    return JSONResponse(
        {
            "success": True,
            "order_id": order_id,
            "telegram_id": telegram_id,
            "delivered_at": datetime.now(UTC).isoformat(),
        },
    )
