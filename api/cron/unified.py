"""
Unified Cron Job - combines critical tasks
Schedule: */5 * * * * (every 5 minutes)

Tasks:
1. Expire pending orders (payment timeout)
2. Auto-allocate stock for paid orders
3. Update exchange rates (hourly check)
"""
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import asyncio

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
    
    from core.services.database import get_database
    
    db = get_database()
    now = datetime.now(timezone.utc)
    results = {
        "timestamp": now.isoformat(),
        "tasks": {}
    }
    
    # ========== TASK 1: Expire Orders ==========
    try:
        expired_orders = await db._orders.get_pending_expired()
        cancelled_count = 0
        
        for order in expired_orders:
            try:
                # Release reserved stock if any
                if order.stock_item_id:
                    await asyncio.to_thread(
                        lambda sid=order.stock_item_id: db.client.table("stock_items").update({
                            "status": "available",
                            "reserved_at": None
                        }).eq("id", sid).eq("status", "reserved").execute()
                    )
                
                # Cancel the order
                await asyncio.to_thread(
                    lambda oid=order.id: db.client.table("orders").update({
                        "status": "cancelled"
                    }).eq("id", oid).eq("status", "pending").execute()
                )
                cancelled_count += 1
                logger.info(f"Expired order {order.id}")
                
            except Exception as e:
                logger.error(f"Failed to expire order {order.id}: {e}")
        
        # Also handle stale orders (no expires_at, older than 15 min - matches payment timeout)
        stale_orders = await db._orders.get_pending_stale(minutes=15)
        for order in stale_orders:
            try:
                if order.stock_item_id:
                    await asyncio.to_thread(
                        lambda sid=order.stock_item_id: db.client.table("stock_items").update({
                            "status": "available",
                            "reserved_at": None
                        }).eq("id", sid).eq("status", "reserved").execute()
                    )
                
                await asyncio.to_thread(
                    lambda oid=order.id: db.client.table("orders").update({
                        "status": "cancelled"
                    }).eq("id", oid).eq("status", "pending").execute()
                )
                cancelled_count += 1
                logger.info(f"Cancelled stale order {order.id}")
            except Exception as e:
                logger.error(f"Failed to cancel stale order {order.id}: {e}")
        
        results["tasks"]["expired_orders"] = cancelled_count
        
    except Exception as e:
        results["tasks"]["expire_orders_error"] = str(e)
        logger.error(f"Expire orders task failed: {e}")
    
    # ========== TASK 2: Auto-Allocate Stock ==========
    try:
        from core.services.domains.delivery import DeliveryService
        
        delivery_service = DeliveryService(db)
        
        # Get paid orders awaiting delivery
        paid_orders = await asyncio.to_thread(
            lambda: db.client.table("orders").select("*")
                .eq("status", "paid")
                .is_("delivered_at", "null")
                .execute()
        )
        
        allocated_count = 0
        for order_data in (paid_orders.data or []):
            order_id = order_data.get("id")
            try:
                # Check if order is confirmed (payment confirmed)
                if order_data.get("status") != "paid":
                    logger.info(f"Order {order_id} is still {order_data.get('status')} - skipping")
                    continue
                
                # Deliver goods
                result = await delivery_service.deliver_order(order_id)
                if result:
                    allocated_count += 1
                    logger.info(f"Delivered order {order_id}")
                    
            except Exception as e:
                logger.error(f"Failed to deliver order {order_id}: {e}")
        
        results["tasks"]["auto_allocated"] = allocated_count
        
    except Exception as e:
        results["tasks"]["auto_alloc_error"] = str(e)
        logger.error(f"Auto-alloc task failed: {e}")
    
    # ========== TASK 3: Update Exchange Rates (hourly) ==========
    try:
        # Only run on the hour (minute == 0 or 5)
        if now.minute < 10:
            from core.services.currency import CurrencyService
            
            currency_service = CurrencyService()
            updated = await currency_service.update_rates_if_stale()
            results["tasks"]["exchange_rates_updated"] = updated
    except Exception as e:
        results["tasks"]["exchange_rates_error"] = str(e)
        logger.error(f"Exchange rates update failed: {e}")
    
    results["success"] = True
    return JSONResponse(results)
