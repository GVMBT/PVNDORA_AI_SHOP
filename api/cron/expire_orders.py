"""
Expire Orders Cron Job
Schedule: */5 * * * * (every 5 minutes)

Tasks:
1. Cancel pending orders that have expired (expires_at < now)
2. Release reserved stock items for cancelled orders
3. Handle stale orders without expires_at (fallback: older than 15 min - matches payment timeout)
"""

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger

logger = get_logger(__name__)

# Verify cron secret to prevent unauthorized access
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# ASGI app (only export app to Vercel, avoid 'handler' symbol)
app = FastAPI()


@app.get("/api/cron/expire_orders")
async def expire_orders_entrypoint(request: Request):
    """
    Vercel Cron entrypoint.
    """
    # Verify the request is from Vercel Cron
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from core.services.database import get_database_async

    db = await get_database_async()
    now = datetime.now(UTC)
    results: dict[str, Any] = {"timestamp": now.isoformat(), "tasks": {}}

    try:
        # 1. Get expired pending orders (expires_at < now)
        expired_orders = await db.orders_domain.get_pending_expired()
        cancelled_count = 0
        released_stock_count = 0

        for order in expired_orders:
            try:
                # Release reserved stock if any
                if order.stock_item_id:
                    await db.client.table("stock_items").update(
                        {"status": "available", "reserved_at": None}
                    ).eq("id", order.stock_item_id).eq("status", "reserved").execute()
                    released_stock_count += 1

                # Cancel the order
                await db.client.table("orders").update({"status": "cancelled"}).eq(
                    "id", order.id
                ).eq("status", "pending").execute()
                cancelled_count += 1

            except Exception as e:
                logger.error(f"Failed to expire order {order.id}: {e}", exc_info=True)

        results["tasks"]["expired_orders"] = cancelled_count
        results["tasks"]["released_stock"] = released_stock_count

        # 2. Get stale pending orders without expires_at
        # (fallback: older than 15 min - matches payment timeout)
        stale_orders = await db.orders_domain.get_pending_stale(minutes=15)
        stale_cancelled = 0

        for order in stale_orders:
            try:
                # Release reserved stock if any
                if order.stock_item_id:
                    await db.client.table("stock_items").update(
                        {"status": "available", "reserved_at": None}
                    ).eq("id", order.stock_item_id).eq("status", "reserved").execute()

                # Cancel the order
                await db.client.table("orders").update({"status": "cancelled"}).eq(
                    "id", order.id
                ).eq("status", "pending").execute()
                stale_cancelled += 1

            except Exception as e:
                logger.error(f"Failed to cancel stale order {order.id}: {e}", exc_info=True)

        results["tasks"]["stale_orders"] = stale_cancelled
        results["success"] = True

    except Exception as e:
        results["success"] = False
        results["error"] = str(e)

    return JSONResponse(results)
