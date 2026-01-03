"""
Low Stock Alert Cron Job
Schedule: */30 * * * * (every 30 minutes)

Tasks:
1. Check for products with low stock (<5 items)
2. Send Telegram notification to admin(s)
"""
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import asyncio
import httpx

# Verify cron secret to prevent unauthorized access
CRON_SECRET = os.environ.get("CRON_SECRET", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_CHAT_IDS = os.environ.get("ADMIN_CHAT_IDS", "").split(",")  # Comma-separated list

# ASGI app
app = FastAPI()


async def send_telegram_message(chat_id: str, text: str) -> bool:
    """Send a message via Telegram Bot API."""
    if not TELEGRAM_TOKEN or not chat_id:
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id.strip(),
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            return response.status_code == 200
    except Exception:
        return False


def format_stock_alert(products: list) -> str:
    """Format stock alert message."""
    lines = ["<b>⚠️ Low Stock Alert</b>\n"]
    
    for p in products:
        status_emoji = {
            "prepaid_only": "🔴",
            "critical": "🟠",
            "low": "🟡"
        }.get(p.get("stock_status"), "⚪")
        
        name = p.get("name", "Unknown")
        count = p.get("available_count", 0)
        discount_price = p.get("discount_price")
        
        price_str = f" (${discount_price})" if discount_price else ""
        
        lines.append(f"{status_emoji} <b>{name}</b>{price_str}: {count} items")
    
    lines.append(f"\n<i>Checked at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</i>")
    
    return "\n".join(lines)


@app.get("/api/cron/low_stock_alert")
async def low_stock_alert_entrypoint(request: Request):
    """
    Vercel Cron entrypoint for low stock alerts.
    """
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from core.services.database import get_database
    
    db = get_database()
    now = datetime.now(timezone.utc)
    results = {
        "timestamp": now.isoformat(),
        "low_stock_count": 0,
        "notifications_sent": 0
    }
    
    try:
        # Query low_stock_alert view
        low_stock_result = await asyncio.to_thread(
            lambda: db.client.table("low_stock_alert").select("*").execute()
        )
        
        low_stock_products = low_stock_result.data or []
        results["low_stock_count"] = len(low_stock_products)
        
        if low_stock_products:
            # Format message
            message = format_stock_alert(low_stock_products)
            
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
                "status": p.get("stock_status")
            }
            for p in low_stock_products
        ]
        
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
    
    return JSONResponse(results)
