"""
Cron: Check pending CrystalPay payments.

Since CrystalPay webhook may not work reliably, poll invoice status via API.
Runs every 1 minute to check pending orders.
"""
import os
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)

router = APIRouter()

CRYSTALPAY_API_URL = os.environ.get("CRYSTALPAY_API_URL", "https://api.crystalpay.io/v3")
CRYSTALPAY_LOGIN = os.environ.get("CRYSTALPAY_LOGIN", "")
CRYSTALPAY_SECRET = os.environ.get("CRYSTALPAY_SECRET", "")


async def check_invoice_status(invoice_id: str) -> dict:
    """Check invoice status via CrystalPay API."""
    try:
        payload = {
            "auth_login": CRYSTALPAY_LOGIN,
            "auth_secret": CRYSTALPAY_SECRET,
            "id": invoice_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CRYSTALPAY_API_URL}/invoice/info/",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data.get("error"):
                    return {
                        "success": True,
                        "state": data.get("state"),
                        "amount": data.get("amount"),
                        "rub_amount": data.get("rub_amount"),
                        "currency": data.get("currency")
                    }
        
        return {"success": False, "error": "API error"}
    except Exception as e:
        logger.error(f"Invoice check error: {e}")
        return {"success": False, "error": str(e)}


async def process_paid_order(db, order_id: str, order_data: dict):
    """Process a paid order - update status and schedule delivery."""
    try:
        source_channel = order_data.get("source_channel")
        
        # Update order status to paid
        await asyncio.to_thread(
            lambda: db.client.table("orders").update({
                "status": "paid",
                "payment_confirmed_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", order_id).execute()
        )
        
        logger.info(f"Order {order_id} marked as paid via polling")
        
        # For discount orders - schedule delayed delivery
        if source_channel == "discount":
            from core.services.domains import DiscountOrderService
            import random
            
            delay_seconds = random.randint(3600, 14400)  # 1-4 hours
            
            discount_service = DiscountOrderService(db.client)
            result = await discount_service.schedule_delayed_delivery(
                order_id=order_id,
                delay_seconds=delay_seconds
            )
            
            if result.get("success"):
                logger.info(f"Discount order {order_id} scheduled for delayed delivery")
            else:
                logger.warning(f"Failed to schedule discount delivery: {result}")
        else:
            # Premium orders - instant delivery via QStash
            from core.qstash import publish_to_worker, WorkerEndpoints
            
            await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": order_id},
                retries=2,
                deduplication_id=f"deliver-{order_id}"
            )
            logger.info(f"Order {order_id} sent to delivery worker")
        
        # Send notification to user
        try:
            from core.bot.handlers.notifications import send_payment_confirmation
            user_telegram_id = order_data.get("user_telegram_id")
            if user_telegram_id:
                await send_payment_confirmation(user_telegram_id, order_id)
        except Exception as notify_err:
            logger.warning(f"Failed to send payment notification: {notify_err}")
            
    except Exception as e:
        logger.error(f"Failed to process paid order {order_id}: {e}")


@router.get("/api/cron/check-pending-payments")
@router.post("/api/cron/check-pending-payments")
async def check_pending_payments():
    """
    Check pending CrystalPay orders and update their status.
    
    This is a fallback when webhook doesn't work.
    """
    if not CRYSTALPAY_LOGIN or not CRYSTALPAY_SECRET:
        logger.warning("CrystalPay credentials not configured")
        return {"ok": False, "error": "Not configured"}
    
    try:
        db = get_database()
        
        # Get pending orders with payment_id (CrystalPay invoice)
        # Only check orders created in last 2 hours (invoice lifetime)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=2)
        
        result = await asyncio.to_thread(
            lambda: db.client.table("orders")
            .select("id, payment_id, source_channel, user_telegram_id, amount")
            .eq("status", "pending")
            .eq("payment_gateway", "crystalpay")
            .not_.is_("payment_id", "null")
            .gte("created_at", cutoff_time.isoformat())
            .limit(20)
            .execute()
        )
        
        pending_orders = result.data or []
        
        if not pending_orders:
            return {"ok": True, "checked": 0, "paid": 0}
        
        logger.info(f"Checking {len(pending_orders)} pending CrystalPay orders")
        
        paid_count = 0
        
        for order in pending_orders:
            order_id = order["id"]
            invoice_id = order["payment_id"]
            
            # Check invoice status
            status_result = await check_invoice_status(invoice_id)
            
            if status_result.get("success"):
                state = status_result.get("state", "").lower()
                
                if state == "payed":
                    # Invoice is paid! Process the order
                    logger.info(f"Invoice {invoice_id} is PAID - processing order {order_id}")
                    await process_paid_order(db, order_id, order)
                    paid_count += 1
                elif state in ["cancelled", "failed"]:
                    # Invoice cancelled/failed - update order
                    await asyncio.to_thread(
                        lambda: db.client.table("orders").update({
                            "status": "cancelled",
                            "notes": f"Payment {state}"
                        }).eq("id", order_id).execute()
                    )
                    logger.info(f"Order {order_id} marked as cancelled (invoice {state})")
            
            # Small delay between API calls
            await asyncio.sleep(0.2)
        
        return {
            "ok": True,
            "checked": len(pending_orders),
            "paid": paid_count
        }
        
    except Exception as e:
        logger.error(f"Check pending payments error: {e}")
        return {"ok": False, "error": str(e)}
