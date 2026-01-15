"""Daily Cleanup Cron Job
Schedule: 0 3 * * * (3:00 AM UTC daily).

Tasks:
1. Clear expired cart reservations (older than 24h)
2. Clear old chat history (older than 30 days)
3. Clean up expired promo codes
4. Release stuck stock reservations
"""

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Add project root to path for imports BEFORE any core.* imports
_base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_base_path))
if str(_base_path) not in sys.path:
    sys.path.insert(0, str(_base_path.resolve()))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Verify cron secret to prevent unauthorized access
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# ASGI app (only export app to Vercel, avoid 'handler' symbol)
app = FastAPI()


async def _fix_inconsistent_order_statuses(db, now: datetime) -> int:
    """Fix orders with inconsistent statuses.
    E.g., orders with status 'partial' where all items are actually 'delivered'.

    OPTIMIZED: Uses batch query to get all items at once, avoiding N+1 queries.
    """
    try:
        # Find orders with status 'partial' that might be fully delivered
        partial_orders = (
            await db.client.table("orders")
            .select("id")
            .eq("status", "partial")
            .execute()
        )

        if not partial_orders.data:
            return 0

        order_ids = [o["id"] for o in partial_orders.data]

        # BATCH QUERY: Get all items for all partial orders at once
        all_items_result = (
            await db.client.table("order_items")
            .select("order_id, status")
            .in_("order_id", order_ids)
            .execute()
        )

        # Group items by order_id
        items_by_order: dict[str, list[dict]] = {}
        for item in (all_items_result.data or []):
            oid = item["order_id"]
            if oid not in items_by_order:
                items_by_order[oid] = []
            items_by_order[oid].append(item)

        # Find orders where all items are delivered
        orders_to_fix = []
        for order_id in order_ids:
            items = items_by_order.get(order_id, [])
            if not items:
                continue

            delivered = sum(1 for i in items if i.get("status") == "delivered")
            pending = sum(1 for i in items if i.get("status") in ("pending", "prepaid"))

            if delivered > 0 and pending == 0:
                orders_to_fix.append(order_id)

        # BATCH UPDATE: Update all qualifying orders at once
        if orders_to_fix:
            await db.client.table("orders").update(
                {"status": "delivered", "delivered_at": now.isoformat()},
            ).in_("id", orders_to_fix).eq("status", "partial").execute()

        return len(orders_to_fix)

    except Exception as e:
        # Log but don't fail the entire cron job
        import logging
        logging.warning(f"Error fixing order statuses: {e}")
        return 0


@app.get("/api/cron/daily_cleanup")
async def daily_cleanup_entrypoint(request: Request):
    """Vercel Cron entrypoint for daily cleanup tasks."""
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from core.services.database import get_database_async

    db = await get_database_async()
    now = datetime.now(UTC)
    results: dict[str, Any] = {"timestamp": now.isoformat(), "tasks": {}}

    try:
        # 1. Release stuck stock reservations (older than 30 min)
        cutoff_reservations = now - timedelta(minutes=30)
        stuck_reservations = (
            await db.client.table("stock_items")
            .update({"status": "available", "reserved_at": None})
            .eq("status", "reserved")
            .lt("reserved_at", cutoff_reservations.isoformat())
            .execute()
        )
        results["tasks"]["released_reservations"] = len(stuck_reservations.data or [])

        # 2. Clear old chat history (older than 30 days)
        cutoff_chat = now - timedelta(days=30)
        old_chats = (
            await db.client.table("chat_history")
            .delete()
            .lt("timestamp", cutoff_chat.isoformat())
            .execute()
        )
        results["tasks"]["deleted_old_chats"] = len(old_chats.data or [])

        # 3. Deactivate expired promo codes
        expired_promos = (
            await db.client.table("promo_codes")
            .update({"is_active": False})
            .eq("is_active", True)
            .lt("expires_at", now.isoformat())
            .execute()
        )
        results["tasks"]["expired_promos"] = len(expired_promos.data or [])

        # 4. Clean wishlist items older than 90 days that have been reminded
        cutoff_wishlist = now - timedelta(days=90)
        old_wishlist = (
            await db.client.table("wishlist")
            .delete()
            .eq("reminded", True)
            .lt("created_at", cutoff_wishlist.isoformat())
            .execute()
        )
        results["tasks"]["cleaned_wishlist"] = len(old_wishlist.data or [])

        # 5. Fix inconsistent order statuses (partial orders where all items are delivered)
        fixed_orders = await _fix_inconsistent_order_statuses(db, now)
        results["tasks"]["fixed_order_statuses"] = fixed_orders

        results["success"] = True

    except Exception as e:
        results["success"] = False
        results["error"] = str(e)

    return JSONResponse(results)
