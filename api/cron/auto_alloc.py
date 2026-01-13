"""
Auto Allocation Cron Job
Schedule: */5 * * * * (every 5 minutes) on Pro

Tasks:
1. Attempt to deliver waiting order_items (pending/prepaid) for all products.
2. Process approved replacement tickets waiting for stock.
"""

import os
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger

logger = get_logger(__name__)

CRON_SECRET = os.environ.get("CRON_SECRET", "")

app = FastAPI()


@app.get("/api/cron/auto_alloc")
async def auto_alloc_entrypoint(request: Request):
    """
    Vercel Cron entrypoint.
    """
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from core.routers.deps import get_notification_service
    from core.routers.workers import _deliver_items_for_order
    from core.services.database import get_database_async

    db = await get_database_async()
    notification_service = get_notification_service()
    now = datetime.now(UTC)

    results: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "order_items": {"processed": 0, "delivered": 0},
        "replacements": {"processed": 0, "delivered": 0},
    }

    # ========== TASK 1: Deliver pending order items ==========
    # NOTE: We exclude discount channel orders - they use separate delayed delivery via QStash
    try:
        # First, get order_ids that are NOT from discount channel and have valid statuses
        # Query orders first, then get their order_items
        valid_orders = (
            await db.client.table("orders")
            .select("id")
            .neq("source_channel", "discount")
            .in_("status", ["paid", "prepaid", "partial", "delivered"])
            .limit(500)
            .execute()
        )

        valid_order_ids: list[str] = []
        if valid_orders.data:
            for row in valid_orders.data:
                if isinstance(row, dict):
                    row_dict = cast(dict[str, Any], row)
                    order_id = row_dict.get("id")
                    if order_id:
                        valid_order_ids.append(str(order_id))

        if not valid_order_ids:
            results["order_items"]["processed"] = 0
        else:
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
            order_ids_set: set[str] = set()
            if open_items.data:
                for row in open_items.data:
                    if isinstance(row, dict):
                        row_dict = cast(dict[str, Any], row)
                        order_id = row_dict.get("order_id")
                        if order_id:
                            order_ids_set.add(str(order_id))
            order_ids = list(order_ids_set)
            results["order_items"]["processed"] = len(order_ids)

            for oid in order_ids:
                try:
                    res = await _deliver_items_for_order(
                        db, notification_service, oid, only_instant=False
                    )
                    if res.get("delivered", 0) > 0:
                        results["order_items"]["delivered"] += res["delivered"]
                except Exception:
                    logger.exception("auto_alloc: Failed to deliver order %s", oid)
    except Exception:
        logger.exception("auto_alloc: Failed to query open items")

    # ========== TASK 2: Process approved replacement tickets ==========
    try:
        # Find approved replacement tickets waiting for stock
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
            ticket_id = str(ticket.get("id", "")) if ticket.get("id") else None
            item_id_raw = ticket.get("item_id")
            item_id = str(item_id_raw) if item_id_raw else None

            if not item_id:
                continue

            try:
                # Get order item info
                item_res = (
                    await db.client.table("order_items")
                    .select("product_id, order_id")
                    .eq("id", item_id)
                    .single()
                    .execute()
                )

                if not item_res.data or not isinstance(item_res.data, dict):
                    continue

                item_data = cast(dict[str, Any], item_res.data)
                product_id_raw = item_data.get("product_id")
                product_id = str(product_id_raw) if product_id_raw else None
                order_id_raw = item_data.get("order_id")
                order_id = str(order_id_raw) if order_id_raw else None

                if not product_id or not order_id:
                    continue

                # Check if stock is available now
                stock_res = (
                    await db.client.table("stock_items")
                    .select("id, content")
                    .eq("product_id", product_id)
                    .eq("status", "available")
                    .limit(1)
                    .execute()
                )

                if not stock_res.data:
                    # Still no stock - skip
                    continue

                # Stock available! Process replacement
                raw_stock = stock_res.data[0]
                if not isinstance(raw_stock, dict):
                    continue
                stock_item = cast(dict[str, Any], raw_stock)
                stock_id_raw = stock_item.get("id")
                stock_id = str(stock_id_raw) if stock_id_raw else None
                if not stock_id:
                    continue
                stock_content_raw = stock_item.get("content")
                stock_content = str(stock_content_raw) if stock_content_raw else ""

                # Mark stock as sold
                await db.client.table("stock_items").update(
                    {"status": "sold", "reserved_at": now.isoformat(), "sold_at": now.isoformat()}
                ).eq("id", stock_id).execute()

                # Get product info for expiration
                product_res = (
                    await db.client.table("products")
                    .select("duration_days, name")
                    .eq("id", product_id)
                    .single()
                    .execute()
                )

                product_raw = product_res.data
                product = cast(dict[str, Any], product_raw) if isinstance(product_raw, dict) else {}
                duration_days_raw = product.get("duration_days")
                duration_days = (
                    int(duration_days_raw)
                    if isinstance(duration_days_raw, (int, float)) and duration_days_raw > 0
                    else 0
                )
                product_name_raw = product.get("name")
                product_name = str(product_name_raw) if product_name_raw else "Product"

                # Calculate expires_at
                expires_at_str = None
                if duration_days and duration_days > 0:
                    expires_at = now + timedelta(days=duration_days)
                    expires_at_str = expires_at.isoformat()

                # Update order item with new credentials
                update_data = {
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
                await db.client.table("tickets").update(
                    {
                        "status": "closed",
                        "admin_comment": "Replacement auto-delivered when stock became available.",
                    }
                ).eq("id", ticket_id).execute()

                # Notify user
                order_res = (
                    await db.client.table("orders")
                    .select("user_telegram_id")
                    .eq("id", order_id)
                    .single()
                    .execute()
                )

                if order_res.data and isinstance(order_res.data, dict):
                    order_data = cast(dict[str, Any], order_res.data)
                    user_telegram_id_raw = order_data.get("user_telegram_id")
                    user_telegram_id = (
                        int(user_telegram_id_raw)
                        if isinstance(user_telegram_id_raw, (int, str))
                        and str(user_telegram_id_raw).isdigit()
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

                results["replacements"]["delivered"] += 1
                logger.info("auto_alloc: Delivered replacement for ticket %s", ticket_id)

            except Exception:
                logger.exception("auto_alloc: Failed to process ticket %s", ticket_id)

    except Exception:
        logger.exception("auto_alloc: Failed to process replacement tickets")

    return JSONResponse(results)
