"""
Unified Cron Job - combines critical tasks
Schedule: */5 * * * * (every 5 minutes)

Tasks:
1. Expire pending orders (payment timeout)
2. Auto-allocate stock for paid orders
3. Update exchange rates (hourly check)
"""

import os
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger

logger = get_logger(__name__)

CRON_SECRET = os.environ.get("CRON_SECRET", "")

app = FastAPI()


@app.get("/api/cron/unified")
async def unified_cron_entrypoint(request: Request):
    """
    Unified cron entrypoint - runs all critical tasks.
    """
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from core.services.database import get_database_async

    db = await get_database_async()
    now = datetime.now(UTC)
    results: dict[str, Any] = {"timestamp": now.isoformat(), "tasks": {}}

    # ========== TASK 1: Expire Orders ==========
    try:
        expired_orders = await db.orders_domain.get_pending_expired()
        cancelled_count = 0

        for order in expired_orders:
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
                cancelled_count += 1
                logger.info(f"Expired order {order.id}")

            except Exception:
                logger.exception(f"Failed to expire order {order.id}")

        # Also handle stale orders (no expires_at, older than 15 min - matches payment timeout)
        stale_orders = await db.orders_domain.get_pending_stale(minutes=15)
        for order in stale_orders:
            try:
                if order.stock_item_id:
                    await db.client.table("stock_items").update(
                        {"status": "available", "reserved_at": None}
                    ).eq("id", order.stock_item_id).eq("status", "reserved").execute()

                await db.client.table("orders").update({"status": "cancelled"}).eq(
                    "id", order.id
                ).eq("status", "pending").execute()
                cancelled_count += 1
                logger.info(f"Cancelled stale order {order.id}")
            except Exception:
                logger.exception(f"Failed to cancel stale order {order.id}")

        results["tasks"]["expired_orders"] = cancelled_count

    except Exception as e:
        results["tasks"]["expire_orders_error"] = str(e)
        logger.exception("Expire orders task failed")

    # ========== TASK 2: Auto-Allocate Stock ==========
    try:
        from core.services.domains.delivery import DeliveryService

        delivery_service = DeliveryService(db)

        # Get paid orders awaiting delivery
        paid_orders = (
            await db.client.table("orders")
            .select("*")
            .eq("status", "paid")
            .is_("delivered_at", "null")
            .execute()
        )

        allocated_count = 0
        for order_data_raw in paid_orders.data or []:
            if not isinstance(order_data_raw, dict):
                continue
            order_data = cast(dict[str, Any], order_data_raw)
            order_id = order_data.get("id")
            try:
                # Check if order is confirmed (payment confirmed)
                order_status = order_data.get("status")
                if order_status != "paid":
                    logger.info(f"Order {order_id} is still {order_status} - skipping")
                    continue

                # Deliver goods
                result = await delivery_service.deliver_order(order_id)
                if result:
                    allocated_count += 1
                    logger.info(f"Delivered order {order_id}")

            except Exception:
                logger.exception(f"Failed to deliver order {order_id}")

        results["tasks"]["auto_allocated"] = allocated_count

    except Exception as e:
        results["tasks"]["auto_alloc_error"] = str(e)
        logger.exception("Auto-alloc task failed")

    # ========== TASK 3: Update Exchange Rates (hourly) ==========
    # NOTE: Exchange rates are updated by separate cron: /api/cron/update_exchange_rates
    # This task is deprecated - rates should be updated via dedicated endpoint
    # to avoid conflicts and ensure proper error handling
    try:
        # Exchange rates are handled by update_exchange_rates.py cron
        # No need to update here - rates are fetched hourly by dedicated cron
        results["tasks"]["exchange_rates_updated"] = "handled_by_separate_cron"
    except Exception as e:
        results["tasks"]["exchange_rates_error"] = str(e)
        logger.exception("Exchange rates check failed")

    results["success"] = True
    return JSONResponse(results)
