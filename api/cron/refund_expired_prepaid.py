"""
Refund Expired Prepaid Items Cron Job
Schedule: 0 * * * * (every hour)

Tasks:
1. Find prepaid ORDER ITEMS where fulfillment_deadline has passed
2. Process refund (update item status, optionally order status, notify user)
3. Use add_to_user_balance RPC for atomic balance update
"""
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os

from core.logging import get_logger

logger = get_logger(__name__)

CRON_SECRET = os.environ.get("CRON_SECRET", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

# ASGI app (only export app to Vercel, avoid 'handler' symbol)
app = FastAPI()


@app.get("/api/cron/refund_expired_prepaid")
async def refund_expired_prepaid_entrypoint(request: Request):
    """
    Vercel Cron entrypoint for refunding expired prepaid order items.
    
    Now operates on order_items level since fulfillment_deadline is per-item.
    """
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from core.services.database import get_database_async
    from core.services.money import to_float
    import httpx
    
    db = await get_database_async()
    now = datetime.now(timezone.utc)
    results = {
        "timestamp": now.isoformat(),
        "items_refunded": 0,
        "orders_updated": 0,
        "errors": []
    }
    
    try:
        # Find prepaid ORDER ITEMS with expired fulfillment_deadline
        # Join with orders to get user info, join with products for name
        expired_items = await db.client.table("order_items").select("""
            id,
            order_id,
            price,
            product_id,
            products(name),
            orders(id, user_id, user_telegram_id, amount, fiat_amount, fiat_currency)
        """).eq("status", "prepaid").lt(
            "fulfillment_deadline", now.isoformat()
        ).limit(50).execute()
        
        processed_orders = set()
        
        for item in (expired_items.data or []):
            item_id = item.get("id")
            order_id = item.get("order_id")
            order_data = item.get("orders", {}) or {}
            product_data = item.get("products", {}) or {}
            
            user_id = order_data.get("user_id")
            telegram_id = order_data.get("user_telegram_id")
            item_price = to_float(item.get("price", 0))
            product_name = product_data.get("name", "Unknown")
            
            # Get user's balance_currency for proper refund
            balance_currency = "RUB"  # Default
            try:
                if user_id:
                    user_result = await db.client.table("users").select("balance_currency").eq(
                        "id", user_id
                    ).single().execute()
                    if user_result.data:
                        balance_currency = user_result.data.get("balance_currency", "RUB") or "RUB"
            except Exception:
                pass
            
            # Calculate refund amount in user's currency
            # item.price is in USD, need to convert
            if balance_currency == "USD":
                refund_amount = item_price
            else:
                # Get current exchange rate
                from core.db import get_redis
                from core.services.currency import get_currency_service
                redis = get_redis()
                currency_service = get_currency_service(redis)
                rate = await currency_service.get_exchange_rate(balance_currency)
                refund_amount = round(item_price * rate)  # Round for integer currencies
            
            try:
                # 1. Update order_item status to refunded
                await db.client.table("order_items").update({
                    "status": "refunded"
                }).eq("id", item_id).execute()
                
                # 2. Credit user balance using RPC (atomic)
                if user_id and refund_amount > 0:
                    await db.client.rpc(
                        "add_to_user_balance",
                        {
                            "p_user_id": str(user_id), 
                            "p_amount": refund_amount,
                            "p_reason": f"Авто-возврат: товар «{product_name}» не поступил в срок"
                        }
                    ).execute()
                
                # 3. Check if order should be marked as refunded (all items refunded)
                if order_id not in processed_orders:
                    remaining_items = await db.client.table("order_items").select("id").eq(
                        "order_id", order_id
                    ).not_.eq("status", "refunded").execute()
                    
                    if not remaining_items.data:
                        # All items refunded, update order status
                        await db.client.table("orders").update({
                            "status": "refunded",
                            "refund_reason": "Auto-refund: fulfillment deadline exceeded"
                        }).eq("id", order_id).execute()
                        results["orders_updated"] += 1
                    
                    processed_orders.add(order_id)
                
                # 4. Notify user via Telegram
                if telegram_id and TELEGRAM_TOKEN:
                    # Format amount with currency
                    if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
                        amount_str = f"{int(refund_amount)} {balance_currency}"
                    else:
                        amount_str = f"${refund_amount:.2f}"
                    
                    message = (
                        f"💰 <b>Возврат средств</b>\n\n"
                        f"Товар «{product_name}» не поступил в срок.\n"
                        f"Сумма <b>{amount_str}</b> возвращена на ваш баланс.\n\n"
                        f"<i>Приносим извинения за неудобства!</i>"
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
                        logger.warning(f"Failed to notify user {telegram_id}: {notify_err}")
                
                results["items_refunded"] += 1
                logger.info(f"Auto-refunded item {item_id}: {refund_amount} {balance_currency} for {product_name}")
                
            except Exception as e:
                error_msg = f"Failed to refund item {item_id}: {e}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append(error_msg)
        
        results["success"] = True
        
    except Exception as e:
        logger.error(f"Cron job failed: {e}", exc_info=True)
        results["success"] = False
        results["error"] = str(e)
    
    return JSONResponse(results)
