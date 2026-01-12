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
        from core.routers.webapp.orders.helpers import persist_order, persist_order_items
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
        async def get_partner_discount() -> int:
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
                logger.warning(f"Failed to get partner discount: {e}")
                return 0

        partner_discount = await get_partner_discount()

        # 1. Determine target currency for Anchor Pricing
        # If paying with balance, use balance_currency.
        # If paying with gateway, use gateway currency (usually RUB for CrystalPay if user is RU, else USD/etc)
        redis = get_redis()
        currency_service = get_currency_service(redis)

        payment_gateway = os.environ.get("DEFAULT_PAYMENT_GATEWAY", "crystalpay")
        target_currency = "USD"

        if payment_method == "balance":
            target_currency = balance_currency
        elif payment_gateway == "crystalpay":
            try:
                # Get user's currency from profile
                user_lang = (
                    db_user.get("interface_language")
                    or db_user.get("language_code")
                    or ctx.currency
                )
                preferred_currency = db_user.get("preferred_currency")
                user_currency = currency_service.get_user_currency(user_lang, preferred_currency)

                supported_currencies = ["USD", "RUB", "EUR", "UAH", "TRY", "INR", "AED"]
                if user_currency in supported_currencies:
                    target_currency = user_currency
                else:
                    target_currency = GATEWAY_CURRENCY.get("crystalpay", "RUB")
            except Exception:
                target_currency = "RUB"
        else:
            target_currency = GATEWAY_CURRENCY.get(payment_gateway or "", "RUB")

        gateway_currency = target_currency

        # 2. Validate cart items and calculate totals using Anchor Prices
        async def validate_cart_items(
            cart_items, target_curr, curr_service
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

        # Prepare items and totals
        total_amount, total_original, total_fiat_amount, order_items = await validate_cart_items(
            cart.items, target_currency, currency_service
        )

        # Currency Handling (using values from validate_cart_items)
        # payable_amount is what we send to the gateway (in gateway_currency)
        # fiat_amount is what we store in the DB (in fiat_currency)
        payable_amount = total_fiat_amount
        fiat_amount = total_fiat_amount
        fiat_currency = target_currency

        exchange_rate_snapshot = 1.0
        try:
            # Get and snapshot the exchange rate for historical record
            exchange_rate_snapshot = await currency_service.snapshot_rate(gateway_currency)

            # CRITICAL: Recalculate base USD amount from the realized Fiat amount
            # This ensures P&L reflects the actual value received (e.g. 400 RUB / 90 = $4.44),
            # rather than the list price (e.g. $5.00) which might be different due to anchor pricing.
            if exchange_rate_snapshot > 0:
                # Round to 2 decimal places for USD storage
                total_amount = round_money(divide(fiat_amount, to_decimal(exchange_rate_snapshot)))

            logger.info(
                f"Order created: {to_float(total_amount)} USD | {to_float(fiat_amount)} {fiat_currency} (Rate: {exchange_rate_snapshot})"
            )
        except Exception as e:
            logger.warning(f"Failed to snapshot rate or recalculate USD amount: {e}")
            exchange_rate_snapshot = 1.0

        # Calculate discount percent using Decimal (safe: clamped to 0-100)
        discount_pct = 0
        if total_original > 0:
            # (1 - amount/original) * 100, clamped to [0, 100]
            discount_ratio = subtract(Decimal("1"), divide(total_amount, total_original))
            discount_pct = max(
                0, min(100, int(round_money(multiply(discount_ratio, Decimal("100")), to_int=True)))
            )

        # 3. Create order using persist_order (includes currency snapshot)
        payment_expires_at = datetime.now(UTC) + timedelta(minutes=15)
        order = await persist_order(
            db=db,
            user_id=user_id,
            amount=total_amount,  # Always in USD (base currency)
            original_price=total_original,
            discount_percent=discount_pct,
            payment_method=payment_method,
            payment_gateway=payment_gateway if payment_method != "balance" else None,
            user_telegram_id=ctx.telegram_id,
            expires_at=payment_expires_at,
            # Currency snapshot fields
            fiat_amount=fiat_amount,
            fiat_currency=fiat_currency,
            exchange_rate_snapshot=exchange_rate_snapshot,
        )

        order_id = order.id

        # Create order_items using persist_order_items
        try:
            await persist_order_items(db, order.id, order_items)
        except Exception:
            # Critical: order without items is invalid - delete order and fail
            logger.exception(f"Failed to create order_items for order {order.id}")
            await db.client.table("orders").delete().eq("id", order.id).execute()
            return {"success": False, "error": "Failed to create order items. Please try again."}

        # 4. Handle payment based on method
        if payment_method == "balance":
            # Get order total in user's balance currency
            order_total_usd = total_amount  # total_amount is in USD

            if balance_currency == "USD":
                order_total_in_balance_currency = order_total_usd
            else:
                # Convert USD order total to user's balance currency
                rate = await currency_service.get_exchange_rate(balance_currency)
                order_total_in_balance_currency = to_decimal(to_float(order_total_usd) * rate)
                # Round for integer currencies
                if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
                    order_total_in_balance_currency = to_decimal(
                        round(to_float(order_total_in_balance_currency))
                    )

            # Compare in user's balance currency
            if user_balance < order_total_in_balance_currency:
                # Delete order if balance insufficient
                await db.client.table("orders").delete().eq("id", order.id).execute()

                balance_formatted = currency_service.format_price(
                    to_float(user_balance), balance_currency
                )
                amount_formatted = currency_service.format_price(
                    to_float(order_total_in_balance_currency), balance_currency
                )
                error_msg = f"Недостаточно средств на балансе. Доступно: {balance_formatted}, требуется: {amount_formatted}"

                return {"success": False, "error": error_msg, "action": "suggest_card_payment"}

            # Deduct from balance in user's balance currency using RPC
            try:
                await db.client.rpc(
                    "add_to_user_balance",
                    {
                        "p_user_id": user_id,
                        "p_amount": -to_float(order_total_in_balance_currency),
                        "p_reason": f"Payment for order {order.id}",
                    },
                ).execute()
                logger.info(
                    f"Balance deducted {to_float(order_total_in_balance_currency):.2f} {balance_currency} for order {order.id}"
                )
            except Exception:
                # Rollback order on balance deduction error
                await db.client.table("orders").delete().eq("id", order.id).execute()
                logger.exception(f"Failed to deduct balance for order {order.id}")
                return {"success": False, "error": "Ошибка списания с баланса. Попробуйте позже."}

            # Update order status to paid
            try:
                from core.orders.status_service import OrderStatusService

                status_service = OrderStatusService(db)
                final_status = await status_service.mark_payment_confirmed(
                    order_id=order.id, payment_id=f"balance-{order.id}", check_stock=True
                )
                logger.info(
                    f"Balance payment confirmed for order {order.id}, final_status={final_status}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to mark payment confirmed for balance order {order.id}: {e}",
                    exc_info=True,
                )
                # Don't fail - order is created and balance is deducted

            # Queue delivery via QStash (async, don't block response)
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
                logger.warning(f"QStash failed for balance order {order.id}: {e}")
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
                await db.client.table("users")
                .select("balance")
                .eq("id", user_id)
                .single()
                .execute()
            )
            new_balance = (
                to_float(updated_user_result.data.get("balance", 0) or 0)
                if updated_user_result.data
                else 0
            )

            if ctx.currency != balance_currency:
                new_balance_display = await currency_service.convert_price(
                    new_balance, ctx.currency
                )
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
                "new_balance_formatted": currency_service.format_price(
                    new_balance_display, ctx.currency
                ),
                "items": items_text,
                "message": f"Заказ #{order_id[:8]} оплачен! Товар будет доставлен в течение нескольких минут.",
                "action": "order_paid",
            }

        # 5. Handle external payment (CrystalPay)
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
                amount=to_float(payable_amount),  # In gateway_currency (user's currency)
                product_name=product_names,
                gateway=payment_gateway,
                payment_method=payment_method,
                user_email=f"{ctx.telegram_id}@telegram.user",
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
                await db.client.table("orders").update(
                    {"payment_id": str(invoice_id), "payment_url": payment_url}
                ).eq("id", order.id).execute()

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
            logger.error(f"Payment service error: {e}", exc_info=True)
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

    except Exception as e:
        logger.error(f"checkout_cart error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


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

        # If display currency matches balance currency, use balance directly
        # Otherwise convert balance to display currency for comparison
        try:
            from core.db import get_redis
            from core.services.currency import get_currency_service

            redis = get_redis()
            currency_service = get_currency_service(redis)

            if user_currency == balance_currency:
                # Display currency matches balance currency - use directly
                balance = balance_in_balance_currency
                cart_total = float(cart.total)  # Cart total is already in user_currency
            else:
                # Convert balance from balance_currency to display currency for comparison
                balance_rate = (
                    await currency_service.get_exchange_rate(balance_currency)
                    if balance_currency != "USD"
                    else 1.0
                )
                display_rate = (
                    await currency_service.get_exchange_rate(user_currency)
                    if user_currency != "USD"
                    else 1.0
                )
                # Convert: balance_currency → USD → display_currency
                balance_usd = (
                    balance_in_balance_currency / balance_rate
                    if balance_rate > 0
                    else balance_in_balance_currency
                )
                balance = balance_usd * display_rate if display_rate > 0 else balance_usd
                cart_total = float(cart.total)  # Already in display currency
        except Exception as e:
            logger.warning(f"Currency conversion failed in pay_cart_from_balance: {e}")
            # Fallback: assume balance is in display currency (may be incorrect, but better than crash)
            balance = balance_in_balance_currency
            cart_total = float(cart.total)
            currency_service = None

        if balance < cart_total:
            if currency_service:
                try:
                    balance_formatted = currency_service.format_price(balance, user_currency)
                    cart_total_formatted = currency_service.format_price(cart_total, user_currency)
                    message = f"Баланс: {balance_formatted}, нужно: {cart_total_formatted}. Пополни баланс или оплати картой."
                except Exception:
                    message = f"Баланс: {balance:.0f}, нужно: {cart_total:.0f}. Пополни баланс или оплати картой."
            else:
                message = f"Баланс: {balance:.0f}, нужно: {cart_total:.0f}. Пополни баланс или оплати картой."

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
        logger.error(f"pay_cart_from_balance error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
