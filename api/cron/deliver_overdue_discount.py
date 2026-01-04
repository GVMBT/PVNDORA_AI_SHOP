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
            
            # Send delivery message
            delivery_text = (
                f"✅ <b>Заказ доставлен!</b>\n\n"
                f"Товар: {product_name}\n"
                f"Заказ: #{order_id[:8]}\n\n"
                f"<b>Данные доступа:</b>\n"
                f"<code>{content[:500]}</code>\n\n"
                f"{'...(обрезано)' if len(content) > 500 else ''}"
                f"\n\n⚠️ Сохраните эти данные!\n\n"
                f"Есть проблема? Нажмите «📦 Мои заказы» → выберите заказ → «Проблема»"
            ) if lang == "ru" else (
                f"✅ <b>Order Delivered!</b>\n\n"
                f"Product: {product_name}\n"
                f"Order: #{order_id[:8]}\n\n"
                f"<b>Access data:</b>\n"
                f"<code>{content[:500]}</code>\n\n"
                f"{'...(truncated)' if len(content) > 500 else ''}"
                f"\n\n⚠️ Save this data!\n\n"
                f"Have a problem? Click '📦 My Orders' → select order → 'Problem'"
            )
            
            await send_telegram_message(telegram_id, delivery_text)
            
            # Send PVNDORA offer
            await asyncio.sleep(2)
            offer_text = (
                "⭐ <b>Понравилось? Попробуй PVNDORA!</b>\n\n"
                "В PVNDORA ты получишь:\n"
                "• 🚀 Мгновенная доставка (без очереди!)\n"
                "• 🛡 Гарантии на все товары\n"
                "• 💰 Партнерка 10/7/3% — зарабатывай на рефералах\n"
                "• 🎧 Круглосуточная поддержка\n\n"
                "👉 @pvndora_ai_bot"
            ) if lang == "ru" else (
                "⭐ <b>Like it? Try PVNDORA!</b>\n\n"
                "In PVNDORA you get:\n"
                "• 🚀 Instant delivery (no queue!)\n"
                "• 🛡 Warranty on all products\n"
                "• 💰 Affiliate 10/7/3% — earn on referrals\n"
                "• 🎧 24/7 support\n\n"
                "👉 @pvndora_ai_bot"
            )
            await send_telegram_message(telegram_id, offer_text)
        
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
