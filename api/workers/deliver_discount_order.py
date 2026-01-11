"""
Worker: Deliver Discount Order
Called by QStash after 1-4 hour delay.

This worker:
1. Validates the order is still paid
2. Delivers the stock item to user
3. Sends Telegram notification with offer for PVNDORA
"""
import os
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# ASGI app
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
    
    # In development, allow if no keys configured
    if not QSTASH_CURRENT_SIGNING_KEY and not QSTASH_NEXT_SIGNING_KEY:
        return True
    
    return False


async def send_telegram_message(chat_id: int, text: str, token: str = None) -> bool:
    """Send a message via Telegram Bot API.
    
    Wrapper around consolidated telegram_messaging service.
    """
    from core.services.telegram_messaging import send_telegram_message as _send_msg
    
    bot_token = token or DISCOUNT_BOT_TOKEN
    return await _send_msg(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        bot_token=bot_token
    )


@app.post("/api/workers/deliver-discount-order")
async def deliver_discount_order(request: Request):
    """
    Deliver a discount order after delay.
    
    Expected payload:
    {
        "order_id": "uuid",
        "order_item_id": "uuid",
        "telegram_id": 123456,
        "stock_item_id": "uuid",
        "scheduled_at": "2026-01-03T20:00:00Z"
    }
    """
    body = await request.body()
    
    # Verify signature
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
    
    # 1. Validate order status
    order_result = await db.client.table("orders").select("status").eq("id", order_id).single().execute()
    
    if not order_result.data:
        return JSONResponse({"error": "Order not found"}, status_code=404)
    
    if order_result.data["status"] != "paid":
        return JSONResponse({
            "error": f"Order status is {order_result.data['status']}, not paid",
            "skipped": True
        })
    
    # 2. Get stock item data
    stock_result = await db.client.table("stock_items").select(
        "id, product_id, content, products(name)"
    ).eq("id", stock_item_id).single().execute()
    
    if not stock_result.data:
        return JSONResponse({"error": "Stock item not found"}, status_code=404)
    
    stock_item = stock_result.data
    product_name = stock_item.get("products", {}).get("name", "Product") if isinstance(stock_item.get("products"), dict) else "Product"
    content = stock_item.get("content", "")
    
    # 3. Mark stock as sold and update order
    await db.client.table("stock_items").update({
        "status": "sold",
        "sold_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", stock_item_id).execute()
    
    await db.client.table("order_items").update({
        "stock_item_id": stock_item_id,
        "delivered_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", order_item_id).execute()
    
    await db.client.table("orders").update({
        "status": "delivered",
        "delivered_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", order_id).execute()
    
    # 4. Get user language and user_id
    user_result = await db.client.table("users").select("id, language_code").eq(
        "telegram_id", telegram_id
    ).single().execute()
    lang = user_result.data.get("language_code", "en") if user_result.data else "en"
    user_id = user_result.data.get("id") if user_result.data else None
    
    # 5. Send delivery message (structured format)
    if lang == "ru":
        delivery_text = (
            f"╔══════════════════════════════╗\n"
            f"     ✅ <b>ЗАКАЗ ДОСТАВЛЕН</b>\n"
            f"╚══════════════════════════════╝\n\n"
            f"📦 <b>Товар:</b> {product_name}\n"
            f"🔖 <b>Заказ:</b> <code>#{order_id[:8]}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔐 <b>ДАННЫЕ ДОСТУПА:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<code>{content[:500]}</code>"
            f"{'...(обрезано)' if len(content) > 500 else ''}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>СОХРАНИТЕ ЭТИ ДАННЫЕ!</b>\n\n"
            f"💬 Проблема? → /orders → выберите заказ"
        )
    else:
        delivery_text = (
            f"╔══════════════════════════════╗\n"
            f"      ✅ <b>ORDER DELIVERED</b>\n"
            f"╚══════════════════════════════╝\n\n"
            f"📦 <b>Product:</b> {product_name}\n"
            f"🔖 <b>Order:</b> <code>#{order_id[:8]}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔐 <b>ACCESS CREDENTIALS:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<code>{content[:500]}</code>"
            f"{'...(truncated)' if len(content) > 500 else ''}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>SAVE THIS DATA!</b>\n\n"
            f"💬 Problem? → /orders → select order"
        )
    
    await send_telegram_message(telegram_id, delivery_text)
    
    # 6. Get user purchase count for personalization
    user_orders_result = await db.client.table("orders").select("id", count="exact").eq(
        "user_telegram_id", telegram_id
    ).eq("source_channel", "discount").eq("status", "delivered").execute()
    purchase_count = user_orders_result.count if user_orders_result.count else 1
    
    # 7. Send personalized PVNDORA warm-up offer (delay for natural feel)
    await asyncio.sleep(10)
    
    # Progress to affiliate - in PVNDORA, first purchase unlocks affiliate
    if lang == "ru":
        # Personalized based on product and purchase count
        if purchase_count == 1:
            progress_text = (
                "🎯 <b>Это твоя первая покупка!</b>\n"
                "   В PVNDORA ты сразу получишь партнёрку\n"
                "   и сможешь зарабатывать 10% с друзей\n"
            )
        elif purchase_count < 3:
            remaining = 3 - purchase_count
            progress_text = (
                f"🎯 <b>Уже {purchase_count} покупок!</b>\n"
                f"   Ещё {remaining} — и персональная скидка 50%\n"
            )
        else:
            # User reached 3+ purchases - send loyal offer NOW (not via delayed cron)
            progress_text = (
                "🎯 <b>Ты наш постоянный клиент!</b>\n"
                "   Смотри ниже — там подарок!\n"
            )
        
        offer_text = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>ПОНРАВИЛСЯ {product_name.upper()}?</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{progress_text}\n"
            f"В <b>PVNDORA</b> такие товары:\n\n"
            f"⚡️ <b>Доставляются мгновенно</b>\n"
            f"   Не ждёшь 1-4 часа в очереди\n\n"
            f"🛡 <b>С полной гарантией</b>\n"
            f"   Проблема? Бесплатная замена\n\n"
            f"💰 <b>+ Партнёрка 10/7/3%</b>\n"
            f"   Пригласи друга — получи 10% с его покупок\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👉 <b>@pvndora_ai_bot</b>"
        )
    else:
        if purchase_count == 1:
            progress_text = (
                "🎯 <b>This is your first purchase!</b>\n"
                "   In PVNDORA you instantly get affiliate\n"
                "   and can earn 10% from friends' orders\n"
            )
        elif purchase_count < 3:
            remaining = 3 - purchase_count
            progress_text = (
                f"🎯 <b>Already {purchase_count} purchases!</b>\n"
                f"   {remaining} more — and personal 50% discount\n"
            )
        else:
            # User reached 3+ purchases - send loyal offer NOW (not via delayed cron)
            progress_text = (
                "🎯 <b>You're a loyal customer!</b>\n"
                "   Check below — there's a gift!\n"
            )
        
        offer_text = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>LIKED {product_name.upper()}?</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{progress_text}\n"
            f"In <b>PVNDORA</b> such products:\n\n"
            f"⚡️ <b>Delivered instantly</b>\n"
            f"   No 1-4 hour queue wait\n\n"
            f"🛡 <b>With full warranty</b>\n"
            f"   Problem? Free replacement\n\n"
            f"💰 <b>+ Affiliate 10/7/3%</b>\n"
            f"   Invite a friend — get 10% of their purchases\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👉 <b>@pvndora_ai_bot</b>"
        )
    
    await send_telegram_message(telegram_id, offer_text)
    
    # If user reached 3+ purchases, send loyal promo immediately (not via delayed cron)
    if purchase_count >= 3 and user_id:
        await _send_loyal_promo_if_eligible(user_id, telegram_id, lang, purchase_count)
    
    return JSONResponse({
        "success": True,
        "order_id": order_id,
        "telegram_id": telegram_id,
        "delivered_at": datetime.now(timezone.utc).isoformat()
    })


async def _send_loyal_promo_if_eligible(user_id: str, telegram_id: int, lang: str, purchase_count: int) -> bool:
    """Send loyal customer promo code immediately after 3rd purchase.
    
    Returns True if promo was sent, False otherwise.
    """
    from core.services.database import get_database_async
    from core.services.domains.promo import PromoCodeService, PromoTriggers
    
    db = await get_database_async()
    promo_service = PromoCodeService(db.client)
    
    try:
        # Check if already received loyal promo
        existing = await promo_service.get_promo_by_trigger(user_id, PromoTriggers.LOYAL_3_PURCHASES)
        if existing:
            return False  # Already has promo, skip
        
        # Generate personal promo code
        promo_code = await promo_service.generate_personal_promo(
            user_id=user_id,
            telegram_id=telegram_id,
            trigger=PromoTriggers.LOYAL_3_PURCHASES,
            discount_percent=50
        )
        
        if not promo_code:
            return False
        
        # Send promo message (to PVNDORA bot, not discount bot)
        text = (
            f"🎉 <b>Спасибо за доверие!</b>\n\n"
            f"Вы совершили {purchase_count} покупок — это круто!\n\n"
            f"В благодарность дарим вам <b>-50% на первую покупку</b> в PVNDORA:\n\n"
            f"🎁 <b>Промокод: {promo_code}</b>\n\n"
            f"В PVNDORA вас ждут:\n"
            f"• 🚀 Мгновенная доставка\n"
            f"• 🛡 Гарантии на все товары\n"
            f"• 💰 Партнерка 10/7/3%\n"
            f"• 🎧 Круглосуточная поддержка\n\n"
            f"👉 @pvndora_ai_bot"
        ) if lang == "ru" else (
            f"🎉 <b>Thank you for your loyalty!</b>\n\n"
            f"You've made {purchase_count} purchases — awesome!\n\n"
            f"As a thank you, we're giving you <b>-50% off your first purchase</b> in PVNDORA:\n\n"
            f"🎁 <b>Promo code: {promo_code}</b>\n\n"
            f"In PVNDORA you get:\n"
            f"• 🚀 Instant delivery\n"
            f"• 🛡 Warranty on all products\n"
            f"• 💰 Affiliate 10/7/3%\n"
            f"• 🎧 24/7 support\n\n"
            f"👉 @pvndora_ai_bot"
        )
        
        # Send to PVNDORA main bot (not discount bot)
        pvndora_token = TELEGRAM_TOKEN  # Main bot token
        await send_telegram_message(telegram_id, text, pvndora_token)
        
        return True
        
    except Exception as e:
        import logging
        logging.warning(f"Failed to send loyal promo to {telegram_id}: {e}")
        return False
