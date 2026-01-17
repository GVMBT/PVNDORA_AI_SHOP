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
from starlette.responses import Response

from core.logging import get_logger

logger = get_logger(__name__)

# Verify cron secret to prevent unauthorized access
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# ASGI app (only export app to Vercel, avoid 'handler' symbol)
app = FastAPI()


async def _release_stock_batch(db: Any, stock_item_ids: list[str]) -> int:
    """Release reserved stock items in batch. Returns count of released items."""
    if not stock_item_ids:
        return 0

    try:
        stock_result = (
            await db.client.table("stock_items")
            .update({"status": "available", "reserved_at": None})
            .in_("id", stock_item_ids)
            .eq("status", "reserved")
            .execute()
        )
        return len(stock_result.data) if stock_result.data else 0
    except Exception as e:
        logger.error(f"Failed to release stock in batch: {e}", exc_info=True)
        return 0


async def _cancel_orders_batch(db: Any, order_ids: list[str]) -> int:
    """Cancel orders in batch. Returns count of cancelled orders."""
    if not order_ids:
        return 0

    try:
        orders_result = (
            await db.client.table("orders")
            .update({"status": "cancelled"})
            .in_("id", order_ids)
            .eq("status", "pending")
            .execute()
        )
        return len(orders_result.data) if orders_result.data else 0
    except Exception as e:
        logger.error(f"Failed to cancel orders in batch: {e}", exc_info=True)
        return 0


async def _cancel_order_individual(db: Any, order: Any, order_type: str) -> tuple[bool, bool]:
    """Cancel single order and release stock individually.
    Returns (order_cancelled, stock_released).
    """
    stock_released = False
    order_cancelled = False

    try:
        if order.stock_item_id:
            await (
                db.client.table("stock_items")
                .update({"status": "available", "reserved_at": None})
                .eq("id", order.stock_item_id)
                .eq("status", "reserved")
                .execute()
            )
            stock_released = True

        await (
            db.client.table("orders")
            .update({"status": "cancelled"})
            .eq("id", order.id)
            .eq("status", "pending")
            .execute()
        )
        order_cancelled = True
    except Exception as e2:
        logger.error(f"Failed to cancel {order_type} order {order.id}: {e2}", exc_info=True)

    return (order_cancelled, stock_released)


async def _cancel_orders_and_release_stock(
    db: Any,
    orders: list[Any],
    order_type: str = "order",
) -> tuple[int, int]:
    """Cancel orders and release reserved stock items.

    Args:
        db: Database instance
        orders: List of order objects with id and stock_item_id
        order_type: Order type for logging (e.g., "expired", "stale")

    Returns:
        Tuple of (cancelled_count, released_stock_count)
    """
    if not orders:
        return (0, 0)

    # Collect IDs for batch operations (avoid N+1)
    stock_item_ids = [o.stock_item_id for o in orders if o.stock_item_id]
    order_ids = [o.id for o in orders]

    # Try batch operations first
    released_stock_count = await _release_stock_batch(db, stock_item_ids)
    cancelled_count = await _cancel_orders_batch(db, order_ids)

    # If batch failed, fallback to individual processing
    if not cancelled_count and not released_stock_count:
        logger.warning(f"Batch operations failed for {order_type} orders, falling back to individual processing")
        for order in orders:
            order_cancelled, stock_released = await _cancel_order_individual(db, order, order_type)
            if order_cancelled:
                cancelled_count += 1
            if stock_released:
                released_stock_count += 1

    return (cancelled_count, released_stock_count)


@app.get("/api/cron/expire_orders")
async def expire_orders_entrypoint(request: Request) -> Response:
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
        cancelled_count, released_stock_count = await _cancel_orders_and_release_stock(
            db, expired_orders, order_type="expired"
        )

        results["tasks"]["expired_orders"] = cancelled_count
        results["tasks"]["released_stock"] = released_stock_count

        # 2. Get stale pending orders without expires_at
        # (fallback: older than 15 min - matches payment timeout)
        stale_orders = await db.orders_domain.get_pending_stale(minutes=15)
        stale_cancelled, _ = await _cancel_orders_and_release_stock(
            db, stale_orders, order_type="stale"
        )

        results["tasks"]["stale_orders"] = stale_cancelled
        results["success"] = True

    except Exception as e:
        results["success"] = False
        results["error"] = str(e)

    return JSONResponse(results)
