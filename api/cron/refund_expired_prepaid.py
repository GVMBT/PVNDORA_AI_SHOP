"""
Refund Expired Prepaid Items Cron Job
Schedule: 0 * * * * (every hour)

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


async def _calculate_refund_amount(
    item_price: float,
    order_amount: float,
    order_fiat_amount: float | None,
    order_fiat_currency: str | None,
    balance_currency: str,
) -> int:
    """Calculate refund amount in user's currency."""
    if order_fiat_amount and order_fiat_currency == balance_currency and order_amount > 0:
        # Use proportional share of fiat_amount
        return int(round((item_price / order_amount) * order_fiat_amount))

    if balance_currency == "USD":
        return int(item_price)

    # Fallback: Get current exchange rate
    from core.db import get_redis
    from core.services.currency import get_currency_service

    redis = get_redis()
    currency_service = get_currency_service(redis)
    rate = await currency_service.get_exchange_rate(balance_currency)
    return int(round(item_price * rate))


async def _update_order_status_if_all_refunded(
    db: Any, order_id: str, processed_orders: set[str], results: dict[str, Any]
) -> None:
    """Update order status to refunded if all items are refunded."""
    if order_id in processed_orders:
        return

    remaining_items = (
        await db.client.table("order_items")
        .select("id")
        .eq("order_id", order_id)
        .not_.eq("status", "refunded")
        .execute()
    )

    if not remaining_items.data:
        await (
            db.client.table("orders")
            .update(
                {
                    "status": "refunded",
                    "refund_reason": "Auto-refund: fulfillment deadline exceeded",
                }
            )
            .eq("id", order_id)
            .execute()
        )
        results["orders_updated"] += 1

    processed_orders.add(order_id)


async def _notify_user_refund(
    telegram_id: int | str, product_name: str, refund_amount: int, balance_currency: str
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
    db: Any, item: dict[str, Any], processed_orders: set[str], results: dict[str, Any]
) -> bool:
    """Process refund for a single expired item. Returns True on success."""
    from core.services.money import to_float

    item_id = item.get("id")
    order_id = item.get("order_id")
    order_data = item.get("orders") if isinstance(item.get("orders"), dict) else {}
    product_data = item.get("products") if isinstance(item.get("products"), dict) else {}

    user_id = order_data.get("user_id")
    telegram_id = order_data.get("user_telegram_id")
    item_price = to_float(item.get("price", 0))
    product_name = product_data.get("name", "Unknown")
    order_amount = to_float(order_data.get("amount", 0))
    order_fiat_amount = (
        to_float(order_data.get("fiat_amount")) if order_data.get("fiat_amount") else None
    )
    order_fiat_currency = order_data.get("fiat_currency")

    balance_currency = await _get_user_balance_currency(db, user_id)
    refund_amount = await _calculate_refund_amount(
        item_price, order_amount, order_fiat_amount, order_fiat_currency, balance_currency
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
            },
        ).execute()

    # 3. Check if order should be marked as refunded
    await _update_order_status_if_all_refunded(db, order_id, processed_orders, results)

    # 4. Notify user
    if telegram_id:
        await _notify_user_refund(telegram_id, product_name, refund_amount, balance_currency)

    logger.info(
        f"Auto-refunded item {item_id}: {refund_amount} {balance_currency} for {product_name}"
    )
    return True


@app.get("/api/cron/refund_expired_prepaid")
async def refund_expired_prepaid_entrypoint(request: Request):
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
                """
            )
            .eq("status", "prepaid")
            .lt("fulfillment_deadline", now.isoformat())
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
