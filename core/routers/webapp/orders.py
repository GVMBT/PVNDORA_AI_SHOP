"""
WebApp Orders Router

Order creation and history endpoints.
"""
import os
import asyncio
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends

from src.services.database import get_database
from core.auth import verify_telegram_auth
from core.routers.deps import get_payment_service
from .models import CreateOrderRequest, OrderResponse

router = APIRouter(tags=["webapp-orders"])


@router.get("/orders")
async def get_webapp_orders(user=Depends(verify_telegram_auth)):
    """Get user's order history with currency conversion."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
        print(f"Warning: Currency service unavailable: {e}, using USD")
    
    orders = await db.get_user_orders(db_user.id, limit=50)
    
    result = []
    for o in orders:
        product = await db.get_product_by_id(o.product_id)
        
        # Convert prices from USD to user currency
        amount_converted = float(o.amount)
        original_price_converted = float(o.original_price) if o.original_price else None
        
        if currency_service and currency != "USD":
            try:
                amount_converted = await currency_service.convert_price(float(o.amount), currency, round_to_int=True)
                if original_price_converted:
                    original_price_converted = await currency_service.convert_price(float(o.original_price), currency, round_to_int=True)
            except Exception as e:
                print(f"Warning: Failed to convert order prices: {e}")
        
        result.append({
            "id": o.id, "product_id": o.product_id,
            "product_name": product.name if product else "Unknown Product",
            "amount": amount_converted, 
            "original_price": original_price_converted,
            "discount_percent": o.discount_percent, "status": o.status,
            "order_type": getattr(o, 'order_type', 'instant'),
            "currency": currency,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "delivered_at": o.delivered_at.isoformat() if hasattr(o, 'delivered_at') and o.delivered_at else None,
            "expires_at": o.expires_at.isoformat() if o.expires_at else None,
            "warranty_until": o.warranty_until.isoformat() if hasattr(o, 'warranty_until') and o.warranty_until else None
        })
    
    return {"orders": result, "count": len(result), "currency": currency}


@router.post("/orders")
async def create_webapp_order(request: CreateOrderRequest, user=Depends(verify_telegram_auth)):
    """Create new order from Mini App. Supports both single product and cart-based orders."""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Determine payment gateway - support both 1Plat and Freekassa
    payment_gateway = request.payment_gateway or os.environ.get("DEFAULT_PAYMENT_GATEWAY", "1plat")
    
    # Check if requested gateway is configured
    if payment_gateway == "freekassa":
        freekassa_configured = bool(
            os.environ.get("FREEKASSA_MERCHANT_ID") and
            os.environ.get("FREEKASSA_SECRET_WORD_1") and
            os.environ.get("FREEKASSA_SECRET_WORD_2")
        )
        if not freekassa_configured:
            raise HTTPException(
                status_code=500,
                detail="Freekassa не настроен. Настройте FREEKASSA_MERCHANT_ID, FREEKASSA_SECRET_WORD_1, FREEKASSA_SECRET_WORD_2"
            )
    else:  # Default to 1Plat
        onplat_configured = bool(
            (os.environ.get("ONEPLAT_SHOP_ID") or os.environ.get("ONEPLAT_MERCHANT_ID")) and
            os.environ.get("ONEPLAT_SECRET_KEY")
        )
        if not onplat_configured:
            raise HTTPException(
                status_code=500,
                detail="Payment service not configured. Please configure 1Plat credentials."
            )
    
    payment_method = request.payment_method or "card"
    
    payment_service = get_payment_service()
    
    # Cart-based order
    if request.use_cart or (not request.product_id):
        return await _create_cart_order(db, db_user, user, payment_service, payment_method, payment_gateway)
    
    # Single product order
    return await _create_single_order(db, db_user, user, request, payment_service, payment_method, payment_gateway)


@router.get("/payments/methods")
async def get_payment_methods(user=Depends(verify_telegram_auth)):
    """Get available payment methods from 1Plat."""
    payment_service = get_payment_service()
    try:
        data = await payment_service.list_payment_methods()
        return data
    except Exception as e:
        print(f"Failed to fetch payment methods: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch payment methods")


async def _create_cart_order(db, db_user, user, payment_service, payment_method: str, payment_gateway: str = "1plat") -> OrderResponse:
    """Create order from cart items."""
    from core.cart import get_cart_manager
    cart_manager = get_cart_manager()
    cart = await cart_manager.get_cart(user.id)
    
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    total_amount, total_original = 0.0, 0.0
    order_items = []
    
    for item in cart.items:
        product = await db.get_product_by_id(item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        # Cart already splits items into instant_quantity and prepaid_quantity
        # We need to create orders for both types
        # For now, we'll create one order per item (can be optimized to create separate orders for instant/prepaid)
        
        # Check if instant items are still available (stock might have changed)
        if item.instant_quantity > 0:
            available_stock = await db.get_available_stock_count(item.product_id)
            if available_stock < item.instant_quantity:
                # Stock changed - update cart split or create prepaid order
                # For simplicity, convert to prepaid if stock insufficient
                print(f"Warning: Stock changed for {product.name}. Requested {item.instant_quantity}, available {available_stock}")
                # Continue with prepaid for unavailable items
                # TODO: Better handling - update cart or create mixed order
        
        original_price = product.price * item.quantity
        discount_percent = item.discount_percent
        if cart.promo_code and cart.promo_discount_percent > 0:
            discount_percent = max(discount_percent, cart.promo_discount_percent)
        
        final_price = original_price * (1 - discount_percent / 100)
        total_amount += final_price
        total_original += original_price
        
        order_items.append({
            "product_id": item.product_id, "product_name": product.name,
            "quantity": item.quantity, 
            "instant_quantity": item.instant_quantity,
            "prepaid_quantity": item.prepaid_quantity,
            "amount": final_price,
            "original_price": original_price, "discount_percent": discount_percent
        })
    
    # Cooldown: не бомбим 1Plat, если недавно создавали платеж
    cooldown_seconds = 90
    redis = None
    try:
        from core.db import get_redis
        redis = get_redis()  # async client
        cooldown_key = f"pay:cooldown:{user.id}"
        existing = await redis.get(cooldown_key)
        if existing:
            raise HTTPException(
                status_code=429,
                detail="Подождите ~1 минуту перед повторным созданием платежа"
            )
    except HTTPException:
        raise
    except (ValueError, AttributeError) as e:
        # Redis не настроен или недоступен - используем fallback через БД
        print(f"Warning: Redis unavailable, using DB fallback for cooldown: {e}")
        redis = None
    except Exception as e:
        # Другие ошибки Redis - используем fallback через БД
        print(f"Warning: Redis error, using DB fallback for cooldown: {e}")
        redis = None

    # Не создаём новый заказ, если есть свежий pending (дубликаты)
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
        print(f"Warning: pending order check failed: {e}")

    first_item = order_items[0]
    order = await db.create_order(
        user_id=db_user.id, product_id=first_item["product_id"],
        amount=total_amount, original_price=total_original,
        discount_percent=int((1 - total_amount / total_original) * 100) if total_original > 0 else 0,
        payment_method=payment_method
    )
    
    product_names = ", ".join([item["product_name"] for item in order_items[:3]])
    if len(order_items) > 3:
        product_names += f" и еще {len(order_items) - 3}"
    
    # Конвертация суммы в RUB для платёжного шлюза
    payable_amount = total_amount
    try:
        from core.db import get_redis
        from src.services.currency import get_currency_service
        redis = get_redis()
        currency_service = get_currency_service(redis)
        user_currency = currency_service.get_user_currency(db_user.language_code or user.language_code)
        payable_amount = await currency_service.convert_price(float(total_amount), "RUB", round_to_int=True)
    except Exception as e:
        print(f"Warning: currency conversion failed, using raw amount: {e}")
    
    try:
        payment_url = await payment_service.create_payment(
            order_id=order.id, amount=payable_amount, product_name=product_names,
            method=payment_gateway, payment_method=payment_method,
            user_email=f"{user.id}@telegram.user",
            user_id=user.id  # Telegram user id (numeric) for gateway
        )
        if redis:
            try:
                await redis.set(f"pay:cooldown:{user.id}", "1", ex=cooldown_seconds)
            except Exception as e:
                print(f"Warning: failed to set cooldown key: {e}")
    except HTTPException:
        # Уже обработано выше
        raise
    except ValueError as e:
        print(f"Payment creation failed for cart order {order.id}: {e}")
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        print(f"Payment creation failed for cart order {order.id}: {e}")
        raise HTTPException(status_code=502, detail="Payment service unavailable")
    
    if cart.promo_code:
        await db.use_promo_code(cart.promo_code)
    await cart_manager.clear_cart(user.id)
    
    return OrderResponse(
        order_id=order.id, amount=total_amount, original_price=total_original,
        discount_percent=int((1 - total_amount / total_original) * 100) if total_original > 0 else 0,
        payment_url=payment_url, payment_method=payment_method
    )


async def _create_single_order(db, db_user, user, request: CreateOrderRequest, payment_service, payment_method: str, payment_gateway: str = "1plat") -> OrderResponse:
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
