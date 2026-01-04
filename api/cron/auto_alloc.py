"""
Auto Allocation Cron Job
Schedule: */5 * * * * (every 5 minutes) on Pro

Tasks:
1. Attempt to deliver waiting order_items (pending/prepaid/fulfilling) for all products.
2. Process approved replacement tickets waiting for stock.
"""
import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta

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
    
    from core.services.database import get_database
    from core.routers.deps import get_notification_service
    from core.routers.workers import _deliver_items_for_order
    
    db = get_database()
    notification_service = get_notification_service()
    now = datetime.now(timezone.utc)
    
    results = {
        "timestamp": now.isoformat(),
        "order_items": {"processed": 0, "delivered": 0},
        "replacements": {"processed": 0, "delivered": 0}
    }
    
    # ========== TASK 1: Deliver pending order items ==========
    # NOTE: We exclude discount channel orders - they use separate delayed delivery via QStash
    try:
        # First, get order_ids that are NOT from discount channel
        # Join order_items with orders to filter by source_channel
        open_items = await asyncio.to_thread(
            lambda: db.client.table("order_items")
            .select("order_id, orders!inner(source_channel)")
            .in_("status", ["pending", "prepaid", "fulfilling"])
            .neq("orders.source_channel", "discount")
            .order("created_at")
            .limit(200)
            .execute()
        )
        order_ids = list({row["order_id"] for row in (open_items.data or [])})
        results["order_items"]["processed"] = len(order_ids)
        
        for oid in order_ids:
            try:
                res = await _deliver_items_for_order(db, notification_service, oid, only_instant=False)
                if res.get("delivered", 0) > 0:
                    results["order_items"]["delivered"] += res["delivered"]
            except Exception as e:
                logger.error(f"auto_alloc: Failed to deliver order {oid}: {e}")
    except Exception as e:
        logger.error(f"auto_alloc: Failed to query open items: {e}")
    
    # ========== TASK 2: Process approved replacement tickets ==========
    try:
        # Find approved replacement tickets waiting for stock
        approved_tickets = await asyncio.to_thread(
            lambda: db.client.table("tickets")
            .select("id, item_id, order_id, user_id")
            .eq("status", "approved")
            .eq("issue_type", "replacement")
            .order("created_at")
            .limit(50)
            .execute()
        )
        
        results["replacements"]["processed"] = len(approved_tickets.data or [])
        
        for ticket in (approved_tickets.data or []):
            ticket_id = ticket.get("id")
            item_id = ticket.get("item_id")
            
            if not item_id:
                continue
            
            try:
                # Get order item info
                item_res = await asyncio.to_thread(
                    lambda iid=item_id: db.client.table("order_items")
                    .select("product_id, order_id")
                    .eq("id", iid)
                    .single()
                    .execute()
                )
                
                if not item_res.data:
                    continue
                
                product_id = item_res.data.get("product_id")
                order_id = item_res.data.get("order_id")
                
                # Check if stock is available now
                stock_res = await asyncio.to_thread(
                    lambda pid=product_id: db.client.table("stock_items")
                    .select("id, content")
                    .eq("product_id", pid)
                    .eq("status", "available")
                    .limit(1)
                    .execute()
                )
                
                if not stock_res.data:
                    # Still no stock - skip
                    continue
                
                # Stock available! Process replacement
                stock_item = stock_res.data[0]
                stock_id = stock_item["id"]
                stock_content = stock_item.get("content", "")
                
                # Mark stock as sold
                await asyncio.to_thread(
                    lambda sid=stock_id: db.client.table("stock_items")
                    .update({
                        "status": "sold",
                        "reserved_at": now.isoformat(),
                        "sold_at": now.isoformat()
                    })
                    .eq("id", sid)
                    .execute()
                )
                
                # Get product info for expiration
                product_res = await asyncio.to_thread(
                    lambda pid=product_id: db.client.table("products")
                    .select("duration_days, name")
                    .eq("id", pid)
                    .single()
                    .execute()
                )
                
                product = product_res.data if product_res.data else {}
                duration_days = product.get("duration_days")
                product_name = product.get("name", "Product")
                
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
                    "status": "delivered"
                }
                if expires_at_str:
                    update_data["expires_at"] = expires_at_str
                
                await asyncio.to_thread(
                    lambda iid=item_id: db.client.table("order_items")
                    .update(update_data)
                    .eq("id", iid)
                    .execute()
                )
                
                # Close ticket
                await asyncio.to_thread(
                    lambda tid=ticket_id: db.client.table("tickets")
                    .update({
                        "status": "closed",
                        "admin_comment": "Replacement auto-delivered when stock became available."
                    })
                    .eq("id", tid)
                    .execute()
                )
                
                # Notify user
                order_res = await asyncio.to_thread(
                    lambda oid=order_id: db.client.table("orders")
                    .select("user_telegram_id")
                    .eq("id", oid)
                    .single()
                    .execute()
                )
                
                if order_res.data:
                    user_telegram_id = order_res.data.get("user_telegram_id")
                    if user_telegram_id:
                        try:
                            await notification_service.send_replacement_notification(
                                telegram_id=user_telegram_id,
                                product_name=product_name,
                                item_id=item_id[:8]
                            )
                        except Exception as e:
                            logger.error(f"auto_alloc: Failed to notify user: {e}")
                
                results["replacements"]["delivered"] += 1
                logger.info(f"auto_alloc: Delivered replacement for ticket {ticket_id}")
                
            except Exception as e:
                logger.error(f"auto_alloc: Failed to process ticket {ticket_id}: {e}")
    
    except Exception as e:
        logger.error(f"auto_alloc: Failed to process replacement tickets: {e}")
    
    return JSONResponse(results)

