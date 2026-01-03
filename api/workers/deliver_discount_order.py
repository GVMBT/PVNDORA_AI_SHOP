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
import httpx

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
    """Send a message via Telegram Bot API."""
    bot_token = token or DISCOUNT_BOT_TOKEN
    if not bot_token:
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
            return response.status_code == 200
    except Exception:
        return False


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
    
    from core.services.database import get_database
    
    db = get_database()
    
    # 1. Validate order status
    order_result = await asyncio.to_thread(
        lambda: db.client.table("orders").select("status").eq("id", order_id).single().execute()
    )
    
    if not order_result.data:
        return JSONResponse({"error": "Order not found"}, status_code=404)
    
    if order_result.data["status"] != "paid":
        return JSONResponse({
            "error": f"Order status is {order_result.data['status']}, not paid",
            "skipped": True
        })
    
    # 2. Get stock item data
    stock_result = await asyncio.to_thread(
        lambda: db.client.table("stock_items").select(
            "id, product_id, content, products(name)"
        ).eq("id", stock_item_id).single().execute()
    )
    
    if not stock_result.data:
        return JSONResponse({"error": "Stock item not found"}, status_code=404)
    
    stock_item = stock_result.data
    product_name = stock_item.get("products", {}).get("name", "Product") if isinstance(stock_item.get("products"), dict) else "Product"
    content = stock_item.get("content", "")
    
    # 3. Mark stock as sold and update order
    await asyncio.to_thread(
        lambda: db.client.table("stock_items").update({
            "status": "sold",
            "sold_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", stock_item_id).execute()
    )
    
    await asyncio.to_thread(
        lambda: db.client.table("order_items").update({
            "stock_item_id": stock_item_id,
            "delivered_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", order_item_id).execute()
    )
    
    await asyncio.to_thread(
        lambda: db.client.table("orders").update({
            "status": "delivered",
            "delivered_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", order_id).execute()
    )
    
    # 4. Get user language
    user_result = await asyncio.to_thread(
        lambda: db.client.table("users").select("language_code").eq(
            "telegram_id", telegram_id
        ).single().execute()
    )
    lang = user_result.data.get("language_code", "en") if user_result.data else "en"
    
    # 5. Send delivery message
    delivery_text = (
        f"✅ <b>Заказ доставлен!</b>\n\n"
        f"Товар: {product_name}\n"
        f"Заказ: #{order_id[:8]}\n\n"
        f"<b>Данные доступа:</b>\n"
        f"<code>{content[:500]}</code>\n\n"
        f"{'...(обрезано)' if len(content) > 500 else ''}\n\n"
        f"⚠️ Сохраните эти данные!\n\n"
        f"Есть проблема? Нажмите «📦 Мои заказы» → выберите заказ → «Проблема»"
    ) if lang == "ru" else (
        f"✅ <b>Order Delivered!</b>\n\n"
        f"Product: {product_name}\n"
        f"Order: #{order_id[:8]}\n\n"
        f"<b>Access data:</b>\n"
        f"<code>{content[:500]}</code>\n\n"
        f"{'...(truncated)' if len(content) > 500 else ''}\n\n"
        f"⚠️ Save this data!\n\n"
        f"Have a problem? Click '📦 My Orders' → select order → 'Problem'"
    )
    
    await send_telegram_message(telegram_id, delivery_text)
    
    # 6. Send PVNDORA offer (after a short delay conceptually, but inline here)
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
    
    # Small delay before promo
    await asyncio.sleep(2)
    await send_telegram_message(telegram_id, offer_text)
    
    return JSONResponse({
        "success": True,
        "order_id": order_id,
        "telegram_id": telegram_id,
        "delivered_at": datetime.now(timezone.utc).isoformat()
    })
