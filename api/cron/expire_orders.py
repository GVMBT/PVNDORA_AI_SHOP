"""Expire Orders Cron Job
Schedule: */5 * * * * (every 5 minutes).

Tasks:
1. Cancel pending orders that have expired (expires_at < now)
2. Release reserved stock items for cancelled orders
3. Handle stale orders without expires_at (fallback: older than 15 min - matches payment timeout)
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add project root to path for imports BEFORE any core.* imports
_base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_base_path))
if str(_base_path) not in sys.path:
    sys.path.insert(0, str(_base_path.resolve()))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger

logger = get_logger(__name__)

# Verify cron secret to prevent unauthorized access
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# ASGI app (only export app to Vercel, avoid 'handler' symbol)
app = FastAPI()


@app.get("/api/cron/expire_orders")
async def expire_orders_entrypoint(request: Request) -> dict[str, str | int]:
    """Vercel Cron entrypoint."""
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

        if expired_orders:
            # Collect IDs for batch operations (avoid N+1)
            stock_item_ids = [o.stock_item_id for o in expired_orders if o.stock_item_id]
            order_ids = [o.id for o in expired_orders]

            try:
                # BATCH: Release all reserved stock items at once
                if stock_item_ids:
                    stock_result = (
                        await db.client.table("stock_items")
                        .update({"status": "available", "reserved_at": None})
                        .in_("id", stock_item_ids)
                        .eq("status", "reserved")
                        .execute()
                    )
                    # Count how many were actually updated (may be less if status changed)
                    released_stock_count = len(stock_result.data) if stock_result.data else 0

                # BATCH: Cancel all expired orders at once
                if order_ids:
                    orders_result = (
                        await db.client.table("orders")
                        .update({"status": "cancelled"})
                        .in_("id", order_ids)
                        .eq("status", "pending")
                        .execute()
                    )
                    # Count how many were actually updated
                    cancelled_count = len(orders_result.data) if orders_result.data else 0

            except Exception as e:
                logger.error(f"Failed to expire orders in batch: {e}", exc_info=True)
                # Fallback: process individually if batch fails
                for order in expired_orders:
                    try:
                        if order.stock_item_id:
                            await (
                                db.client.table("stock_items")
                                .update({"status": "available", "reserved_at": None})
                                .eq("id", order.stock_item_id)
                                .eq("status", "reserved")
                                .execute()
                            )
                            released_stock_count += 1

                        await (
                            db.client.table("orders")
                            .update({"status": "cancelled"})
                            .eq("id", order.id)
                            .eq("status", "pending")
                            .execute()
                        )
                        cancelled_count += 1
                    except Exception as e2:
                        logger.error(f"Failed to expire order {order.id}: {e2}", exc_info=True)

        results["tasks"]["expired_orders"] = cancelled_count
        results["tasks"]["released_stock"] = released_stock_count

        # 2. Get stale pending orders without expires_at
        # (fallback: older than 15 min - matches payment timeout)
        stale_orders = await db.orders_domain.get_pending_stale(minutes=15)
        stale_cancelled = 0

        if stale_orders:
            # Collect IDs for batch operations (avoid N+1)
            stale_stock_ids = [o.stock_item_id for o in stale_orders if o.stock_item_id]
            stale_order_ids = [o.id for o in stale_orders]

            try:
                # BATCH: Release all reserved stock items at once
                if stale_stock_ids:
                    await (
                        db.client.table("stock_items")
                        .update({"status": "available", "reserved_at": None})
                        .in_("id", stale_stock_ids)
                        .eq("status", "reserved")
                        .execute()
                    )

                # BATCH: Cancel all stale orders at once
                if stale_order_ids:
                    stale_result = (
                        await db.client.table("orders")
                        .update({"status": "cancelled"})
                        .in_("id", stale_order_ids)
                        .eq("status", "pending")
                        .execute()
                    )
                    stale_cancelled = len(stale_result.data) if stale_result.data else 0

            except Exception as e:
                logger.error(f"Failed to cancel stale orders in batch: {e}", exc_info=True)
                # Fallback: process individually if batch fails
                for order in stale_orders:
                    try:
                        if order.stock_item_id:
                            await (
                                db.client.table("stock_items")
                                .update({"status": "available", "reserved_at": None})
                                .eq("id", order.stock_item_id)
                                .eq("status", "reserved")
                                .execute()
                            )

                        await (
                            db.client.table("orders")
                            .update({"status": "cancelled"})
                            .eq("id", order.id)
                            .eq("status", "pending")
                            .execute()
                        )
                        stale_cancelled += 1
                    except Exception as e2:
                        logger.error(
                            f"Failed to cancel stale order {order.id}: {e2}", exc_info=True
                        )

        results["tasks"]["stale_orders"] = stale_cancelled
        results["success"] = True

    except Exception as e:
        results["success"] = False
        results["error"] = str(e)

    return JSONResponse(results)
