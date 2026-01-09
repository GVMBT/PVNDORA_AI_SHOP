"""
WebApp Orders Router

Order creation and history endpoints.
"""
import os
import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Header

from core.services.database import get_database
from core.services.money import to_decimal, to_float, round_money, multiply, subtract, divide
from core.auth import verify_telegram_auth
from core.routers.deps import get_payment_service
from core.payments import (
    validate_gateway_config, 
    normalize_gateway, 
    GATEWAY_CURRENCY,
)
from core.orders import build_order_payload, build_item_payload
from .models import CreateOrderRequest, OrderResponse, ConfirmPaymentRequest

logger = logging.getLogger(__name__)


# ==================== PAYMENT HELPERS ====================

async def create_payment_wrapper(
    payment_service,
    order_id: str,
    amount: Decimal,
    product_name: str,
    gateway: str,
    payment_method: str,
    user_email: str,
    user_id: int,
    currency: str = "RUB",
    is_telegram_miniapp: bool = True,
) -> Dict[str, Any]:
    """
    Unified payment creation wrapper for all gateways.
    
    Converts amount to appropriate format for each gateway:
    - CrystalPay: rubles (float)
    - Others: float rubles
    
    Returns: {"payment_url": str, "invoice_id": str|None}
    """
    gateway = normalize_gateway(gateway)
    
    # Convert amount based on gateway requirements and currency
    # CrystalPay expects amount in major units (rubles), not minor units (kopecks)
    if gateway == "crystalpay":
        # CrystalPay API expects float rubles, not kopecks
        payment_amount = to_float(round_money(amount, to_int=(currency == "RUB")))
    elif currency == "RUB":
        # Rounding to 2 decimals for RUB unless gateway requires ints (current gateways accept decimals)
        payment_amount = to_float(round_money(amount))
    else:
        # For USD/EUR/etc. keep 2 decimals
        payment_amount = to_float(round_money(amount))
    
    pay_result = await payment_service.create_payment(
        order_id=order_id,
        amount=payment_amount,
        product_name=product_name,
        method=gateway,
        payment_method=payment_method,
        user_email=user_email,
        user_id=user_id,
        currency=currency,
        is_telegram_miniapp=is_telegram_miniapp,
    )
    
    if isinstance(pay_result, dict):
        return {
            "payment_url": pay_result.get("url") or pay_result.get("payment_url"),
            "invoice_id": pay_result.get("invoice_id")
        }
    return {"payment_url": pay_result, "invoice_id": None}


async def persist_order(
    db,
    user_id: str,
    amount: Decimal,
    original_price: Decimal,
    discount_percent: int,
    payment_method: str,
    payment_gateway: str,
    user_telegram_id: int,
    expires_at: datetime,
    # New currency snapshot fields
    fiat_amount: Optional[Decimal] = None,
    fiat_currency: Optional[str] = None,
    exchange_rate_snapshot: Optional[float] = None,
):
    """Create order record in database.
    
    Note: product_id removed - products are stored in order_items table.
    
    Args:
        fiat_amount: Amount in user's currency (what they see/pay)
        fiat_currency: User's currency code (RUB, USD, etc.)
        exchange_rate_snapshot: Exchange rate at order creation (1 USD = X fiat)
    """
    return await db.create_order(
        user_id=user_id,
        amount=to_float(amount),
        original_price=to_float(original_price),
        discount_percent=discount_percent,
        payment_method=payment_method,
        payment_gateway=payment_gateway,
        user_telegram_id=user_telegram_id,
        expires_at=expires_at,
        fiat_amount=to_float(fiat_amount) if fiat_amount else None,
        fiat_currency=fiat_currency,
        exchange_rate_snapshot=exchange_rate_snapshot,
    )


async def persist_order_items(db, order_id: str, order_items: List[Dict[str, Any]]) -> None:
    """Create order_items records for partial fulfillment."""
    items_to_insert = []
    for oi in order_items:
        unit_price = divide(to_decimal(oi["amount"]), oi["quantity"]) if oi["quantity"] else to_decimal(oi["amount"])
        # instant (есть в наличии)
        for _ in range(int(oi.get("instant_quantity", 0))):
            items_to_insert.append({
                "order_id": order_id,
                "product_id": oi["product_id"],
                "quantity": 1,
                "status": "pending",
                "fulfillment_type": "instant",
                "price": to_float(unit_price),
                "discount_percent": int(oi.get("discount_percent", 0)),
            })
        # preorder (нет в наличии)
        for _ in range(int(oi.get("prepaid_quantity", 0))):
            items_to_insert.append({
                "order_id": order_id,
                "product_id": oi["product_id"],
                "quantity": 1,
                "status": "prepaid",
                "fulfillment_type": "preorder",
                "price": to_float(unit_price),
                "discount_percent": int(oi.get("discount_percent", 0)),
            })
    if items_to_insert:
        await db.create_order_items(items_to_insert)

router = APIRouter(tags=["webapp-orders"])


@router.get("/orders/{order_id}/status")
async def get_order_status(
    order_id: str,
    payment_id: Optional[str] = Query(None),
    authorization: str = Header(None, alias="Authorization"),
    x_init_data: str = Header(None, alias="X-Init-Data"),
):
    """
    Get order status by ID (for payment polling).

    - Приходит из PaymentResultPage (WebApp) с Telegram initData
    - Приходит из payresult_ deeplink (браузер) без Telegram — тогда проверяем payment_id
    """
    db = get_database()

    # Try auth; if fails, continue as anonymous
    user = None
    try:
        user = await verify_telegram_auth(authorization=authorization, x_init_data=x_init_data)
    except Exception:
        user = None

    order = await db.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if user:
        db_user = await db.get_user_by_telegram_id(user.id)
        if not db_user:
            db_user = await db.create_user(
                telegram_id=user.id,
                username=getattr(user, "username", None),
                first_name=getattr(user, "first_name", None),
                language_code=getattr(user, "language_code", "ru"),
                referrer_telegram_id=None
            )
        if order.user_id != db_user.id:
            raise HTTPException(status_code=403, detail="Order does not belong to user")
    else:
        # Anonymous polling:
        # - if payment_id is provided, must match
        # - if payment_id is absent, allow read-only status (no sensitive data)
        if payment_id and payment_id != order.payment_id:
            raise HTTPException(status_code=401, detail="Unauthorized status check")
    
    return {
        "order_id": order.id,
        "status": order.status,
        "amount": order.amount,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


@router.post("/orders/{order_id}/verify-payment")
async def verify_and_deliver_order(
    order_id: str,
    user=Depends(verify_telegram_auth)
):
    """
    Verify payment status via CrystalPay API and trigger delivery if paid.
    
    This is a FALLBACK endpoint for cases when webhook doesn't arrive.
    User must own the order.
    """
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    order = await db.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Order does not belong to user")
    
    # Only process pending orders
    if order.status not in ("pending", "awaiting_payment"):
        return {"status": order.status, "message": "Order is not in pending state"}
    
    # Check if CrystalPay (by payment_gateway)
    payment_gateway = getattr(order, "payment_gateway", None)
    if payment_gateway != "crystalpay":
        return {"status": order.status, "message": "Manual verification only supported for CrystalPay"}
    
    # Get invoice_id from payment_id field
    invoice_id = getattr(order, "payment_id", None)
    if not invoice_id:
        return {"status": order.status, "message": "No payment_id found for order"}
    
    # Query CrystalPay API for invoice status
    try:
        payment_service = get_payment_service()
        invoice_info = await payment_service.get_crystalpay_invoice_info(invoice_id)
        
        state = invoice_info.get("state", "unknown")
        logger.info(f"CrystalPay invoice {invoice_id} state: {state}")
        
        if state != "payed":
            return {
                "status": order.status,
                "invoice_state": state,
                "message": f"Invoice not paid yet. State: {state}"
            }
        
        # Invoice is paid! Update order status first, then trigger delivery
        logger.info(f"Manual delivery trigger for order {order_id}")
        
        # Check stock availability to determine status
        try:
            order_items_check = await asyncio.to_thread(
                lambda: db.client.table("order_items")
                .select("id, fulfillment_type, product_id")
                .eq("order_id", order_id)
                .execute()
            )
            
            has_stock = False
            if order_items_check.data:
                for item in order_items_check.data:
                    if item.get("fulfillment_type") == "instant":
                        product_id = item.get("product_id")
                        stock_check = await asyncio.to_thread(
                            lambda pid=product_id: db.client.table("stock_items")
                            .select("id")
                            .eq("product_id", pid)
                            .eq("status", "available")
                            .limit(1)
                            .execute()
                        )
                        if stock_check.data:
                            has_stock = True
                            break
            
            # Update order status using centralized service
            from core.orders.status_service import OrderStatusService
            status_service = OrderStatusService(db)
            final_status = await status_service.mark_payment_confirmed(
                order_id=order_id,
                payment_id=None,  # Manual verification, no payment_id update
                check_stock=has_stock
            )
            logger.info(f"Updated order {order_id} status to '{final_status}' (has_stock={has_stock})")
        except Exception as e:
            logger.warning(f"Failed to update order status before delivery: {e}")
        
        from core.routers.workers import _deliver_items_for_order
        from core.routers.deps import get_notification_service
        notification_service = get_notification_service()
        
        delivery_result = await _deliver_items_for_order(db, notification_service, order_id, only_instant=True)
        
        return {
            "status": "processed",
            "invoice_state": state,
            "delivery": delivery_result,
            "message": "Payment verified and delivery triggered"
        }
        
    except Exception as e:
        logger.error(f"Manual payment verification failed for {order_id}: {e}")
        return {
            "status": order.status,
            "error": str(e),
            "message": "Failed to verify payment"
        }


@router.get("/orders")
async def get_webapp_orders(
    user=Depends(verify_telegram_auth),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get user's order history with unified currency handling."""
    from core.db import get_redis
    from core.services.currency_response import CurrencyFormatter
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        db_user = await db.create_user(
            telegram_id=user.id,
            username=getattr(user, "username", None),
            first_name=getattr(user, "first_name", None),
            language_code=getattr(user, "language_code", "ru"),
            referrer_telegram_id=None
        )
    
    # Unified currency formatter
    redis = get_redis()
    formatter = await CurrencyFormatter.create(user.id, db, redis)
    
    # Exclude discount orders from PVNDORA Mini App (they have their own bot)
    orders = await db.get_user_orders(
        db_user.id, 
        limit=limit, 
        offset=offset,
        exclude_source_channel="discount"
    )
    order_ids = [o.id for o in orders]
    
    # Fetch order_items in bulk
    items_data = await db.get_order_items_by_orders(order_ids)
    product_ids = set()
    for o in orders:
        if o.product_id:
            product_ids.add(o.product_id)
    for it in items_data:
        if it.get("product_id"):
            product_ids.add(it["product_id"])
    
    products_map = {}
    try:
        if product_ids:
            prod_res = await asyncio.to_thread(
                lambda: db.client.table("products").select("id,name,instructions,price").in_("id", list(product_ids)).execute()
            )
            products_map = {p["id"]: p for p in (prod_res.data or [])}
    except Exception as e:
        logger.warning(f"Failed to load products map: {e}")
    
    # Fetch reviews for orders - track by (order_id, product_id) pair
    # because a review is for a specific product within an order
    reviews_by_order_product = {}
    try:
        if order_ids:
            reviews_res = await asyncio.to_thread(
                lambda: db.client.table("reviews").select("order_id, product_id").in_("order_id", order_ids).execute()
            )
            for r in (reviews_res.data or []):
                # Key by (order_id, product_id) tuple
                key = (r["order_id"], r.get("product_id"))
                reviews_by_order_product[key] = True
    except Exception as e:
        logger.warning(f"Failed to load reviews: {e}")
    
    # Build items by order
    from collections import defaultdict
    items_by_order = defaultdict(list)
    for it in items_data:
        pid = it.get("product_id")
        prod = products_map.get(pid, {})
        order_id = it.get("order_id")
        # Check if THIS specific product in THIS order has a review
        has_review = reviews_by_order_product.get((order_id, pid), False)
        item_payload = build_item_payload(it, prod, has_review=has_review)
        items_by_order[order_id].append(item_payload)
    
    # Build order payloads with unified currency handling
    result = []
    for o in orders:
        product = products_map.get(o.product_id, {})
        
        # USD values
        amount_usd = to_float(o.amount)
        original_price_usd = to_float(o.original_price) if o.original_price else None
        
        order_payload = build_order_payload(
            order=o,
            product=product,
            amount_converted=formatter.convert(o.amount),
            original_price_converted=formatter.convert(o.original_price) if o.original_price else None,
            currency=formatter.currency,
            items=items_by_order.get(o.id),
            amount_usd=amount_usd,
            original_price_usd=original_price_usd,
        )
        result.append(order_payload)
    
    return {
        "orders": result,
        "count": len(result),
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }


@router.post("/orders")
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


@router.get("/payments/methods")
async def get_payment_methods(
    user=Depends(verify_telegram_auth),
    gateway: str = Query(None, description="Payment gateway (crystalpay)"),
):
    """Get available payment methods.
    
    CrystalPay supports card and crypto payments.
    """
    # CrystalPay methods
    methods = [
        {"system_group": "card", "name": "Банковская карта", "icon": "💳", "enabled": True, "min_amount": 100},
        {"system_group": "crypto", "name": "Криптовалюта", "icon": "₿", "enabled": True, "min_amount": 50},
    ]
    return {"systems": methods}


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
            
            referrer_result = await asyncio.to_thread(
                lambda: db.client.table("users")
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
                        logger.info(f"Partner discount applied: {discount}% from referrer {db_user.referrer_id}")
                        return discount
            return 0
        except Exception as e:
            logger.warning(f"Failed to get partner discount: {e}")
            return 0
    
    partner_discount = await get_partner_discount()
    
    # 1. Determine target currency for Anchor Pricing
    # If paying with balance, use balance_currency.
    # If paying with gateway, use gateway currency (usually RUB for CrystalPay if user is RU, else USD/etc)
    from core.db import get_redis
    from core.services.currency import get_currency_service
    redis = get_redis()
    currency_service = get_currency_service(redis)
    
    target_currency = "USD"
    if payment_method == "balance":
        target_currency = getattr(db_user, 'balance_currency', 'USD') or 'USD'
    elif payment_gateway == "crystalpay":
        # Logic duplicated from below to be available for validate_cart_items
        try:
            # Получаем валюту пользователя из профиля
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
                "amount": final_price_usd,  # Store USD amount in order_items for consistency
                "original_price": original_price_usd,
                "discount_percent": discount_percent
            })
        return total_amount_usd, total_original_usd, total_fiat_amount, prepared_items
    
    async def enforce_cooldown():
        cooldown_seconds = 90
        cooldown_redis = None
        try:
            from core.db import get_redis
            cooldown_redis = get_redis()  # async client
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
            result = await asyncio.to_thread(
                lambda: db.client.table("orders")
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
    
    # Currency Handling (using values from validate_cart_items)
    gateway_currency = target_currency  # Determined before validate_cart_items
    
    # payable_amount is what we send to the gateway (in gateway_currency)
    # fiat_amount is what we store in the DB (in fiat_currency)
    payable_amount = total_fiat_amount
    fiat_amount = total_fiat_amount
    fiat_currency = target_currency
    
    exchange_rate_snapshot = 1.0
    try:
        # Get and snapshot the exchange rate for historical record
        # Note: We already used the rate (implicitly) in get_anchor_price if no anchor was set,
        # but we capture it here for the record.
        exchange_rate_snapshot = await currency_service.snapshot_rate(gateway_currency)
        
        # CRITICAL: Recalculate base USD amount from the realized Fiat amount
        # This ensures P&L reflects the actual value received (e.g. 400 RUB / 90 = $4.44),
        # rather than the list price (e.g. $5.00) which might be different due to anchor pricing.
        if exchange_rate_snapshot > 0:
            # Round to 2 decimal places for USD storage
            total_amount = round_money(divide(fiat_amount, to_decimal(exchange_rate_snapshot)))
            
        logger.info(f"Order created: {to_float(total_amount)} USD | {to_float(fiat_amount)} {fiat_currency} (Rate: {exchange_rate_snapshot})")
    except Exception as e:
        logger.warning(f"Failed to snapshot rate or recalculate USD amount: {e}")
        exchange_rate_snapshot = 1.0

    
    # ============================================================
    # Создаём заказ в БД ПЕРЕД обращением к платёжке
    # ============================================================
    
    # Calculate discount percent using Decimal (safe: clamped to 0-100)
    discount_pct = 0
    if total_original > 0:
        # (1 - amount/original) * 100, clamped to [0, 100]
        discount_ratio = subtract(Decimal("1"), divide(total_amount, total_original))
        discount_pct = max(0, min(100, int(round_money(multiply(discount_ratio, Decimal("100")), to_int=True))))
    
    # Создаём заказ в БД (реальный order_id) ДО обращения к платёжке
    # Now includes currency snapshot for accurate accounting
    payment_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    order = await persist_order(
        db=db,
        user_id=db_user.id, 
        amount=total_amount,  # Always in USD (base currency)
        original_price=total_original,
        discount_percent=discount_pct,
        payment_method=payment_method,
        payment_gateway=payment_gateway,
        user_telegram_id=user.id,  # Telegram ID для webhook доставки
        expires_at=payment_expires_at,
        # Currency snapshot fields
        fiat_amount=fiat_amount,
        fiat_currency=fiat_currency,
        exchange_rate_snapshot=exchange_rate_snapshot,
    )
    
    # Создаём строки order_items СРАЗУ после создания заказа (нужны для balance check)
    try:
        await persist_order_items(db, order.id, order_items)
    except Exception as e:
        # Critical: order without items is invalid - delete order and fail
        logger.error(f"Failed to create order_items for order {order.id}: {e}")
        await asyncio.to_thread(lambda: db.client.table("orders").delete().eq("id", order.id).execute())
        raise HTTPException(
            status_code=500,
            detail="Failed to create order items. Please try again."
        )
    
    # ============================================================
    # ОПЛАТА С БАЛАНСА: Проверка и списание
    # Balance is stored in user's balance_currency (RUB or USD)
    # ============================================================
    if payment_method == "balance":
        from core.db import get_redis
        from core.services.currency import get_currency_service
        
        _redis = get_redis()
        _currency_service = get_currency_service(_redis)
        
        # Get user's balance in their local currency
        user_balance = to_decimal(db_user.balance) if db_user.balance else Decimal("0")
        balance_currency = getattr(db_user, 'balance_currency', 'USD') or 'USD'
        
        # Get order total in user's balance currency
        order_total_usd = to_decimal(total_amount)  # total_amount is in USD
        
        if balance_currency == "USD":
            order_total_in_balance_currency = order_total_usd
        else:
            # Convert USD order total to user's balance currency
            rate = await _currency_service.get_exchange_rate(balance_currency)
            order_total_in_balance_currency = to_decimal(to_float(order_total_usd) * rate)
            # Round for integer currencies
            if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
                order_total_in_balance_currency = to_decimal(round(to_float(order_total_in_balance_currency)))
        
        # Compare in user's balance currency
        if user_balance < order_total_in_balance_currency:
            # Удаляем заказ, если баланс недостаточен
            await asyncio.to_thread(lambda: db.client.table("orders").delete().eq("id", order.id).execute())
            
            balance_formatted = _currency_service.format_price(to_float(user_balance), balance_currency)
            amount_formatted = _currency_service.format_price(to_float(order_total_in_balance_currency), balance_currency)
            error_msg = f"Недостаточно средств на балансе. Доступно: {balance_formatted}, требуется: {amount_formatted}"
            
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Deduct from balance in user's balance currency
        try:
            await asyncio.to_thread(
                lambda: db.client.rpc("add_to_user_balance", {
                    "p_user_id": db_user.id,
                    "p_amount": -to_float(order_total_in_balance_currency),
                    "p_reason": f"Payment for order {order.id}"
                }).execute()
            )
            logger.info(f"Balance deducted {to_float(order_total_in_balance_currency):.2f} {balance_currency} for order {order.id}")
        except Exception as e:
            # Откатываем заказ при ошибке списания
            await asyncio.to_thread(lambda: db.client.table("orders").delete().eq("id", order.id).execute())
            logger.error(f"Failed to deduct balance for order {order.id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Ошибка списания с баланса. Попробуйте позже."
            )
        
        # Обновляем статус заказа через централизованный сервис
        # mark_payment_confirmed проверяет сток и устанавливает 'paid' или 'prepaid'
        try:
            from core.orders.status_service import OrderStatusService
            status_service = OrderStatusService(db)
            final_status = await status_service.mark_payment_confirmed(
                order_id=order.id,
                payment_id=f"balance-{order.id}",
                check_stock=True  # CRITICAL: Check stock even for balance payments!
            )
            logger.info(f"Balance payment confirmed for order {order.id}, final_status={final_status}")
        except Exception as e:
            logger.error(f"Failed to mark payment confirmed for balance order {order.id}: {e}", exc_info=True)
            # Don't fail the request - order is created and balance is deducted
            # Status will be corrected later or delivery will handle it
        
        # Запускаем доставку через QStash (асинхронно, не блокируем ответ)
        try:
            from core.queue import publish_to_worker, WorkerEndpoints
            await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": order.id},
                retries=2,
                deduplication_id=f"deliver-{order.id}"
            )
            logger.info(f"Delivery queued for balance payment order {order.id} (status: {final_status})")
        except Exception as e:
            # Если QStash недоступен, доставляем напрямую
            logger.warning(f"QStash failed for balance order {order.id}, trying direct delivery: {e}")
            try:
                from core.routers.workers import _deliver_items_for_order
                from core.routers.deps import get_notification_service
                notification_service = get_notification_service()
                await _deliver_items_for_order(db, notification_service, order.id, only_instant=True)
            except Exception as direct_err:
                logger.error(f"Direct delivery also failed for order {order.id}: {direct_err}")
                # Не блокируем - доставка может быть повторена позже
        
        # Начисляем реферальные бонусы (асинхронно)
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
        
        # Применяем промокод и очищаем корзину
        if cart.promo_code:
            await db.use_promo_code(cart.promo_code)
        await cart_manager.clear_cart(user.id)
        
        # Возвращаем ответ БЕЗ payment_url (оплата уже прошла)
        return OrderResponse(
            order_id=order.id, 
            amount=to_float(total_amount), 
            original_price=to_float(total_original),
            discount_percent=discount_pct,
            payment_url=None,  # Нет URL - оплата уже прошла
            payment_method=payment_method
        )
    
    # ============================================================
    # ВНЕШНИЙ ПЛАТЁЖ (CrystalPay)
    # ============================================================
    
    # Пытаемся создать платёж уже с реальным order.id
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
        # Откатываем заказ и order_items, если платеж не создан
        # Сначала удаляем order_items (FK constraint), потом заказ
        try:
            await asyncio.to_thread(lambda: db.client.table("order_items").delete().eq("order_id", order.id).execute())
        except Exception:
            pass
        await asyncio.to_thread(lambda: db.client.table("orders").delete().eq("id", order.id).execute())
        error_msg = str(e)
        logger.error(f"Payment creation failed: {error_msg}")
        logger.error(f"Payment gateway: {payment_gateway}, method: {payment_method}, amount: {payable_amount}")
        
        # Понятные сообщения для пользователя
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
        # Откатываем заказ и order_items при ошибке
        try:
            await asyncio.to_thread(lambda: db.client.table("order_items").delete().eq("order_id", order.id).execute())
        except Exception:
            pass
        await asyncio.to_thread(lambda: db.client.table("orders").delete().eq("id", order.id).execute())
        logger.error(f"Payment creation failed: {e}")
        raise HTTPException(
            status_code=502, 
            detail="Платёжная система недоступна. Попробуйте позже."
        )
    
    # Сохраняем payment_url и invoice_id в заказ
    try:
        update_payload = {"payment_url": payment_url}
        if invoice_id:
            update_payload["payment_id"] = str(invoice_id)
        await asyncio.to_thread(
            lambda: db.client.table("orders").update(update_payload).eq("id", order.id).execute()
        )
    except Exception as e:
        logger.warning(f"Failed to save payment info for order {order.id}: {e}")
    
    # order_items уже созданы выше (до проверки баланса/создания платежа)
    # Здесь только устанавливаем cooldown и очищаем корзину
    
    # Устанавливаем cooldown
    if cooldown_redis:
        try:
            await cooldown_redis.set(f"pay:cooldown:{user.id}", "1", ex=cooldown_seconds)
        except Exception as e:
            logger.warning(f"Failed to set cooldown key: {e}")
    
    # Применяем промокод и очищаем корзину
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


async def _create_single_order(db, db_user, user, request: CreateOrderRequest, payment_service, payment_method: str, payment_gateway: str = "crystalpay") -> OrderResponse:
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
    
    # Проверка статуса товара
    product_status = getattr(product, 'status', 'active')
    
    # discontinued - товара больше нет, заказ недоступен
    if product_status == 'discontinued':
        raise HTTPException(
            status_code=400,
            detail="Product is discontinued and no longer available for order."
        )
    
    # coming_soon - только waitlist, заказ недоступен
    if product_status == 'coming_soon':
        raise HTTPException(
            status_code=400,
            detail="Product is coming soon. Please use waitlist to be notified when available."
        )
    
    # active или out_of_stock - можно заказать
    quantity = request.quantity or 1
    
    from core.cart import get_cart_manager
    cart_manager = get_cart_manager()
        
    # Добавляем в корзину (учитывая сток для разбиения instant/prepaid внутри cart_manager)
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
    
    # Применяем промокод к корзине, если передан
    if request.promo_code:
        promo = await db.validate_promo_code(request.promo_code)
        if not promo:
            raise HTTPException(status_code=400, detail="Invalid or expired promo code")
        await cart_manager.apply_promo_code(user.id, request.promo_code, promo["discount_percent"])
    
    # Выполняем checkout по корзине (один заказ на содержимое корзины)
    return await _create_cart_order(db, db_user, user, payment_service, payment_method, payment_gateway)


@router.post("/orders/confirm-payment")
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
    
    # Update order status to "payment_pending" - user claims paid, awaiting webhook
    import asyncio
    await asyncio.to_thread(
        lambda: db.client.table("orders").update({
            "status": "payment_pending",
            "notes": "User confirmed manual payment, awaiting gateway confirmation"
        }).eq("id", request.order_id).execute()
    )
    
    return {"success": True, "message": "Payment confirmation received. Awaiting bank confirmation."}
