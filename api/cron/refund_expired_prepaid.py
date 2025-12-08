"""
Refund Expired Prepaid Orders Cron Job
Schedule: 0 * * * * (every hour)

Tasks:
1. Find prepaid/fulfilling orders where fulfillment_deadline has passed
2. Process refund (update status, notify user)
3. Release any reserved stock
"""
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import asyncio

CRON_SECRET = os.environ.get("CRON_SECRET", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

# ASGI app (only export app to Vercel, avoid 'handler' symbol)
app = FastAPI()


@app.get("/api/cron/refund_expired_prepaid")
async def refund_expired_prepaid_entrypoint(request: Request):
    """
    Vercel Cron entrypoint for refunding expired prepaid orders.
    """
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from src.services.database import get_database
    import httpx
    
    db = get_database()
    now = datetime.now(timezone.utc)
    results = {
        "timestamp": now.isoformat(),
        "refunded": 0,
        "errors": []
    }
    
    try:
        # Find prepaid/fulfilling orders with expired fulfillment_deadline
        expired_prepaid = await asyncio.to_thread(
            lambda: db.client.table("orders")
            .select("id, user_id, amount, user_telegram_id, products(name)")
            .in_("status", ["prepaid", "fulfilling"])
            .lt("fulfillment_deadline", now.isoformat())
            .execute()
        )
        
        for order in (expired_prepaid.data or []):
            order_id = order.get("id")
            user_id = order.get("user_id")
            telegram_id = order.get("user_telegram_id")
            amount = order.get("amount", 0)
            product_name = order.get("products", {}).get("name", "Unknown")
            
            try:
                # 1. Update order status to refunded
                await asyncio.to_thread(
                    lambda oid=order_id: db.client.table("orders").update({
                        "status": "refunded",
                        "notes": "Auto-refund: fulfillment deadline exceeded"
                    }).eq("id", oid).execute()
                )
                
                # 2. Update all order_items to refunded
                await asyncio.to_thread(
                    lambda oid=order_id: db.client.table("order_items").update({
                        "status": "refunded"
                    }).eq("order_id", oid).execute()
                )
                
                # 3. Credit user balance (if applicable)
                if user_id and amount > 0:
                    await asyncio.to_thread(
                        lambda uid=user_id, amt=amount: db.client.rpc(
                            "increment_user_balance",
                            {"p_user_id": uid, "p_amount": amt}
                        ).execute()
                    )
                
                # 4. Notify user via Telegram
                if telegram_id and TELEGRAM_TOKEN:
                    message = (
                        f"💰 Возврат средств\n\n"
                        f"Товар «{product_name}» не поступил в срок.\n"
                        f"Сумма {amount}₽ возвращена на ваш баланс.\n\n"
                        f"Приносим извинения за неудобства!"
                    )
                    try:
                        async with httpx.AsyncClient() as client:
                            await client.post(
                                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                                json={
                                    "chat_id": telegram_id,
                                    "text": message,
                                    "parse_mode": "HTML"
                                },
                                timeout=10
                            )
                    except Exception as notify_err:
                        print(f"Failed to notify user {telegram_id}: {notify_err}")
                
                results["refunded"] += 1
                print(f"Auto-refunded order {order_id}: {amount}₽ for {product_name}")
                
            except Exception as e:
                error_msg = f"Failed to refund order {order_id}: {e}"
                print(error_msg)
                results["errors"].append(error_msg)
        
        results["success"] = True
        
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
    
    return JSONResponse(results)

