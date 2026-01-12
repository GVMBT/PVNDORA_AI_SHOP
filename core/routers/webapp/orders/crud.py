"""
Order CRUD Endpoints

Order history, status, and payment method endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import verify_telegram_auth
from core.services.database import get_database

from ..models import (
    OrdersListResponse,
    OrderStatusResponse,
    PaymentMethod,
    PaymentMethodsResponse,
)

logger = logging.getLogger(__name__)

crud_router = APIRouter()


@crud_router.get("/orders/{order_id}/status")
async def get_webapp_order_status(
    order_id: str, user=Depends(verify_telegram_auth)
) -> OrderStatusResponse:
    """Get order status with delivery progress."""
    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    result = (
        await db.client.table("orders")
        .select("*, order_items(*)")
        .eq("id", order_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Order not found")

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


@crud_router.post("/orders/{order_id}/verify-payment")
async def verify_order_payment(order_id: str, user=Depends(verify_telegram_auth)):
    """
    Manually verify payment status via payment gateway.
    Useful for checking payment on popup/window close.
    """
    from core.routers.deps import get_payment_service

    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.client.table("orders").select("*").eq("id", order_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Order not found")

    order = result.data

    if order["user_id"] != db_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Already processed
    if order["status"] in ("paid", "delivered", "completed"):
        return {"status": order["status"], "verified": True}

    # Check payment gateway status
    payment_id = order.get("payment_id")
    payment_gateway = order.get("payment_gateway")

    if not payment_id:
        return {"status": order["status"], "verified": False, "message": "No payment_id"}

    if payment_gateway == "crystalpay":
        payment_service = get_payment_service()
        try:
            invoice_info = await payment_service.get_invoice_info(payment_id)
            if invoice_info:
                gateway_status = invoice_info.get("state", "")

                if gateway_status == "payed":
                    # Payment confirmed by gateway - process it
                    from core.orders.status_service import OrderStatusService

                    status_service = OrderStatusService(db)
                    final_status = await status_service.mark_payment_confirmed(
                        order_id=order_id, payment_id=payment_id, check_stock=True
                    )

                    # Queue delivery
                    try:
                        from core.queue import WorkerEndpoints, publish_to_worker

                        await publish_to_worker(
                            endpoint=WorkerEndpoints.DELIVER_GOODS,
                            body={"order_id": order_id},
                            retries=2,
                            deduplication_id=f"deliver-{order_id}",
                        )
                    except Exception as e:
                        logger.warning(f"Failed to queue delivery for {order_id}: {e}")

                    return {"status": final_status, "verified": True}
                if gateway_status == "processing":
                    return {
                        "status": "processing",
                        "verified": False,
                        "message": "Payment is being processed",
                    }
                if gateway_status in ("notpayed", "failed"):
                    return {
                        "status": order["status"],
                        "verified": False,
                        "message": "Payment not received",
                    }
        except Exception as e:
            logger.warning(f"Failed to verify payment for order {order_id}: {e}")
            return {"status": order["status"], "verified": False, "message": "Verification failed"}

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
        raise HTTPException(status_code=404, detail="User not found")

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
        logger.error(f"Failed to fetch orders for user {db_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch orders")

    if not result.data:
        logger.info(f"No orders found for user {db_user.id} (telegram_id={user.id})")
        # Get user's preferred currency for empty response
        user_lang = getattr(db_user, "interface_language", None) or (
            db_user.language_code if db_user and db_user.language_code else user.language_code
        )
        preferred_currency = getattr(db_user, "preferred_currency", None)
        user_currency = currency_service.get_user_currency(user_lang, preferred_currency)
        return OrdersListResponse(orders=[], count=0, currency=user_currency)

    # Get user's preferred currency
    user_lang = getattr(db_user, "interface_language", None) or (
        db_user.language_code if db_user and db_user.language_code else user.language_code
    )
    preferred_currency = getattr(db_user, "preferred_currency", None)
    user_currency = currency_service.get_user_currency(user_lang, preferred_currency)

    orders = []
    processed_count = 0
    error_count = 0

    # OPTIMIZATION: Fix N+1 query problem - load all reviews for all orders in one query
    order_ids = [row.get("id") for row in result.data if row.get("id")]
    reviews_by_order = {}
    if order_ids:
        try:
            all_reviews = (
                await db.client.table("reviews")
                .select("order_id, product_id")
                .in_("order_id", order_ids)
                .execute()
            )

            # Group reviews by order_id
            for review in all_reviews.data or []:
                order_id = review.get("order_id")
                product_id = review.get("product_id")
                if order_id not in reviews_by_order:
                    reviews_by_order[order_id] = set()
                if product_id:
                    reviews_by_order[order_id].add(product_id)
        except Exception as e:
            logger.warning(f"Failed to load reviews for orders: {e}")

    for row in result.data:
        try:
            items_data = row.get("order_items", [])

            if not items_data:
                logger.warning(f"Order {row.get('id')} has no order_items")
                continue

            # Get first product for main display
            first_item = items_data[0] if items_data else None
            product_data = first_item.get("product") if first_item else None

            # Build items list in APIOrderItem format
            items = []

            # Get reviewed product IDs for this order (from pre-loaded data)
            order_id = row.get("id")
            reviewed_product_ids = reviews_by_order.get(order_id, set())

            for item in items_data:
                prod = item.get("product")
                product_id = item.get("product_id")
                # fulfillment_type is stored in order_items table, not calculated from instant_quantity
                fulfillment_type = item.get("fulfillment_type", "instant")

                # Check if this product in this order has a review
                has_review = product_id in reviewed_product_ids

                items.append(
                    {
                        "id": item.get("id"),
                        "product_id": product_id,
                        "product_name": prod.get("name") if prod else "Unknown",
                        "quantity": item.get("quantity", 1),
                        "price": float(
                            item.get("price", 0)
                        ),  # Use 'price' column from DB, not 'amount'
                        "status": item.get("status", row["status"]),
                        "fulfillment_type": fulfillment_type,
                        "delivery_content": item.get("delivery_content"),
                        "delivery_instructions": item.get("delivery_instructions"),
                        "credentials": item.get("delivery_content"),  # Alias
                        "expires_at": item.get("expires_at"),
                        "fulfillment_deadline": item.get("fulfillment_deadline")
                        or row.get("fulfillment_deadline"),  # Fallback to order-level deadline
                        "delivered_at": item.get("delivered_at"),
                        "created_at": item.get("created_at"),
                        "has_review": has_review,
                    }
                )

            # Use fiat_amount if available (what user actually paid), otherwise convert from USD
            usd_amount = float(row.get("amount", 0))
            fiat_amount = row.get("fiat_amount")
            fiat_currency_from_order = row.get("fiat_currency")

            if fiat_amount is not None and fiat_currency_from_order == user_currency:
                # Use the exact amount user paid (in their currency)
                display_amount = float(fiat_amount)
            else:
                # Fallback: convert from USD
                display_amount = await currency_service.convert_price(usd_amount, user_currency)

            # Build order in APIOrder format
            order_dict = {
                "id": row["id"],
                "product_id": product_data.get("id") if product_data else None,
                "product_name": product_data.get("name") if product_data else "Multiple items",
                "amount": usd_amount,  # USD amount
                "amount_display": display_amount,  # Converted amount (number)
                "original_price": (
                    float(row.get("original_price", 0)) if row.get("original_price") else None
                ),
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

            orders.append(order_dict)
            processed_count += 1
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to process order {row.get('id')}: {e}", exc_info=True)
            # Continue processing other orders instead of failing entirely
            continue

    logger.info(f"Returning {len(orders)} orders for user {db_user.id}")

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
        raise HTTPException(status_code=404, detail="User not found")

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

    # 1. Balance payment (always available if > 0)
    if user_balance > 0:
        balance_display = currency_service.format_price(user_balance, balance_currency)

        # Check if balance is sufficient for the order
        balance_sufficient = True
        if amount:
            # Convert amount to balance currency
            if user_currency == balance_currency:
                amount_in_balance_currency = amount
            else:
                # First convert user's currency amount to USD, then to balance currency
                try:
                    user_rate = await currency_service.get_exchange_rate(user_currency)
                    balance_rate = await currency_service.get_exchange_rate(balance_currency)
                    usd_amount = amount / user_rate if user_rate > 0 else amount
                    amount_in_balance_currency = usd_amount * balance_rate
                except Exception:
                    amount_in_balance_currency = amount

            balance_sufficient = user_balance >= amount_in_balance_currency

        methods.append(
            PaymentMethod(
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
        )

    # 2. CrystalPay card payment
    methods.append(
        PaymentMethod(
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
    )

    # 3. SBP (for Russian users)
    if user_currency == "RUB" or user_lang in ("ru", "ru-RU"):
        methods.append(
            PaymentMethod(
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
        )

    # 4. Crypto
    methods.append(
        PaymentMethod(
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
    )

    # Calculate default recommendation
    recommended = "card"
    if user_balance > 0 and amount and user_balance >= amount:
        recommended = "balance"
    elif user_currency == "RUB":
        recommended = "sbp"

    return PaymentMethodsResponse(
        methods=methods, default_currency=user_currency, recommended_method=recommended
    )
