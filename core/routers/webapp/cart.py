"""
WebApp Cart Router

Shopping cart endpoints with unified currency handling.

Response format:
- All amounts include both USD value and display value
- Frontend uses USD for calculations, display for UI
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from core.logging import get_logger
from core.services.database import get_database
from core.services.currency_response import CurrencyFormatter
from core.services.money import to_float
from core.auth import verify_telegram_auth
from core.db import get_redis
from .models import AddToCartRequest, UpdateCartItemRequest, ApplyPromoRequest

logger = get_logger(__name__)

router = APIRouter(tags=["webapp-cart"])


async def _format_cart_response(cart, db, user_telegram_id: int):
    """
    Build cart response with unified currency handling.
    
    Response includes:
    - *_usd fields: values in USD for calculations
    - * fields: values in user's currency for display
    - currency: user's preferred currency
    - exchange_rate: for frontend fallback conversion
    """
    redis = get_redis()
    formatter = await CurrencyFormatter.create(user_telegram_id, db, redis)
    
    if not cart:
        return {
            "cart": None,
            "items": [],
            # USD values (for calculations)
            "total_usd": 0.0,
            "subtotal_usd": 0.0,
            "instant_total_usd": 0.0,
            "prepaid_total_usd": 0.0,
            # Display values (for UI)
            "total": 0.0,
            "subtotal": 0.0,
            "instant_total": 0.0,
            "prepaid_total": 0.0,
            # Promo
            "promo_code": None,
            "promo_discount_percent": 0.0,
            "original_total_usd": 0.0,
            "original_total": 0.0,
            # Currency info
            "currency": formatter.currency,
            "exchange_rate": formatter.exchange_rate,
        }
    
    # Fetch all products in parallel
    products = await asyncio.gather(*[db.get_product_by_id(item.product_id) for item in cart.items])
    
    items_with_details = []
    for item, product in zip(cart.items, products):
        # USD values (base)
        unit_price_usd = to_float(item.unit_price)
        final_price_usd = to_float(item.final_price)
        total_price_usd = to_float(item.total_price)
        
        items_with_details.append({
            "product_id": item.product_id,
            "product_name": product.name if product else "Unknown",
            "image_url": product.image_url if product else None,
            "quantity": item.quantity,
            "instant_quantity": item.instant_quantity,
            "prepaid_quantity": item.prepaid_quantity,
            "discount_percent": item.discount_percent,
            # USD values (for calculations)
            "unit_price_usd": unit_price_usd,
            "final_price_usd": final_price_usd,
            "total_price_usd": total_price_usd,
            # Display values (for UI)
            "unit_price": formatter.convert(unit_price_usd),
            "final_price": formatter.convert(final_price_usd),
            "total_price": formatter.convert(total_price_usd),
            # Currency (for this item)
            "currency": formatter.currency,
        })
    
    # Calculate original total (before promo) if promo applied
    original_total_usd = to_float(cart.subtotal) if cart.promo_code else to_float(cart.total)
    
    return {
        "cart": {
            "user_telegram_id": cart.user_telegram_id,
            "created_at": cart.created_at,
            "updated_at": cart.updated_at,
        },
        "items": items_with_details,
        # USD values (for calculations)
        "total_usd": to_float(cart.total),
        "subtotal_usd": to_float(cart.subtotal),
        "instant_total_usd": to_float(cart.instant_total),
        "prepaid_total_usd": to_float(cart.prepaid_total),
        "original_total_usd": original_total_usd,
        # Display values (for UI)
        "total": formatter.convert(cart.total),
        "subtotal": formatter.convert(cart.subtotal),
        "instant_total": formatter.convert(cart.instant_total),
        "prepaid_total": formatter.convert(cart.prepaid_total),
        "original_total": formatter.convert(original_total_usd),
        # Promo
        "promo_code": cart.promo_code,
        "promo_discount_percent": cart.promo_discount_percent,
        # Currency info (for frontend)
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
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
        
        return await _format_cart_response(cart, db, user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cart: {e}", exc_info=True)
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
        logger.error(f"Failed to add to cart: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add item to cart")
    
    cart = await cart_manager.get_cart(user.id)
    return await _format_cart_response(cart, db, user.id)


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
        logger.error(f"Failed to update cart item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update cart item")
    
    cart = await cart_manager.get_cart(user.id)
    return await _format_cart_response(cart, db, user.id)


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
        logger.error(f"Failed to remove cart item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove cart item")
    
    db = get_database()
    cart = await cart_manager.get_cart(user.id)
    return await _format_cart_response(cart, db, user.id)


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
    
    return await _format_cart_response(cart, db, user.id)


@router.post("/cart/promo/remove")
async def remove_cart_promo(user=Depends(verify_telegram_auth)):
    """Remove promo code from cart."""
    from core.cart import get_cart_manager
    
    cart_manager = get_cart_manager()
    cart = await cart_manager.remove_promo_code(user.id)
    if cart is None:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    db = get_database()
    return await _format_cart_response(cart, db, user.id)
