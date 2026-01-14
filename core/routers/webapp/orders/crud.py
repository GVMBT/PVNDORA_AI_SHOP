"""
Order CRUD Endpoints

Order history, status, and payment method endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import verify_telegram_auth
from core.errors import ERROR_FAILED_TO_FETCH_ORDERS, ERROR_ORDER_NOT_FOUND, ERROR_USER_NOT_FOUND
from core.services.database import get_database

from ..models import OrdersListResponse, OrderStatusResponse, PaymentMethod, PaymentMethodsResponse

logger = logging.getLogger(__name__)

crud_router = APIRouter()

# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


async def _check_balance_sufficiency(
    amount: float | None,
    user_currency: str,
    balance_currency: str,
    user_balance: float,
    currency_service,
) -> bool:
    """Check if balance is sufficient for order amount (reduces cognitive complexity)."""
    if not amount:
        return True

    if user_currency == balance_currency:
        return user_balance >= amount

    try:
        user_rate = await currency_service.get_exchange_rate(user_currency)
        balance_rate = await currency_service.get_exchange_rate(balance_currency)
        usd_amount = amount / user_rate if user_rate > 0 else amount
        amount_in_balance_currency = usd_amount * balance_rate
        return user_balance >= amount_in_balance_currency
    except Exception:
        return user_balance >= amount


def _get_user_currency(db_user, user, currency_service) -> str:
    """Get user's preferred currency (reduces cognitive complexity)."""
    user_lang = getattr(db_user, "interface_language", None) or (
        db_user.language_code if db_user and db_user.language_code else user.language_code
    )
    preferred_currency = getattr(db_user, "preferred_currency", None)
    return currency_service.get_user_currency(user_lang, preferred_currency)


async def _load_reviews_for_orders(db, order_ids: list[str]) -> dict[str, set]:
    """Load reviews for multiple orders in one query (reduces N+1)."""
    reviews_by_order: dict[str, set] = {}
    if not order_ids:
        return reviews_by_order

    try:
        all_reviews = (
            await db.client.table("reviews")
            .select("order_id, product_id")
            .in_("order_id", order_ids)
            .execute()
        )

        for review in all_reviews.data or []:
            order_id = review.get("order_id")
            product_id = review.get("product_id")
            if order_id not in reviews_by_order:
                reviews_by_order[order_id] = set()
            if product_id:
                reviews_by_order[order_id].add(product_id)
    except Exception as e:
        logger.warning("Failed to load reviews for orders: %s", type(e).__name__)

    return reviews_by_order


def _build_order_item(item: dict, order_status: str, reviewed_product_ids: set) -> dict:
    """Build APIOrderItem from order_item data (reduces cognitive complexity)."""
    prod = item.get("product")
    product_id = item.get("product_id")
    fulfillment_type = item.get("fulfillment_type", "instant")
    has_review = product_id in reviewed_product_ids

    return {
        "id": item.get("id"),
        "product_id": product_id,
        "product_name": prod.get("name") if prod else "Unknown",
        "quantity": item.get("quantity", 1),
        "price": float(item.get("price", 0)),
        "status": item.get("status", order_status),
        "fulfillment_type": fulfillment_type,
        "delivery_content": item.get("delivery_content"),
        "delivery_instructions": item.get("delivery_instructions"),
        "credentials": item.get("delivery_content"),
        "expires_at": item.get("expires_at"),
        "fulfillment_deadline": item.get("fulfillment_deadline"),
        "delivered_at": item.get("delivered_at"),
        "created_at": item.get("created_at"),
        "has_review": has_review,
    }


async def _process_order_row(
    row: dict,
    reviews_by_order: dict[str, set],
    user_currency: str,
    currency_service,
) -> dict | None:
    """Process a single order row and build order dict (reduces cognitive complexity)."""
    from core.logging import sanitize_id_for_logging

    items_data = row.get("order_items", [])

    if not items_data:
        logger.warning("Order %s has no order_items", sanitize_id_for_logging(str(row.get("id"))))
        return None

    # Get first product for main display
    first_item = items_data[0] if items_data else None
    product_data = first_item.get("product") if first_item else None

    # Get reviewed product IDs for this order (from pre-loaded data)
    order_id = row.get("id")
    reviewed_product_ids = reviews_by_order.get(order_id, set())

    # Build items using helper
    items = [_build_order_item(item, row["status"], reviewed_product_ids) for item in items_data]
    # Fix: Add fallback fulfillment_deadline from order
    for i, item in enumerate(items_data):
        if not items[i]["fulfillment_deadline"]:
            items[i]["fulfillment_deadline"] = row.get("fulfillment_deadline")

    # Build order dict using helper
    return await _build_order_dict(row, items, product_data, user_currency, currency_service)


def _build_balance_payment_method(
    user_balance: float,
    balance_currency: str,
    balance_display: str,
    balance_sufficient: bool,
) -> PaymentMethod:
    """Build balance payment method (reduces cognitive complexity)."""
    return PaymentMethod(
        id="balance",
        name="Баланс аккаунта",
        description=f"Доступно: {balance_display}",
        icon="wallet",
        available=balance_sufficient,
        min_amount=None,
        max_amount=user_balance,
        fee_percent=0,
        processing_time="Мгновенно",
        currency=balance_currency,
    )


def _build_card_payment_method(user_currency: str) -> PaymentMethod:
    """Build card payment method (reduces cognitive complexity)."""
    return PaymentMethod(
        id="card",
        name="Банковская карта",
        description="Visa, MasterCard, МИР",
        icon="credit-card",
        available=True,
        min_amount=10 if user_currency == "RUB" else 0.5,
        max_amount=100000 if user_currency == "RUB" else 5000,
        fee_percent=0,
        processing_time="1-5 минут",
        currency=user_currency,
    )


def _build_sbp_payment_method() -> PaymentMethod:
    """Build SBP payment method (reduces cognitive complexity)."""
    return PaymentMethod(
        id="sbp",
        name="СБП",
        description="Система быстрых платежей",
        icon="zap",
        available=True,
        min_amount=10,
        max_amount=600000,
        fee_percent=0,
        processing_time="Мгновенно",
        currency="RUB",
    )


def _build_crypto_payment_method(user_currency: str) -> PaymentMethod:
    """Build crypto payment method (reduces cognitive complexity)."""
    return PaymentMethod(
        id="crypto",
        name="Криптовалюта",
        description="BTC, ETH, USDT, TON",
        icon="bitcoin",
        available=True,
        min_amount=1 if user_currency == "USD" else 100,
        max_amount=None,
        fee_percent=0,
        processing_time="10-30 минут",
        currency="USD",
    )


async def _build_order_dict(
    row: dict,
    items: list[dict],
    product_data: dict | None,
    user_currency: str,
    currency_service,
) -> dict:
    """Build APIOrder dict from order data (reduces cognitive complexity)."""
    usd_amount = float(row.get("amount", 0))
    fiat_amount = row.get("fiat_amount")
    fiat_currency_from_order = row.get("fiat_currency")

    if fiat_amount is not None and fiat_currency_from_order == user_currency:
        display_amount = float(fiat_amount)
    else:
        display_amount = await currency_service.convert_price(usd_amount, user_currency)

    return {
        "id": row["id"],
        "product_id": product_data.get("id") if product_data else None,
        "product_name": product_data.get("name") if product_data else "Multiple items",
        "amount": usd_amount,
        "amount_display": display_amount,
        "original_price": float(row.get("original_price", 0))
        if row.get("original_price")
        else None,
        "discount_percent": int(row.get("discount_percent", 0)),
        "status": row["status"],
        "order_type": row.get("order_type", "instant"),
        "created_at": row.get("created_at"),
        "expires_at": row.get("expires_at"),
        "fulfillment_deadline": row.get("fulfillment_deadline"),
        "delivered_at": row.get("delivered_at"),
        "warranty_until": row.get("warranty_until"),
        "payment_url": row.get("payment_url"),
        "payment_id": row.get("payment_id"),
        "payment_gateway": row.get("payment_gateway"),
        "items": items,
        "currency": user_currency,
    }


@crud_router.get("/orders/{order_id}/status")
async def get_webapp_order_status(
    order_id: str, user=Depends(verify_telegram_auth)
) -> OrderStatusResponse:
    """Get order status with delivery progress."""
    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail=ERROR_USER_NOT_FOUND)

    result = (
        await db.client.table("orders")
        .select("*, order_items(*)")
        .eq("id", order_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail=ERROR_ORDER_NOT_FOUND)

    order = result.data

    if order["user_id"] != db_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Calculate delivery progress
    items_data = order.get("order_items", [])
    total_quantity = sum(item.get("quantity", 0) for item in items_data)
    delivered_quantity = sum(item.get("delivered_quantity", 0) for item in items_data)

    progress = 0
    if total_quantity > 0:
        progress = int((delivered_quantity / total_quantity) * 100)

    # Calculate estimated delivery
    estimated_delivery_at = None
    if order["status"] in ("paid", "processing", "partially_delivered"):
        max_hours = 0
        for item in items_data:
            hours = item.get("fulfillment_time_hours") or 24
            max_hours = max(max_hours, hours)

        paid_at = order.get("paid_at") or order.get("created_at")
        if paid_at:
            try:
                paid_dt = datetime.fromisoformat(paid_at.replace("Z", "+00:00"))
                est_dt = paid_dt + timedelta(hours=max_hours)
                estimated_delivery_at = est_dt.isoformat()
            except Exception:
                pass

    return OrderStatusResponse(
        order_id=order_id,
        status=order["status"],
        progress=progress,
        delivered_quantity=delivered_quantity,
        total_quantity=total_quantity,
        estimated_delivery_at=estimated_delivery_at,
        payment_url=order.get("payment_url"),
    )


# Helper to process confirmed payment (reduces cognitive complexity)
async def _process_confirmed_payment(order_id: str, payment_id: str, db) -> dict:
    """Process confirmed payment and queue delivery."""
    from core.orders.status_service import OrderStatusService

    status_service = OrderStatusService(db)
    final_status = await status_service.mark_payment_confirmed(
        order_id=order_id, payment_id=payment_id, check_stock=True
    )

    try:
        from core.queue import WorkerEndpoints, publish_to_worker

        await publish_to_worker(
            endpoint=WorkerEndpoints.DELIVER_GOODS,
            body={"order_id": order_id},
            retries=2,
            deduplication_id=f"deliver-{order_id}",
        )
    except Exception as e:
        error_type = type(e).__name__
        logger.warning(
            "Failed to queue delivery: %s",
            error_type,
        )

    return {"status": final_status, "verified": True}


# Helper to verify crystalpay payment (reduces cognitive complexity)
async def _verify_crystalpay_payment(payment_id: str, order_id: str, order_status: str, db) -> dict:
    """Verify payment via CrystalPay gateway (reduces cognitive complexity)."""
    from core.routers.deps import get_payment_service

    payment_service = get_payment_service()
    try:
        invoice_info = await payment_service.get_invoice_info(payment_id)
        if invoice_info:
            gateway_status = invoice_info.get("state", "")
            return await _handle_gateway_status(
                gateway_status, order_id, order_status, payment_id, db
            )
    except Exception as e:
        error_type = type(e).__name__
        logger.warning(
            "Failed to verify payment: %s",
            error_type,
        )
    return {"status": order_status, "verified": False, "message": "Verification failed"}


# Helper to handle gateway status (reduces cognitive complexity)
async def _handle_gateway_status(
    gateway_status: str, order_id: str, order_status: str, payment_id: str, db
) -> dict:
    """Handle different gateway payment statuses."""
    if gateway_status == "payed":
        return await _process_confirmed_payment(order_id, payment_id, db)

    if gateway_status == "processing":
        return {
            "status": "processing",
            "verified": False,
            "message": "Payment is being processed",
        }

    if gateway_status in ("notpayed", "failed"):
        return {
            "status": order_status,
            "verified": False,
            "message": "Payment not received",
        }

    return {
        "status": order_status,
        "verified": False,
        "message": "Unknown payment status",
    }


@crud_router.post("/orders/{order_id}/verify-payment")
async def verify_order_payment(order_id: str, user=Depends(verify_telegram_auth)):
    """
    Manually verify payment status via payment gateway.
    Useful for checking payment on popup/window close.
    """
    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail=ERROR_USER_NOT_FOUND)

    result = await db.client.table("orders").select("*").eq("id", order_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=ERROR_ORDER_NOT_FOUND)

    order = result.data

    if order["user_id"] != db_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if order["status"] in ("paid", "delivered", "completed"):
        return {"status": order["status"], "verified": True}

    payment_id = order.get("payment_id")
    payment_gateway = order.get("payment_gateway")

    if not payment_id:
        return {"status": order["status"], "verified": False, "message": "No payment_id"}

    if payment_gateway == "crystalpay":
        return await _verify_crystalpay_payment(payment_id, order_id, order["status"], db)

    return {"status": order["status"], "verified": False, "message": "Unknown gateway"}


@crud_router.get("/orders")
async def get_webapp_orders(
    user=Depends(verify_telegram_auth),
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> OrdersListResponse:
    """Get user's order history with filtering."""
    from core.db import get_redis
    from core.services.currency import get_currency_service

    db = get_database()
    redis = get_redis()
    currency_service = get_currency_service(redis)

    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user:
        raise HTTPException(status_code=404, detail=ERROR_USER_NOT_FOUND)

    # Build query
    query = (
        db.client.table("orders")
        .select("*, order_items(*, product:products(*))")
        .eq("user_id", db_user.id)
    )

    if status:
        query = query.eq("status", status)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

    try:
        result = await query.execute()
    except Exception as e:
        from core.logging import sanitize_id_for_logging

        logger.error(
            "Failed to fetch orders for user %s: %s",
            sanitize_id_for_logging(str(db_user.id)),
            type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=ERROR_FAILED_TO_FETCH_ORDERS)

    user_currency = _get_user_currency(db_user, user, currency_service)

    if not result.data:
        from core.logging import sanitize_id_for_logging

        logger.info("No orders found for user %s", sanitize_id_for_logging(str(db_user.id)))
        return OrdersListResponse(orders=[], count=0, currency=user_currency)

    orders = []

    # OPTIMIZATION: Fix N+1 query problem - load all reviews for all orders in one query
    order_ids = [row.get("id") for row in result.data if row.get("id")]
    reviews_by_order = await _load_reviews_for_orders(db, order_ids)

    for row in result.data:
        try:
            order_dict = await _process_order_row(
                row, reviews_by_order, user_currency, currency_service
            )
            if order_dict:
                orders.append(order_dict)
        except Exception as e:
            from core.logging import sanitize_id_for_logging

            logger.error(
                "Failed to process order %s: %s",
                sanitize_id_for_logging(str(row.get("id"))),
                type(e).__name__,
                exc_info=True,
            )
            continue

    from core.logging import sanitize_id_for_logging

    logger.info(
        "Returning %d orders for user %s", len(orders), sanitize_id_for_logging(str(db_user.id))
    )

    return OrdersListResponse(orders=orders, count=len(orders), currency=user_currency)


@crud_router.get("/payments/methods")
async def get_payment_methods(
    user=Depends(verify_telegram_auth),
    amount: float | None = Query(
        None, description="Order amount in user's currency for availability check"
    ),
    currency: str | None = Query(None, description="Currency code (RUB, USD, etc)"),
) -> PaymentMethodsResponse:
    """
    Get available payment methods for user based on their region and balance.
    Returns methods sorted by preference for the user's locale.
    """
    from core.db import get_redis
    from core.services.currency import get_currency_service

    db = get_database()
    redis = get_redis()
    currency_service = get_currency_service(redis)

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail=ERROR_USER_NOT_FOUND)

    # Determine user's currency
    user_lang = getattr(db_user, "interface_language", None) or (
        db_user.language_code if db_user and db_user.language_code else user.language_code
    )
    preferred_currency = getattr(db_user, "preferred_currency", None)
    user_currency = currency or currency_service.get_user_currency(user_lang, preferred_currency)

    # Get user balance
    user_balance = float(db_user.balance or 0)
    balance_currency = getattr(db_user, "balance_currency", "USD") or "USD"

    methods = []

    if user_balance > 0:
        balance_display = currency_service.format_price(user_balance, balance_currency)
        balance_sufficient = await _check_balance_sufficiency(
            amount, user_currency, balance_currency, user_balance, currency_service
        )
        methods.append(
            _build_balance_payment_method(
                user_balance, balance_currency, balance_display, balance_sufficient
            )
        )

    # 2. CrystalPay card payment
    methods.append(_build_card_payment_method(user_currency))

    # 3. SBP (for Russian users)
    if user_currency == "RUB" or user_lang in ("ru", "ru-RU"):
        methods.append(_build_sbp_payment_method())

    # 4. Crypto
    methods.append(_build_crypto_payment_method(user_currency))

    # Calculate default recommendation
    recommended = "card"
    if user_balance > 0 and amount and user_balance >= amount:
        recommended = "balance"
    elif user_currency == "RUB":
        recommended = "sbp"

    return PaymentMethodsResponse(
        methods=methods, default_currency=user_currency, recommended_method=recommended
    )
