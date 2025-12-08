"""
Auto Allocation Cron Job
Schedule: */10 * * * * (every 10 minutes) on Pro

Tasks:
- Attempt to deliver waiting order_items (pending/prepaid/fulfilling) for all products.
- Uses same delivery helper as worker_deliver_batch (no QStash signature needed here).
"""
import os
import asyncio
from fastapi import Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

CRON_SECRET = os.environ.get("CRON_SECRET", "")


async def handler(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from src.services.database import get_database
    from core.routers.deps import get_notification_service
    from core.routers.workers import _deliver_items_for_order
    
    db = get_database()
    notification_service = get_notification_service()
    
    try:
        open_items = await asyncio.to_thread(
            lambda: db.client.table("order_items")
            .select("order_id")
            .in_("status", ["pending", "prepaid", "fulfilling"])
            .order("created_at")
            .limit(200)
            .execute()
        )
        order_ids = list({row["order_id"] for row in (open_items.data or [])})
    except Exception as e:
        return JSONResponse({"error": f"failed to query open items: {e}"}, status_code=500)
    
    results = []
    for oid in order_ids:
        try:
            res = await _deliver_items_for_order(db, notification_service, oid, only_instant=False)
            results.append({"order_id": oid, **res})
        except Exception as e:
            results.append({"order_id": oid, "error": str(e)})
    
    return JSONResponse({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processed": len(order_ids),
        "results": results
    })

