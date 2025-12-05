"""
WebApp Orders Router

Order creation and history endpoints.
"""
import os
import asyncio

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
        redis = await get_redis()
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
    
    # Determine payment method based on user region
    # Priority: 1Plat > CardLink > AAIO > Stripe
    onplat_configured = bool(os.environ.get("ONEPLAT_API_KEY"))
    cardlink_configured = bool(os.environ.get("CARDLINK_API_TOKEN") and os.environ.get("CARDLINK_SHOP_ID"))
    
    if onplat_configured and db_user.language_code in ["ru", "uk", "be", "kk"]:
        payment_method = "1plat"
    elif cardlink_configured and db_user.language_code in ["ru", "uk", "be", "kk"]:
        payment_method = "cardlink"
    elif db_user.language_code in ["ru", "uk", "be", "kk"]:
        payment_method = "aaio"
    else:
        payment_method = "stripe"
    
    payment_service = get_payment_service()
    
    # Cart-based order
    if request.use_cart or (not request.product_id):
        return await _create_cart_order(db, db_user, user, payment_service, payment_method)
    
    # Single product order
    return await _create_single_order(db, db_user, user, request, payment_service, payment_method)


async def _create_cart_order(db, db_user, user, payment_service, payment_method: str) -> OrderResponse:
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
        
        if item.instant_quantity > 0:
            available_stock = await db.get_available_stock_count(item.product_id)
            if available_stock < item.instant_quantity:
                raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}")
        
        original_price = product.price * item.quantity
        discount_percent = item.discount_percent
        if cart.promo_code and cart.promo_discount_percent > 0:
            discount_percent = max(discount_percent, cart.promo_discount_percent)
        
        final_price = original_price * (1 - discount_percent / 100)
        total_amount += final_price
        total_original += original_price
        
        order_items.append({
            "product_id": item.product_id, "product_name": product.name,
            "quantity": item.quantity, "amount": final_price,
            "original_price": original_price, "discount_percent": discount_percent
        })
    
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
    
    payment_url = await payment_service.create_payment(
        order_id=order.id, amount=total_amount, product_name=product_names,
        method=payment_method, user_email=f"{user.id}@telegram.user"
    )
    
    if cart.promo_code:
        await db.use_promo_code(cart.promo_code)
    await cart_manager.clear_cart(user.id)
    
    return OrderResponse(
        order_id=order.id, amount=total_amount, original_price=total_original,
        discount_percent=int((1 - total_amount / total_original) * 100) if total_original > 0 else 0,
        payment_url=payment_url, payment_method=payment_method
    )


async def _create_single_order(db, db_user, user, request: CreateOrderRequest, payment_service, payment_method: str) -> OrderResponse:
    """Create order for single product."""
    if not request.product_id:
        raise HTTPException(status_code=400, detail="product_id is required")
    
    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    quantity = request.quantity or 1
    available_stock = await db.get_available_stock_count(request.product_id)
    if available_stock < quantity:
        raise HTTPException(status_code=400, detail=f"Not enough stock. Available: {available_stock}")
    
    original_price = product.price * quantity
    discount_percent = 0
    
    stock_item = await db.get_available_stock_item(request.product_id)
    if stock_item:
        discount_percent = await db.calculate_discount(stock_item, product)
    
    if request.promo_code:
        promo = await db.validate_promo_code(request.promo_code)
        if promo:
            discount_percent = max(discount_percent, promo["discount_percent"])
    
    final_price = original_price * (1 - discount_percent / 100)
    
    order = await db.create_order(
        user_id=db_user.id, product_id=request.product_id,
        amount=final_price, original_price=original_price,
        discount_percent=discount_percent, payment_method=payment_method
    )
    
    payment_url = await payment_service.create_payment(
        order_id=order.id, amount=final_price, product_name=product.name,
        method=payment_method, user_email=f"{user.id}@telegram.user"
    )
    
    if request.promo_code:
        await db.use_promo_code(request.promo_code)
    
    return OrderResponse(
        order_id=order.id, amount=final_price, original_price=original_price,
        discount_percent=discount_percent, payment_url=payment_url, payment_method=payment_method
    )
