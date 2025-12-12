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

from src.services.database import get_database
from src.services.money import to_decimal, to_float, round_money, multiply, subtract, divide, to_kopecks
from core.auth import verify_telegram_auth
from core.routers.deps import get_payment_service
from core.payments import (
    validate_gateway_config, 
    normalize_gateway, 
    DELIVERED_STATES,
    OrderStatus,
    GATEWAY_CURRENCY,
)
from core.orders import build_order_payload, build_item_payload, convert_order_prices
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
) -> Dict[str, Any]:
    """
    Unified payment creation wrapper for all gateways.
    
    Converts amount to appropriate format for each gateway:
    - 1Plat: kopecks (integer minor units)
    - Others: float rubles
    
    Returns: {"payment_url": str, "invoice_id": str|None}
    """
    gateway = normalize_gateway(gateway)
    
    # Convert amount based on gateway requirements and currency
    if gateway == "1plat":
        payment_amount = to_kopecks(amount)  # minor units
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
        currency=currency
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
    product_id: str,
    amount: Decimal,
    original_price: Decimal,
    discount_percent: int,
    payment_method: str,
    payment_gateway: str,
    user_telegram_id: int,
    expires_at: datetime
):
    """Create order record in database."""
    return await db.create_order(
        user_id=user_id,
        product_id=product_id,
        amount=to_float(amount),
        original_price=to_float(original_price),
        discount_percent=discount_percent,
        payment_method=payment_method,
        payment_gateway=payment_gateway,
        user_telegram_id=user_telegram_id,
        expires_at=expires_at
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
        
        # Invoice is paid! Trigger delivery
        logger.info(f"Manual delivery trigger for order {order_id}")
        
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
    """Get user's order history with currency conversion and pagination."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        # Авто-создание пользователя, если он впервые
        db_user = await db.create_user(
            telegram_id=user.id,
            username=getattr(user, "username", None),
            first_name=getattr(user, "first_name", None),
            language_code=getattr(user, "language_code", "ru"),
            referrer_telegram_id=None
        )
    
    # Get currency service and convert prices
    currency = "USD"
    currency_service = None
    
    try:
        from core.db import get_redis
        from src.services.currency import get_currency_service
        redis = get_redis()  # get_redis() is synchronous, no await needed
        currency_service = get_currency_service(redis)
        currency = currency_service.get_user_currency(db_user.language_code or user.language_code)
    except Exception as e:
        logger.warning(f"Currency service unavailable: {e}, using USD")
    
    orders = await db.get_user_orders(db_user.id, limit=limit, offset=offset)
    order_ids = [o.id for o in orders]
    
    # Fetch order_items in bulk
    items_data = await db.get_order_items_by_orders(order_ids)
    # Collect product ids from both orders (legacy product_id) and items
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
    
    # Fetch reviews for orders (to determine has_review)
    reviews_by_order = {}
    try:
        if order_ids:
            reviews_res = await asyncio.to_thread(
                lambda: db.client.table("reviews").select("order_id").in_("order_id", order_ids).execute()
            )
            for r in (reviews_res.data or []):
                reviews_by_order[r["order_id"]] = True
    except Exception as e:
        logger.warning(f"Failed to load reviews: {e}")
    
    # Build items by order using helper
    from collections import defaultdict
    items_by_order = defaultdict(list)
    for it in items_data:
        pid = it.get("product_id")
        prod = products_map.get(pid, {})
        order_id = it.get("order_id")
        has_review = reviews_by_order.get(order_id, False)
        item_payload = build_item_payload(it, prod, has_review=has_review)
        items_by_order[order_id].append(item_payload)
    
    # Build order payloads using helper
    result = []
    for o in orders:
        product = products_map.get(o.product_id, {})
        
        # Convert prices
        amount_converted, original_price_converted = await convert_order_prices(
            to_decimal(o.amount),
            to_decimal(o.original_price) if o.original_price else None,
            currency,
            currency_service
        )
        
        # Build order payload
        order_payload = build_order_payload(
            order=o,
            product=product,
            amount_converted=amount_converted,
            original_price_converted=original_price_converted,
            currency=currency,
            items=items_by_order.get(o.id)
        )
        result.append(order_payload)
    
    return {"orders": result, "count": len(result), "currency": currency}


@router.post("/orders")
async def create_webapp_order(request: CreateOrderRequest, user=Depends(verify_telegram_auth)):
    """Create new order from Mini App. Supports both single product and cart-based orders."""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Determine payment gateway - support 1Plat, Freekassa, Rukassa, CrystalPay
    payment_gateway = request.payment_gateway or os.environ.get("DEFAULT_PAYMENT_GATEWAY", "rukassa")
    # Normalize + validate gateway configuration
    payment_gateway = validate_gateway_config(payment_gateway)
    
    payment_method = request.payment_method or "card"
    
    payment_service = get_payment_service()
    
    # Cart-based order
    if request.use_cart or (not request.product_id):
        return await _create_cart_order(db, db_user, user, payment_service, payment_method, payment_gateway)
    
    # Single product order
    return await _create_single_order(db, db_user, user, request, payment_service, payment_method, payment_gateway)


@router.get("/payments/methods")
async def get_payment_methods(
    user=Depends(verify_telegram_auth),
    gateway: str = Query(None, description="Payment gateway override (rukassa|crystalpay|1plat|freekassa)"),
):
    """Get available payment methods based on configured gateway.
    
    Returns methods with their status (enabled/disabled).
    Disabled methods are read from RUKASSA_DISABLED_METHODS env (comma-separated).
    Example: RUKASSA_DISABLED_METHODS=sbp_qr,clever
    """
    selected_gateway = (gateway or os.environ.get("DEFAULT_PAYMENT_GATEWAY", "rukassa")).lower()
    
    # Rukassa methods (https://lk.rukassa.io)
    if selected_gateway == "rukassa":
        # Read disabled methods from env (comma-separated list)
        disabled_methods_str = os.environ.get("RUKASSA_DISABLED_METHODS", "")
        disabled_methods = set(m.strip().lower() for m in disabled_methods_str.split(",") if m.strip())
        
        # Base methods with min amounts (from Rukassa settings)
        methods = [
            {"system_group": "card", "name": "Карта", "icon": "💳", "min_amount": 1000},
            {"system_group": "sbp", "name": "СБП", "icon": "🏦", "min_amount": 1000},
            {"system_group": "sbp_qr", "name": "QR-код СБП", "icon": "📱", "min_amount": 10},
            {"system_group": "crypto", "name": "Криптовалюта", "icon": "₿", "min_amount": 50},
        ]
        
        # Add enabled/disabled status
        for method in methods:
            method["enabled"] = method["system_group"] not in disabled_methods
        
        return {"systems": methods}
    
    # CrystalPay methods
    elif selected_gateway == "crystalpay":
        # CrystalPay accepts all methods generally, but we can restrict if needed
        # Assuming all main methods are available via their single payment page
        methods = [
            {"system_group": "card", "name": "Банковская карта", "icon": "💳", "enabled": True, "min_amount": 100},
            {"system_group": "sbp", "name": "СБП", "icon": "🏦", "enabled": True, "min_amount": 100},
            {"system_group": "crypto", "name": "Криптовалюта", "icon": "₿", "enabled": True, "min_amount": 50},
        ]
        return {"systems": methods}
    
    # Fallback to 1Plat methods
    payment_service = get_payment_service()
    try:
        data = await payment_service.list_payment_methods()
        return data
    except Exception as e:
        logger.warning(f"Failed to fetch payment methods: {e}")
        # Return default methods on error
        return {
            "systems": [
                {"system_group": "card", "name": "Карта", "icon": "💳", "enabled": True, "min_amount": 0},
                {"system_group": "sbp", "name": "СБП", "icon": "🏦", "enabled": True, "min_amount": 0},
            ]
        }


async def _create_cart_order(db, db_user, user, payment_service, payment_method: str, payment_gateway: str = "rukassa") -> OrderResponse:
    """Create order from cart items."""
    from core.cart import get_cart_manager
    cart_manager = get_cart_manager()
    cart = await cart_manager.get_cart(user.id)
    
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Helpers
    async def validate_cart_items(cart_items) -> Tuple[Decimal, Decimal, List[Dict[str, Any]]]:
        """Validate cart items, calculate totals using Decimal, handle stock deficits."""
        total_amount = Decimal("0")
        total_original = Decimal("0")
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
            
            # Use Decimal for all price calculations
            product_price = to_decimal(product.price)
            original_price = multiply(product_price, item.quantity)
            
            discount_percent = item.discount_percent
            if cart.promo_code and cart.promo_discount_percent > 0:
                discount_percent = max(discount_percent, cart.promo_discount_percent)
            
            # Validate discount is in reasonable range
            discount_percent = max(0, min(100, discount_percent))
            
            # Calculate discount: original * (1 - discount/100)
            discount_multiplier = subtract(Decimal("1"), divide(to_decimal(discount_percent), Decimal("100")))
            final_price = round_money(multiply(original_price, discount_multiplier))
            
            total_amount += final_price
            total_original += original_price
            
            prepared_items.append({
                "product_id": item.product_id,
                "product_name": product.name,
                "quantity": item.quantity, 
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity,
                "amount": final_price,
                "original_price": original_price,
                "discount_percent": discount_percent
            })
        return total_amount, total_original, prepared_items
    
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
    total_amount, total_original, order_items = await validate_cart_items(cart.items)
    
    # Cooldown checks
    cooldown_redis, cooldown_seconds = await enforce_cooldown()
    
    first_item = order_items[0]
    product_names = ", ".join([item["product_name"] for item in order_items[:3]])
    if len(order_items) > 3:
        product_names += f" и еще {len(order_items) - 3}"
    
    # Определяем валюту шлюза
    gateway_currency = GATEWAY_CURRENCY.get(payment_gateway, "RUB")
    
    # Конвертация суммы в валюту шлюза
    payable_amount = to_decimal(total_amount)
    try:
        from core.db import get_redis
        from src.services.currency import get_currency_service
        currency_redis = get_redis()
        currency_service = get_currency_service(currency_redis)
        # Конвертация из базовой валюты (USD) в валюту шлюза
        if gateway_currency != "USD":
            payable_amount = to_decimal(await currency_service.convert_price(total_amount, gateway_currency, round_to_int=True))
    except Exception as e:
        logger.warning(f"Currency conversion failed, using raw amount: {e}")
    
    # Если Rukassa: попытаться отменить предыдущий незавершённый платёж (антифрод)
    if payment_gateway == "rukassa":
        try:
            result = await asyncio.to_thread(
                lambda: db.client.table("orders")
                .select("id,payment_id,status")
                .eq("user_id", db_user.id)
                .eq("status", "pending")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                prev = result.data[0]
                prev_payment_id = prev.get("payment_id")
                if prev_payment_id:
                    cancel_res = await payment_service.revoke_rukassa_payment(prev_payment_id)
                    if cancel_res.get("success") and cancel_res.get("status") == "CANCEL":
                        try:
                            await asyncio.to_thread(
                                lambda: db.client.table("orders")
                                .update({"status": "cancelled"})
                                .eq("id", prev.get("id"))
                                .execute()
                            )
                        except Exception as e:
                            logger.warning(f"Failed to mark order {prev.get('id')} cancelled: {e}")
                    else:
                        # если revoke не удался, просто логируем; это не должно блокировать создание
                        logger.info(f"Rukassa revoke skipped: {cancel_res}")
        except Exception as e:
            logger.warning(f"Revoke previous Rukassa payment failed: {e}")

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
    payment_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    order = await persist_order(
        db=db,
        user_id=db_user.id, 
        product_id=first_item["product_id"],  # legacy field, first product
        amount=total_amount, 
        original_price=total_original,
        discount_percent=discount_pct,
        payment_method=payment_method,
        payment_gateway=payment_gateway,
        user_telegram_id=user.id,  # Telegram ID для webhook доставки
        expires_at=payment_expires_at
    )
    
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
        )
        payment_url = pay_result.get("payment_url")
        invoice_id = pay_result.get("invoice_id")
    except ValueError as e:
        # Откатываем заказ, если платеж не создан
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
    
    # Создаём строки order_items (по одному на штуку, для удобства частичной выдачи)
    try:
        await persist_order_items(db, order.id, order_items)
    except Exception as e:
        # Critical: order without items is invalid - mark as error status
        logger.error(f"Failed to create order_items for order {order.id}: {e}")
        try:
            await asyncio.to_thread(
                lambda: db.client.table("orders").update({
                    "status": OrderStatus.ERROR.value,
                    "notes": f"Failed to create order items: {str(e)[:200]}"
                }).eq("id", order.id).execute()
            )
        except Exception as rollback_err:
            logger.error(f"Failed to mark order {order.id} as error: {rollback_err}")
    
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
    
    return OrderResponse(
        order_id=order.id, 
        amount=to_float(total_amount), 
        original_price=to_float(total_original),
        discount_percent=discount_pct,
        payment_url=payment_url, 
        payment_method=payment_method
    )


async def _create_single_order(db, db_user, user, request: CreateOrderRequest, payment_service, payment_method: str, payment_gateway: str = "rukassa") -> OrderResponse:
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
