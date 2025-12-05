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
    
    # Determine payment method - only 1Plat is supported
    # 1Plat использует x-shop (ONEPLAT_SHOP_ID) и x-secret (ONEPLAT_SECRET_KEY)
    onplat_configured = bool(
        (os.environ.get("ONEPLAT_SHOP_ID") or os.environ.get("ONEPLAT_MERCHANT_ID")) and
        os.environ.get("ONEPLAT_SECRET_KEY")
    )
    
    if not onplat_configured:
        raise HTTPException(
            status_code=500,
            detail="Payment service not configured. Please configure 1Plat credentials."
        )
    
    payment_method = "1plat"
    
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
        method=payment_method, user_email=f"{user.id}@telegram.user",
        user_id=db_user.id
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
    """
    Create order for single product.
    
    Uses create_order_with_availability_check RPC function which:
    - If product is in stock → creates instant order
    - If product is not in stock → creates prepaid order automatically
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
    
    # active или out_of_stock - можно заказать (RPC функция обработает)
    quantity = request.quantity or 1
    
    # For quantity > 1, we need to handle it differently
    # For now, we'll create orders one by one (can be optimized later)
    if quantity > 1:
        # TODO: Support multiple quantities - create multiple orders or use cart
        raise HTTPException(
            status_code=400, 
            detail=f"Multiple quantities not yet supported. Please use cart for multiple items."
        )
    
    # Use RPC function that automatically handles instant vs prepaid
    # RPC функция принимает только active и out_of_stock
    try:
        order_result = await db.create_order_with_availability_check(
            product_id=request.product_id,
            user_telegram_id=user.id
        )
    except Exception as e:
        error_msg = str(e)
        if "not found or unavailable" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Product is not available for ordering. Status must be active or out_of_stock."
            )
        print(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")
    
    order_id = order_result["order_id"]
    order_type = order_result["order_type"]  # "instant" or "prepaid"
    
    # Get the created order to get full details (amount, original_price, discount_percent)
    order = await db.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=500, detail="Order created but not found")
    
    # Get prices from order (RPC function already calculated discount for instant orders)
    amount = float(order.amount)
    original_price = float(order.original_price) if order.original_price else amount
    discount_percent = order.discount_percent or 0
    
    # Apply promo code discount if provided (additional discount on top of stock discount)
    if request.promo_code:
        promo = await db.validate_promo_code(request.promo_code)
        if promo:
            promo_discount = promo["discount_percent"]
            # Apply promo discount on top of existing discount
            # Calculate from original_price
            total_discount = max(discount_percent, promo_discount)
            amount = original_price * (1 - total_discount / 100)
            discount_percent = total_discount
            # TODO: Update order amount and discount_percent in DB if promo applied
    
    # Prepare product name for payment
    product_name = product.name
    if order_type == "prepaid":
        fulfillment_deadline = order_result.get("fulfillment_deadline")
        if fulfillment_deadline:
            # Add prepaid info to product name
            product_name = f"{product.name} (под заказ)"
    
    payment_url = await payment_service.create_payment(
        order_id=order_id, amount=amount, product_name=product_name,
        method=payment_method, user_email=f"{user.id}@telegram.user",
        user_id=db_user.id
    )
    
    if request.promo_code:
        await db.use_promo_code(request.promo_code)
    
    return OrderResponse(
        order_id=order_id, amount=amount, original_price=original_price,
        discount_percent=discount_percent, payment_url=payment_url, payment_method=payment_method
    )
