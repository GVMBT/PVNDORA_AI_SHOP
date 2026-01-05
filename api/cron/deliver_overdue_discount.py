"""
Cron: Deliver Overdue Discount Orders

Fallback for QStash - if scheduled_delivery_at has passed
but order is still 'paid', deliver it.

Runs every 5 minutes.
"""
import os
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx

from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)

CRON_SECRET = os.environ.get("CRON_SECRET", "")
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

app = FastAPI()


async def send_telegram_message(chat_id: int, text: str) -> bool:
    """Send a message via Telegram Bot API."""
    bot_token = DISCOUNT_BOT_TOKEN or TELEGRAM_TOKEN
    if not bot_token:
        logger.warning("No bot token configured for sending message")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False


async def deliver_discount_order(db, order_id: str, order_data: dict):
    """Actually deliver a discount order."""
    try:
        telegram_id = order_data.get("user_telegram_id")
        
        # Get order items
        order_items = await asyncio.to_thread(
            lambda: db.client.table("order_items").select(
                "id, product_id, stock_item_id"
            ).eq("order_id", order_id).execute()
        )
        
        if not order_items.data:
            logger.warning(f"No order items for order {order_id}")
            return False
        
        for item in order_items.data:
            order_item_id = item["id"]
            product_id = item["product_id"]
            stock_item_id = item.get("stock_item_id")
            
            # If no stock assigned, find one
            if not stock_item_id:
                stock_result = await asyncio.to_thread(
                    lambda: db.client.table("stock_items").select("id").eq(
                        "product_id", product_id
                    ).in_("status", ["available", "reserved"]).limit(1).execute()
                )
                
                if not stock_result.data:
                    logger.warning(f"No stock available for order {order_id}, product {product_id}")
                    continue
                
                stock_item_id = stock_result.data[0]["id"]
            
            # Get stock item content
            stock_item = await asyncio.to_thread(
                lambda: db.client.table("stock_items").select(
                    "content, products(name)"
                ).eq("id", stock_item_id).single().execute()
            )
            
            if not stock_item.data:
                logger.warning(f"Stock item {stock_item_id} not found")
                continue
            
            content = stock_item.data.get("content", "")
            product_name = stock_item.data.get("products", {}).get("name", "Product") if isinstance(stock_item.data.get("products"), dict) else "Product"
            
            # Mark stock as sold
            await asyncio.to_thread(
                lambda: db.client.table("stock_items").update({
                    "status": "sold",
                    "sold_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", stock_item_id).execute()
            )
            
            # Update order item
            await asyncio.to_thread(
                lambda: db.client.table("order_items").update({
                    "stock_item_id": stock_item_id,
                    "delivered_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", order_item_id).execute()
            )
            
            # Get user language
            user_result = await asyncio.to_thread(
                lambda: db.client.table("users").select("language_code").eq(
                    "telegram_id", telegram_id
                ).single().execute()
            )
            lang = user_result.data.get("language_code", "en") if user_result.data else "en"
            
            # Send delivery message (structured format)
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
            
            # Get user purchase count for personalization
            user_orders_result = await asyncio.to_thread(
                lambda: db.client.table("orders").select("id", count="exact").eq(
                    "user_telegram_id", telegram_id
                ).eq("source_channel", "discount").eq("status", "delivered").execute()
            )
            purchase_count = user_orders_result.count if user_orders_result.count else 1
            
            # Send personalized PVNDORA warm-up offer
            await asyncio.sleep(10)
            
            if lang == "ru":
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
                    # Loyal customer - promo will be sent below
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
                    # Loyal customer - promo will be sent below
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
            
            # If user reached 3+ purchases, send loyal promo immediately
            if purchase_count >= 3:
                await _send_loyal_promo_if_eligible(user_id, telegram_id, lang, purchase_count)
        
        # Update order status
        await asyncio.to_thread(
            lambda: db.client.table("orders").update({
                "status": "delivered",
                "delivered_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", order_id).execute()
        )
        
        logger.info(f"Discount order {order_id} delivered successfully via cron fallback")
        return True
        
    except Exception as e:
        logger.error(f"Failed to deliver discount order {order_id}: {e}")
        return False


async def _send_loyal_promo_if_eligible(user_id: str, telegram_id: int, lang: str, purchase_count: int) -> bool:
    """Send loyal customer promo code immediately after 3rd purchase.
    
    Returns True if promo was sent, False otherwise.
    """
    from core.services.domains.promo import get_promo_service, PromoTriggers
    
    db = get_database()
    promo_service = get_promo_service(db.client)
    
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
        
        # Send promo message to PVNDORA main bot
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
        
        # Use main bot token for PVNDORA messages
        import httpx
        bot_token = TELEGRAM_TOKEN
        if not bot_token:
            logger.warning("No TELEGRAM_TOKEN configured for loyal promo")
            return False
            
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": telegram_id, "text": text, "parse_mode": "HTML"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            return response.status_code == 200
        
    except Exception as e:
        logger.warning(f"Failed to send loyal promo to {telegram_id}: {e}")
        return False


@app.get("/api/cron/deliver_overdue_discount")
async def deliver_overdue_discount(request: Request):
    """
    Find and deliver discount orders where:
    - status = 'paid'
    - source_channel = 'discount'
    - scheduled_delivery_at has passed
    
    This is a fallback for when QStash doesn't deliver.
    """
    # Verify cron auth
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    try:
        db = get_database()
        
        # Get paid discount orders with overdue delivery
        now = datetime.now(timezone.utc).isoformat()
        
        result = await asyncio.to_thread(
            lambda: db.client.table("orders")
            .select("id, user_telegram_id, source_channel, scheduled_delivery_at")
            .eq("status", "paid")
            .eq("source_channel", "discount")
            .lte("scheduled_delivery_at", now)  # scheduled time has passed
            .limit(10)
            .execute()
        )
        
        overdue_orders = result.data or []
        
        if not overdue_orders:
            logger.info("No overdue discount orders to deliver")
            return JSONResponse({"ok": True, "delivered": 0})
        
        logger.info(f"Found {len(overdue_orders)} overdue discount orders to deliver")
        
        delivered_count = 0
        
        for order in overdue_orders:
            order_id = order["id"]
            success = await deliver_discount_order(db, order_id, order)
            if success:
                delivered_count += 1
        
        return JSONResponse({
            "ok": True,
            "checked": len(overdue_orders),
            "delivered": delivered_count
        })
        
    except Exception as e:
        logger.error(f"deliver_overdue_discount error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
