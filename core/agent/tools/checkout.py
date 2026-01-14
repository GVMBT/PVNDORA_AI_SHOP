"""
Checkout & Payment Tools for Shop Agent.

Order creation, payment processing, balance payments.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from langchain_core.tools import tool

from core.logging import get_logger
from core.payments import GATEWAY_CURRENCY
from core.services.money import divide, multiply, round_money, subtract, to_decimal, to_float

from .base import get_db, get_user_context

logger = get_logger(__name__)


# Helper: Get partner discount from referrer (reduces cognitive complexity)
async def _get_partner_discount(db: Any, db_user: dict) -> int:
    """Get discount from referrer if they use partner_mode='discount'."""
    try:
        referrer_id = db_user.get("referrer_id")
        if not referrer_id:
            return 0

        referrer_result = (
            await db.client.table("users")
            .select("partner_mode, partner_discount_percent")
            .eq("id", str(referrer_id))
            .single()
            .execute()
        )

        if referrer_result.data:
            referrer = referrer_result.data
            if referrer.get("partner_mode") == "discount":
                discount = int(referrer.get("partner_discount_percent") or 0)
                if discount > 0:
                    logger.info(
                        f"Partner discount applied: {discount}% from referrer {referrer_id}"
                    )
                    return discount
        return 0
    except Exception as e:
        logger.warning("Failed to get partner discount: %s", type(e).__name__)
        return 0


# Helper: Validate cart items and calculate totals (reduces cognitive complexity)
async def _validate_and_prepare_cart_items(
    db: Any,
    cart_items: list[Any],
    cart: Any,
    partner_discount: int,
    target_curr: str,
    curr_service: Any,
) -> tuple[Decimal, Decimal, Decimal, list[dict[str, Any]]]:
    """
    Validate cart items, calculate totals using Decimal, handle stock deficits.
    Calculates both USD total and Fiat total (using Anchor Prices).
    """
    total_amount_usd = Decimal("0")
    total_original_usd = Decimal("0")
    total_fiat_amount = Decimal("0")
    prepared_items = []

    for item in cart_items:
        product = await db.get_product_by_id(item.product_id)
        if not product:
            raise ValueError(f"Product {item.product_id} not found")

        # Check instant availability
        instant_q = item.instant_quantity
        if instant_q > 0:
            available_stock = await db.get_available_stock_count(item.product_id)
            if available_stock < instant_q:
                logger.warning(
                    f"Stock changed for {product.name}. Requested {instant_q}, available {available_stock}"
                )
                # Convert deficit to prepaid
                deficit = instant_q - available_stock
                item.instant_quantity = max(0, available_stock)
                item.prepaid_quantity += max(0, deficit)

        # --- Pricing Logic ---

        # 1. USD Calculations (Base)
        product_price_usd = to_decimal(product.price)
        original_price_usd = multiply(product_price_usd, item.quantity)

        # 2. Fiat Calculations (Anchor)
        # This uses prices['RUB'] if available, else converts from USD
        anchor_price = await curr_service.get_anchor_price(product, target_curr)
        product_price_fiat = to_decimal(anchor_price)
        original_price_fiat = multiply(product_price_fiat, item.quantity)

        # Apply discounts
        discount_percent = item.discount_percent
        if cart.promo_code and cart.promo_discount_percent > 0:
            discount_percent = max(discount_percent, cart.promo_discount_percent)
        if partner_discount > 0:
            discount_percent = max(discount_percent, partner_discount)

        discount_percent = max(0, min(100, discount_percent))

        # Calculate multiplier: (1 - discount/100)
        discount_multiplier = subtract(
            Decimal("1"), divide(to_decimal(discount_percent), Decimal("100"))
        )

        # Final prices
        final_price_usd = round_money(multiply(original_price_usd, discount_multiplier))
        final_price_fiat = round_money(multiply(original_price_fiat, discount_multiplier))

        # For integer currencies, round fiat amount to int
        if target_curr in ["RUB", "UAH", "TRY", "INR"]:
            final_price_fiat = round_money(final_price_fiat, to_int=True)

        total_amount_usd += final_price_usd
        total_original_usd += original_price_usd
        total_fiat_amount += final_price_fiat

        prepared_items.append(
            {
                "product_id": item.product_id,
                "product_name": product.name,
                "quantity": item.quantity,
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity,
                "amount": final_price_usd,  # Store USD amount in order_items for consistency
                "original_price": original_price_usd,
                "discount_percent": discount_percent,
            }
        )
    return total_amount_usd, total_original_usd, total_fiat_amount, prepared_items


# Helper: Process external payment (reduces cognitive complexity)
async def _process_external_payment(
    db: Any,
    order: Any,
    order_id: str,
    order_items: list[dict[str, Any]],
    cart: Any,
    cart_manager: Any,
    ctx: Any,
    currency_service: Any,
    payable_amount: Decimal,
    gateway_currency: str,
    payment_gateway: str,
    payment_method: str,
) -> dict[str, Any]:
    """Process external payment via payment gateway."""
    from core.routers.deps import get_payment_service
    from core.routers.webapp.orders.helpers import create_payment_wrapper

    payment_service = get_payment_service()

    try:
        product_names = ", ".join([item["product_name"] for item in order_items[:3]])
        if len(order_items) > 3:
            product_names += f" и еще {len(order_items) - 3}"

        pay_result = await create_payment_wrapper(
            payment_service=payment_service,
            order_id=order.id,
            amount=payable_amount,  # In gateway_currency (user's currency), Decimal type
            product_name=product_names,
            gateway=payment_gateway,
            user_id=ctx.telegram_id,
            currency=gateway_currency,  # Pass user's currency, not USD!
            is_telegram_miniapp=True,
        )

        payment_url = pay_result.get("payment_url")
        invoice_id = pay_result.get("invoice_id")
        logger.info(
            f"CrystalPay payment created for order {order.id}: payment_url={payment_url[:50] if payment_url else 'None'}..., invoice_id={invoice_id}"
        )

        # Update order with payment details
        if invoice_id:
            await (
                db.client.table("orders")
                .update({"payment_id": str(invoice_id), "payment_url": payment_url})
                .eq("id", order.id)
                .execute()
            )

        # Apply promo code and clear cart
        if cart.promo_code:
            await db.use_promo_code(cart.promo_code)
        await cart_manager.clear_cart(ctx.telegram_id)

        # Format response
        if ctx.currency != gateway_currency:
            amount_display = await currency_service.convert_price(
                to_float(payable_amount), ctx.currency
            )
        else:
            amount_display = to_float(payable_amount)

        items_text = ", ".join([f"{item.product_name}" for item in cart.items])

        return {
            "success": True,
            "order_id": order_id[:8],
            "status": "pending",
            "payment_method": "card",
            "amount": amount_display,
            "amount_formatted": currency_service.format_price(amount_display, ctx.currency),
            "payment_url": payment_url,
            "items": items_text,
            "expires_in_minutes": 15,
            "message": f"Заказ #{order_id[:8]} создан! Оплати по ссылке в течение 15 минут.",
            "action": "show_payment_link",
        }

    except Exception as e:
        logger.error("Payment service error: %s", type(e).__name__, exc_info=True)
        # Rollback order on payment creation error
        try:
            await db.client.table("order_items").delete().eq("order_id", order.id).execute()
        except Exception:
            pass
        await db.client.table("orders").delete().eq("id", order.id).execute()
        return {
            "success": False,
            "error": f"Ошибка платежного шлюза: {e!s}",
            "action": "retry_payment",
        }


# Helper: Create order with currency snapshot (reduces cognitive complexity)
async def _create_order_with_currency_snapshot(
    db: Any,
    user_id: str,
    ctx: Any,
    total_amount: Decimal,
    total_original: Decimal,
    total_fiat_amount: Decimal,
    target_currency: str,
    gateway_currency: str,
    currency_service: Any,
    payment_method: str,
    payment_gateway: str,
    order_items: list[dict[str, Any]],
) -> tuple[Any, str]:
    """Create order with currency snapshot and order items."""
    from core.routers.webapp.orders.helpers import persist_order, persist_order_items

    # Currency Handling
    fiat_amount = total_fiat_amount
    fiat_currency = target_currency

    exchange_rate_snapshot = 1.0
    try:
        exchange_rate_snapshot = await currency_service.snapshot_rate(gateway_currency)

        # CRITICAL: Recalculate base USD amount from the realized Fiat amount
        if exchange_rate_snapshot > 0:
            total_amount = round_money(divide(fiat_amount, to_decimal(exchange_rate_snapshot)))

        logger.info(
            f"Order created: {to_float(total_amount)} USD | {to_float(fiat_amount)} {fiat_currency} (Rate: {exchange_rate_snapshot})"
        )
    except Exception as e:
        logger.warning("Failed to snapshot rate or recalculate USD amount: %s", type(e).__name__)
        exchange_rate_snapshot = 1.0

    # Calculate discount percent
    discount_pct = 0
    if total_original > 0:
        discount_ratio = subtract(Decimal("1"), divide(total_amount, total_original))
        discount_pct = max(
            0, min(100, int(round_money(multiply(discount_ratio, Decimal("100")), to_int=True)))
        )

    # Create order
    payment_expires_at = datetime.now(UTC) + timedelta(minutes=15)
    order = await persist_order(
        db=db,
        user_id=user_id,
        amount=total_amount,
        original_price=total_original,
        discount_percent=discount_pct,
        payment_method=payment_method,
        payment_gateway=payment_gateway if payment_method != "balance" else None,
        user_telegram_id=ctx.telegram_id,
        expires_at=payment_expires_at,
        fiat_amount=fiat_amount,
        fiat_currency=fiat_currency,
        exchange_rate_snapshot=exchange_rate_snapshot,
    )

    order_id = order.id

    # Create order_items
    try:
        await persist_order_items(db, order.id, order_items)
    except Exception:
        from core.logging import sanitize_id_for_logging

        logger.exception(
            "Failed to create order_items for order %s", sanitize_id_for_logging(order.id)
        )
        await db.client.table("orders").delete().eq("id", order.id).execute()
        raise ValueError("Failed to create order items. Please try again.")

    return order, order_id


# Helper: Determine target currency for payment (reduces cognitive complexity)
def _determine_target_currency(
    payment_method: str,
    balance_currency: str,
    payment_gateway: str,
    db_user: dict[str, Any],
    ctx: Any,
    currency_service: Any,
) -> tuple[str, str]:
    """Determine target currency based on payment method and gateway."""
    if payment_method == "balance":
        return balance_currency, balance_currency

    if payment_gateway == "crystalpay":
        try:
            user_lang = (
                db_user.get("interface_language") or db_user.get("language_code") or ctx.currency
            )
            preferred_currency = db_user.get("preferred_currency")
            user_currency = currency_service.get_user_currency(user_lang, preferred_currency)

            supported_currencies = ["USD", "RUB", "EUR", "UAH", "TRY", "INR", "AED"]
            if user_currency in supported_currencies:
                return user_currency, user_currency
            return GATEWAY_CURRENCY.get("crystalpay", "RUB"), GATEWAY_CURRENCY.get(
                "crystalpay", "RUB"
            )
        except Exception:
            return "RUB", "RUB"

    gateway_curr = GATEWAY_CURRENCY.get(payment_gateway or "", "RUB")
    return gateway_curr, gateway_curr


# Helper: Convert order total to balance currency (reduces cognitive complexity)
async def _convert_order_total_to_balance_currency(
    order_total_usd: Decimal,
    balance_currency: str,
    currency_service: Any,
) -> Decimal:
    """Convert USD order total to user's balance currency."""
    if balance_currency == "USD":
        return order_total_usd

    rate = await currency_service.get_exchange_rate(balance_currency)
    order_total = to_decimal(to_float(order_total_usd) * rate)

    # Round for integer currencies
    if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
        order_total = to_decimal(round(to_float(order_total)))

    return order_total


# Helper: Check balance sufficiency and format error (reduces cognitive complexity)
def _check_balance_sufficiency(
    user_balance: Decimal,
    order_total: Decimal,
    balance_currency: str,
    currency_service: Any,
) -> dict[str, Any] | None:
    """Check if user has sufficient balance, return error dict if not."""
    if user_balance >= order_total:
        return None

    balance_formatted = currency_service.format_price(to_float(user_balance), balance_currency)
    amount_formatted = currency_service.format_price(to_float(order_total), balance_currency)
    error_msg = f"Недостаточно средств на балансе. Доступно: {balance_formatted}, требуется: {amount_formatted}"

    return {"success": False, "error": error_msg, "action": "suggest_card_payment"}


# Helper: Process balance payment (reduces cognitive complexity)
async def _process_balance_payment(
    db: Any,
    order_id: str,
    user_id: str,
    order_total_in_balance_currency: Decimal,
    balance_currency: str,
) -> dict[str, Any] | None:
    """Process balance payment, return error dict on failure."""
    try:
        await db.client.rpc(
            "add_to_user_balance",
            {
                "p_user_id": user_id,
                "p_amount": -to_float(order_total_in_balance_currency),
                "p_reason": f"Payment for order {order_id}",
            },
        ).execute()
        from core.logging import sanitize_id_for_logging

        logger.info(
            "Balance deducted %.2f %s for order %s",
            to_float(order_total_in_balance_currency),
            balance_currency,
            sanitize_id_for_logging(order_id),
        )
        return None
    except Exception:
        from core.logging import sanitize_id_for_logging

        # Rollback order on balance deduction error
        await db.client.table("orders").delete().eq("id", order_id).execute()
        logger.exception("Failed to deduct balance for order %s", sanitize_id_for_logging(order_id))
        return {"success": False, "error": "Ошибка списания с баланса. Попробуйте позже."}


# Helper: Mark payment confirmed and queue delivery (reduces cognitive complexity)
async def _finalize_balance_payment(
    db: Any,
    order_id: str,
    cart: Any,
    cart_manager: Any,
    ctx: Any,
    currency_service: Any,
    order_total_in_balance_currency: Decimal,
    balance_currency: str,
) -> dict[str, Any]:
    """Finalize balance payment: mark paid, queue delivery, format response."""
    # Update order status to paid
    try:
        from core.orders.status_service import OrderStatusService

        status_service = OrderStatusService(db)
        final_status = await status_service.mark_payment_confirmed(
            order_id=order_id, payment_id=f"balance-{order_id}", check_stock=True
        )
        from core.logging import sanitize_id_for_logging

        logger.info(
            "Balance payment confirmed for order %s, final_status=%s",
            sanitize_id_for_logging(order_id),
            final_status,
        )
    except Exception as e:
        from core.logging import sanitize_id_for_logging

        logger.error(
            "Failed to mark payment confirmed for balance order %s: %s",
            sanitize_id_for_logging(order_id),
            type(e).__name__,
            exc_info=True,
        )
        # Don't fail - order is created and balance is deducted

    # Queue delivery via QStash (async, don't block response)
    try:
        from core.queue import WorkerEndpoints, publish_to_worker

        await publish_to_worker(
            endpoint=WorkerEndpoints.DELIVER_GOODS,
            body={"order_id": order_id},
            retries=2,
            deduplication_id=f"deliver-{order_id}",
        )
        from core.logging import sanitize_id_for_logging

        logger.info(
            "Delivery queued for balance payment order %s", sanitize_id_for_logging(order_id)
        )
    except Exception as e:
        from core.logging import sanitize_id_for_logging

        logger.warning(
            "QStash failed for balance order %s: %s",
            sanitize_id_for_logging(order_id),
            type(e).__name__,
        )
        # Don't fail - delivery can be retried later

    # Apply promo code and clear cart
    if cart.promo_code:
        await db.use_promo_code(cart.promo_code)
    await cart_manager.clear_cart(ctx.telegram_id)

    # Format response
    if ctx.currency != balance_currency:
        amount_display = await currency_service.convert_price(
            to_float(order_total_in_balance_currency), ctx.currency
        )
    else:
        amount_display = to_float(order_total_in_balance_currency)

    # Get updated balance for display
    updated_user_result = (
        await db.client.table("users").select("balance").eq("id", ctx.user_id).single().execute()
    )
    new_balance = (
        to_float(updated_user_result.data.get("balance", 0) or 0) if updated_user_result.data else 0
    )

    if ctx.currency != balance_currency:
        new_balance_display = await currency_service.convert_price(new_balance, ctx.currency)
    else:
        new_balance_display = new_balance

    items_text = ", ".join([f"{item.product_name}" for item in cart.items])

    return {
        "success": True,
        "order_id": order_id[:8],
        "status": "paid",
        "payment_method": "balance",
        "amount": amount_display,
        "amount_formatted": currency_service.format_price(amount_display, ctx.currency),
        "new_balance": new_balance_display,
        "new_balance_formatted": currency_service.format_price(new_balance_display, ctx.currency),
        "items": items_text,
        "message": f"Заказ #{order_id[:8]} оплачен! Товар будет доставлен в течение нескольких минут.",
        "action": "order_paid",
    }


@tool
async def checkout_cart(payment_method: str = "card") -> dict:
    """
    Create order from cart and get payment link.
    Use when user confirms they want to buy/purchase/order.

    CRITICAL: Call this when user says:
    - "купи", "оформи", "заказать", "оплатить"
    - "buy", "checkout", "order", "purchase"
    - "да" (after adding to cart)

    Args:
        payment_method: "card" (external payment) or "balance" (pay from internal balance)

    Returns:
        Order info with payment URL or confirmation
    """
    try:
        from core.cart import get_cart_manager
        from core.db import get_redis
        from core.services.currency import get_currency_service

        ctx = get_user_context()
        db = get_db()
        cart_manager = get_cart_manager()

        cart = await cart_manager.get_cart(ctx.telegram_id)
        if not cart or not cart.items:
            return {
                "success": False,
                "error": "Корзина пуста. Сначала добавь товары.",
                "action": "show_catalog",
            }

        # Get user with balance_currency and referrer_id for partner discount
        user_result = (
            await db.client.table("users")
            .select(
                "id, balance, balance_currency, preferred_currency, language_code, referrer_id, interface_language"
            )
            .eq("telegram_id", ctx.telegram_id)
            .single()
            .execute()
        )

        if not user_result.data:
            return {"success": False, "error": "User not found"}

        db_user = user_result.data
        user_id = db_user["id"]
        balance_currency = db_user.get("balance_currency") or "USD"
        user_balance = to_decimal(db_user.get("balance", 0) or 0)

        # Get partner discount (if user was referred by partner with discount mode)
        partner_discount = await _get_partner_discount(db, db_user)

        # 1. Determine target currency for Anchor Pricing
        redis = get_redis()
        currency_service = get_currency_service(redis)
        payment_gateway = os.environ.get("DEFAULT_PAYMENT_GATEWAY", "crystalpay")
        target_currency, gateway_currency = _determine_target_currency(
            payment_method,
            balance_currency,
            payment_gateway,
            db_user,
            ctx,
            currency_service,
        )

        # 2. Validate cart items and calculate totals using Anchor Prices
        (
            total_amount,
            total_original,
            total_fiat_amount,
            order_items,
        ) = await _validate_and_prepare_cart_items(
            db,
            cart.items,
            cart,
            partner_discount,
            target_currency,
            currency_service,
        )

        # 3. Calculate currency snapshot and create order
        order, order_id = await _create_order_with_currency_snapshot(
            db,
            user_id,
            ctx,
            total_amount,
            total_original,
            total_fiat_amount,
            target_currency,
            gateway_currency,
            currency_service,
            payment_method,
            payment_gateway,
            order_items,
        )

        # 4. Handle payment based on method
        if payment_method == "balance":
            # Convert order total to balance currency
            order_total_in_balance_currency = await _convert_order_total_to_balance_currency(
                total_amount, balance_currency, currency_service
            )

            # Check balance sufficiency
            error = _check_balance_sufficiency(
                user_balance, order_total_in_balance_currency, balance_currency, currency_service
            )
            if error:
                await db.client.table("orders").delete().eq("id", order.id).execute()
                return error

            # Process balance payment
            error = await _process_balance_payment(
                db, order.id, user_id, order_total_in_balance_currency, balance_currency
            )
            if error:
                return error

            # Finalize payment and return response
            return await _finalize_balance_payment(
                db,
                order.id,
                cart,
                cart_manager,
                ctx,
                currency_service,
                order_total_in_balance_currency,
                balance_currency,
            )

        # 5. Handle external payment (CrystalPay)
        return await _process_external_payment(
            db,
            order,
            order_id,
            order_items,
            cart,
            cart_manager,
            ctx,
            currency_service,
            total_fiat_amount,  # Use fiat amount for payment
            gateway_currency,
            payment_gateway,
            payment_method,
        )

    except Exception as e:
        logger.error("checkout_cart error: %s", type(e).__name__, exc_info=True)
        return {"success": False, "error": str(e)}


# Helper to format insufficient balance message (reduces cognitive complexity)
def _format_insufficient_balance_message(
    currency_service, balance: float, cart_total: float, user_currency: str
) -> str:
    """Format insufficient balance error message."""
    if currency_service:
        try:
            balance_formatted = currency_service.format_price(balance, user_currency)
            cart_total_formatted = currency_service.format_price(cart_total, user_currency)
            return f"Баланс: {balance_formatted}, нужно: {cart_total_formatted}. Пополни баланс или оплати картой."
        except Exception:
            return (
                f"Баланс: {balance:.0f}, нужно: {cart_total:.0f}. Пополни баланс или оплати картой."
            )
    return f"Баланс: {balance:.0f}, нужно: {cart_total:.0f}. Пополни баланс или оплати картой."


# Helper to calculate balance in display currency (reduces cognitive complexity)
async def _calculate_balance_in_display_currency(
    balance_in_balance_currency: float,
    balance_currency: str,
    user_currency: str,
    currency_service,
) -> float:
    """Calculate balance in display currency."""
    if user_currency == balance_currency:
        return balance_in_balance_currency

    balance_rate = (
        await currency_service.get_exchange_rate(balance_currency)
        if balance_currency != "USD"
        else 1.0
    )
    display_rate = (
        await currency_service.get_exchange_rate(user_currency) if user_currency != "USD" else 1.0
    )

    balance_usd = (
        balance_in_balance_currency / balance_rate
        if balance_rate > 0
        else balance_in_balance_currency
    )
    balance = balance_usd * display_rate if display_rate > 0 else balance_usd

    return balance


@tool
async def pay_cart_from_balance() -> dict:
    """
    Pay for cart items using internal balance.
    Use when user says "оплати с баланса", "спиши с баланса", "pay from balance".
    Uses telegram_id and user_id from context.

    Returns:
        Instructions or confirmation
    """
    try:
        from core.cart import get_cart_manager

        ctx = get_user_context()
        db = get_db()

        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(ctx.telegram_id)

        if not cart or not cart.items:
            return {"success": False, "error": "Корзина пуста. Сначала добавь товары."}

        # Get user's balance and balance_currency (actual currency of balance)
        user_result = (
            await db.client.table("users")
            .select("balance, balance_currency, language_code, preferred_currency")
            .eq("id", ctx.user_id)
            .single()
            .execute()
        )

        if not user_result.data:
            return {"success": False, "error": "Пользователь не найден"}

        # Balance is stored in balance_currency, NOT always USD!
        balance_in_balance_currency = float(user_result.data.get("balance", 0) or 0)
        balance_currency = user_result.data.get("balance_currency") or "USD"
        user_currency = ctx.currency  # Display currency for AI agent

        try:
            from core.db import get_redis
            from core.services.currency import get_currency_service

            redis = get_redis()
            currency_service = get_currency_service(redis)

            balance = await _calculate_balance_in_display_currency(
                balance_in_balance_currency, balance_currency, user_currency, currency_service
            )
            cart_total = float(cart.total)
        except Exception as e:
            logger.warning(
                "Currency conversion failed in pay_cart_from_balance: %s", type(e).__name__
            )
            balance = balance_in_balance_currency
            cart_total = float(cart.total)
            currency_service = None

        if balance < cart_total:
            message = _format_insufficient_balance_message(
                currency_service, balance, cart_total, user_currency
            )

            return {
                "success": False,
                "error": "Недостаточно средств на балансе",
                "balance": balance,
                "cart_total": cart_total,
                "shortage": cart_total - balance,
                "message": message,
            }

        items_text = ", ".join([f"{item.product_name} x{item.quantity}" for item in cart.items])

        return {
            "success": True,
            "can_pay": True,
            "balance": balance,
            "cart_total": cart_total,
            "remaining_after": balance - cart_total,
            "items": items_text,
            "message": "Можно оплатить с баланса! Нажми Магазин → Корзина → выбери 'С баланса' и подтверди.",
            "instructions": "В корзине выбери способ оплаты 'С баланса' и нажми 'Оплатить'",
        }

    except Exception as e:
        logger.error("pay_cart_from_balance error: %s", type(e).__name__, exc_info=True)
        return {"success": False, "error": str(e)}
