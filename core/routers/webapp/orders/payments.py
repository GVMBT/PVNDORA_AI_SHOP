"""
Order Payment Endpoints

Order creation and payment processing.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import logging
import os
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException

from core.auth import verify_telegram_auth
from core.errors import ERROR_ORDER_NOT_FOUND, ERROR_PRODUCT_NOT_FOUND, ERROR_USER_NOT_FOUND
from core.payments import validate_gateway_config
from core.routers.deps import get_payment_service
from core.services.database import get_database
from core.services.money import to_decimal, to_float

from ..models import ConfirmPaymentRequest, CreateOrderRequest, OrderResponse
from .helpers import (
    calculate_discount_percent,
    cleanup_promo_and_cart,
    create_order_with_items,
    determine_target_currency,
    enforce_order_cooldown,
    format_product_names,
    get_partner_discount,
    process_external_payment,
    save_payment_info,
    set_order_cooldown,
    validate_and_prepare_cart_items,
)

logger = logging.getLogger(__name__)

payments_router = APIRouter()


@payments_router.post("/orders")
async def create_webapp_order(
    request: CreateOrderRequest,
    user=Depends(verify_telegram_auth),
    x_init_data: str = Header(None, alias="X-Init-Data"),
):
    """Create new order from Mini App. Supports both single product and cart-based orders."""
    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail=ERROR_USER_NOT_FOUND)

    payment_method = request.payment_method or "card"

    # Determine payment gateway - only needed for external payments
    # For balance payments, gateway is not used
    if payment_method != "balance":
        payment_gateway = request.payment_gateway or os.environ.get(
            "DEFAULT_PAYMENT_GATEWAY", "crystalpay"
        )
        # Normalize + validate gateway configuration
        payment_gateway = validate_gateway_config(payment_gateway)
    else:
        payment_gateway = None  # Not used for balance payments

    # Determine if user is in Telegram Mini App or external browser
    # If X-Init-Data is present, user is in Telegram Mini App
    # Otherwise, user is in external browser
    is_telegram_miniapp = bool(x_init_data)

    payment_service = get_payment_service()

    # Cart-based order
    if request.use_cart or (not request.product_id):
        return await _create_cart_order(
            db,
            db_user,
            user,
            payment_service,
            payment_method,
            payment_gateway or "crystalpay",
            is_telegram_miniapp=is_telegram_miniapp,
        )

    # Single product order
    return await _create_single_order(
        db,
        db_user,
        user,
        request,
        payment_service,
        payment_method,
        payment_gateway or "crystalpay",
        is_telegram_miniapp=is_telegram_miniapp,
    )


async def _create_cart_order(
    db,
    db_user,
    user,
    payment_service,
    payment_method: str,
    payment_gateway: str = "crystalpay",
    is_telegram_miniapp: bool = True,
) -> OrderResponse:
    """Create order from cart items."""
    from core.cart import get_cart_manager
    from core.db import get_redis
    from core.services.currency import get_currency_service

    cart_manager = get_cart_manager()
    cart = await cart_manager.get_cart(user.id)

    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Initialize services
    redis = get_redis()
    currency_service = get_currency_service(redis)

    # Get partner discount
    partner_discount = await get_partner_discount(db, db_user)

    # Determine target currency
    target_currency = determine_target_currency(
        db_user, user, payment_method, payment_gateway, currency_service
    )

    # Validate cart items and calculate totals
    (
        total_amount,
        total_original,
        total_fiat_amount,
        order_items,
    ) = await validate_and_prepare_cart_items(
        db, cart.items, cart, partner_discount, target_currency, currency_service
    )

    # Enforce cooldown
    cooldown_redis, cooldown_seconds = await enforce_order_cooldown(db, db_user, user.id)

    # Format product names
    product_names = format_product_names(order_items)

    # After RUB-only migration: total_amount = total_fiat_amount (all in RUB)
    # Calculate discount percent
    discount_pct = calculate_discount_percent(total_fiat_amount, total_original)

    # Create order with items
    logger.info(
        f"[DEBUG-HYP-E] Order created, before payment processing: payment_method={payment_method}, total_amount={total_fiat_amount}"
    )
    order = await create_order_with_items(
        db=db,
        db_user=db_user,
        user_id=user.id,
        total_amount=total_fiat_amount,
        total_original=total_original,
        discount_pct=discount_pct,
        payment_method=payment_method,
        payment_gateway=payment_gateway,
        order_items=order_items,
    )

    logger.info(
        f"[DEBUG-HYP-E] Order created: order_id={order.id}, payment_method={payment_method}, total_amount={total_amount}"
    )

    # Process payment based on method
    if payment_method == "balance":
        logger.info(f"[DEBUG-HYP-E] Entering balance payment processing: order_id={order.id}")
        return await _process_balance_payment(
            db,
            db_user,
            user,
            order,
            total_amount,
            total_original,
            discount_pct,
            payment_method,
            cart,
            cart_manager,
            order_items,
        )

    # External payment processing
    logger.info(
        f"[DEBUG-HYP-D] Entering external payment creation: order_id={order.id}, payment_gateway={payment_gateway}"
    )
    payment_url, invoice_id = await process_external_payment(
        payment_service=payment_service,
        order_id=order.id,
        payable_amount=total_fiat_amount,
        product_names=product_names,
        payment_gateway=payment_gateway,
        user_id=user.id,
        gateway_currency=target_currency,
        is_telegram_miniapp=is_telegram_miniapp,
        db=db,
    )

    # Save payment info
    await save_payment_info(db, order.id, payment_url, invoice_id)

    # Set cooldown
    await set_order_cooldown(cooldown_redis, user.id, cooldown_seconds)

    # Cleanup promo and cart
    logger.info(
        f"[DEBUG-HYP-E] Before external payment promo/cart cleanup: has_promo={bool(cart.promo_code)}"
    )
    await cleanup_promo_and_cart(db, cart_manager, user.id, cart)

    # Return response
    logger.info(
        f"[DEBUG-HYP-E] Returning OrderResponse for external payment: order_id={order.id}, has_payment_url={bool(payment_url)}"
    )
    response = OrderResponse(
        order_id=order.id,
        amount=to_float(total_amount),
        original_price=to_float(total_original),
        discount_percent=discount_pct,
        payment_url=payment_url,
        payment_method=payment_method,
    )
    logger.info(
        f"Returning order response for {order.id}: payment_url present={bool(payment_url)}, method={payment_method}"
    )
    return response


async def _process_balance_payment(
    db,
    db_user,
    user,
    order,
    total_amount,
    total_original,
    discount_pct,
    payment_method,
    cart,
    cart_manager,
    _order_items,
) -> OrderResponse:
    """Process balance payment for an order."""
    # #region agent log
    logger.info(
        f"[DEBUG-HYP-E] _process_balance_payment entry: order_id={order.id}, user_id={db_user.id}"
    )
    # #endregion
    from core.db import get_redis
    from core.services.currency import get_currency_service

    _redis = get_redis()
    _currency_service = get_currency_service(_redis)

    # Get user's balance in their local currency
    user_balance = to_decimal(db_user.balance) if db_user.balance else Decimal("0")
    balance_currency = getattr(db_user, "balance_currency", "RUB") or "RUB"  # Default RUB after currency migration

    # Get order total in user's balance currency
    order_total_usd = to_decimal(total_amount)

    if balance_currency == "USD":
        order_total_in_balance_currency = order_total_usd
    else:
        rate = await _currency_service.get_exchange_rate(balance_currency)
        order_total_in_balance_currency = to_decimal(to_float(order_total_usd) * rate)
        if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
            order_total_in_balance_currency = to_decimal(
                round(to_float(order_total_in_balance_currency))
            )

    # #region agent log
    logger.info(
        f"[DEBUG-HYP-A] Before balance check: user_balance={user_balance}, order_total={order_total_in_balance_currency}, balance_currency={balance_currency}"
    )
    # #endregion

    # Compare in user's balance currency
    if user_balance < order_total_in_balance_currency:
        await db.client.table("orders").delete().eq("id", order.id).execute()

        balance_formatted = _currency_service.format_price(to_float(user_balance), balance_currency)
        amount_formatted = _currency_service.format_price(
            to_float(order_total_in_balance_currency), balance_currency
        )
        error_msg = f"Недостаточно средств на балансе. Доступно: {balance_formatted}, требуется: {amount_formatted}"

        raise HTTPException(status_code=400, detail=error_msg)

    # Deduct from balance
    # #region agent log
    logger.info(
        f"[DEBUG-HYP-A] Before RPC add_to_user_balance: user_id={db_user.id}, amount={-to_float(order_total_in_balance_currency)}"
    )
    # #endregion
    try:
        await db.client.rpc(
            "add_to_user_balance",
            {
                "p_user_id": db_user.id,
                "p_amount": -to_float(order_total_in_balance_currency),
                "p_reason": f"Payment for order {order.id}",
            },
        ).execute()
        # #region agent log
        logger.info(f"[DEBUG-HYP-A] RPC add_to_user_balance success: order_id={order.id}")
        # #endregion
        logger.info(
            f"Balance deducted {to_float(order_total_in_balance_currency):.2f} {balance_currency} for order {order.id}"
        )
    except Exception as e:
        # #region agent log
        error_type = type(e).__name__
        logger.exception(f"[DEBUG-HYP-A] RPC add_to_user_balance FAILED: error_type={error_type}")
        # #endregion
        await db.client.table("orders").delete().eq("id", order.id).execute()
        logger.exception(f"Failed to deduct balance for order {order.id}")
        raise HTTPException(status_code=500, detail="Ошибка списания с баланса. Попробуйте позже.")

    # Update order status
    # #region agent log
    try:
        from core.orders.status_service import OrderStatusService

        status_service = OrderStatusService(db)
        final_status = await status_service.mark_payment_confirmed(
            order_id=order.id, payment_id=f"balance-{order.id}", check_stock=True
        )
        # #region agent log
        logger.info(f"Balance payment confirmed for order {order.id}, final_status={final_status}")
    except Exception as e:
        # #region agent log
        logger.error(
            f"Failed to mark payment confirmed for balance order {order.id}: {e}", exc_info=True
        )

    # Queue delivery via QStash
    try:
        from core.queue import WorkerEndpoints, publish_to_worker

        await publish_to_worker(
            endpoint=WorkerEndpoints.DELIVER_GOODS,
            body={"order_id": order.id},
            retries=2,
            deduplication_id=f"deliver-{order.id}",
        )
        logger.info(f"Delivery queued for balance payment order {order.id}")
    except Exception as e:
        logger.warning(f"QStash failed for balance order {order.id}, trying direct delivery: {e}")
        try:
            from core.routers.deps import get_notification_service
            from core.routers.workers import _deliver_items_for_order

            notification_service = get_notification_service()
            await _deliver_items_for_order(db, notification_service, order.id, only_instant=True)
        except Exception:
            logger.exception(f"Direct delivery also failed for order {order.id}")

    # Queue referral bonuses
    try:
        from core.queue import WorkerEndpoints, publish_to_worker

        await publish_to_worker(
            endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
            body={"order_id": order.id},
            retries=2,
            deduplication_id=f"referral-{order.id}",
        )
    except Exception as e:
        logger.warning(f"Failed to queue referral bonus for order {order.id}: {e}")

    # Apply promo code and clear cart
    # #region agent log
    logger.info(f"[DEBUG-HYP-C] Before promo/cart cleanup: has_promo={bool(cart.promo_code)}")
    # #endregion
    try:
        if cart.promo_code:
            await db.use_promo_code(cart.promo_code)
        await cart_manager.clear_cart(user.id)
        # #region agent log
        logger.info("[DEBUG-HYP-C] Promo/cart cleanup success")
        # #endregion
    except Exception as e:
        # #region agent log
        error_type = type(e).__name__
        logger.exception(f"[DEBUG-HYP-C] Promo/cart cleanup FAILED: error_type={error_type}")
        # #endregion
        logger.warning(f"Failed to cleanup promo/cart for order {order.id}: {e}")

    # #region agent log
    logger.info(f"[DEBUG-HYP-E] Returning OrderResponse: order_id={order.id}")
    # #endregion
    return OrderResponse(
        order_id=order.id,
        amount=to_float(total_amount),
        original_price=to_float(total_original),
        discount_percent=discount_pct,
        payment_url=None,
        payment_method=payment_method,
    )


async def _create_single_order(
    db,
    db_user,
    user,
    request: CreateOrderRequest,
    payment_service,
    payment_method: str,
    payment_gateway: str = "crystalpay",
    is_telegram_miniapp: bool = True,
) -> OrderResponse:
    """
    Create order for single product.

    Теперь весь поток идёт через корзину: добавляем товар в корзину
    (учитывая доступный сток) и оформляем заказ как cart checkout,
    чтобы не было рассинхрона с предзаказами/instant.
    """
    if not request.product_id:
        raise HTTPException(status_code=400, detail="product_id is required")

    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=ERROR_PRODUCT_NOT_FOUND)

    # Check product status
    product_status = getattr(product, "status", "active")

    if product_status == "discontinued":
        raise HTTPException(
            status_code=400, detail="Product is discontinued and no longer available for order."
        )

    if product_status == "coming_soon":
        raise HTTPException(
            status_code=400,
            detail="Product is coming soon. Please use waitlist to be notified when available.",
        )

    quantity = request.quantity or 1

    from core.cart import get_cart_manager

    cart_manager = get_cart_manager()

    # Add to cart
    available_stock = await db.get_available_stock_count(request.product_id)
    await cart_manager.add_item(
        user_telegram_id=user.id,
        product_id=request.product_id,
        product_name=product.name,
        quantity=quantity,
        available_stock=available_stock,
        unit_price=product.price,
        discount_percent=0.0,
    )

    # Apply promo code if provided
    if request.promo_code:
        promo = await db.validate_promo_code(request.promo_code)
        if not promo:
            raise HTTPException(status_code=400, detail="Invalid or expired promo code")
        await cart_manager.apply_promo_code(user.id, request.promo_code, promo["discount_percent"])

    # Checkout via cart
    return await _create_cart_order(
        db, db_user, user, payment_service, payment_method, payment_gateway, is_telegram_miniapp
    )


@payments_router.post("/orders/confirm-payment")
async def confirm_manual_payment(
    request: ConfirmPaymentRequest, user=Depends(verify_telegram_auth)
):
    """
    Confirm that user has made manual payment (H2H mode).

    This updates order status to indicate user claims payment was made.
    Actual confirmation happens via webhook from payment gateway.
    """
    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail=ERROR_USER_NOT_FOUND)

    # Get order and verify ownership
    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail=ERROR_ORDER_NOT_FOUND)

    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Order does not belong to user")

    # Only pending orders can be confirmed
    if order.status not in ["pending", "awaiting_payment"]:
        raise HTTPException(
            status_code=400, detail=f"Order status is {order.status}, cannot confirm"
        )

    # Update order status
    await (
        db.client.table("orders")
        .update(
            {
                "status": "payment_pending",
                "notes": "User confirmed manual payment, awaiting gateway confirmation",
            }
        )
        .eq("id", request.order_id)
        .execute()
    )

    return {
        "success": True,
        "message": "Payment confirmation received. Awaiting bank confirmation.",
    }
