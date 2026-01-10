"""
Order Payment Endpoints

Order creation and payment processing.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
import os
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List

from fastapi import APIRouter, HTTPException, Depends, Header

from core.services.database import get_database
from core.services.money import to_decimal, to_float, round_money, multiply, subtract, divide
from core.auth import verify_telegram_auth
from core.routers.deps import get_payment_service
from core.payments import (
    validate_gateway_config, 
    GATEWAY_CURRENCY,
)
from ..models import CreateOrderRequest, OrderResponse, ConfirmPaymentRequest

from .helpers import create_payment_wrapper, persist_order, persist_order_items

logger = logging.getLogger(__name__)

payments_router = APIRouter()


@payments_router.post("/orders")
async def create_webapp_order(
    request: CreateOrderRequest, 
    user=Depends(verify_telegram_auth),
    x_init_data: str = Header(None, alias="X-Init-Data"),
    user_agent: str = Header(None, alias="User-Agent")
):
    """Create new order from Mini App. Supports both single product and cart-based orders."""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    payment_method = request.payment_method or "card"
    
    # Determine payment gateway - only needed for external payments
    # For balance payments, gateway is not used
    if payment_method != "balance":
        payment_gateway = request.payment_gateway or os.environ.get("DEFAULT_PAYMENT_GATEWAY", "crystalpay")
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
            db, db_user, user, payment_service, payment_method, payment_gateway, 
            is_telegram_miniapp=is_telegram_miniapp
        )
    
    # Single product order
    return await _create_single_order(
        db, db_user, user, request, payment_service, payment_method, payment_gateway,
        is_telegram_miniapp=is_telegram_miniapp
    )


async def _create_cart_order(
    db, db_user, user, payment_service, payment_method: str, payment_gateway: str = "crystalpay",
    is_telegram_miniapp: bool = True
) -> OrderResponse:
    """Create order from cart items."""
    from core.cart import get_cart_manager
    cart_manager = get_cart_manager()
    cart = await cart_manager.get_cart(user.id)
    
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Helpers
    # Check if user was referred by a partner with discount mode
    async def get_partner_discount() -> int:
        """
        Get discount from referrer if they use partner_mode='discount'.
        Returns discount percent (0 if no discount).
        """
        try:
            if not db_user.referrer_id:
                return 0
            
            referrer_result = await db.client.table("users").select(
                "partner_mode, partner_discount_percent"
            ).eq("id", str(db_user.referrer_id)).single().execute()
            
            if referrer_result.data:
                referrer = referrer_result.data
                if referrer.get("partner_mode") == "discount":
                    discount = int(referrer.get("partner_discount_percent") or 0)
                    if discount > 0:
                        logger.info(f"Partner discount applied: {discount}% from referrer {db_user.referrer_id}")
                        return discount
            return 0
        except Exception as e:
            logger.warning(f"Failed to get partner discount: {e}")
            return 0
    
    partner_discount = await get_partner_discount()
    
    # 1. Determine target currency for Anchor Pricing
    from core.db import get_redis
    from core.services.currency import get_currency_service
    redis = get_redis()
    currency_service = get_currency_service(redis)
    
    target_currency = "USD"
    if payment_method == "balance":
        target_currency = getattr(db_user, 'balance_currency', 'USD') or 'USD'
    elif payment_gateway == "crystalpay":
        try:
            user_lang = getattr(db_user, 'interface_language', None) or (db_user.language_code if db_user and db_user.language_code else user.language_code)
            preferred_currency = getattr(db_user, 'preferred_currency', None)
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

    async def validate_cart_items(cart_items, target_curr, curr_service) -> Tuple[Decimal, Decimal, Decimal, List[Dict[str, Any]]]:
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
            
            # Check instant availability
            instant_q = item.instant_quantity
            if instant_q > 0:
                available_stock = await db.get_available_stock_count(item.product_id)
                if available_stock < instant_q:
                    logger.warning(f"Stock changed for {product.name}. Requested {instant_q}, available {available_stock}")
                    deficit = instant_q - available_stock
                    item.instant_quantity = max(0, available_stock)
                    item.prepaid_quantity += max(0, deficit)
            
            # --- Pricing Logic ---
            
            # 1. USD Calculations (Base)
            product_price_usd = to_decimal(product.price)
            original_price_usd = multiply(product_price_usd, item.quantity)
            
            # 2. Fiat Calculations (Anchor)
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
            discount_multiplier = subtract(Decimal("1"), divide(to_decimal(discount_percent), Decimal("100")))
            
            # Final prices
            final_price_usd = round_money(multiply(original_price_usd, discount_multiplier))
            final_price_fiat = round_money(multiply(original_price_fiat, discount_multiplier))
            
            # For integer currencies, round fiat amount to int
            if target_curr in ["RUB", "UAH", "TRY", "INR"]:
                final_price_fiat = round_money(final_price_fiat, to_int=True)
            
            total_amount_usd += final_price_usd
            total_original_usd += original_price_usd
            total_fiat_amount += final_price_fiat
            
            prepared_items.append({
                "product_id": item.product_id,
                "product_name": product.name,
                "quantity": item.quantity, 
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity,
                "amount": final_price_usd,
                "original_price": original_price_usd,
                "discount_percent": discount_percent,
                "fulfillment_time_hours": getattr(product, 'fulfillment_time_hours', None) or 24,
            })
        return total_amount_usd, total_original_usd, total_fiat_amount, prepared_items
    
    async def enforce_cooldown():
        cooldown_seconds = 90
        cooldown_redis = None
        try:
            from core.db import get_redis
            cooldown_redis = get_redis()
            cooldown_key = f"pay:cooldown:{user.id}"
            existing = await cooldown_redis.get(cooldown_key)
            if existing:
                raise HTTPException(
                    status_code=429,
                    detail="Подождите ~1 минуту перед повторным созданием платежа"
                )
        except HTTPException:
            raise
        except (ValueError, AttributeError) as e:
            logger.warning(f"Redis unavailable, using DB fallback for cooldown: {e}")
            cooldown_redis = None
        except Exception as e:
            logger.warning(f"Redis error, using DB fallback for cooldown: {e}")
            cooldown_redis = None
        
        try:
            result = await db.client.table("orders").select("*").eq(
                "user_id", db_user.id
            ).eq("status", "pending").order("created_at", desc=True).limit(1).execute()
            if result.data:
                row = result.data[0]
                created_at = row.get("created_at")
                if created_at:
                    try:
                        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        if datetime.now(timezone.utc) - created_dt < timedelta(seconds=cooldown_seconds):
                            raise HTTPException(
                                status_code=429,
                                detail="Заказ уже создаётся, попробуйте через минуту"
                            )
                    except HTTPException:
                        raise
                    except Exception:
                        pass
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Pending order check failed: {e}")
        return cooldown_redis, cooldown_seconds
    
    # Prepare items and totals
    total_amount, total_original, total_fiat_amount, order_items = await validate_cart_items(cart.items, target_currency, currency_service)
    
    # Cooldown checks
    cooldown_redis, cooldown_seconds = await enforce_cooldown()
    
    product_names = ", ".join([item["product_name"] for item in order_items[:3]])
    if len(order_items) > 3:
        product_names += f" и еще {len(order_items) - 3}"
    
    # Currency Handling
    gateway_currency = target_currency
    payable_amount = total_fiat_amount
    fiat_amount = total_fiat_amount
    fiat_currency = target_currency
    
    exchange_rate_snapshot = 1.0
    try:
        exchange_rate_snapshot = await currency_service.snapshot_rate(gateway_currency)
        
        if exchange_rate_snapshot > 0:
            total_amount = round_money(divide(fiat_amount, to_decimal(exchange_rate_snapshot)))
            
        logger.info(f"Order created: {to_float(total_amount)} USD | {to_float(fiat_amount)} {fiat_currency} (Rate: {exchange_rate_snapshot})")
    except Exception as e:
        logger.warning(f"Failed to snapshot rate or recalculate USD amount: {e}")
        exchange_rate_snapshot = 1.0

    
    # Calculate discount percent using Decimal
    discount_pct = 0
    if total_original > 0:
        discount_ratio = subtract(Decimal("1"), divide(total_amount, total_original))
        discount_pct = max(0, min(100, int(round_money(multiply(discount_ratio, Decimal("100")), to_int=True))))
    
    # Create order in DB BEFORE calling payment gateway
    payment_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    order = await persist_order(
        db=db,
        user_id=db_user.id, 
        amount=total_amount,
        original_price=total_original,
        discount_percent=discount_pct,
        payment_method=payment_method,
        payment_gateway=payment_gateway,
        user_telegram_id=user.id,
        expires_at=payment_expires_at,
        fiat_amount=fiat_amount,
        fiat_currency=fiat_currency,
        exchange_rate_snapshot=exchange_rate_snapshot,
    )
    
    # Create order_items immediately after order creation
    try:
        await persist_order_items(db, order.id, order_items)
    except Exception as e:
        logger.error(f"Failed to create order_items for order {order.id}: {e}")
        await db.client.table("orders").delete().eq("id", order.id).execute()
        raise HTTPException(
            status_code=500,
            detail="Failed to create order items. Please try again."
        )
    
    # BALANCE PAYMENT: Check and deduct
    if payment_method == "balance":
        return await _process_balance_payment(
            db, db_user, user, order, total_amount, total_original, discount_pct,
            payment_method, cart, cart_manager, order_items
        )
    
    # EXTERNAL PAYMENT (CrystalPay)
    payment_url = None
    invoice_id = None
    try:
        pay_result = await create_payment_wrapper(
            payment_service=payment_service,
            order_id=order.id, 
            amount=payable_amount, 
            product_name=product_names,
            gateway=payment_gateway, 
            payment_method=payment_method,
            user_email=f"{user.id}@telegram.user",
            user_id=user.id,
            currency=gateway_currency,
            is_telegram_miniapp=is_telegram_miniapp,
        )
        payment_url = pay_result.get("payment_url")
        invoice_id = pay_result.get("invoice_id")
        logger.info(f"CrystalPay payment created for order {order.id}: payment_url={payment_url[:50] if payment_url else 'None'}..., invoice_id={invoice_id}")
    except ValueError as e:
        try:
            await db.client.table("order_items").delete().eq("order_id", order.id).execute()
        except Exception:
            pass
        await db.client.table("orders").delete().eq("id", order.id).execute()
        error_msg = str(e)
        logger.error(f"Payment creation failed: {error_msg}")
        
        if "frozen" in error_msg.lower() or "заморожен" in error_msg.lower():
            raise HTTPException(
                status_code=503, 
                detail="Платёжная система временно недоступна. Попробуйте позже или обратитесь в поддержку."
            )
        elif "disabled" in error_msg.lower() or "недоступен" in error_msg.lower():
            raise HTTPException(
                status_code=400, 
                detail="Выбранный способ оплаты временно недоступен. Попробуйте другой."
            )
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        try:
            await db.client.table("order_items").delete().eq("order_id", order.id).execute()
        except Exception:
            pass
        await db.client.table("orders").delete().eq("id", order.id).execute()
        logger.error(f"Payment creation failed: {e}")
        raise HTTPException(
            status_code=502, 
            detail="Платёжная система недоступна. Попробуйте позже."
        )
    
    # Save payment_url and invoice_id to order
    try:
        update_payload = {"payment_url": payment_url}
        if invoice_id:
            update_payload["payment_id"] = str(invoice_id)
        await db.client.table("orders").update(update_payload).eq("id", order.id).execute()
    except Exception as e:
        logger.warning(f"Failed to save payment info for order {order.id}: {e}")
    
    # Set cooldown
    if cooldown_redis:
        try:
            await cooldown_redis.set(f"pay:cooldown:{user.id}", "1", ex=cooldown_seconds)
        except Exception as e:
            logger.warning(f"Failed to set cooldown key: {e}")
    
    # Apply promo code and clear cart
    if cart.promo_code:
        await db.use_promo_code(cart.promo_code)
    await cart_manager.clear_cart(user.id)
    
    response = OrderResponse(
        order_id=order.id, 
        amount=to_float(total_amount), 
        original_price=to_float(total_original),
        discount_percent=discount_pct,
        payment_url=payment_url, 
        payment_method=payment_method
    )
    logger.info(f"Returning order response for {order.id}: payment_url present={bool(payment_url)}, method={payment_method}")
    return response


async def _process_balance_payment(
    db, db_user, user, order, total_amount, total_original, discount_pct,
    payment_method, cart, cart_manager, order_items
) -> OrderResponse:
    """Process balance payment for an order."""
    from core.db import get_redis
    from core.services.currency import get_currency_service
    
    _redis = get_redis()
    _currency_service = get_currency_service(_redis)
    
    # Get user's balance in their local currency
    user_balance = to_decimal(db_user.balance) if db_user.balance else Decimal("0")
    balance_currency = getattr(db_user, 'balance_currency', 'USD') or 'USD'
    
    # Get order total in user's balance currency
    order_total_usd = to_decimal(total_amount)
    
    if balance_currency == "USD":
        order_total_in_balance_currency = order_total_usd
    else:
        rate = await _currency_service.get_exchange_rate(balance_currency)
        order_total_in_balance_currency = to_decimal(to_float(order_total_usd) * rate)
        if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
            order_total_in_balance_currency = to_decimal(round(to_float(order_total_in_balance_currency)))
    
    # Compare in user's balance currency
    if user_balance < order_total_in_balance_currency:
        await db.client.table("orders").delete().eq("id", order.id).execute()
        
        balance_formatted = _currency_service.format_price(to_float(user_balance), balance_currency)
        amount_formatted = _currency_service.format_price(to_float(order_total_in_balance_currency), balance_currency)
        error_msg = f"Недостаточно средств на балансе. Доступно: {balance_formatted}, требуется: {amount_formatted}"
        
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Deduct from balance
    try:
        await db.client.rpc("add_to_user_balance", {
            "p_user_id": db_user.id,
            "p_amount": -to_float(order_total_in_balance_currency),
            "p_reason": f"Payment for order {order.id}"
        }).execute()
        logger.info(f"Balance deducted {to_float(order_total_in_balance_currency):.2f} {balance_currency} for order {order.id}")
    except Exception as e:
        await db.client.table("orders").delete().eq("id", order.id).execute()
        logger.error(f"Failed to deduct balance for order {order.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ошибка списания с баланса. Попробуйте позже."
        )
    
    # Update order status
    try:
        from core.orders.status_service import OrderStatusService
        status_service = OrderStatusService(db)
        final_status = await status_service.mark_payment_confirmed(
            order_id=order.id,
            payment_id=f"balance-{order.id}",
            check_stock=True
        )
        logger.info(f"Balance payment confirmed for order {order.id}, final_status={final_status}")
    except Exception as e:
        logger.error(f"Failed to mark payment confirmed for balance order {order.id}: {e}", exc_info=True)
    
    # Queue delivery via QStash
    try:
        from core.queue import publish_to_worker, WorkerEndpoints
        await publish_to_worker(
            endpoint=WorkerEndpoints.DELIVER_GOODS,
            body={"order_id": order.id},
            retries=2,
            deduplication_id=f"deliver-{order.id}"
        )
        logger.info(f"Delivery queued for balance payment order {order.id}")
    except Exception as e:
        logger.warning(f"QStash failed for balance order {order.id}, trying direct delivery: {e}")
        try:
            from core.routers.workers import _deliver_items_for_order
            from core.routers.deps import get_notification_service
            notification_service = get_notification_service()
            await _deliver_items_for_order(db, notification_service, order.id, only_instant=True)
        except Exception as direct_err:
            logger.error(f"Direct delivery also failed for order {order.id}: {direct_err}")
    
    # Queue referral bonuses
    try:
        from core.queue import publish_to_worker, WorkerEndpoints
        await publish_to_worker(
            endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
            body={"order_id": order.id},
            retries=2,
            deduplication_id=f"referral-{order.id}"
        )
    except Exception as e:
        logger.warning(f"Failed to queue referral bonus for order {order.id}: {e}")
    
    # Apply promo code and clear cart
    if cart.promo_code:
        await db.use_promo_code(cart.promo_code)
    await cart_manager.clear_cart(user.id)
    
    return OrderResponse(
        order_id=order.id, 
        amount=to_float(total_amount), 
        original_price=to_float(total_original),
        discount_percent=discount_pct,
        payment_url=None,
        payment_method=payment_method
    )


async def _create_single_order(db, db_user, user, request: CreateOrderRequest, payment_service, payment_method: str, payment_gateway: str = "crystalpay", is_telegram_miniapp: bool = True) -> OrderResponse:
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
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check product status
    product_status = getattr(product, 'status', 'active')
    
    if product_status == 'discontinued':
        raise HTTPException(
            status_code=400,
            detail="Product is discontinued and no longer available for order."
        )
    
    if product_status == 'coming_soon':
        raise HTTPException(
            status_code=400,
            detail="Product is coming soon. Please use waitlist to be notified when available."
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
        discount_percent=0.0
    )
    
    # Apply promo code if provided
    if request.promo_code:
        promo = await db.validate_promo_code(request.promo_code)
        if not promo:
            raise HTTPException(status_code=400, detail="Invalid or expired promo code")
        await cart_manager.apply_promo_code(user.id, request.promo_code, promo["discount_percent"])
    
    # Checkout via cart
    return await _create_cart_order(db, db_user, user, payment_service, payment_method, payment_gateway, is_telegram_miniapp)


@payments_router.post("/orders/confirm-payment")
async def confirm_manual_payment(request: ConfirmPaymentRequest, user=Depends(verify_telegram_auth)):
    """
    Confirm that user has made manual payment (H2H mode).
    
    This updates order status to indicate user claims payment was made.
    Actual confirmation happens via webhook from payment gateway.
    """
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get order and verify ownership
    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Order does not belong to user")
    
    # Only pending orders can be confirmed
    if order.status not in ["pending", "awaiting_payment"]:
        raise HTTPException(status_code=400, detail=f"Order status is {order.status}, cannot confirm")
    
    # Update order status
    await db.client.table("orders").update({
        "status": "payment_pending",
        "notes": "User confirmed manual payment, awaiting gateway confirmation"
    }).eq("id", request.order_id).execute()
    
    return {"success": True, "message": "Payment confirmation received. Awaiting bank confirmation."}
