"""Refund Expired Prepaid Items Cron Job
Schedule: */5 * * * * (every 5 minutes).

Tasks:
1. Find prepaid ORDER ITEMS where fulfillment_deadline has passed
2. Process refund (update item status, optionally order status, notify user)
3. Use add_to_user_balance RPC for atomic balance update
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

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

CRON_SECRET = os.environ.get("CRON_SECRET", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

app = FastAPI()


async def _get_user_balance_currency(db: Any, user_id: str | None) -> str:
    """Get user's balance currency."""
    if not user_id:
        return "RUB"
    try:
        user_result = (
            await db.client.table("users")
            .select("balance_currency")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if user_result.data and isinstance(user_result.data, dict):
            return user_result.data.get("balance_currency", "RUB") or "RUB"
    except Exception:
        pass
    return "RUB"


def _calculate_refund_amount(
    item_price: float,
    order_amount: float,
    order_fiat_amount: float | None,
    order_fiat_currency: str | None,
    balance_currency: str,
) -> int:
    """Calculate refund amount in user's currency."""
    if order_fiat_amount and order_fiat_currency == balance_currency and order_amount > 0:
        # Use proportional share of fiat_amount
        return round((item_price / order_amount) * order_fiat_amount)

    if balance_currency == "USD":
        return int(item_price)

    # Fallback: Get current exchange rate
    from core.db import get_redis
    from core.services.currency import get_currency_service

    redis = get_redis()
    currency_service = get_currency_service(redis)
    rate = currency_service.get_exchange_rate(balance_currency)
    return round(item_price * rate)


async def _update_order_status_after_refund(
    db: Any,
    order_id: str,
    user_id: str | None,
    processed_orders: set[str],
    results: dict[str, Any],
) -> None:
    """Update order status after refunding items.

    Logic:
    - If ALL items are in final state (delivered/refunded/cancelled):
      - If any item is 'delivered' → order.status = 'delivered'
      - Else (all refunded/cancelled) → order.status = 'refunded'
    - If some items still pending/prepaid → don't change order status
    """
    if order_id in processed_orders:
        return

    # Get all items for this order with their statuses
    all_items = (
        await db.client.table("order_items")
        .select("id, status")
        .eq("order_id", order_id)
        .execute()
    )

    if not all_items.data:
        processed_orders.add(order_id)
        return

    statuses = [item.get("status", "") for item in all_items.data if isinstance(item, dict)]
    pending_statuses = {"pending", "prepaid"}

    # Check if any items are still pending
    has_pending = any(s in pending_statuses for s in statuses)
    if has_pending:
        # Some items not yet processed - emit event but don't change order status
        if user_id:
            try:
                from core.realtime import emit_order_status_change

                await emit_order_status_change(order_id, user_id, "partial_refund")
            except Exception as e:
                logger.warning(f"Failed to emit order status change: {e}")
        processed_orders.add(order_id)
        return

    # All items in final state - determine new order status
    has_delivered = any(s == "delivered" for s in statuses)
    new_status = "delivered" if has_delivered else "refunded"

    update_data: dict[str, Any] = {"status": new_status}
    if new_status == "refunded":
        update_data["refund_reason"] = "Auto-refund: fulfillment deadline exceeded"

    await (
        db.client.table("orders")
        .update(update_data)
        .eq("id", order_id)
        .execute()
    )
    results["orders_updated"] += 1

    # Emit realtime event for frontend update
    if user_id:
        try:
            from core.realtime import emit_order_status_change

            await emit_order_status_change(order_id, user_id, new_status)
        except Exception as e:
            logger.warning(f"Failed to emit order status change: {e}")

    processed_orders.add(order_id)


async def _notify_user_refund(
    telegram_id: int | str,
    product_name: str,
    refund_amount: int,
    balance_currency: str,
) -> None:
    """Notify user about refund via Telegram."""
    if not TELEGRAM_TOKEN:
        return

    import httpx

    from core.services.currency import CURRENCY_SYMBOLS

    symbol = CURRENCY_SYMBOLS.get(balance_currency, balance_currency)
    if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
        amount_str = f"{int(refund_amount)} {symbol}"
    else:
        amount_str = f"{refund_amount:.2f} {symbol}"

    message = (
        f"💰 <b>Возврат средств</b>\n\n"
        f"Товар «{product_name}» не поступил в срок.\n"
        f"Сумма <b>{amount_str}</b> возвращена на ваш баланс.\n\n"
        f"<i>Приносим извинения за неудобства!</i>"
    )

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": telegram_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
    except Exception as e:
        logger.warning(f"Failed to notify user {telegram_id}: {e}")


async def _process_single_refund(
    db: Any,
    item: dict[str, Any],
    processed_orders: set[str],
    results: dict[str, Any],
) -> bool:
    """Process refund for a single expired item. Returns True on success."""
    from core.services.money import to_float

    order_data = item.get("orders") if isinstance(item.get("orders"), dict) else {}
    product_data = item.get("products") if isinstance(item.get("products"), dict) else {}

    item_id = item.get("id")
    order_id = item.get("order_id")
    if not item_id or not order_id:
        logger.warning(f"Missing item_id or order_id in item: {item}")
        return False

    user_id = order_data.get("user_id")
    telegram_id = order_data.get("user_telegram_id")
    item_price = to_float(item.get("price", 0))
    product_name = product_data.get("name", "Unknown")
    order_amount = to_float(order_data.get("amount", 0))
    fiat_amount_raw = order_data.get("fiat_amount")
    order_fiat_amount = to_float(fiat_amount_raw) if fiat_amount_raw is not None else None
    order_fiat_currency = order_data.get("fiat_currency")

    balance_currency = await _get_user_balance_currency(db, user_id)
    refund_amount = _calculate_refund_amount(
        item_price,
        order_amount,
        order_fiat_amount,
        order_fiat_currency,
        balance_currency,
    )

    # 1. Update order_item status to refunded
    await db.client.table("order_items").update({"status": "refunded"}).eq("id", item_id).execute()

    # 2. Credit user balance using RPC (atomic)
    if user_id and refund_amount > 0:
        await db.client.rpc(
            "add_to_user_balance",
            {
                "p_user_id": str(user_id),
                "p_amount": refund_amount,
                "p_reason": f"Авто-возврат: товар «{product_name}» не поступил в срок",
                "p_reference_type": "order_item",
                "p_reference_id": str(item_id),
                "p_metadata": {
                    "order_id": str(order_id),
                    "item_id": str(item_id),
                    "product_name": product_name,
                    "refund_type": "auto_expired",
                },
            },
        ).execute()

        # Emit profile update for balance change
        try:
            from core.realtime import emit_profile_update

            await emit_profile_update(str(user_id), {"balance_changed": True, "refund": True})
        except Exception as e:
            logger.warning(f"Failed to emit profile update: {e}")

    # 3. Update order status if all items are in final state
    await _update_order_status_after_refund(db, str(order_id), user_id, processed_orders, results)

    # 4. Notify user
    if telegram_id:
        await _notify_user_refund(telegram_id, product_name, refund_amount, balance_currency)

    logger.info(
        f"Auto-refunded item {item_id}: {refund_amount} {balance_currency} for {product_name}",
    )
    return True


@app.get("/api/cron/refund_expired_prepaid")
async def refund_expired_prepaid_entrypoint(request: Request) -> Response:
    """Vercel Cron entrypoint for refunding expired prepaid order items."""
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    from core.services.database import get_database_async

    db = await get_database_async()
    now = datetime.now(UTC)
    results: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "items_refunded": 0,
        "orders_updated": 0,
        "errors": [],
        "success": True,
    }

    try:
        # Step 1: Find orders with expired fulfillment_deadline
        # fulfillment_deadline is on orders table, not order_items!
        expired_orders = (
            await db.client.table("orders")
            .select("id")
            .in_("status", ["prepaid", "partial", "paid"])
            .not_.is_("fulfillment_deadline", "null")
            .lt("fulfillment_deadline", now.isoformat())
            .limit(100)
            .execute()
        )

        expired_order_ids = [
            str(o["id"]) for o in (expired_orders.data or []) if isinstance(o, dict) and o.get("id")
        ]

        if not expired_order_ids:
            logger.info("refund_expired_prepaid: No expired orders found")
            return JSONResponse(results)

        logger.info(f"refund_expired_prepaid: Found {len(expired_order_ids)} expired orders")

        # Step 2: Find undelivered items for these orders
        # Items can be 'pending' or 'prepaid' - both need refund if order deadline expired
        expired_items = (
            await db.client.table("order_items")
            .select(
                """
                id,
                order_id,
                price,
                product_id,
                products(name),
                orders(id, user_id, user_telegram_id, amount, fiat_amount, fiat_currency)
                """,
            )
            .in_("order_id", expired_order_ids)
            .in_("status", ["pending", "prepaid"])
            .limit(50)
            .execute()
        )

        processed_orders: set[str] = set()

        for item_raw in expired_items.data or []:
            if not isinstance(item_raw, dict):
                continue
            item = cast(dict[str, Any], item_raw)

            try:
                if await _process_single_refund(db, item, processed_orders, results):
                    results["items_refunded"] += 1
            except Exception as e:
                error_msg = f"Failed to refund item {item.get('id')}: {e}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append(error_msg)

    except Exception as e:
        logger.error(f"Cron job failed: {e}", exc_info=True)
        results["success"] = False
        results["error"] = str(e)

    return JSONResponse(results)
