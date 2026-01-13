"""
Cron: Check pending CrystalPay payments.

Since CrystalPay webhook may not work reliably, poll invoice status via API.
Runs every 1 minute to check pending orders.
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger
from core.services.database import get_database_async

logger = get_logger(__name__)

CRYSTALPAY_API_URL = os.environ.get("CRYSTALPAY_API_URL", "https://api.crystalpay.io/v3")
CRYSTALPAY_LOGIN = os.environ.get("CRYSTALPAY_LOGIN", "")
CRYSTALPAY_SECRET = os.environ.get("CRYSTALPAY_SECRET", "")
CRON_SECRET = os.environ.get("CRON_SECRET", "")
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")

# ASGI app for Vercel Cron
app = FastAPI()


async def send_discount_payment_confirmation(telegram_id: int, order_id: str):
    """Send payment confirmation via discount bot."""
    if not DISCOUNT_BOT_TOKEN:
        logger.warning("DISCOUNT_BOT_TOKEN not configured")
        return False

    text = (
        f"✅ <b>Оплата получена!</b>\n\n"
        f"Заказ #{order_id[:8]} оплачен.\n\n"
        f"⏳ Доставка в течение 1-4 часов.\n"
        f"Вы получите уведомление когда заказ будет готов."
    )

    url = f"https://api.telegram.org/bot{DISCOUNT_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": telegram_id, "text": text, "parse_mode": "HTML"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            return response.status_code == 200
    except Exception:
        logger.exception("Failed to send discount notification")
        return False


async def check_invoice_status(invoice_id: str) -> dict:
    """Check invoice status via CrystalPay API."""
    try:
        payload = {
            "auth_login": CRYSTALPAY_LOGIN,
            "auth_secret": CRYSTALPAY_SECRET,
            "id": invoice_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CRYSTALPAY_API_URL}/invoice/info/", json=payload, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"CrystalPay invoice {invoice_id} status: {data}")
                if not data.get("error"):
                    return {
                        "success": True,
                        "state": data.get("state"),
                        "amount": data.get("amount"),
                        "rub_amount": data.get("rub_amount"),
                        "currency": data.get("currency"),
                    }
                logger.warning(f"CrystalPay API error for {invoice_id}: {data}")

        return {"success": False, "error": "API error"}
    except Exception as e:
        logger.exception("Invoice check error")
        return {"success": False, "error": str(e)}


async def process_paid_order(db, order_id: str, order_data: dict):
    """Process a paid order - update status and schedule delivery."""
    try:
        source_channel = order_data.get("source_channel")

        # Update order status to paid
        await db.client.table("orders").update({"status": "paid"}).eq("id", order_id).execute()

        logger.info(f"Order {order_id} marked as paid via polling")

        # For discount orders - schedule delayed delivery
        if source_channel == "discount":
            from core.services.domains import DiscountOrderService

            # Get order_item info
            order_items = (
                await db.client.table("order_items")
                .select("id, product_id")
                .eq("order_id", order_id)
                .limit(1)
                .execute()
            )

            if order_items.data:
                order_item = order_items.data[0]

                # Find available stock item
                stock_result = (
                    await db.client.table("stock_items")
                    .select("id")
                    .eq("product_id", order_item["product_id"])
                    .eq("status", "available")
                    .is_("sold_at", "null")
                    .limit(1)
                    .execute()
                )

                if stock_result.data:
                    stock_item_id = stock_result.data[0]["id"]
                    telegram_id = order_data.get("user_telegram_id")

                    # Reserve stock item
                    await db.client.table("stock_items").update({"status": "reserved"}).eq(
                        "id", stock_item_id
                    ).execute()

                    # Schedule delayed delivery
                    discount_service = DiscountOrderService(db.client)
                    delivery_task = await discount_service.schedule_delayed_delivery(
                        order_id=order_id,
                        order_item_id=order_item["id"],
                        telegram_id=telegram_id,
                        stock_item_id=stock_item_id,
                    )

                    if delivery_task is not None:
                        logger.info(
                            f"Discount order {order_id} scheduled for delayed delivery "
                            f"in {delivery_task.delay_minutes} minutes"
                        )
                    else:
                        logger.warning(f"Failed to schedule discount delivery for order {order_id}")
                else:
                    logger.warning(f"No stock available for discount order {order_id}")
        else:
            # Premium orders - instant delivery via QStash
            from core.queue import WorkerEndpoints, publish_to_worker

            await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": order_id},
                retries=2,
                deduplication_id=f"deliver-{order_id}",
            )
            logger.info(f"Order {order_id} sent to delivery worker")

        # Note: Payment notifications are sent via OrderStatusService.mark_payment_confirmed
        # (called from webhook handlers). No need to send here.

    except Exception:
        logger.exception(f"Failed to process paid order {order_id}")


async def _process_invoice_state(
    db: Any, order_id_str: str, invoice_id_str: str, order_dict: dict[str, Any], state: str
) -> bool:
    """Process invoice state. Returns True if payment was processed."""
    if state == "payed":
        logger.info(f"Invoice {invoice_id_str} is PAID - processing order {order_id_str}")
        await process_paid_order(db, order_id_str, order_dict)
        return True

    if state in ["cancelled", "failed"]:
        await db.client.table("orders").update(
            {"status": "cancelled", "notes": f"Payment {state}"}
        ).eq("id", order_id_str).execute()
        logger.info(f"Order {order_id_str} marked as cancelled (invoice {state})")

    return False


async def _fetch_pending_orders(db: Any, cutoff_time: datetime) -> list[Any]:
    """Fetch pending CrystalPay orders."""
    result = (
        await db.client.table("orders")
        .select("id, payment_id, source_channel, user_telegram_id, amount")
        .eq("status", "pending")
        .eq("payment_gateway", "crystalpay")
        .not_.is_("payment_id", "null")
        .gte("created_at", cutoff_time.isoformat())
        .limit(20)
        .execute()
    )
    return result.data or []


@app.get("/api/cron/check_pending_payments")
async def check_pending_payments(request: Request):
    """Check pending CrystalPay orders and update their status."""
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    if not CRYSTALPAY_LOGIN or not CRYSTALPAY_SECRET:
        logger.warning("CrystalPay credentials not configured")
        return JSONResponse({"ok": False, "error": "Not configured"})

    try:
        db = await get_database_async()
        cutoff_time = datetime.now(UTC) - timedelta(hours=2)
        pending_orders = await _fetch_pending_orders(db, cutoff_time)

        if not pending_orders:
            logger.info("No pending CrystalPay orders to check")
            return JSONResponse({"ok": True, "checked": 0, "paid": 0})

        logger.info(f"Checking {len(pending_orders)} pending CrystalPay orders")
        paid_count = 0

        for order in pending_orders:
            if not isinstance(order, dict):
                continue
            order_dict = cast(dict[str, Any], order)
            order_id = order_dict.get("id")
            invoice_id = order_dict.get("payment_id")

            if not order_id or not invoice_id:
                continue

            status_result = await check_invoice_status(str(invoice_id))
            if status_result.get("success"):
                state = status_result.get("state", "").lower()
                if await _process_invoice_state(db, str(order_id), str(invoice_id), order_dict, state):
                    paid_count += 1

            await asyncio.sleep(0.2)

        return JSONResponse({"ok": True, "checked": len(pending_orders), "paid": paid_count})

    except Exception as e:
        logger.exception("Check pending payments error")
        return JSONResponse({"ok": False, "error": str(e)})
