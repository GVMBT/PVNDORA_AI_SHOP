"""
WebApp Cart Router

Shopping cart endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends

from src.services.database import get_database
from core.auth import verify_telegram_auth
from .models import AddToCartRequest, UpdateCartItemRequest, ApplyPromoRequest

router = APIRouter(tags=["webapp-cart"])


async def _format_cart_response(cart, db, user_language: str):
    """Build cart response with currency conversion."""
    from core.db import get_redis
    from src.services.currency import get_currency_service
    
    currency = "USD"
    currency_service = None
    
    try:
        redis = get_redis()  # get_redis() is synchronous, no await needed
        currency_service = get_currency_service(redis)
        currency = currency_service.get_user_currency(user_language)
    except Exception as e:
        print(f"Warning: Currency service unavailable: {e}, using USD")
    
    if not cart:
        return {
            "cart": None, "items": [], "total": 0.0, "subtotal": 0.0,
            "instant_total": 0.0, "prepaid_total": 0.0, 
            "promo_code": None, "promo_discount_percent": 0.0,
            "currency": currency
        }
    
    items_with_details = []
    total_converted = cart.total
    subtotal_converted = cart.subtotal
    instant_total_converted = cart.instant_total
    prepaid_total_converted = cart.prepaid_total
    
    for item in cart.items:
        product = await db.get_product_by_id(item.product_id)
        
        # Convert prices from USD to user currency
        unit_price_converted = float(item.unit_price)
        final_price_converted = float(item.final_price)
        total_price_converted = float(item.total_price)
        
        if currency_service and currency != "USD":
            try:
                unit_price_converted = await currency_service.convert_price(float(item.unit_price), currency, round_to_int=True)
                final_price_converted = await currency_service.convert_price(float(item.final_price), currency, round_to_int=True)
                total_price_converted = await currency_service.convert_price(float(item.total_price), currency, round_to_int=True)
            except Exception as e:
                print(f"Warning: Failed to convert cart item prices: {e}")
        
        items_with_details.append({
            "product_id": item.product_id, 
            "product_name": product.name if product else "Unknown",
            "quantity": item.quantity, 
            "instant_quantity": item.instant_quantity,
            "prepaid_quantity": item.prepaid_quantity, 
            "unit_price": unit_price_converted,
            "final_price": final_price_converted, 
            "total_price": total_price_converted, 
            "discount_percent": item.discount_percent,
            "currency": currency
        })
    
    # Convert totals
    if currency_service and currency != "USD":
        try:
            total_converted = await currency_service.convert_price(float(cart.total), currency, round_to_int=True)
            subtotal_converted = await currency_service.convert_price(float(cart.subtotal), currency, round_to_int=True)
            instant_total_converted = await currency_service.convert_price(float(cart.instant_total), currency, round_to_int=True)
            prepaid_total_converted = await currency_service.convert_price(float(cart.prepaid_total), currency, round_to_int=True)
        except Exception as e:
            print(f"Warning: Failed to convert cart totals: {e}")
    
    return {
        "cart": {
            "user_telegram_id": cart.user_telegram_id, 
            "created_at": cart.created_at, 
            "updated_at": cart.updated_at
        },
        "items": items_with_details, 
        "total": total_converted, 
        "subtotal": subtotal_converted,
        "instant_total": instant_total_converted, 
        "prepaid_total": prepaid_total_converted,
        "promo_code": cart.promo_code, 
        "promo_discount_percent": cart.promo_discount_percent,
        "currency": currency
    }


def _ensure_product_orderable(product):
    """Validate product status for cart operations."""
    status = getattr(product, "status", "active")
    if status == "discontinued":
        raise HTTPException(status_code=400, detail="Product is discontinued and unavailable for order.")
    if status == "coming_soon":
        raise HTTPException(status_code=400, detail="Product is coming soon. Use waitlist to be notified.")
    return status


@router.get("/cart")
async def get_webapp_cart(user=Depends(verify_telegram_auth)):
    """Get user's shopping cart with currency conversion."""
    from core.cart import get_cart_manager
    
    try:
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)
        
        db = get_database()
        db_user = await db.get_user_by_telegram_id(user.id)
        user_language = (db_user.language_code if db_user else None) or user.language_code
        
        return await _format_cart_response(cart, db, user_language)
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to get cart: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cart: {str(e)}")


@router.post("/cart/add")
async def add_to_cart(request: AddToCartRequest, user=Depends(verify_telegram_auth)):
    """Add item to cart (with instant/prepaid split)."""
    from core.cart import get_cart_manager
    
    db = get_database()
    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    _ensure_product_orderable(product)
    
    available_stock = await db.get_available_stock_count(request.product_id)
    
    cart_manager = get_cart_manager()
    try:
        await cart_manager.add_item(
            user_telegram_id=user.id,
            product_id=request.product_id,
            product_name=product.name,
            quantity=request.quantity,
            available_stock=available_stock,
            unit_price=product.price,
            discount_percent=0.0
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"ERROR: Failed to add to cart: {e}")
        raise HTTPException(status_code=500, detail="Failed to add item to cart")
    
    cart = await cart_manager.get_cart(user.id)
    db_user = await db.get_user_by_telegram_id(user.id)
    user_language = (db_user.language_code if db_user else None) or user.language_code
    return await _format_cart_response(cart, db, user_language)


@router.patch("/cart/item")
async def update_cart_item(request: UpdateCartItemRequest, user=Depends(verify_telegram_auth)):
    """Update cart item quantity (0 = remove)."""
    from core.cart import get_cart_manager
    
    db = get_database()
    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    _ensure_product_orderable(product)
    
    available_stock = await db.get_available_stock_count(request.product_id)
    
    cart_manager = get_cart_manager()
    try:
        await cart_manager.update_item_quantity(
            user_telegram_id=user.id,
            product_id=request.product_id,
            new_quantity=request.quantity,
            available_stock=available_stock
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"ERROR: Failed to update cart item: {e}")
        raise HTTPException(status_code=500, detail="Failed to update cart item")
    
    cart = await cart_manager.get_cart(user.id)
    db_user = await db.get_user_by_telegram_id(user.id)
    user_language = (db_user.language_code if db_user else None) or user.language_code
    return await _format_cart_response(cart, db, user_language)


@router.delete("/cart/item")
async def remove_cart_item(product_id: str, user=Depends(verify_telegram_auth)):
    """Remove item from cart."""
    from core.cart import get_cart_manager
    
    cart_manager = get_cart_manager()
    try:
        await cart_manager.remove_item(user.id, product_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"ERROR: Failed to remove cart item: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove cart item")
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    user_language = (db_user.language_code if db_user else None) or user.language_code
    cart = await cart_manager.get_cart(user.id)
    return await _format_cart_response(cart, db, user_language)


@router.post("/cart/promo/apply")
async def apply_cart_promo(request: ApplyPromoRequest, user=Depends(verify_telegram_auth)):
    """Apply promo code to cart."""
    from core.cart import get_cart_manager
    
    db = get_database()
    code = request.code.strip().upper()
    promo = await db.validate_promo_code(code)
    if not promo:
        raise HTTPException(status_code=400, detail="Invalid or expired promo code")
    
    cart_manager = get_cart_manager()
    cart = await cart_manager.apply_promo_code(user.id, code, promo["discount_percent"])
    if cart is None:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    db_user = await db.get_user_by_telegram_id(user.id)
    user_language = (db_user.language_code if db_user else None) or user.language_code
    return await _format_cart_response(cart, db, user_language)


@router.post("/cart/promo/remove")
async def remove_cart_promo(user=Depends(verify_telegram_auth)):
    """Remove promo code from cart."""
    from core.cart import get_cart_manager
    
    cart_manager = get_cart_manager()
    cart = await cart_manager.remove_promo_code(user.id)
    if cart is None:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    user_language = (db_user.language_code if db_user else None) or user.language_code
    return await _format_cart_response(cart, db, user_language)
