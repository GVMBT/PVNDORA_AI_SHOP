"""
Auto Allocation Cron Job
Schedule: */5 * * * * (every 5 minutes) on Pro

Tasks:
1. Attempt to deliver waiting order_items (pending/prepaid) for all products.
2. Process approved replacement tickets waiting for stock.
"""

import os
import sys
from datetime import UTC, datetime, timedelta
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


def _extract_order_ids_from_response(response_data: list[Any] | None) -> list[str]:
    """Extract order IDs from query response."""
    if not response_data:
        return []
    result: list[str] = []
    for row in response_data:
        if isinstance(row, dict):
            order_id = row.get("id") or row.get("order_id")
            if order_id:
                result.append(str(order_id))
    return result


async def _process_order_items(db: Any, notification_service: Any, results: dict[str, Any]) -> None:
    """Process pending order items for delivery."""
    from core.routers.workers import _deliver_items_for_order

    # Get order_ids that are NOT from discount channel
    valid_orders = (
        await db.client.table("orders")
        .select("id")
        .neq("source_channel", "discount")
        .in_("status", ["paid", "prepaid", "partial", "delivered"])
        .limit(500)
        .execute()
    )

    valid_order_ids = _extract_order_ids_from_response(valid_orders.data)
    if not valid_order_ids:
        results["order_items"]["processed"] = 0
        return

    # Get order_items for these orders that are pending/prepaid
    open_items = (
        await db.client.table("order_items")
        .select("order_id")
        .in_("order_id", valid_order_ids)
        .in_("status", ["pending", "prepaid"])
        .order("created_at")
        .limit(200)
        .execute()
    )

    order_ids = list(set(_extract_order_ids_from_response(open_items.data)))
    results["order_items"]["processed"] = len(order_ids)

    for oid in order_ids:
        try:
            res = await _deliver_items_for_order(db, notification_service, oid, only_instant=False)
            if res.get("delivered", 0) > 0:
                results["order_items"]["delivered"] += res["delivered"]
        except Exception:
            logger.exception("auto_alloc: Failed to deliver order %s", oid)


async def _get_replacement_context(db: Any, item_id: str) -> tuple[str | None, str | None]:
    """Get product_id and order_id for replacement item."""
    item_res = (
        await db.client.table("order_items")
        .select("product_id, order_id")
        .eq("id", item_id)
        .single()
        .execute()
    )
    if not item_res.data or not isinstance(item_res.data, dict):
        return None, None
    item_data = cast(dict[str, Any], item_res.data)
    product_id = str(item_data.get("product_id")) if item_data.get("product_id") else None
    order_id = str(item_data.get("order_id")) if item_data.get("order_id") else None
    return product_id, order_id


async def _find_available_stock(db: Any, product_id: str) -> tuple[str | None, str]:
    """Find available stock for product. Returns (stock_id, content)."""
    stock_res = (
        await db.client.table("stock_items")
        .select("id, content")
        .eq("product_id", product_id)
        .eq("status", "available")
        .limit(1)
        .execute()
    )
    if not stock_res.data:
        return None, ""
    raw_stock = stock_res.data[0]
    if not isinstance(raw_stock, dict):
        return None, ""
    stock_item = cast(dict[str, Any], raw_stock)
    stock_id = str(stock_item.get("id")) if stock_item.get("id") else None
    stock_content = str(stock_item.get("content", ""))
    return stock_id, stock_content


async def _get_product_expiry_info(db: Any, product_id: str) -> tuple[int, str]:
    """Get product duration and name. Returns (duration_days, product_name)."""
    product_res = (
        await db.client.table("products")
        .select("duration_days, name")
        .eq("id", product_id)
        .single()
        .execute()
    )
    product = cast(dict[str, Any], product_res.data) if isinstance(product_res.data, dict) else {}
    duration_raw = product.get("duration_days")
    duration = (
        int(duration_raw) if isinstance(duration_raw, (int, float)) and duration_raw > 0 else 0
    )
    return duration, str(product.get("name", "Product"))


async def _process_single_replacement(
    db: Any,
    notification_service: Any,
    ticket: dict[str, Any],
    now: datetime,
) -> bool:
    """Process a single replacement ticket. Returns True if delivered."""
    ticket_id = str(ticket.get("id", "")) if ticket.get("id") else None
    item_id = str(ticket.get("item_id")) if ticket.get("item_id") else None
    if not item_id:
        return False

    product_id, order_id = await _get_replacement_context(db, item_id)
    if not product_id or not order_id:
        return False

    stock_id, stock_content = await _find_available_stock(db, product_id)
    if not stock_id:
        return False

    # Mark stock as sold
    await (
        db.client.table("stock_items")
        .update({"status": "sold", "reserved_at": now.isoformat(), "sold_at": now.isoformat()})
        .eq("id", stock_id)
        .execute()
    )

    duration_days, product_name = await _get_product_expiry_info(db, product_id)
    expires_at_str = (
        (now + timedelta(days=duration_days)).isoformat() if duration_days > 0 else None
    )

    # Update order item
    update_data: dict[str, Any] = {
        "stock_item_id": stock_id,
        "delivery_content": stock_content,
        "delivered_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "status": "delivered",
    }
    if expires_at_str:
        update_data["expires_at"] = expires_at_str
    await db.client.table("order_items").update(update_data).eq("id", item_id).execute()

    # Close ticket
    await (
        db.client.table("tickets")
        .update(
            {
                "status": "closed",
                "admin_comment": "Replacement auto-delivered when stock became available.",
            }
        )
        .eq("id", ticket_id)
        .execute()
    )

    await _notify_replacement_user(db, notification_service, order_id, product_name, item_id)
    logger.info("auto_alloc: Delivered replacement for ticket %s", ticket_id)
    return True


async def _notify_replacement_user(
    db: Any,
    notification_service: Any,
    order_id: str,
    product_name: str,
    item_id: str,
) -> None:
    """Notify user about replacement delivery."""
    order_res = (
        await db.client.table("orders")
        .select("user_telegram_id")
        .eq("id", order_id)
        .single()
        .execute()
    )

    if not order_res.data or not isinstance(order_res.data, dict):
        return

    order_data = cast(dict[str, Any], order_res.data)
    user_telegram_id_raw = order_data.get("user_telegram_id")
    user_telegram_id = (
        int(user_telegram_id_raw)
        if isinstance(user_telegram_id_raw, (int, str)) and str(user_telegram_id_raw).isdigit()
        else None
    )

    if user_telegram_id:
        try:
            await notification_service.send_replacement_notification(
                telegram_id=user_telegram_id,
                product_name=product_name,
                item_id=item_id[:8] if item_id else "",
            )
        except Exception:
            logger.exception("auto_alloc: Failed to notify user")


async def _process_replacement_tickets(
    db: Any, notification_service: Any, results: dict[str, Any], now: datetime
) -> None:
    """Process approved replacement tickets waiting for stock."""
    approved_tickets = (
        await db.client.table("tickets")
        .select("id, item_id, order_id, user_id")
        .eq("status", "approved")
        .eq("issue_type", "replacement")
        .order("created_at")
        .limit(50)
        .execute()
    )

    results["replacements"]["processed"] = len(approved_tickets.data or [])

    for raw_ticket in approved_tickets.data or []:
        if not isinstance(raw_ticket, dict):
            continue
        ticket = cast(dict[str, Any], raw_ticket)
        try:
            if await _process_single_replacement(db, notification_service, ticket, now):
                results["replacements"]["delivered"] += 1
        except Exception:
            logger.exception("auto_alloc: Failed to process ticket %s", ticket.get("id"))


@app.get("/api/cron/auto_alloc")
async def auto_alloc_entrypoint(request: Request):
    """Vercel Cron entrypoint."""
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from core.routers.deps import get_notification_service
    from core.services.database import get_database_async

    db = await get_database_async()
    notification_service = get_notification_service()
    now = datetime.now(UTC)

    results: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "order_items": {"processed": 0, "delivered": 0},
        "replacements": {"processed": 0, "delivered": 0},
    }

    # TASK 1: Deliver pending order items
    try:
        await _process_order_items(db, notification_service, results)
    except Exception:
        logger.exception("auto_alloc: Failed to query open items")

    # TASK 2: Process approved replacement tickets
    try:
        await _process_replacement_tickets(db, notification_service, results, now)
    except Exception:
        logger.exception("auto_alloc: Failed to process replacement tickets")

    return JSONResponse(results)
