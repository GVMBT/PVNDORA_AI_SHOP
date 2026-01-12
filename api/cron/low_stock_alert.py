"""
Low Stock Alert Cron Job
Schedule: */30 * * * * (every 30 minutes)

Tasks:
1. Check for products with low stock (<5 items)
2. Send Telegram notification to admin(s)
3. Deduplicate alerts - only send once per product until restocked

Uses Redis to track alerted products. Alert cooldown:
- Out of stock (0 items): Alert once, then cooldown 6 hours
- Critical (1-2 items): Alert once, then cooldown 4 hours
- Low (3-5 items): Alert once, then cooldown 2 hours
"""

import os
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Verify cron secret to prevent unauthorized access
CRON_SECRET = os.environ.get("CRON_SECRET", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_CHAT_IDS = os.environ.get("ADMIN_CHAT_IDS", "").split(",")  # Comma-separated list

# Redis for deduplication
UPSTASH_REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

# Alert cooldowns in seconds based on stock level
ALERT_COOLDOWNS = {
    "prepaid_only": 6 * 60 * 60,  # 6 hours for out of stock
    "critical": 4 * 60 * 60,  # 4 hours for critical (1-2 items)
    "low": 2 * 60 * 60,  # 2 hours for low (3-5 items)
}

# ASGI app
app = FastAPI()


async def redis_get(key: str) -> str | None:
    """Get value from Redis via REST API."""
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{UPSTASH_REDIS_URL}/get/{key}",
                headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result")
    except Exception:
        pass
    return None


async def redis_setex(key: str, seconds: int, value: str) -> bool:
    """Set value in Redis with expiry via REST API."""
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return False
    try:
        from urllib.parse import quote

        # URL encode the value to handle special characters like : + .
        encoded_value = quote(value, safe="")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{UPSTASH_REDIS_URL}/setex/{key}/{seconds}/{encoded_value}",
                headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                timeout=5,
            )
            return resp.status_code == 200
    except Exception:
        pass
    return False


def get_alert_key(product_id: str, stock_status: str) -> str:
    """Generate Redis key for alert deduplication."""
    return f"stock_alert:{product_id}:{stock_status}"


async def send_telegram_message(chat_id: str, text: str) -> bool:
    """Send a message via Telegram Bot API.

    Wrapper around consolidated telegram_messaging service.
    """
    from core.services.telegram_messaging import send_telegram_message as _send_msg

    if not chat_id:
        return False

    # Convert string chat_id to int (for admin chat IDs from env)
    try:
        chat_id_int = int(chat_id.strip())
    except ValueError:
        return False

    return await _send_msg(
        chat_id=chat_id_int, text=text, parse_mode="HTML", bot_token=TELEGRAM_TOKEN
    )


def format_stock_alert(products: list) -> str:
    """Format stock alert message in Russian with actionable instructions."""

    # Group by status for better readability
    out_of_stock = []
    critical = []
    low = []

    for p in products:
        status = p.get("stock_status", "low")
        if status == "prepaid_only":
            out_of_stock.append(p)
        elif status == "critical":
            critical.append(p)
        else:
            low.append(p)

    lines = ["<b>📦 КОНТРОЛЬ ЗАПАСОВ</b>\n"]

    # Out of stock - urgent
    if out_of_stock:
        lines.append("🔴 <b>НЕТ В НАЛИЧИИ</b> — требуется срочное пополнение:")
        for p in out_of_stock:
            name = p.get("name", "Неизвестно")
            discount_price = p.get("discount_price")
            price_str = f" (${discount_price})" if discount_price else ""
            lines.append(f"   • {name}{price_str}")
        lines.append("")

    # Critical - action needed
    if critical:
        lines.append("🟠 <b>КРИТИЧЕСКИ МАЛО</b> (1-2 шт) — пополнить в ближайшее время:")
        for p in critical:
            name = p.get("name", "Неизвестно")
            count = p.get("available_count", 0)
            lines.append(f"   • {name}: {count} шт")
        lines.append("")

    # Low stock - warning
    if low:
        lines.append("🟡 <b>ЗАКАНЧИВАЕТСЯ</b> (3-5 шт) — запланировать пополнение:")
        for p in low:
            name = p.get("name", "Неизвестно")
            count = p.get("available_count", 0)
            lines.append(f"   • {name}: {count} шт")
        lines.append("")

    # Action summary
    total = len(out_of_stock) + len(critical) + len(low)
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 <b>Итого:</b> {total} товаров требуют внимания")

    if out_of_stock:
        lines.append(f"⚡ <b>Действие:</b> Добавить сток для {len(out_of_stock)} товаров")

    lines.append(f"\n<i>🕐 {datetime.now(UTC).strftime('%d.%m.%Y %H:%M')} UTC</i>")

    return "\n".join(lines)


@app.get("/api/cron/low_stock_alert")
async def low_stock_alert_entrypoint(request: Request):
    """
    Vercel Cron entrypoint for low stock alerts.
    Uses Redis to deduplicate alerts - only sends once per product/status combo.
    """
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from core.services.database import get_database_async

    db = await get_database_async()
    now = datetime.now(UTC)
    results = {
        "timestamp": now.isoformat(),
        "low_stock_count": 0,
        "new_alerts": 0,
        "skipped_cooldown": 0,
        "notifications_sent": 0,
    }

    try:
        # Query low_stock_alert view
        low_stock_result = await db.client.table("low_stock_alert").select("*").execute()

        low_stock_products = low_stock_result.data or []
        results["low_stock_count"] = len(low_stock_products)

        # Filter products that haven't been alerted recently
        new_alerts = []
        for product in low_stock_products:
            product_id = product.get("product_id", product.get("id", ""))
            stock_status = product.get("stock_status", "low")

            # Check if already alerted
            alert_key = get_alert_key(product_id, stock_status)
            existing = await redis_get(alert_key)

            if existing:
                # Already alerted, skip
                results["skipped_cooldown"] += 1
                continue

            # Mark as alerted with cooldown
            cooldown = ALERT_COOLDOWNS.get(stock_status, 2 * 60 * 60)
            await redis_setex(alert_key, cooldown, now.isoformat())

            new_alerts.append(product)
            results["new_alerts"] += 1

        if new_alerts:
            # Format message only for new alerts
            message = format_stock_alert(new_alerts)

            # Send to all admin chat IDs
            for chat_id in ADMIN_CHAT_IDS:
                if chat_id.strip():
                    success = await send_telegram_message(chat_id, message)
                    if success:
                        results["notifications_sent"] += 1

        results["success"] = True
        results["products"] = [
            {
                "name": p.get("name"),
                "count": p.get("available_count"),
                "status": p.get("stock_status"),
            }
            for p in new_alerts
        ]

    except Exception as e:
        results["success"] = False
        results["error"] = str(e)

    return JSONResponse(results)
