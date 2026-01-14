"""
Order Helper Functions

Shared utilities for order creation and payment processing.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from core.payments import GATEWAY_CURRENCY
from core.services.models import Order
from core.services.money import divide, multiply, round_money, subtract, to_decimal, to_float

logger = logging.getLogger(__name__)


async def create_payment_wrapper(
    payment_service,
    order_id: str,
    amount: Decimal,
    product_name: str,
    gateway: str = "crystalpay",
    user_id: int = 0,
    currency: str = "RUB",
    is_telegram_miniapp: bool = True,
) -> dict[str, Any]:
    """
    Async wrapper for synchronous payment creation.
    Returns dict with payment_url and invoice_id.
    """
    formatted_amount = to_float(amount)

    if gateway == "crystalpay":

        async def _make_crystalpay_invoice():
            invoice_data = await payment_service.create_payment(
                order_id=order_id,
                amount=formatted_amount,
                product_name=product_name,
                user_id=str(user_id),
                currency=currency,
                is_telegram_miniapp=is_telegram_miniapp,
            )

            if isinstance(invoice_data, dict):
                return {
                    "payment_url": invoice_data.get("payment_url") or invoice_data.get("url"),
                    "invoice_id": invoice_data.get("invoice_id") or invoice_data.get("id"),
                }
            if hasattr(invoice_data, "url") or hasattr(invoice_data, "payment_url"):
                return {
                    "payment_url": getattr(invoice_data, "payment_url", None)
                    or getattr(invoice_data, "url", None),
                    "invoice_id": getattr(invoice_data, "invoice_id", None)
                    or getattr(invoice_data, "id", None),
                }
            raise ValueError(f"Unexpected response type from CrystalPay: {type(invoice_data)}")

        return await _make_crystalpay_invoice()
    raise ValueError(f"Unsupported payment gateway: {gateway}")


async def persist_order(
    db,
    user_id: str,
    amount: Decimal,
    original_price: Decimal,
    discount_percent: int,
    payment_method: str,
    payment_gateway: str | None,
    user_telegram_id: int,
    expires_at: datetime,
    fiat_amount: Decimal | None = None,
    fiat_currency: str | None = None,
    exchange_rate_snapshot: float | None = None,
):
    """Create order record in database using thread for sync operation."""
    order_payload = {
        "user_id": user_id,
        "amount": to_float(amount),
        "original_price": to_float(original_price),
        "discount_percent": discount_percent,
        "status": "pending",
        "payment_method": payment_method,
        "payment_gateway": payment_gateway,
        "created_at": datetime.now(UTC).isoformat(),
        "user_telegram_id": user_telegram_id,
        "expires_at": expires_at.isoformat(),
    }

    # Add fiat fields if provided
    if fiat_amount is not None:
        order_payload["fiat_amount"] = to_float(fiat_amount)
    if fiat_currency:
        order_payload["fiat_currency"] = fiat_currency
    if exchange_rate_snapshot is not None:
        order_payload["exchange_rate_snapshot"] = exchange_rate_snapshot

    result = await db.client.table("orders").insert(order_payload).execute()
    row = result.data[0]
    return Order(
        id=row["id"],
        user_id=row["user_id"],
        amount=row["amount"],
        status=row["status"],
        created_at=row.get("created_at"),
        payment_method=row.get("payment_method"),
        payment_gateway=row.get("payment_gateway"),
        original_price=row.get("original_price"),
        discount_percent=row.get("discount_percent"),
        user_telegram_id=row.get("user_telegram_id"),
        items=None,
    )


async def persist_order_items(db, order_id: str, items: list[dict[str, Any]]) -> None:
    """Insert multiple order_items in bulk.

    CRITICAL: Each order_item now has quantity=1 (split bulk orders into separate items).
    This allows independent processing of each key (delivery, replacement, tickets).

    Example: If user orders 3x GPT GO, create 3 separate order_items (quantity=1 each).

    Maps cart data (instant_quantity, prepaid_quantity) to DB schema (fulfillment_type).
    Note: instant_quantity/prepaid_quantity are cart-only fields, not stored in order_items table.
    """
    if not items:
        return

    rows = []
    for item in items:
        # Determine fulfillment_type from instant_quantity/prepaid_quantity if present
        # If instant_quantity > 0, it's instant; otherwise preorder
        fulfillment_type = "instant"  # default
        if "instant_quantity" in item and "prepaid_quantity" in item:
            fulfillment_type = "instant" if item.get("instant_quantity", 0) > 0 else "preorder"
        elif "fulfillment_type" in item:
            fulfillment_type = item["fulfillment_type"]

        # Split quantity into separate order_items (quantity=1 each)
        # This allows independent processing (delivery, replacement, tickets)
        # CRITICAL: Convert all numeric values to correct types for JSON serialization
        # - quantity: INTEGER (not float)
        # - discount_percent: INTEGER (not float)
        # - price: NUMERIC (float is OK)
        item_quantity = int(item.get("quantity", 1))  # Ensure int for range()
        total_amount = to_float(item["amount"])  # Total price for all quantity
        unit_price = (
            float(total_amount / item_quantity) if item_quantity > 0 else float(total_amount)
        )
        # discount_percent is INTEGER in DB - convert to int, not float
        discount_pct = int(round(to_float(item.get("discount_percent", 0))))

        for _ in range(item_quantity):
            row = {
                "order_id": order_id,
                "product_id": item["product_id"],
                "quantity": 1,  # Always 1 - each order_item = 1 key (INTEGER)
                "price": unit_price,  # Price per unit (not total) - NUMERIC
                "discount_percent": discount_pct,  # INTEGER (0-100)
                "fulfillment_type": fulfillment_type,
            }
            rows.append(row)

    await db.client.table("order_items").insert(rows).execute()


# =============================================================================
# Cart Order Creation Helpers (Refactored from _create_cart_order)
# =============================================================================


async def get_partner_discount(db, db_user) -> int:
    """
    Get discount from referrer if they use partner_mode='discount'.
    Returns discount percent (0 if no discount).
    """
    try:
        if not db_user.referrer_id:
            return 0

        referrer_result = (
            await db.client.table("users")
            .select("partner_mode, partner_discount_percent")
            .eq("id", str(db_user.referrer_id))
            .single()
            .execute()
        )

        if referrer_result.data:
            referrer = referrer_result.data
            if referrer.get("partner_mode") == "discount":
                discount = int(referrer.get("partner_discount_percent") or 0)
                if discount > 0:
                    referrer_id = db_user.referrer_id
                    logger.info(
                        "Partner discount applied: %s%% from referrer %s", discount, referrer_id
                    )
                    return discount
        return 0
    except Exception as e:
        logger.warning(f"Failed to get partner discount: {e}")
        return 0


def determine_target_currency(
    db_user, user, payment_method: str, payment_gateway: str, currency_service
) -> str:
    """Determine target currency for Anchor Pricing based on payment method and gateway."""
    if payment_method == "balance":
        # TODO(tech-debt): Default "RUB" after RUB-only migration
        return getattr(db_user, "balance_currency", "RUB") or "RUB"

    if payment_gateway == "crystalpay":
        try:
            user_lang = getattr(db_user, "interface_language", None) or (
                db_user.language_code if db_user and db_user.language_code else user.language_code
            )
            preferred_currency = getattr(db_user, "preferred_currency", None)
            user_currency = currency_service.get_user_currency(user_lang, preferred_currency)

            supported_currencies = ["USD", "RUB", "EUR", "UAH", "TRY", "INR", "AED"]
            if user_currency in supported_currencies:
                return user_currency
            return GATEWAY_CURRENCY.get("crystalpay", "RUB")
        except Exception:
            return "RUB"

    return GATEWAY_CURRENCY.get(payment_gateway or "", "RUB")


async def _check_and_adjust_stock(db, item, product) -> None:
    """Check instant availability and adjust quantities if needed."""
    instant_q = item.instant_quantity
    if instant_q > 0:
        available_stock = await db.get_available_stock_count(item.product_id)
        if available_stock < instant_q:
            logger.warning(
                "Stock changed for %s. Requested %s, available %s",
                product.name,
                instant_q,
                available_stock,
            )
            deficit = instant_q - available_stock
            item.instant_quantity = max(0, available_stock)
            item.prepaid_quantity += max(0, deficit)


def _calculate_product_prices(product, item_quantity: int) -> tuple[Decimal, Decimal]:
    """Calculate MSRP and product price in USD."""
    product_msrp_usd = (
        to_decimal(product.msrp)
        if hasattr(product, "msrp") and product.msrp
        else to_decimal(product.price)
    )
    original_price_usd = multiply(product_msrp_usd, item_quantity)
    product_price_usd = to_decimal(product.price)
    return original_price_usd, product_price_usd


def _calculate_discount_percent(
    item_discount: int, cart_promo_discount: int, partner_discount: int
) -> int:
    """Calculate effective discount percent from all sources."""
    discount_percent = item_discount
    if cart_promo_discount > 0:
        discount_percent = max(discount_percent, cart_promo_discount)
    if partner_discount > 0:
        discount_percent = max(discount_percent, partner_discount)
    return max(0, min(100, discount_percent))


def _calculate_final_prices(
    product_price_usd: Decimal,
    product_price_fiat: Decimal,
    discount_percent: int,
    quantity: int,
    target_currency: str,
) -> tuple[Decimal, Decimal]:
    """Calculate final prices per unit and totals after discount."""
    discount_multiplier = subtract(
        Decimal("1"), divide(to_decimal(discount_percent), Decimal("100"))
    )

    final_price_per_unit_usd = round_money(multiply(product_price_usd, discount_multiplier))
    final_price_per_unit_fiat = round_money(multiply(product_price_fiat, discount_multiplier))

    if target_currency in ["RUB", "UAH", "TRY", "INR"]:
        final_price_per_unit_fiat = round_money(final_price_per_unit_fiat, to_int=True)

    final_price_total_usd = round_money(multiply(final_price_per_unit_usd, quantity))
    final_price_total_fiat = round_money(multiply(final_price_per_unit_fiat, quantity))

    return final_price_total_usd, final_price_total_fiat


async def validate_and_prepare_cart_items(
    db,
    cart_items,
    cart,
    partner_discount: int,
    target_currency: str,
    currency_service,
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
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        await _check_and_adjust_stock(db, item, product)

        original_price_usd, product_price_usd = _calculate_product_prices(product, item.quantity)

        anchor_price = await currency_service.get_anchor_price(product, target_currency)
        product_price_fiat = to_decimal(anchor_price)

        cart_promo_discount = (
            cart.promo_discount_percent
            if cart.promo_code and cart.promo_discount_percent > 0
            else 0
        )
        discount_percent = _calculate_discount_percent(
            item.discount_percent, cart_promo_discount, partner_discount
        )

        final_price_total_usd, final_price_total_fiat = _calculate_final_prices(
            product_price_usd, product_price_fiat, discount_percent, item.quantity, target_currency
        )

        total_amount_usd += final_price_total_usd
        total_original_usd += original_price_usd
        total_fiat_amount += final_price_total_fiat

        prepared_items.append(
            {
                "product_id": item.product_id,
                "product_name": product.name,
                "quantity": item.quantity,
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity,
                "amount": final_price_total_usd,
                "original_price": original_price_usd,
                "discount_percent": discount_percent,
                "fulfillment_time_hours": getattr(product, "fulfillment_time_hours", None) or 24,
            }
        )
    return total_amount_usd, total_original_usd, total_fiat_amount, prepared_items


async def _check_redis_cooldown(user_id: int) -> tuple[Any, bool]:
    """Check cooldown in Redis, return (redis_client, has_cooldown)."""
    try:
        from core.db import get_redis

        cooldown_redis = get_redis()
        cooldown_key = f"pay:cooldown:{user_id}"
        existing = await cooldown_redis.get(cooldown_key)
        if existing:
            raise HTTPException(
                status_code=429, detail="Подождите ~1 минуту перед повторным созданием платежа"
            )
        return cooldown_redis, False
    except HTTPException:
        raise
    except (ValueError, AttributeError) as e:
        logger.warning("Redis unavailable, using DB fallback for cooldown: %s", e)
        return None, False
    except Exception as e:
        logger.warning("Redis error, using DB fallback for cooldown: %s", e)
        return None, False


async def _check_db_cooldown(db, db_user, cooldown_seconds: int) -> None:
    """Check cooldown in database."""
    try:
        result = (
            await db.client.table("orders")
            .select("*")
            .eq("user_id", db_user.id)
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            created_at = row.get("created_at")
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if datetime.now(UTC) - created_dt < timedelta(seconds=cooldown_seconds):
                        raise HTTPException(
                            status_code=429,
                            detail="Заказ уже создаётся, попробуйте через минуту",
                        )
                except HTTPException:
                    raise
                except Exception:
                    pass
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Pending order check failed: %s", e)


async def enforce_order_cooldown(db, db_user, user_id: int) -> tuple[Any, int]:
    """
    Enforce cooldown between order creations.
    Returns (cooldown_redis, cooldown_seconds) tuple.
    """
    cooldown_seconds = 90

    cooldown_redis, _ = await _check_redis_cooldown(user_id)
    await _check_db_cooldown(db, db_user, cooldown_seconds)

    return cooldown_redis, cooldown_seconds


def format_product_names(order_items: list[dict[str, Any]]) -> str:
    """Format product names with quantities for payment description."""
    product_name_parts = []
    for item in order_items[:3]:
        name = item["product_name"]
        quantity = item.get("quantity", 1)
        if quantity > 1:
            product_name_parts.append(f"{name} (x{quantity})")
        else:
            product_name_parts.append(name)

    product_names = ", ".join(product_name_parts)
    if len(order_items) > 3:
        product_names += f" и еще {len(order_items) - 3}"
    return product_names


async def calculate_currency_snapshot(
    currency_service, target_currency: str, fiat_amount: Decimal
) -> tuple[Decimal, float]:
    """
    Calculate currency snapshot and convert fiat amount back to USD.
    Returns (total_amount_usd, exchange_rate_snapshot).
    """
    exchange_rate_snapshot = 1.0
    total_amount = fiat_amount

    try:
        exchange_rate_snapshot = await currency_service.snapshot_rate(target_currency)
        if exchange_rate_snapshot > 0:
            total_amount = round_money(divide(fiat_amount, to_decimal(exchange_rate_snapshot)))

        logger.info(
            f"Order created: {to_float(total_amount)} USD | {to_float(fiat_amount)} {target_currency} (Rate: {exchange_rate_snapshot})"
        )
    except Exception as e:
        logger.warning(f"Failed to snapshot rate or recalculate USD amount: {e}")
        exchange_rate_snapshot = 1.0

    return total_amount, exchange_rate_snapshot


def calculate_discount_percent(total_amount: Decimal, total_original: Decimal) -> int:
    """Calculate discount percent from totals using Decimal."""
    if total_original <= 0:
        return 0

    discount_ratio = subtract(Decimal("1"), divide(total_amount, total_original))
    return max(0, min(100, int(round_money(multiply(discount_ratio, Decimal("100")), to_int=True))))


async def create_order_with_items(
    db,
    db_user,
    user_id: int,
    total_amount: Decimal,
    total_original: Decimal,
    discount_pct: int,
    payment_method: str,
    payment_gateway: str | None,
    fiat_amount: Decimal,
    fiat_currency: str,
    exchange_rate_snapshot: float,
    order_items: list[dict[str, Any]],
) -> Order:
    """
    Create order in DB with order items.
    Rolls back order if items creation fails.
    """
    payment_expires_at = datetime.now(UTC) + timedelta(minutes=15)
    order = await persist_order(
        db=db,
        user_id=db_user.id,
        amount=total_amount,
        original_price=total_original,
        discount_percent=discount_pct,
        payment_method=payment_method,
        payment_gateway=payment_gateway,
        user_telegram_id=user_id,
        expires_at=payment_expires_at,
        fiat_amount=fiat_amount,
        fiat_currency=fiat_currency,
        exchange_rate_snapshot=exchange_rate_snapshot,
    )

    try:
        await persist_order_items(db, order.id, order_items)
    except Exception:
        logger.exception(f"Failed to create order_items for order {order.id}")
        await db.client.table("orders").delete().eq("id", order.id).execute()
        raise HTTPException(
            status_code=500, detail="Failed to create order items. Please try again."
        )

    return order


async def process_external_payment(
    payment_service,
    order_id: str,
    payable_amount: Decimal,
    product_names: str,
    payment_gateway: str,
    user_id: int,
    gateway_currency: str,
    is_telegram_miniapp: bool,
    db,
) -> tuple[str | None, str | None]:
    """
    Process external payment creation.
    Returns (payment_url, invoice_id) or raises HTTPException on failure.
    Rolls back order on payment creation failure.
    """
    try:
        pay_result = await create_payment_wrapper(
            payment_service=payment_service,
            order_id=order_id,
            amount=payable_amount,
            product_name=product_names,
            gateway=payment_gateway,
            user_id=user_id,
            currency=gateway_currency,
            is_telegram_miniapp=is_telegram_miniapp,
        )
        payment_url = pay_result.get("payment_url")
        invoice_id = pay_result.get("invoice_id")
        logger.info(
            f"CrystalPay payment created for order {order_id}: payment_url={payment_url[:50] if payment_url else 'None'}..., invoice_id={invoice_id}"
        )
        return payment_url, invoice_id

    except ValueError as e:
        logger.exception("[DEBUG-HYP-D] create_payment_wrapper ValueError: error_type=ValueError")
        try:
            await db.client.table("order_items").delete().eq("order_id", order_id).execute()
        except Exception:
            pass
        await db.client.table("orders").delete().eq("id", order_id).execute()
        error_msg = str(e)
        logger.exception(f"Payment creation failed: {error_msg}")

        if "frozen" in error_msg.lower() or "заморожен" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Платёжная система временно недоступна. Попробуйте позже или обратитесь в поддержку.",
            )
        if "disabled" in error_msg.lower() or "недоступен" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Выбранный способ оплаты временно недоступен. Попробуйте другой.",
            )
        raise HTTPException(status_code=400, detail=error_msg)

    except Exception as e:
        error_type = type(e).__name__
        logger.exception(f"[DEBUG-HYP-D] create_payment_wrapper Exception: error_type={error_type}")
        try:
            await db.client.table("order_items").delete().eq("order_id", order_id).execute()
        except Exception:
            pass
        await db.client.table("orders").delete().eq("id", order_id).execute()
        logger.exception("Payment creation failed")
        raise HTTPException(
            status_code=502, detail="Платёжная система недоступна. Попробуйте позже."
        )


async def save_payment_info(
    db, order_id: str, payment_url: str | None, invoice_id: str | None
) -> None:
    """Save payment URL and invoice ID to order."""
    try:
        update_payload = {"payment_url": payment_url}
        if invoice_id:
            update_payload["payment_id"] = str(invoice_id)
        await db.client.table("orders").update(update_payload).eq("id", order_id).execute()
    except Exception as e:
        logger.warning(f"Failed to save payment info for order {order_id}: {e}")


async def set_order_cooldown(cooldown_redis: Any, user_id: int, cooldown_seconds: int) -> None:
    """Set cooldown key in Redis."""
    if cooldown_redis:
        try:
            await cooldown_redis.set(f"pay:cooldown:{user_id}", "1", ex=cooldown_seconds)
        except Exception as e:
            logger.warning(f"Failed to set cooldown key: {e}")


async def cleanup_promo_and_cart(db, cart_manager, user_id: int, cart) -> None:
    """Apply promo code usage and clear cart."""
    try:
        if cart.promo_code:
            await db.use_promo_code(cart.promo_code)
        await cart_manager.clear_cart(user_id)
        logger.info("[DEBUG-HYP-E] Promo/cart cleanup success")
    except Exception as e:
        error_type = type(e).__name__
        logger.exception(f"[DEBUG-HYP-E] Promo/cart cleanup FAILED: error_type={error_type}")
        logger.warning(f"Failed to cleanup promo/cart for order: {e}")
