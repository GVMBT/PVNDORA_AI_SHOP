"""Unified Cron Job - combines critical tasks
Schedule: */5 * * * * (every 5 minutes).

Tasks:
1. Expire pending orders (payment timeout)
2. Auto-allocate stock for paid orders
3. Update exchange rates (hourly check)
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

# Add project root to path for imports BEFORE any core.* imports
_base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_base_path))
if str(_base_path) not in sys.path:
    sys.path.insert(0, str(_base_path.resolve()))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger

logger = get_logger(__name__)

CRON_SECRET = os.environ.get("CRON_SECRET", "")

app = FastAPI()


async def _cancel_single_order(db: Any, order: Any) -> bool:
    """Cancel a single expired/stale order. Returns True on success."""
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
        return True
    except Exception:
        logger.exception(f"Failed to cancel order {order.id}")
        return False


async def _expire_orders_task(db: Any, results: dict[str, Any]) -> None:
    """Task 1: Expire pending orders."""
    expired_orders = await db.orders_domain.get_pending_expired()
    cancelled_count = 0

    for order in expired_orders:
        if await _cancel_single_order(db, order):
            cancelled_count += 1
            logger.info(f"Expired order {order.id}")

    stale_orders = await db.orders_domain.get_pending_stale(minutes=15)
    for order in stale_orders:
        if await _cancel_single_order(db, order):
            cancelled_count += 1
            logger.info(f"Cancelled stale order {order.id}")

    results["tasks"]["expired_orders"] = cancelled_count


async def _auto_allocate_task(db: Any, results: dict[str, Any]) -> None:
    """Task 2: Auto-allocate stock for paid orders."""
    from core.services.domains.delivery import DeliveryService

    delivery_service = DeliveryService(db)
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

        if order_data.get("status") != "paid":
            continue

        try:
            if await delivery_service.deliver_order(order_id):
                allocated_count += 1
                logger.info(f"Delivered order {order_id}")
        except Exception:
            logger.exception(f"Failed to deliver order {order_id}")

    results["tasks"]["auto_allocated"] = allocated_count


@app.get("/api/cron/unified")
async def unified_cron_entrypoint(request: Request) -> dict[str, str | bool]:
    """Unified cron entrypoint - runs all critical tasks."""
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from core.services.database import get_database_async

    db = await get_database_async()
    now = datetime.now(UTC)
    results: dict[str, Any] = {"timestamp": now.isoformat(), "tasks": {}}

    # Task 1: Expire Orders
    try:
        await _expire_orders_task(db, results)
    except Exception as e:
        results["tasks"]["expire_orders_error"] = str(e)
        logger.exception("Expire orders task failed")

    # Task 2: Auto-Allocate Stock
    try:
        await _auto_allocate_task(db, results)
    except Exception as e:
        results["tasks"]["auto_alloc_error"] = str(e)
        logger.exception("Auto-alloc task failed")

    # Task 3: Exchange rates handled by separate cron
    results["tasks"]["exchange_rates_updated"] = "handled_by_separate_cron"

    results["success"] = True
    return JSONResponse(results)
