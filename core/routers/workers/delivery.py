"""
Delivery Workers

QStash workers for order delivery operations.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
from fastapi import APIRouter, Request

from core.services.database import get_database
from core.routers.deps import verify_qstash, get_notification_service
from core.logging import get_logger

logger = get_logger(__name__)

delivery_router = APIRouter()


@delivery_router.post("/deliver-goods")
async def worker_deliver_goods(request: Request):
    """
    QStash Worker: Deliver digital goods after payment.
    Called by QStash with guaranteed delivery.
    """
    data = await verify_qstash(request)
    order_id = data.get("order_id")
    
    if not order_id:
        return {"error": "order_id required"}
    
    db = get_database()
    notification_service = get_notification_service()
    
    # Import from router module to get the shared function
    from .router import _deliver_items_for_order
    
    result = await _deliver_items_for_order(db, notification_service, order_id, only_instant=True)
    return {"success": True, "order_id": order_id, **result}


@delivery_router.post("/deliver-batch")
async def worker_deliver_batch(request: Request):
    """
    QStash Worker: Try to deliver all waiting items (pending/prepaid), any fulfillment_type.
    Useful for auto-allocation when stock is replenished.
    """
    await verify_qstash(request)  # Verify QStash signature
    
    db = get_database()
    notification_service = get_notification_service()
    
    # Import from router module
    from .router import _deliver_items_for_order
    
    # Найти открытые позиции
    try:
        open_items = await db.client.table("order_items").select(
            "order_id"
        ).in_("status", ["pending", "prepaid", "partial"]).order(
            "created_at"
        ).limit(200).execute()
        order_ids = list({row["order_id"] for row in (open_items.data or [])})
    except Exception as e:
        return {"error": f"failed to query open items: {e}"}
    
    results = []
    for oid in order_ids:
        res = await _deliver_items_for_order(db, notification_service, oid, only_instant=False)
        results.append({"order_id": oid, **res})
    
    return {"processed": len(order_ids), "results": results}
